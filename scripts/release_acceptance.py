from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixed_env(mplconfig: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MPLBACKEND"] = "Agg"
    if mplconfig is not None:
        mplconfig.mkdir(parents=True, exist_ok=True)
        env["MPLCONFIGDIR"] = str(mplconfig)
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "1"
    return env


def run_step(
    name: str,
    cmd: list[str],
    *,
    timeout: int = 180,
    mplconfig: Path | None = None,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=fixed_env(mplconfig),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "name": name,
            "status": "failed",
            "returncode": None,
            "failure_type": "timeout",
            "timeout_seconds": timeout,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }
    result = {
        "name": name,
        "status": "pass" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
    }
    if completed.returncode != 0:
        result["stdout"] = completed.stdout.strip()
        result["stderr"] = completed.stderr.strip()
    return result


def parse_environment_failure(result: dict[str, Any]) -> list[str]:
    if result.get("name") != "environment_preflight" or result.get("status") != "failed":
        return []
    try:
        payload = json.loads(result.get("stdout") or "{}")
    except json.JSONDecodeError:
        return []
    missing = payload.get("missing_required")
    return [str(item) for item in missing] if isinstance(missing, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scientific figure release acceptance for more-paper-workflow.")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    version_match = re.search(r"^version:\s*([^\s(]+)", skill_text, flags=re.MULTILINE)
    version = version_match.group(1) if version_match else "unknown"
    checks: dict[str, str] = {}
    details: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="more-paper-figure-release-") as tmp:
        workspace = Path(tmp)
        zip_path = workspace / "more-paper-workflow.zip"
        baseline = workspace / "baseline"
        bundle = workspace / "bundle"
        mplconfig = workspace / "mplconfig"
        spec = ROOT / "examples" / "line_plot" / "visualspec_v2.json"

        steps = [
            ("environment_preflight", [sys.executable, str(SCRIPTS / "check_environment.py")]),
            ("root_package", [sys.executable, str(SCRIPTS / "validate_skill_package.py"), "--root", str(ROOT)]),
            ("digitization_contract", [sys.executable, str(ROOT / "tests" / "test_figure_evidence_pipeline.py")]),
            ("build_zip", [sys.executable, str(SCRIPTS / "build_skill_package.py"), "--root", str(ROOT), "--out", str(zip_path)]),
            ("zip_package", [sys.executable, str(SCRIPTS / "validate_skill_package.py"), "--root", str(ROOT), "--zip", str(zip_path)]),
            ("render_baseline", [sys.executable, str(SCRIPTS / "render_matplotlib.py"), "--spec", str(spec), "--out-dir", str(baseline)]),
            ("run_reproduction", [sys.executable, str(SCRIPTS / "run_reproduction.py"), "--spec", str(spec), "--source", str(baseline / "render.png"), "--out-dir", str(bundle), "--require-strict", "--transform-authorization", "explicit_user_request"]),
            ("bundle_verify", [sys.executable, str(bundle / "verify.py")]),
            ("portability", [sys.executable, str(SCRIPTS / "validate_portability.py"), "--root", str(bundle)]),
        ]
        for name, cmd in steps:
            result = run_step(name, cmd, timeout=240, mplconfig=mplconfig)
            details[name] = result
            checks[name] = result["status"]
            if result["status"] != "pass":
                break

        manifest_path = bundle / "reproduction_manifest.json"
        if manifest_path.exists():
            manifest = load_json(manifest_path)
            checks["official_example"] = str(manifest.get("status"))
        else:
            checks["official_example"] = "missing_manifest"

    status = "pass" if all(value in {"pass", "semantic_strict_pass"} for value in checks.values()) and checks.get("official_example") == "semantic_strict_pass" else "failed"
    failed_steps = [
        name
        for name, value in checks.items()
        if value not in {"pass", "semantic_strict_pass"}
    ]
    environment_result = details.get("environment_preflight", {})
    missing_dependencies = parse_environment_failure(environment_result)
    report = {
        "schema": "morepaper.figure_release_acceptance.v1",
        "version": version,
        "status": status,
        "checks": checks,
        "details": details,
        "failure_stage": failed_steps[0] if failed_steps else None,
        "failure_type": (
            "missing_dependency"
            if missing_dependencies
            else (
                str(details.get(failed_steps[0], {}).get("failure_type", "step_failed"))
                if failed_steps
                else None
            )
        ),
        "missing_dependencies": missing_dependencies,
    }
    output = args.json_out or ROOT / "release_acceptance.json"
    write_json(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
