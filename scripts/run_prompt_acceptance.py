#!/usr/bin/env python3
"""Judge captured host responses against reproducible prompt acceptance cases."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "prompt_acceptance.json"
EXPECTED_LANGUAGES = {"zh", "en"}
EXPECTED_STEPS = {
    "step1-topic",
    "step2-outline",
    "step3-search-plan",
    "step4-search-execute",
    "step5-download",
    "step6-zotero",
    "step7-writing",
    "step8-polishing",
}


def load_cases(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("case file must contain a JSON object")
    return payload


def validate_case_file(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "prompt-acceptance.v1":
        errors.append("schema_version must be prompt-acceptance.v1")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        return errors + ["cases must be a list"]
    ids: set[str] = set()
    coverage: set[tuple[str, str]] = set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = str(case.get("id", ""))
        if not case_id:
            errors.append(f"{prefix}.id is required")
        elif case_id in ids:
            errors.append(f"duplicate case id: {case_id}")
        ids.add(case_id)
        language = str(case.get("language", ""))
        step = str(case.get("expected_step", ""))
        if language not in EXPECTED_LANGUAGES:
            errors.append(f"{case_id}.language is invalid")
        if step not in EXPECTED_STEPS:
            errors.append(f"{case_id}.expected_step is invalid")
        coverage.add((language, step))
        if not str(case.get("prompt", "")).strip():
            errors.append(f"{case_id}.prompt is required")
        for field in ("required_all", "required_any", "forbidden"):
            if not isinstance(case.get(field), list):
                errors.append(f"{case_id}.{field} must be a list")
    expected_coverage = {
        (language, step)
        for language in EXPECTED_LANGUAGES
        for step in EXPECTED_STEPS
    }
    if coverage != expected_coverage:
        missing = sorted(expected_coverage - coverage)
        extra = sorted(coverage - expected_coverage)
        errors.append(f"case coverage mismatch: missing={missing}, extra={extra}")
    return errors


def find_case(payload: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in payload.get("cases", []):
        if isinstance(case, dict) and case.get("id") == case_id:
            return case
    raise KeyError(f"unknown case id: {case_id}")


def judge_response(case: dict[str, Any], response: str) -> list[str]:
    failures: list[str] = []
    normalized = response.casefold()
    for token in case.get("required_all", []):
        if str(token).casefold() not in normalized:
            failures.append(f"missing_required:{token}")
    for alternatives in case.get("required_any", []):
        if not isinstance(alternatives, list) or not alternatives:
            failures.append("invalid_required_any_group")
            continue
        if not any(str(token).casefold() in normalized for token in alternatives):
            failures.append(f"missing_any:{'|'.join(map(str, alternatives))}")
    for token in case.get("forbidden", []):
        if str(token).casefold() in normalized:
            failures.append(f"forbidden_claim:{token}")
    return failures


def current_commit(root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def build_report(
    payload: dict[str, Any],
    case: dict[str, Any],
    host: str,
    response_paths: list[Path],
    commit: str,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for index, path in enumerate(response_paths, 1):
        response = path.read_text(encoding="utf-8")
        failures = judge_response(case, response)
        runs.append({
            "run": index,
            "response_path": str(path),
            "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
            "raw_response": response,
            "status": "pass" if not failures else "failed",
            "failures": failures,
        })
    pass_count = sum(run["status"] == "pass" for run in runs)
    return {
        "schema_version": "prompt-acceptance-report.v1",
        "case_schema_version": payload.get("schema_version"),
        "case_id": case["id"],
        "language": case["language"],
        "expected_step": case["expected_step"],
        "host": host,
        "commit": commit,
        "baseline_commit": payload.get("baseline_commit"),
        "run_count": len(runs),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(runs) if runs else 0.0,
        "consistent": bool(runs) and pass_count in {0, len(runs)},
        "status": "pass" if runs and pass_count == len(runs) else "failed",
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate prompt cases or judge captured host responses.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--validate-cases", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--case")
    parser.add_argument("--host", default="unspecified")
    parser.add_argument("--response", type=Path, action="append", default=[])
    parser.add_argument("--commit")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        payload = load_cases(args.cases)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    errors = validate_case_file(payload)
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, ensure_ascii=False, indent=2))
        return 2
    if args.list:
        for case in payload["cases"]:
            print(f"{case['id']}\t{case['language']}\t{case['expected_step']}\t{case['prompt']}")
        return 0
    if args.validate_cases and not args.case:
        print(json.dumps({
            "status": "pass",
            "schema_version": payload["schema_version"],
            "case_count": len(payload["cases"]),
        }, ensure_ascii=False, indent=2))
        return 0
    if not args.case or not args.response:
        parser.error("--case and at least one --response are required unless using --validate-cases or --list")

    try:
        case = find_case(payload, args.case)
        report = build_report(
            payload,
            case,
            args.host,
            args.response,
            args.commit or current_commit(),
        )
    except (KeyError, OSError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
