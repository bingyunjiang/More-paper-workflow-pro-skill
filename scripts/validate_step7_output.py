#!/usr/bin/env python3
"""Validate the Step 7 writing artifact chain.

This checks whether a Step 7 output directory has the minimum runtime
artifacts before a draft is treated as complete. It also enforces citation
and figure-format floor rules, but does not judge prose quality.
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
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


MECHANISM_TERMS = [
    "机理",
    "机制",
    "受力",
    "变形特征",
    "影响规律",
    "演化规律",
    "作用路径",
    "耦合",
    "mechanism",
    "mechanistic",
    "causal pathway",
    "coupling",
]

DRAFT_PATTERNS = [
    "*draft*.md",
    "*初稿*.md",
    "*草稿*.md",
    "论文*.md",
    "journal_paper*.md",
    "section_*draft*.md",
]

ZOTERO_KEY_RE = re.compile(r"\b[A-Z0-9]{8}\b")
NUMBERED_DEPTH_RE = re.compile(r"\[\d+\](?:[，,、;；\s]*（已读(?:全文|摘要)|（仅元数据）)")
AUTHOR_YEAR_DEPTH_RE = re.compile(
    r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z .·&-]{0,40}"
    r"(?:等|和[\u4e00-\u9fffA-Za-z .·&-]{1,30}|et al\.)?"
    r"[（(](?:19|20)\d{2}[）)](?:（已读(?:全文|摘要)|（仅元数据）)"
)
FIGURE_MARKER_RE = re.compile(r"(\[\[FIGURE:[^\]]+\]\]|!\[[^\]]*\]\([^)]+\))")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
REVIEWER_SCORE_THRESHOLDS = {
    "originality": 3,
    "importance": 3,
    "technical_soundness": 4,
    "evidence_adequacy": 4,
    "readability_structure": 3,
}


@dataclass
class Finding:
    severity: str
    code: str
    message: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _exists_any(root: Path, names: list[str], patterns: list[str] | None = None) -> bool:
    for name in names:
        if (root / name).exists():
            return True
    for pattern in patterns or []:
        if any(root.glob(pattern)):
            return True
    return False


def _find_drafts(root: Path) -> list[Path]:
    drafts: list[Path] = []
    seen: set[Path] = set()
    excluded = {
        "citation_audit.md",
        "引用审计报告.md",
        "draft_risk_summary.md",
        "step7_execution_card.md",
        "evidence_matrix.md",
        "journal_evidence_matrix.md",
    }
    for pattern in DRAFT_PATTERNS:
        for path in root.glob(pattern):
            if path.name in excluded:
                continue
            if path not in seen and path.is_file():
                seen.add(path)
                drafts.append(path)
    return sorted(drafts)


def _load_json(path: Path) -> object | None:
    try:
        return json.loads(_read_text(path))
    except Exception:
        return None


def _execution_card_text(root: Path) -> str:
    card = root / "step7_execution_card.md"
    return _read_text(card) if card.exists() else ""


def _risk_boundary_present(root: Path, card_text: str) -> bool:
    if (root / "draft_risk_summary.md").exists() or (root / "draft_risk_summary.json").exists():
        return True
    return bool(re.search(
        r"(?:risk_status|citation_risk|evidence_gaps?|risk_boundary)\s*[:=]\s*\S+",
        card_text,
        flags=re.IGNORECASE,
    ))


def _mechanism_decision(root: Path, card_text: str) -> str:
    for path in [
        root / "mechanism_trigger_decision.json",
        root / "mechanism_trigger_decision.md",
    ]:
        if not path.exists():
            continue
        if path.suffix == ".json":
            payload = _load_json(path)
            if isinstance(payload, dict):
                decision = payload.get("decision") or payload.get("mechanism_trigger_decision")
                if isinstance(decision, str):
                    return decision
        text = _read_text(path)
        match = re.search(r"(enter_mechanism_analysis|skip_mechanism_analysis)", text)
        if match:
            return match.group(1)
    match = re.search(r"(enter_mechanism_analysis|skip_mechanism_analysis)", card_text)
    return match.group(1) if match else ""


def _figure_mode_present(root: Path, card_text: str) -> bool:
    if (root / "figure_asset_check.md").exists() or (root / "figure_asset_check.json").exists():
        return True
    risk = root / "draft_risk_summary.md"
    texts = [card_text]
    if risk.exists():
        texts.append(_read_text(risk))
    return any(re.search(r"figure_mode\s*[:=]\s*(auto_insert|post_write|skip)", text) for text in texts)


def _figure_mode(root: Path, card_text: str) -> str:
    asset_payload = _load_json(root / "figure_asset_check.json")
    if isinstance(asset_payload, dict) and asset_payload.get("figure_mode") in {
        "auto_insert",
        "post_write",
        "skip",
    }:
        return str(asset_payload["figure_mode"])
    texts = [card_text]
    for name in ["figure_asset_check.md", "draft_risk_summary.md"]:
        path = root / name
        if path.exists():
            texts.append(_read_text(path))
    for text in texts:
        match = re.search(r"figure_mode\s*[:=]\s*(auto_insert|post_write|skip)", text)
        if match:
            return match.group(1)
    return ""


def _figure_backend(root: Path, card_text: str) -> str:
    asset_payload = _load_json(root / "figure_asset_check.json")
    if isinstance(asset_payload, dict) and asset_payload.get("figure_backend") in {
        "auto",
        "quick",
        "reproduction",
        "not_applicable",
    }:
        return str(asset_payload["figure_backend"])
    texts = [card_text]
    for name in ["figure_asset_check.md", "draft_risk_summary.md"]:
        path = root / name
        if path.exists():
            texts.append(_read_text(path))
    for text in texts:
        match = re.search(r"figure_backend\s*[:=]\s*(auto|quick|reproduction|not_applicable)", text)
        if match:
            return match.group(1)
    return ""


def _validate_figure_evidence_report(
    root: Path,
    *,
    figure_backend: str,
    require_evidence_closure: bool,
) -> list[Finding]:
    path = root / "figure_evidence_report.json"
    if figure_backend == "reproduction" and not path.exists():
        return [Finding("fail", "missing_figure_evidence_report", "reproduction backend requires figure_evidence_report.json")]
    if not path.exists():
        return []
    payload = _load_json(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != "figure-evidence.v1":
        return [Finding("fail", "invalid_figure_evidence_report", "figure_evidence_report.json has an invalid schema")]
    records = payload.get("records")
    if not isinstance(records, list):
        return [Finding("fail", "invalid_figure_evidence_records", "figure evidence records must be a list")]

    findings: list[Finding] = []
    required = {
        "generation_backend", "visualspec_path", "reproduction_bundle", "manifest_path",
        "reproduction_status", "qa_profile", "verification_status",
    }
    complete_statuses = {"semantic_strict_pass", "semantic_validated_pass", "semantic_near_pass"}
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            findings.append(Finding("fail", "invalid_figure_evidence_record", f"figure record {index} is not an object"))
            continue
        if record.get("generation_backend") != "reproduction":
            continue
        asset_action = str(record.get("figure_asset_action") or "")
        transform_authorization = str(
            record.get("figure_transform_authorization") or ""
        )
        if asset_action not in {"redraw", "digitize"}:
            findings.append(
                Finding(
                    "fail",
                    "reproduction_without_transform_action",
                    f"figure record {index} uses reproduction without redraw/digitize action",
                )
            )
        if transform_authorization != "explicit_user_request":
            findings.append(
                Finding(
                    "fail",
                    "figure_transform_not_explicitly_authorized",
                    f"figure record {index} lacks explicit user authorization for redraw/digitize",
                )
            )
        missing = sorted(field for field in required if not record.get(field))
        if missing:
            findings.append(Finding("fail", "incomplete_reproduction_record", f"figure record {index} lacks {', '.join(missing)}"))
            continue
        status = str(record.get("reproduction_status"))
        if require_evidence_closure and status not in complete_statuses:
            findings.append(Finding("fail", "figure_reproduction_not_complete", f"figure record {index} has non-complete status {status}"))
        elif not require_evidence_closure and status not in complete_statuses:
            findings.append(Finding("warn", "figure_reproduction_not_complete", f"figure record {index} remains {status}"))
        if require_evidence_closure and record.get("verification_status") != "pass":
            findings.append(Finding("fail", "figure_bundle_not_verified", f"figure record {index} bundle verification did not pass"))
        if status == "semantic_near_pass" and not record.get("figure_risk_note"):
            findings.append(Finding("fail", "missing_figure_deviation", f"figure record {index} is near-pass but has no deviation note"))
        extraction_status = str(record.get("extraction_status") or "")
        if extraction_status:
            extraction_required = {"extraction_project_path", "extraction_report_path"}
            extraction_missing = sorted(
                field for field in extraction_required if not record.get(field)
            )
            if extraction_missing:
                findings.append(
                    Finding(
                        "fail",
                        "incomplete_digitization_record",
                        f"figure record {index} lacks {', '.join(extraction_missing)}",
                    )
                )
            if extraction_status == "formal_data_ready":
                formal_required = {
                    "review_decisions_path",
                    "observations_path",
                    "data_path",
                    "data_sha256",
                    "visualspec_data_sha256",
                }
                formal_missing = sorted(field for field in formal_required if not record.get(field))
                if formal_missing:
                    findings.append(
                        Finding(
                            "fail",
                            "incomplete_formal_data_record",
                            f"figure record {index} lacks {', '.join(formal_missing)}",
                        )
                    )
                if record.get("review_status") != "complete":
                    findings.append(
                        Finding(
                            "fail",
                            "digitization_review_incomplete",
                            f"figure record {index} lacks complete review_status",
                        )
                    )
                if record.get("data_sha256") != record.get("visualspec_data_sha256"):
                    findings.append(
                        Finding(
                            "fail",
                            "visualspec_formal_data_hash_mismatch",
                            f"figure record {index} VisualSpec is not bound to formal data.csv",
                        )
                    )
                if record.get("value_delivery_authorized") is not True:
                    findings.append(
                        Finding(
                            "fail",
                            "digitized_values_not_authorized",
                            f"figure record {index} has formal data without value delivery authorization",
                        )
                    )
            elif record.get("value_delivery_authorized") is True:
                findings.append(
                    Finding(
                        "fail",
                        "digitization_status_authorization_conflict",
                        f"figure record {index} authorizes candidate/not-reviewed values with extraction status {extraction_status}",
                    )
                )
            elif require_evidence_closure:
                findings.append(
                    Finding(
                        "fail",
                        "digitization_not_complete",
                        f"figure record {index} has non-formal extraction status {extraction_status}",
                    )
                )
            else:
                findings.append(
                    Finding(
                        "warn",
                        "digitization_not_complete",
                        f"figure record {index} remains {extraction_status}",
                    )
                )
    return findings


def _figure_assets_available(root: Path) -> bool:
    json_path = root / "figure_asset_check.json"
    payload = _load_json(json_path) if json_path.exists() else None
    if isinstance(payload, dict) and payload.get("original_assets_available") is True:
        return True
    texts: list[str] = []
    for name in ["figure_asset_check.md", "figure_asset_check.json", "step7_execution_card.md"]:
        path = root / name
        if path.exists():
            texts.append(_read_text(path))
    combined = "\n".join(texts).lower()
    if not combined:
        return False
    return any(token in combined for token in [
        "mineru zip",
        "mineru_zip",
        "llm-for-zotero-mineru-cache",
        "figure_index: available",
        "local_figures: available",
    ])


def _has_figure_index(root: Path) -> bool:
    json_path = root / "figure_index.json"
    if json_path.exists():
        payload = _load_json(json_path)
        return bool(
            isinstance(payload, dict)
            and isinstance(payload.get("records"), list)
            and payload["records"]
        )
    return (root / "figure_index.md").exists()


def _has_figure_marker(text: str) -> bool:
    return bool(FIGURE_MARKER_RE.search(text))


def _validate_inserted_images(drafts: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for draft in drafts:
        text = _read_text(draft)
        for reference in MARKDOWN_IMAGE_RE.findall(text):
            clean = reference.strip().strip("<>")
            if re.match(r"^(?:https?|data):", clean, flags=re.IGNORECASE):
                continue
            image_path = (draft.parent / clean).resolve()
            if not image_path.is_file():
                findings.append(
                    Finding(
                        "fail",
                        "missing_inserted_image",
                        f"{draft.name} references missing image {clean}",
                    )
                )
                continue
            try:
                with Image.open(image_path) as image:
                    image.verify()
            except Exception:
                findings.append(
                    Finding(
                        "fail",
                        "invalid_inserted_image",
                        f"{draft.name} references an unreadable image {clean}",
                    )
                )
    return findings


def _validate_original_figure_provenance(
    root: Path,
    draft_hash: str,
) -> list[Finding]:
    report_path = root / "figure_resolution_report.json"
    evidence_path = root / "figure_evidence_report.json"
    findings: list[Finding] = []
    report = _load_json(report_path)
    if not isinstance(report, dict):
        return [
            Finding(
                "fail",
                "missing_figure_resolution_report",
                "ready_for_step8 requires figure_resolution_report.json",
            )
        ]
    if report.get("output_sha256") != draft_hash:
        findings.append(
            Finding(
                "fail",
                "stale_figure_resolution_report",
                "figure resolution report does not match the current draft",
            )
        )
    if report.get("unresolved_count", 0) > 0:
        findings.append(
            Finding(
                "fail",
                "unresolved_figure_matches",
                "figure resolution report contains unresolved matches",
            )
        )
    records = report.get("records")
    if not isinstance(records, list) or not records:
        findings.append(
            Finding(
                "fail",
                "missing_figure_resolution_records",
                "figure resolution report has no resolved provenance records",
            )
        )
    else:
        for index, record in enumerate(records, 1):
            if not isinstance(record, dict) or record.get("status") != "resolved":
                continue
            for field in (
                "source_image_path",
                "local_image_path",
                "source_image_sha256",
                "materialized_sha256",
            ):
                if not record.get(field):
                    findings.append(
                        Finding(
                            "fail",
                            "incomplete_original_figure_provenance",
                            f"figure resolution record {index} lacks {field}",
                        )
                    )
    evidence = _load_json(evidence_path)
    if not isinstance(evidence, dict) or evidence.get("schema_version") != "figure-evidence.v1":
        findings.append(
            Finding(
                "fail",
                "missing_original_figure_evidence_report",
                "ready_for_step8 requires a valid figure_evidence_report.json",
            )
        )
    return findings


def _strip_internal_sections(text: str) -> str:
    stop_markers = [
        "\n## 参考文献",
        "\n# 参考文献",
        "\n## Reference",
        "\n# Reference",
        "\n## 证据",
        "\n# Evidence",
    ]
    body = text
    for marker in stop_markers:
        index = body.find(marker)
        if index >= 0:
            body = body[:index]
    return body


def _strip_figure_markers(text: str) -> str:
    return FIGURE_MARKER_RE.sub("", text)


def _zotero_keys_in_body(text: str) -> list[str]:
    body = _strip_figure_markers(_strip_internal_sections(text))
    return sorted(set(ZOTERO_KEY_RE.findall(body)))


def _has_submission_style_citation(text: str) -> bool:
    body = _strip_internal_sections(text)
    return bool(NUMBERED_DEPTH_RE.search(body) or AUTHOR_YEAR_DEPTH_RE.search(body))


def _contains_mechanism_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in MECHANISM_TERMS)


def _draft_sha256(drafts: list[Path]) -> str:
    combined = "\n".join(_read_text(path) for path in drafts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _target_state(card_text: str, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    match = re.search(r"(?:target_state|completion_target)\s*[:=]\s*(draft_ready|evidence_closed|ready_for_step8)", card_text)
    return match.group(1) if match else "draft_ready"


def _validate_reviewer_scorecard(root: Path, draft_sha256: str, require_freshness: bool) -> list[Finding]:
    path = root / "reviewer_scorecard.json"
    if not path.exists():
        return [Finding("fail", "missing_reviewer_scorecard", "draft exists but reviewer_scorecard.json is missing")]
    payload = _load_json(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != "reviewer-scorecard.v1":
        return [Finding("fail", "invalid_reviewer_scorecard", "reviewer_scorecard.json has an invalid schema")]

    findings: list[Finding] = []
    scorecard_hash = payload.get("draft_sha256")
    if require_freshness and scorecard_hash != draft_sha256:
        findings.append(Finding("fail", "stale_reviewer_scorecard", "reviewer scorecard is not bound to the current draft_sha256"))
    elif scorecard_hash and scorecard_hash != draft_sha256:
        findings.append(Finding("warn", "stale_reviewer_scorecard", "reviewer scorecard hash differs from the current draft"))
    boundary = payload.get("assessment_boundary")
    if not isinstance(boundary, str) or not boundary.strip():
        findings.append(Finding("fail", "missing_review_assessment_boundary", "review scorecard lacks assessment_boundary"))
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        return findings + [Finding("fail", "invalid_reviewer_scores", "reviewer scorecard scores must be an object")]

    for axis, threshold in REVIEWER_SCORE_THRESHOLDS.items():
        record = scores.get(axis)
        if not isinstance(record, dict):
            findings.append(Finding("fail", f"missing_reviewer_axis_{axis}", f"reviewer scorecard lacks {axis}"))
            continue
        score = record.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
            findings.append(Finding("fail", f"invalid_reviewer_score_{axis}", f"{axis} score must be between 1 and 5"))
        elif score < threshold:
            findings.append(Finding("fail", f"reviewer_score_below_gate_{axis}", f"{axis} score {score} is below {threshold}"))
        locations = record.get("evidence_locations")
        if not isinstance(locations, list) or not any(str(item).strip() for item in locations):
            findings.append(Finding("fail", f"missing_reviewer_evidence_{axis}", f"{axis} lacks evidence_locations"))
        if not isinstance(record.get("reason"), str) or not record["reason"].strip():
            findings.append(Finding("fail", f"missing_reviewer_reason_{axis}", f"{axis} lacks a scoring reason"))

    critical = payload.get("critical_issues")
    if not isinstance(critical, list):
        findings.append(Finding("fail", "invalid_reviewer_critical_issues", "critical_issues must be a list"))
    elif critical:
        findings.append(Finding("fail", "reviewer_critical_issues_open", f"{len(critical)} CRITICAL reviewer issue(s) remain open"))
    return findings


def _validate_claim_evidence_audit(root: Path, draft_sha256: str) -> tuple[list[Finding], dict[str, object]]:
    path = root / "claim_evidence_audit.json"
    if not path.exists():
        return [Finding("fail", "missing_claim_evidence_audit", "claim_evidence_audit.json is required for evidence closure")], {}
    payload = _load_json(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != "claim-evidence-audit.v1":
        return [Finding("fail", "invalid_claim_evidence_audit", "claim_evidence_audit.json has an invalid schema")], {}
    findings: list[Finding] = []
    if payload.get("draft_sha256") != draft_sha256:
        findings.append(Finding("fail", "stale_claim_evidence_audit", "claim evidence audit does not match the current draft"))
    records = payload.get("records")
    if not isinstance(records, list):
        return findings + [Finding("fail", "invalid_claim_evidence_records", "claim evidence records must be a list")], payload
    required_fields = {
        "claim_segment_id", "claim_text", "claim_strength", "required_evidence", "support_grade",
        "reading_depth", "evidence_anchor", "downgrade_required", "recommended_action", "resolution_status",
    }
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            findings.append(Finding("fail", "invalid_claim_evidence_record", f"claim record {index} is not an object"))
            continue
        missing = sorted(field for field in required_fields if field not in record)
        if missing:
            findings.append(Finding("fail", "incomplete_claim_evidence_record", f"claim record {index} lacks {', '.join(missing)}"))
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    unresolved = summary.get("unresolved_count")
    if not isinstance(unresolved, int):
        findings.append(Finding("fail", "missing_claim_unresolved_count", "claim audit summary lacks unresolved_count"))
    elif unresolved > 0:
        findings.append(Finding("fail", "unresolved_claim_evidence", f"{unresolved} claim evidence issue(s) remain unresolved"))
    return findings, payload


def validate(root: Path, target_state: str = "auto") -> tuple[list[Finding], dict[str, object]]:
    findings: list[Finding] = []
    drafts = _find_drafts(root)
    card_text = _execution_card_text(root)
    combined_draft_text = "\n".join(_read_text(path) for path in drafts)
    draft_hash = _draft_sha256(drafts) if drafts else ""
    requested_state = _target_state(card_text, target_state)
    require_evidence_closure = requested_state in {"evidence_closed", "ready_for_step8"}
    task_text = "\n".join([card_text, combined_draft_text])
    mechanism_task = _contains_mechanism_terms(task_text)
    decision = _mechanism_decision(root, card_text)

    if drafts and not (root / "step7_execution_card.md").exists():
        findings.append(Finding("fail", "missing_execution_card", "draft exists but step7_execution_card.md is missing"))
    if drafts and not _risk_boundary_present(root, card_text):
        findings.append(Finding(
            "fail",
            "missing_draft_risk_boundary",
            "draft_ready requires a risk_status/citation_risk/evidence_gap boundary or draft_risk_summary artifact",
        ))

    if drafts and require_evidence_closure:
        findings.extend(_validate_reviewer_scorecard(root, draft_hash, require_evidence_closure))

    if drafts and require_evidence_closure and not _exists_any(
        root,
        ["evidence_matrix.md", "综述矩阵.md", "deep_read_cards.md", "evidence_pack.json"],
        ["*evidence_matrix*.md", "*deep_read_cards*.json", "*deep_read_cards*.md"],
    ):
        findings.append(Finding("fail", "missing_evidence_mapping", "draft exists but no evidence matrix, deep_read_cards, or evidence_pack was found"))

    if drafts and require_evidence_closure and not _exists_any(
        root,
        ["citation_audit.md", "引用审计报告.md", "claim_evidence_audit.md", "claim_evidence_audit.json"],
        ["*citation*audit*.md", "*引用审计*.md", "*claim*evidence*audit*.md", "*claim*evidence*audit*.json"],
    ):
        findings.append(Finding("fail", "missing_citation_audit", "draft exists but citation/claim evidence audit is missing"))

    claim_audit: dict[str, object] = {}
    if drafts and require_evidence_closure:
        claim_findings, claim_audit = _validate_claim_evidence_audit(root, draft_hash)
        findings.extend(claim_findings)

    if drafts and not _figure_mode_present(root, card_text):
        findings.append(Finding("fail", "missing_figure_gate", "draft exists but figure_asset_check or explicit figure_mode is missing"))

    figure_mode = _figure_mode(root, card_text)
    figure_backend = _figure_backend(root, card_text)
    figure_assets_available = _figure_assets_available(root)
    if drafts:
        findings.extend(_validate_figure_evidence_report(
            root,
            figure_backend=figure_backend,
            require_evidence_closure=require_evidence_closure,
        ))
    if drafts and figure_assets_available and figure_mode in {"auto_insert", "post_write"}:
        if not _has_figure_index(root):
            findings.append(Finding("fail", "missing_figure_index", "figure assets are available but figure_index.json/md is missing or empty"))
        if not _has_figure_marker(combined_draft_text):
            findings.append(Finding("fail", "missing_figure_marker", "figure assets are available but draft has no image path or [[FIGURE:...]] marker"))
        if requested_state == "ready_for_step8":
            findings.extend(_validate_original_figure_provenance(root, draft_hash))

    if drafts:
        findings.extend(_validate_inserted_images(drafts))

    if drafts:
        zotero_keys = _zotero_keys_in_body(combined_draft_text)
        if zotero_keys:
            findings.append(Finding(
                "fail",
                "raw_zotero_key_citations",
                "draft body contains raw Zotero keys used like citations: " + ", ".join(zotero_keys[:8]),
            ))
        if require_evidence_closure and not _has_submission_style_citation(combined_draft_text):
            findings.append(Finding(
                "fail",
                "missing_submission_style_citations",
                "draft body lacks [n]（已读全文） or 作者（年份）（已读全文） style citations",
            ))
        elif not require_evidence_closure and not _has_submission_style_citation(combined_draft_text):
            findings.append(Finding(
                "warn",
                "draft_without_submission_style_citations",
                "draft_ready may continue without closed citations, but citation safety has not been established",
            ))

    if mechanism_task and not decision:
        findings.append(Finding("fail", "missing_mechanism_decision", "mechanism-like task detected but mechanism_trigger_decision is missing"))

    if mechanism_task and decision == "enter_mechanism_analysis":
        required = [
            ("mechanism_cards", ["mechanism_cards.md", "mechanism_cards.json"]),
            ("mechanism_argument_plan", ["mechanism_argument_plan.md", "mechanism_argument_plan.json"]),
            ("mechanism_claim_audit", ["mechanism_claim_audit.md", "mechanism_claim_audit.json"]),
        ]
        for code, names in required:
            if not _exists_any(root, names):
                findings.append(Finding("fail", f"missing_{code}", f"mechanism task entered analysis but {code} is missing"))

    has_failures = any(item.severity == "fail" for item in findings)
    completion_state = "blocked" if has_failures else requested_state
    summary = {
        "root": str(root),
        "draft_count": len(drafts),
        "mechanism_task_detected": mechanism_task,
        "mechanism_decision": decision,
        "figure_mode": figure_mode,
        "figure_backend": figure_backend,
        "figure_assets_available": figure_assets_available,
        "draft_sha256": draft_hash,
        "target_state": requested_state,
        "completion_state": completion_state,
        "claim_audit_present": bool(claim_audit),
        "status": "pass" if not has_failures else "fail",
    }
    return findings, summary


def render(findings: list[Finding], summary: dict[str, object]) -> str:
    lines = [
        f"STEP7_VALIDATION: {summary['status']}",
        f"root: {summary['root']}",
        f"draft_count: {summary['draft_count']}",
        f"mechanism_task_detected: {summary['mechanism_task_detected']}",
        f"mechanism_decision: {summary['mechanism_decision'] or '-'}",
        f"figure_mode: {summary['figure_mode'] or '-'}",
        f"figure_backend: {summary['figure_backend'] or '-'}",
        f"figure_assets_available: {summary['figure_assets_available']}",
        f"target_state: {summary['target_state']}",
        f"completion_state: {summary['completion_state']}",
        f"draft_sha256: {summary['draft_sha256'] or '-'}",
    ]
    for item in findings:
        lines.append(f"{item.severity.upper()}: {item.code}: {item.message}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Step 7 output artifacts before treating a draft as complete.")
    parser.add_argument("output_dir", help="Step 7 output directory")
    parser.add_argument("--target-state", choices=("auto", "draft_ready", "evidence_closed", "ready_for_step8"), default="auto")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    root = Path(args.output_dir).expanduser().resolve()
    findings, summary = validate(root, args.target_state)
    if args.json:
        print(json.dumps({
            "summary": summary,
            "findings": [item.__dict__ for item in findings],
        }, ensure_ascii=False, indent=2))
    else:
        print(render(findings, summary))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
