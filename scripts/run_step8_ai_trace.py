#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Step 8 AI-trace runner.

Wires draft -> deterministic diagnostics -> diagnostic_summary block ->
revision_ledger merge into one local command for Step 8.

Usage:
  python3 run_step8_ai_trace.py --project-root .
  python3 run_step8_ai_trace.py --project-root . --draft 指定章节草稿.md --lang en
"""
from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from deterministic_writing_diagnostics import (
    diagnose_text,
    merge_into_revision_ledger,
    render_diagnostic_summary_section,
)
from audit_polish_fidelity import audit_fidelity, render_markdown as render_fidelity_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 8 AI-trace diagnostics with default artifact names.")
    parser.add_argument("--project-root", default=".", help="Project directory to operate on.")
    parser.add_argument("--draft", default="论文初稿.md", help="Draft path relative to project root or absolute path.")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="Draft language for deterministic diagnostics.")
    parser.add_argument(
        "--diagnostics-json",
        default=".skill-state/ai_trace_diagnostics.json",
        help="Where to write raw diagnostics JSON.",
    )
    parser.add_argument(
        "--diagnostic-summary",
        default="diagnostic_summary.md",
        help="Where to write or update the Step 8 diagnostic summary.",
    )
    parser.add_argument(
        "--revision-ledger",
        default="revision_ledger.json",
        help="Where to write or update the merged revision ledger JSON.",
    )
    parser.add_argument(
        "--revision-ledger-md",
        default="revision_ledger.md",
        help="Where to write the human-readable revision ledger Markdown.",
    )
    parser.add_argument(
        "--polish-quality-report",
        default="润色质量报告.md",
        help="Where to write or update the polish quality report.",
    )
    parser.add_argument("--polished-draft", default="论文润色稿.md", help="Polished draft to verify when it exists.")
    parser.add_argument("--fidelity-json", default="polish_fidelity_audit.json")
    parser.add_argument("--fidelity-md", default="polish_fidelity_audit.md")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the final shared readiness is blocked.",
    )
    return parser.parse_args()


def _resolve(project_root: Path, candidate: str) -> Path:
    path = Path(candidate).expanduser()
    if path.is_absolute():
        return path
    return project_root / path


def _atomic_write_text(path: Path, text: str) -> None:
    """Write Step 8 state in-place and atomically replace the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _replace_or_append_section(existing: str, heading: str, section_body: str) -> str:
    if heading not in existing:
        existing = existing.rstrip()
        spacer = "\n\n" if existing else ""
        return f"{existing}{spacer}{section_body}".strip() + "\n"

    lines = existing.splitlines()
    new_lines: list[str] = []
    in_target = False
    replaced = False
    section_lines = section_body.rstrip().splitlines()
    for line in lines:
        if line.strip() == heading:
            if not replaced:
                new_lines.extend(section_lines)
                replaced = True
            in_target = True
            continue
        if in_target and line.startswith("## "):
            in_target = False
            new_lines.append(line)
            continue
        if not in_target:
            new_lines.append(line)
    return "\n".join(new_lines).rstrip() + "\n"


def _compute_step8_decision(payload: dict) -> dict:
    summary = payload["summary"]
    structure_rollbacks = summary.get("structure_material_rollback_count", 0)
    citation_rollbacks = summary.get("citation_evidence_rollback_count", 0)
    direct_fix_count = summary.get("direct_fix_count", 0)
    manual_review_count = summary.get("manual_review_count", 0)
    issue_count = summary.get("issue_count", 0)

    if structure_rollbacks > 0:
        return {
            "overall_status": "not_ready_requires_rollback",
            "next_action": "return_to_step_4_or_6",
            "decision_reason": "存在结构/资料缺口回退项，Step 8 不应在证据底座缺失时继续硬修。",
        }
    if citation_rollbacks > 0:
        return {
            "overall_status": "ready_with_warnings",
            "next_action": "return_to_step_7_citation_audit",
            "decision_reason": "存在引用/证据型回退项，正文可局部保留，但应先回到 Step 7 做引用审计或原文确认。",
        }
    if issue_count == 0:
        return {
            "overall_status": "ready_to_polish",
            "next_action": "apply_polish_and_verify",
            "decision_reason": "诊断未检测到高置信 AI 味/机械化表达问题，但尚未生成并验证润色稿。",
        }
    if manual_review_count == 0 and direct_fix_count == issue_count:
        return {
            "overall_status": "ready_to_polish",
            "next_action": "apply_polish_and_verify",
            "decision_reason": "仅存在可直接修订的轻量问题；完成实际修改和 before/after 保真验证后才能定稿。",
        }
    return {
        "overall_status": "ready_with_warnings",
        "next_action": "转人工复核",
        "decision_reason": "存在需作者决定或人工复核项，但未达到必须回退证据底座的程度。",
    }


def _compute_status_contract(payload: dict, step8_decision: dict) -> dict:
    summary = payload["summary"]
    overall_status = step8_decision["overall_status"]
    next_action = step8_decision["next_action"]

    if overall_status == "ready_for_finalize":
        return {
            "readiness": "complete",
            "can_continue": True,
            "blocking": [],
            "warnings": [],
            "recommended_next_step": "Step 8",
        }

    if overall_status == "ready_to_polish":
        return {
            "readiness": "partial",
            "can_continue": True,
            "blocking": [],
            "warnings": ["Step 8 诊断已完成，但润色稿和 before/after 保真验证尚未完成"],
            "recommended_next_step": "Step 8",
        }

    if overall_status == "not_ready_requires_rollback":
        blocking = []
        if summary.get("structure_material_rollback_count", 0) > 0:
            blocking.append("存在待补文献/图表/实验材料，占位提示尚未闭环")
        if next_action == "revise_polished_draft":
            blocking.append("before/after 保真审计失败，润色稿存在受保护内容或含义漂移")
        if next_action == "return_to_step_7_citation_audit":
            blocking.append("已提供的 Step 7 claim evidence audit 过期、无效或仍有未关闭问题")
        return {
            "readiness": "blocked",
            "can_continue": False,
            "blocking": blocking,
            "warnings": [],
            "recommended_next_step": (
                "Step 4/6"
                if next_action == "return_to_step_4_or_6"
                else "Step 8"
                if next_action == "revise_polished_draft"
                else "Step 7"
            ),
        }

    warnings: list[str] = []
    if summary.get("citation_evidence_rollback_count", 0) > 0:
        warnings.append("存在引用/证据型回退项，建议回到 Step 7 做引用审计或原文确认")
    if summary.get("manual_review_count", 0) > 0:
        warnings.append("存在需作者决定或人工复核项，当前仅建议带警告继续")
    if summary.get("issue_count", 0) > 0:
        warnings.append("仍有 AI 味/机械化表达问题待处理或待确认")

    recommended = "Step 8"
    if next_action == "return_to_step_7_citation_audit":
        recommended = "Step 7"
    elif next_action == "return_to_step_4_or_6":
        recommended = "Step 4/6"

    return {
        "readiness": "partial",
        "can_continue": True,
        "blocking": [],
        "warnings": warnings,
        "recommended_next_step": recommended,
    }


def _step7_evidence_gate(project_root: Path, draft_text: str) -> dict:
    path = project_root / "claim_evidence_audit.json"
    if not path.exists():
        return {
            "status": "not_provided",
            "blocking": False,
            "reason": "No structured Step 7 claim audit was provided; direct-entry polishing remains available.",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "blocking": True, "reason": "claim_evidence_audit.json is invalid"}
    expected_hash = hashlib.sha256(draft_text.encode("utf-8")).hexdigest()
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    unresolved = summary.get("unresolved_count")
    if payload.get("schema_version") != "claim-evidence-audit.v1":
        return {"status": "invalid", "blocking": True, "reason": "claim evidence audit schema is invalid"}
    if payload.get("draft_sha256") != expected_hash:
        return {"status": "stale", "blocking": True, "reason": "claim evidence audit does not match the Step 8 input draft"}
    if not isinstance(unresolved, int) or unresolved > 0:
        return {
            "status": "unresolved",
            "blocking": True,
            "unresolved_count": unresolved,
            "reason": "claim evidence audit still contains unresolved issues",
        }
    return {"status": "pass", "blocking": False, "unresolved_count": 0, "reason": "structured claim evidence audit is current and closed"}


def _apply_step7_evidence_gate(decision: dict, gate: dict) -> dict:
    if not gate.get("blocking"):
        return decision
    return {
        "overall_status": "not_ready_requires_rollback",
        "next_action": "return_to_step_7_citation_audit",
        "decision_reason": gate.get("reason", "Step 7 claim evidence audit requires repair."),
    }


def _compute_verified_decision(
    original_payload: dict,
    polished_payload: dict,
    fidelity_payload: dict,
    diagnostic_decision: dict,
) -> dict:
    if diagnostic_decision["next_action"] in {"return_to_step_4_or_6", "return_to_step_7_citation_audit"}:
        return diagnostic_decision
    fidelity_status = fidelity_payload["summary"]["status"]
    if fidelity_status == "fail":
        return {
            "overall_status": "not_ready_requires_rollback",
            "next_action": "revise_polished_draft",
            "decision_reason": "before/after 保真审计发现硬失败，必须回滚或人工确认相关修改。",
        }
    if fidelity_status == "warn":
        return {
            "overall_status": "ready_with_warnings",
            "next_action": "转人工复核",
            "decision_reason": "before/after 保真审计发现责任主体等语义风险，需人工确认。",
        }

    original_count = original_payload["summary"].get("issue_count", 0)
    polished_count = polished_payload["summary"].get("issue_count", 0)
    if polished_count == 0 or polished_count < original_count:
        return {
            "overall_status": "ready_for_finalize",
            "next_action": "finalize_polished_draft",
            "decision_reason": "润色稿已存在，before/after 保真审计通过，且机械化表达问题未回归。",
        }
    return {
        "overall_status": "ready_with_warnings",
        "next_action": "continue_polish_and_verify",
        "decision_reason": "保真审计通过，但润色稿中的机械化表达问题没有减少。",
    }


def _render_revision_ledger_md(ledger: dict) -> str:
    issues = ledger.get("issues", [])
    ai_summary = ledger.get("ai_trace_diagnostics", {}).get("summary", {})
    step8_decision = ledger.get("ai_trace_diagnostics", {}).get("step8_decision", {})
    status_contract = ledger.get("ai_trace_diagnostics", {}).get("status_contract", {})
    evidence_gate = ledger.get("ai_trace_diagnostics", {}).get("step7_evidence_gate", {})
    category_order = ["可直接修订", "需作者决定", "当前依据不足"]
    category_buckets = {name: [] for name in category_order}
    for issue in issues:
        category = issue.get("category", "需作者决定")
        category_buckets.setdefault(category, []).append(issue)
    lines = [
        "# revision_ledger",
        "",
        f"- issues: {len(issues)}",
        f"- direct_fix_count: {ai_summary.get('direct_fix_count', 0)}",
        f"- manual_review_count: {ai_summary.get('manual_review_count', 0)}",
        f"- overall_status: `{step8_decision.get('overall_status', '')}`",
        f"- next_action: `{step8_decision.get('next_action', '')}`",
        f"- readiness: `{status_contract.get('readiness', '')}`",
        f"- can_continue: `{status_contract.get('can_continue', '')}`",
        f"- recommended_next_step: `{status_contract.get('recommended_next_step', '')}`",
        f"- step7_evidence_gate: `{evidence_gate.get('status', 'not_provided')}`",
        "",
        "## Step 8 问题闭环摘要",
        "",
        "| issue_id | issue_type | severity | allowed_action | next_action | rule_family |",
        "|---|---|---|---|---|---|",
    ]
    for issue in issues:
        lines.append(
            "| {issue_id} | {issue_type} | {severity} | {allowed_action} | {next_action} | {rule_family} |".format(
                issue_id=issue.get("issue_id", ""),
                issue_type=issue.get("issue_type", ""),
                severity=issue.get("severity", ""),
                allowed_action=issue.get("allowed_action", ""),
                next_action=issue.get("next_action", ""),
                rule_family=issue.get("rule_family", ""),
            )
        )
    lines.extend(["", "## 问题分流", ""])
    for category in category_order:
        bucket = category_buckets.get(category, [])
        default_route = {
            "可直接修订": "保留修改",
            "需作者决定": "转人工复核",
            "当前依据不足": "return_to_step_7_citation_audit / return_to_step_4_or_6",
        }[category]
        lines.extend([f"### {category}", "", f"- count: {len(bucket)}", f"- default_next_action: `{default_route}`", ""])
        if not bucket:
            lines.append("- 无")
            lines.append("")
            continue
        if category == "当前依据不足":
            citation_evidence = [item for item in bucket if item.get("deficiency_kind") == "citation_evidence"]
            structure_material = [item for item in bucket if item.get("deficiency_kind") == "structure_material"]
            other = [item for item in bucket if item not in citation_evidence and item not in structure_material]
            subgroups = [
                ("#### 引用/证据型回退", citation_evidence),
                ("#### 结构/资料缺口回退", structure_material),
                ("#### 其他待判断缺口", other),
            ]
            for heading, subgroup in subgroups:
                lines.extend([heading, "", f"- count: {len(subgroup)}", ""])
                if not subgroup:
                    lines.extend(["- 无", ""])
                    continue
                for issue in subgroup:
                    lines.extend(
                        [
                            f"##### {issue.get('issue_id', '')}",
                            "",
                            f"- issue_type: `{issue.get('issue_type', '')}`",
                            f"- severity: `{issue.get('severity', '')}`",
                            f"- location: `{issue.get('location', '')}`",
                            f"- allowed_action: `{issue.get('allowed_action', '')}`",
                            f"- next_action: `{issue.get('next_action', '')}`",
                            f"- deficiency_kind: `{issue.get('deficiency_kind', '')}`",
                            f"- rule_family: `{issue.get('rule_family', '')}`",
                            f"- problem: {issue.get('problem', '')}",
                            f"- proposed_revision: {issue.get('proposed_revision', '')}",
                            f"- rule_examples: {', '.join(issue.get('rule_examples', [])) or '无'}",
                            "",
                        ]
                    )
            continue
        for issue in bucket:
            lines.extend(
                [
                    f"#### {issue.get('issue_id', '')}",
                    "",
                    f"- issue_type: `{issue.get('issue_type', '')}`",
                    f"- severity: `{issue.get('severity', '')}`",
                    f"- location: `{issue.get('location', '')}`",
                    f"- allowed_action: `{issue.get('allowed_action', '')}`",
                    f"- next_action: `{issue.get('next_action', '')}`",
                    f"- deficiency_kind: `{issue.get('deficiency_kind', '')}`",
                    f"- rule_family: `{issue.get('rule_family', '')}`",
                    f"- problem: {issue.get('problem', '')}",
                    f"- proposed_revision: {issue.get('proposed_revision', '')}",
                    f"- rule_examples: {', '.join(issue.get('rule_examples', [])) or '无'}",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def _render_polish_quality_report_section(
    payload: dict,
    decision: dict | None = None,
    status_contract: dict | None = None,
    fidelity_payload: dict | None = None,
    step7_evidence_gate: dict | None = None,
) -> str:
    summary = payload["summary"]
    decision = decision or _compute_step8_decision(payload)
    status_contract = status_contract or _compute_status_contract(payload, decision)
    lines = [
        "## AI 味检查结果",
        "",
        f"- 命中问题数：{summary['issue_count']}",
        f"- 已处理的高频机械表达候选：{summary['direct_fix_count']}",
        f"- 保留未改的风格性项：{max(summary['issue_count'] - summary['direct_fix_count'], 0)}",
        f"- 建议作者人工复核项：{summary['manual_review_count']}",
        f"- 引用/证据型回退数量：{summary['citation_evidence_rollback_count']}",
        f"- 结构/资料缺口回退数量：{summary['structure_material_rollback_count']}",
        f"- Overall Status：`{decision['overall_status']}`",
        f"- Next Action：`{decision['next_action']}`",
        "",
        "### 统一状态契约",
        f"- readiness：`{status_contract['readiness']}`",
        f"- can_continue：`{status_contract['can_continue']}`",
        f"- blocking：{status_contract['blocking'] or '[]'}",
        f"- warnings：{status_contract['warnings'] or '[]'}",
        f"- recommended_next_step：`{status_contract['recommended_next_step']}`",
        "",
        "### 说明",
        "- AI 味确定性检查只服务于润色诊断，不替代 Step 7 引用审计。",
        "- 风格类命中默认不触发 rollback；仅作为 Step 8 局部修订与人工复核分流依据。",
        f"- 判定理由：{decision['decision_reason']}",
    ]
    if fidelity_payload:
        fidelity = fidelity_payload["summary"]
        lines.extend([
            "",
            "### Before/After 保真审计",
            f"- status：`{fidelity['status']}`",
            f"- hard_failure_count：{fidelity['hard_failure_count']}",
            f"- warning_count：{fidelity['warning_count']}",
        ])
    if step7_evidence_gate:
        lines.extend([
            "",
            "### Step 7 证据风险继承",
            f"- status：`{step7_evidence_gate['status']}`",
            f"- blocking：`{step7_evidence_gate['blocking']}`",
            f"- reason：{step7_evidence_gate['reason']}",
        ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    draft_path = _resolve(project_root, args.draft)
    diagnostics_json = _resolve(project_root, args.diagnostics_json)
    diagnostic_summary = _resolve(project_root, args.diagnostic_summary)
    revision_ledger = _resolve(project_root, args.revision_ledger)
    revision_ledger_md = _resolve(project_root, args.revision_ledger_md)
    polish_quality_report = _resolve(project_root, args.polish_quality_report)
    polished_draft = _resolve(project_root, args.polished_draft)
    fidelity_json = _resolve(project_root, args.fidelity_json)
    fidelity_md = _resolve(project_root, args.fidelity_md)

    text = draft_path.read_text(encoding="utf-8")
    step7_evidence_gate = _step7_evidence_gate(project_root, text)
    payload = diagnose_text(text, lang=args.lang)
    step8_decision = _compute_step8_decision(payload)
    fidelity_payload = None
    if polished_draft.exists():
        polished_text = polished_draft.read_text(encoding="utf-8")
        polished_payload = diagnose_text(polished_text, lang=args.lang)
        fidelity_payload = audit_fidelity(text, polished_text)
        step8_decision = _compute_verified_decision(payload, polished_payload, fidelity_payload, step8_decision)
        _atomic_write_text(fidelity_json, json.dumps(fidelity_payload, ensure_ascii=False, indent=2) + "\n")
        _atomic_write_text(fidelity_md, render_fidelity_markdown(fidelity_payload))
    step8_decision = _apply_step7_evidence_gate(step8_decision, step7_evidence_gate)
    status_contract = _compute_status_contract(payload, step8_decision)

    diagnostics_json.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_payload = dict(payload)
    diagnostics_payload["step8_decision"] = step8_decision
    diagnostics_payload["status_contract"] = status_contract
    diagnostics_payload["step7_evidence_gate"] = step7_evidence_gate
    if fidelity_payload:
        diagnostics_payload["polish_fidelity"] = fidelity_payload["summary"]
    _atomic_write_text(diagnostics_json, json.dumps(diagnostics_payload, ensure_ascii=False, indent=2) + "\n")

    summary_block = render_diagnostic_summary_section(payload)
    summary_block += (
        "\n"
        "### Step 8 总判断\n"
        f"- Overall Status：`{step8_decision['overall_status']}`\n"
        f"- Next Action：`{step8_decision['next_action']}`\n"
        f"- 判定理由：{step8_decision['decision_reason']}\n"
        "\n"
        "### 统一状态契约\n"
        f"- readiness：`{status_contract['readiness']}`\n"
        f"- can_continue：`{status_contract['can_continue']}`\n"
        f"- blocking：{status_contract['blocking'] or '[]'}\n"
        f"- warnings：{status_contract['warnings'] or '[]'}\n"
        f"- recommended_next_step：`{status_contract['recommended_next_step']}`\n"
        "\n"
        "### Step 7 证据风险继承\n"
        f"- status：`{step7_evidence_gate['status']}`\n"
        f"- blocking：`{step7_evidence_gate['blocking']}`\n"
        f"- reason：{step7_evidence_gate['reason']}\n"
    )
    if diagnostic_summary.exists():
        current = diagnostic_summary.read_text(encoding="utf-8")
    else:
        current = "# diagnostic_summary\n"
    updated_summary = _replace_or_append_section(current, "## AI 味确定性检查摘要", summary_block)
    _atomic_write_text(diagnostic_summary, updated_summary)

    if revision_ledger.exists():
        existing_ledger = json.loads(revision_ledger.read_text(encoding="utf-8"))
    else:
        existing_ledger = {}
    merged_ledger = merge_into_revision_ledger(existing_ledger, payload)
    merged_ledger.setdefault("ai_trace_diagnostics", {})
    merged_ledger["ai_trace_diagnostics"]["step8_decision"] = step8_decision
    merged_ledger["ai_trace_diagnostics"]["status_contract"] = status_contract
    merged_ledger["ai_trace_diagnostics"]["step7_evidence_gate"] = step7_evidence_gate
    if fidelity_payload:
        merged_ledger["ai_trace_diagnostics"]["polish_fidelity"] = fidelity_payload["summary"]
    _atomic_write_text(revision_ledger, json.dumps(merged_ledger, ensure_ascii=False, indent=2) + "\n")
    _atomic_write_text(revision_ledger_md, _render_revision_ledger_md(merged_ledger))

    polish_block = _render_polish_quality_report_section(
        payload, step8_decision, status_contract, fidelity_payload, step7_evidence_gate
    )
    if polish_quality_report.exists():
        current_report = polish_quality_report.read_text(encoding="utf-8")
    else:
        current_report = "# 润色质量报告\n"
    updated_report = _replace_or_append_section(current_report, "## AI 味检查结果", polish_block)
    _atomic_write_text(polish_quality_report, updated_report)

    print(f"draft: {draft_path}")
    print(f"diagnostics_json: {diagnostics_json}")
    print(f"diagnostic_summary: {diagnostic_summary}")
    print(f"revision_ledger: {revision_ledger}")
    print(f"revision_ledger_md: {revision_ledger_md}")
    print(f"polish_quality_report: {polish_quality_report}")
    if fidelity_payload:
        print(f"fidelity_json: {fidelity_json}")
        print(f"fidelity_md: {fidelity_md}")
    if args.strict and status_contract["readiness"] == "blocked":
        print("strict_status: blocked")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
