#!/usr/bin/env python3
"""Validate mode-specific Step 6 Zotero planning and write artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from build_zotero_plan import ATTACHMENT_STATES, ITEM_STATES


@dataclass
class Finding:
    severity: str
    code: str
    message: str


def _read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def validate(root: Path, mode: str = "auto", profile: str = "auto") -> tuple[list[Finding], dict[str, object]]:
    findings: list[Finding] = []
    plan_path = root / "文献-Zotero架构对照.json"
    plan = _read_json(plan_path)
    if not isinstance(plan, dict) or plan.get("artifact_type") != "zotero_plan":
        findings.append(Finding("fail", "invalid_zotero_plan", "文献-Zotero架构对照.json is missing or invalid"))
        return findings, {"root": str(root), "status": "fail", "mode": mode, "execution_profile": profile}

    effective_mode = plan.get("execution_mode", "plan-only") if mode == "auto" else mode
    inferred_profile = "plan-only" if effective_mode in {"plan-only", "skip"} else "write"
    effective_profile = plan.get("execution_profile", inferred_profile) if profile == "auto" else profile
    if effective_mode not in {"plan-only", "local", "cloud", "skip"}:
        findings.append(Finding("fail", "invalid_execution_mode", f"unsupported execution mode: {effective_mode}"))
    if effective_profile not in {"plan-only", "write", "repair"}:
        findings.append(Finding("fail", "invalid_execution_profile", f"unsupported execution profile: {effective_profile}"))
    if effective_profile == "plan-only" and effective_mode not in {"plan-only", "skip"}:
        findings.append(Finding("fail", "profile_mode_conflict", "plan-only profile cannot use a write execution mode"))
    if effective_profile in {"write", "repair"} and effective_mode in {"plan-only", "skip"}:
        findings.append(Finding("fail", "profile_mode_conflict", f"{effective_profile} profile requires local or cloud execution mode"))
    records = plan.get("records") if isinstance(plan.get("records"), list) else []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            findings.append(Finding("fail", "invalid_record", f"record {index} is not an object"))
            continue
        if record.get("item_state") not in ITEM_STATES:
            findings.append(Finding("fail", "invalid_item_state", f"record {index} has invalid item_state"))
        if record.get("attachment_state") not in ATTACHMENT_STATES:
            findings.append(Finding("fail", "invalid_attachment_state", f"record {index} has invalid attachment_state"))

    pdf_index = _read_json(root / "pdf-附件池索引.json")
    if not isinstance(pdf_index, dict):
        findings.append(Finding("fail", "missing_pdf_index", "pdf-附件池索引.json is missing or invalid"))

    expected_item_counts = {state: sum(1 for record in records if record.get("item_state") == state) for state in sorted(ITEM_STATES)}
    expected_attachment_counts = {state: sum(1 for record in records if record.get("attachment_state") == state) for state in sorted(ATTACHMENT_STATES)}
    state_counts = plan.get("state_counts") if isinstance(plan.get("state_counts"), dict) else {}
    if state_counts.get("items") != expected_item_counts or state_counts.get("attachments") != expected_attachment_counts:
        findings.append(Finding("fail", "state_count_mismatch", "state_counts do not match records"))

    if effective_profile == "plan-only":
        if plan.get("blocking_missing") or not plan.get("can_continue") or plan.get("completion_state") != "plan_ready":
            findings.append(Finding("fail", "plan_not_ready", "plan-only output is not ready for review"))
    else:
        if not plan.get("cp_zotero_write_confirmed"):
            findings.append(Finding("fail", "missing_write_confirmation", "CP-ZOTERO-WRITE confirmation is missing"))
        if not plan.get("plan_fingerprint"):
            findings.append(Finding("fail", "missing_plan_fingerprint", "write mode requires plan_fingerprint"))
        state = _read_json(root / "zotero_execution_state.json")
        if not isinstance(state, dict) or not isinstance(state.get("operations"), dict):
            findings.append(Finding("fail", "missing_execution_state", "Zotero execution state is missing"))
            operations = {}
        else:
            operations = state["operations"]
            for operation_id, operation in operations.items():
                if not isinstance(operation, dict):
                    findings.append(Finding("fail", "invalid_execution_operation", f"operation {operation_id} is invalid"))
                    continue
                if not operation.get("operation_type") or not operation.get("target_id") or not operation.get("status"):
                    findings.append(Finding("fail", "incomplete_execution_operation", f"operation {operation_id} lacks required fields"))
                if plan.get("plan_fingerprint") and operation.get("plan_fingerprint") != plan.get("plan_fingerprint"):
                    findings.append(Finding("fail", "stale_execution_operation", f"operation {operation_id} belongs to a different plan"))
        if plan.get("completion_state") == "write_complete":
            open_item_states = {"planned", "duplicate_candidate", "metadata_conflict", "import_failed", "manual_confirmation_required"}
            open_attachment_states = {"unlinked_pdf", "duplicate_attachment", "invalid_attachment", "attachment_conflict", "manual_attach_required"}
            if any(record.get("item_state") in open_item_states for record in records):
                findings.append(Finding("fail", "open_item_states", "write_complete contains unresolved item states"))
            if any(record.get("attachment_state") in open_attachment_states for record in records):
                findings.append(Finding("fail", "open_attachment_states", "write_complete contains unresolved attachment states"))
            successful_targets = {
                str(operation.get("target_id")) for operation in operations.values()
                if isinstance(operation, dict) and operation.get("status") == "success"
            }
            required_targets = {
                str(record.get("record_id")) for record in records
                if record.get("item_state") not in {"rejected_do_not_import", "existing_confirmed"}
            }
            missing_targets = sorted(required_targets - successful_targets)
            if missing_targets:
                findings.append(Finding(
                    "fail", "records_without_successful_operation",
                    "write_complete lacks successful operations for: " + ", ".join(missing_targets[:12]),
                ))

            log_path = root / "zotero_write_operations.jsonl"
            if not log_path.exists():
                findings.append(Finding("fail", "missing_operation_log", "write_complete requires zotero_write_operations.jsonl"))
            else:
                seen_event_ids: set[str] = set()
                for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        findings.append(Finding("fail", "invalid_operation_log_row", f"operation log line {line_number} is invalid JSON"))
                        continue
                    event_id = str(event.get("event_id") or "")
                    if not event_id or event_id in seen_event_ids:
                        findings.append(Finding("fail", "invalid_operation_event_id", f"operation log line {line_number} has missing/duplicate event_id"))
                    seen_event_ids.add(event_id)

    status = "pass" if not any(item.severity == "fail" for item in findings) else "fail"
    return findings, {
        "root": str(root),
        "status": status,
        "mode": effective_mode,
        "execution_profile": effective_profile,
        "completion_state": plan.get("completion_state", ""),
        "record_count": len(records),
        "direct_entry": bool(plan.get("direct_entry")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Step 6 Zotero artifacts.")
    parser.add_argument("output_dir")
    parser.add_argument("--mode", choices=("auto", "plan-only", "local", "cloud", "skip"), default="auto")
    parser.add_argument("--profile", choices=("auto", "plan-only", "write", "repair"), default="auto")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    findings, summary = validate(Path(args.output_dir).expanduser().resolve(), args.mode, args.profile)
    if args.json:
        print(json.dumps({"summary": summary, "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    else:
        print(f"STEP6_VALIDATION: {summary['status']}")
        for item in findings:
            print(f"{item.severity.upper()}: {item.code}: {item.message}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
