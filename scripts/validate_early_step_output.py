#!/usr/bin/env python3
"""Validate structured Step 1, Step 2, or Step 3 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


STEP1_SCORE_AXES = ["originality", "importance", "feasibility", "literature_support", "method_readiness"]
STEP2_REQUIRED = ["section_id", "section_title", "section_function", "key_claims", "evidence_needed", "do_not_write"]
STEP3_REQUIRED = ["id", "rq_id", "chapter_id", "evidence_type", "question_to_answer", "query_blocks", "route", "tier"]
STEP3_TOP_REQUIRED = [
    "plan_mode", "execution_context", "retrieval_language", "source_scope",
    "publication_year_range", "document_types", "inclusion_criteria",
    "exclusion_criteria", "deduplication_plan", "query_versions", "search_update_policy",
]
STEP3_SOURCES = {
    "openalex", "crossref", "semantic_scholar", "semantic_scholar_bulk",
    "arxiv", "pubmed", "cnki", "wanfang",
}
CALIBRATION_STATUSES = {"executed", "user_supplied", "unavailable"}
KEYWORD_ORIGINS = {"user", "topic", "corpus", "controlled_vocabulary"}
KEYWORD_ACTIONS = {"keep", "qualify", "expand", "exclude"}


def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    payload = yaml.safe_load(parts[1])
    return payload if isinstance(payload, dict) else {}


def _nonempty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _validate_calibration(value: object, prefix: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{prefix} is required"]
    errors = []
    status = value.get("status")
    if status not in CALIBRATION_STATUSES:
        errors.append(f"{prefix}.status must be executed, user_supplied, or unavailable")
    if not _nonempty(value.get("sources_attempted")):
        errors.append(f"{prefix}.sources_attempted is required")
    if not _nonempty(value.get("queries")):
        errors.append(f"{prefix}.queries is required")
    if status in {"executed", "user_supplied"}:
        records = value.get("representative_records")
        if not isinstance(records, list) or len(records) < 2:
            errors.append(f"{prefix}.representative_records must contain at least 2 records")
        else:
            for index, record in enumerate(records):
                if not isinstance(record, dict) or not _nonempty(record.get("title")):
                    errors.append(f"{prefix}.representative_records[{index}].title is required")
                if not isinstance(record, dict) or not _nonempty(record.get("doi") or record.get("source_id")):
                    errors.append(f"{prefix}.representative_records[{index}] needs doi or source_id")
    if status == "unavailable" and not _nonempty(value.get("limitations")):
        errors.append(f"{prefix}.limitations is required when calibration is unavailable")
    return errors


def _validate_keyword_audit(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["keyword_audit must contain at least one audited term"]
    errors = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"keyword_audit[{index}] must be an object")
            continue
        if not _nonempty(item.get("term")):
            errors.append(f"keyword_audit[{index}].term is required")
        if item.get("origin") not in KEYWORD_ORIGINS:
            errors.append(f"keyword_audit[{index}].origin is invalid")
        observed = item.get("observed_in_records")
        if not isinstance(observed, int) or isinstance(observed, bool) or observed < 0:
            errors.append(f"keyword_audit[{index}].observed_in_records must be a non-negative integer")
        if item.get("ambiguity") not in {"none", "low", "high"}:
            errors.append(f"keyword_audit[{index}].ambiguity is invalid")
        if item.get("action") not in KEYWORD_ACTIONS:
            errors.append(f"keyword_audit[{index}].action is invalid")
    return errors


def validate_step1(path: Path) -> list[str]:
    data = _frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    errors = []
    topic = data.get("topic") if isinstance(data.get("topic"), dict) else {}
    interaction = data.get("interaction_record") if isinstance(data.get("interaction_record"), dict) else {}
    if interaction.get("answer_burden") != "minimal":
        errors.append("interaction_record.answer_burden must be minimal")
    for field in ["user_supplied", "inferred", "assumed", "unresolved_blocking", "unresolved_nonblocking"]:
        if not isinstance(interaction.get(field), list):
            errors.append(f"interaction_record.{field} must be a list")
    errors.extend(_validate_calibration(data.get("evidence_calibration"), "evidence_calibration"))
    for field in ["focused_topic", "primary_rq", "scope_boundaries", "evaluation_metrics"]:
        if not _nonempty(topic.get(field)):
            errors.append(f"topic.{field} is required")
    if len(topic.get("evaluation_metrics") or []) < 3:
        errors.append("topic.evaluation_metrics must contain at least 3 measurable metrics")
    for field in ["working_hypothesis", "falsification_condition", "minimum_viable_study", "topic_kill_criteria"]:
        if not _nonempty(topic.get(field)):
            errors.append(f"topic.{field} is required")

    pre = data.get("pre_review") if isinstance(data.get("pre_review"), dict) else {}
    scores = []
    for axis in STEP1_SCORE_AXES:
        record = pre.get(axis)
        if not isinstance(record, dict):
            errors.append(f"pre_review.{axis} is required")
            continue
        score = record.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 5:
            errors.append(f"pre_review.{axis}.score must be 0-5")
        else:
            scores.append(score)
        if not _nonempty(record.get("reason")):
            errors.append(f"pre_review.{axis}.reason is required")
    fatal_axes = {"feasibility", "method_readiness"}
    fatal_signal = False
    for axis in STEP1_SCORE_AXES:
        record = pre.get(axis)
        if not isinstance(record, dict):
            continue
        score = record.get("score")
        signal = record.get("signal")
        if signal is not None:
            if signal not in {"green", "yellow", "red"}:
                errors.append(f"pre_review.{axis}.signal must be green, yellow, or red")
            elif isinstance(score, (int, float)) and not isinstance(score, bool):
                expected_signal = "green" if score >= 4 else "yellow" if score >= 2 else "red"
                if signal != expected_signal:
                    errors.append(
                        f"pre_review.{axis}.signal must be {expected_signal} for score={score}"
                    )
            if axis in fatal_axes and signal == "red":
                fatal_signal = True
    fatal_risks = pre.get("fatal_risks") or []
    if not isinstance(fatal_risks, list):
        errors.append("pre_review.fatal_risks must be a list")
        fatal_risks = []
    if len(scores) == len(STEP1_SCORE_AXES):
        total = sum(scores)
        if pre.get("total_score") != total:
            errors.append(f"pre_review.total_score must equal {total}")
        expected = (
            "red"
            if fatal_signal or fatal_risks
            else "green"
            if total >= 21
            else "yellow"
            if total >= 15
            else "red"
        )
        if pre.get("decision") != expected:
            reason = "fatal axis/risk precedence" if fatal_signal or fatal_risks else f"total_score={total}"
            errors.append(f"pre_review.decision must be {expected} for {reason}")
    return errors


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_step2(path: Path) -> list[str]:
    payload = _json(path)
    sections = payload if isinstance(payload, list) else payload.get("sections", []) if isinstance(payload, dict) else []
    if not isinstance(sections, list) or not sections:
        return ["section_blueprints must contain a non-empty section list"]
    errors = []
    if isinstance(payload, dict):
        if payload.get("outline_state") not in {"outline_baseline", "search_calibrated", "evidence_validated"}:
            errors.append("outline_state must be outline_baseline, search_calibrated, or evidence_validated")
        errors.extend(_validate_calibration(payload.get("evidence_calibration"), "evidence_calibration"))
        errors.extend(_validate_keyword_audit(payload.get("keyword_audit")))
    seen = set()
    rq_coverage = set()
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"sections[{index}] must be an object")
            continue
        for field in STEP2_REQUIRED:
            if not _nonempty(section.get(field)):
                errors.append(f"sections[{index}].{field} is required")
        section_id = str(section.get("section_id") or "")
        if section_id in seen:
            errors.append(f"duplicate section_id: {section_id}")
        seen.add(section_id)
        rq_ids = section.get("rq_ids") or []
        if not rq_ids and section.get("section_function") not in {"conclusion-and-outlook", "front-matter"}:
            errors.append(f"sections[{index}].rq_ids is required for traceability")
        rq_coverage.update(str(item) for item in rq_ids)
    required_rqs = payload.get("core_research_question_ids", []) if isinstance(payload, dict) else []
    for rq_id in required_rqs:
        if str(rq_id) not in rq_coverage:
            errors.append(f"research question is not mapped to any section: {rq_id}")
    return errors


def validate_step3(path: Path) -> list[str]:
    payload = _json(path)
    tasks = payload.get("search_tasks", []) if isinstance(payload, dict) else []
    if not isinstance(tasks, list) or not tasks:
        return ["search_tasks must be a non-empty list"]
    errors = []
    for field in STEP3_TOP_REQUIRED:
        if not _nonempty(payload.get(field)):
            errors.append(f"{field} is required")
    if payload.get("plan_mode") not in {"standard", "deep", "systematic"}:
        errors.append("plan_mode must be standard, deep, or systematic")
    if payload.get("execution_context") not in {"step3_planning", "step4_direct_entry"}:
        errors.append("execution_context must be step3_planning or step4_direct_entry")
    if payload.get("retrieval_language") not in {"zh", "en", "mixed"}:
        errors.append("retrieval_language must be zh, en, or mixed")
    if "plan_state" in payload and payload.get("plan_state") not in {
        "compiled", "pilot_verified", "offline_unverified",
    }:
        errors.append("plan_state must be compiled, pilot_verified, or offline_unverified")
    if "base_workflow" in payload and payload.get("base_workflow") not in {"standard", "systematic"}:
        errors.append("base_workflow must be standard or systematic")
    if "addons" in payload:
        addons = payload.get("addons")
        allowed_addons = {"citation-expansion", "prisma-s", "chinese-sources"}
        if not isinstance(addons, list) or any(item not in allowed_addons for item in addons):
            errors.append("addons must contain only citation-expansion, prisma-s, or chinese-sources")
        elif len(addons) != len(set(addons)):
            errors.append("addons must not contain duplicates")
    if payload.get("plan_mode") == "systematic" and payload.get("base_workflow") not in {None, "systematic"}:
        errors.append("systematic plan_mode requires base_workflow=systematic")
    include = {str(item).strip().lower() for item in payload.get("inclusion_criteria", []) if str(item).strip()}
    exclude = {str(item).strip().lower() for item in payload.get("exclusion_criteria", []) if str(item).strip()}
    overlap = sorted(include & exclude)
    if overlap:
        errors.append("inclusion/exclusion criteria conflict: " + ", ".join(overlap))
    if payload.get("plan_mode") == "systematic":
        protocol = payload.get("review_protocol") if isinstance(payload.get("review_protocol"), dict) else {}
        for field in ["databases", "platforms", "search_dates", "full_strategies", "controlled_vocabulary", "supplementary_sources", "press_review"]:
            if not _nonempty(protocol.get(field)):
                errors.append(f"review_protocol.{field} is required for systematic mode")
    seen = set()
    rq_coverage = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"search_tasks[{index}] must be an object")
            continue
        for field in STEP3_REQUIRED:
            if not _nonempty(task.get(field)):
                errors.append(f"search_tasks[{index}].{field} is required")
        task_id = str(task.get("id") or "")
        if task_id in seen:
            errors.append(f"duplicate search task id: {task_id}")
        seen.add(task_id)
        rq_coverage.add(str(task.get("rq_id") or ""))
        if task.get("tier") not in {"quick", "standard", "deep"}:
            errors.append(f"search_tasks[{index}].tier is invalid")
        if task.get("framework") not in {"concept_block", "pico", "peo", "methods_focused", "pcc", "spider"}:
            errors.append(f"search_tasks[{index}].framework is invalid")
        route = task.get("route") if isinstance(task.get("route"), dict) else {}
        sources = [str(source).strip().lower() for level in ("l1", "l2", "l3") for source in route.get(level, []) or []]
        if not sources:
            errors.append(f"search_tasks[{index}].route needs at least one source")
        for source in sources:
            if source not in STEP3_SOURCES:
                errors.append(f"search_tasks[{index}].route contains unsupported source: {source}")
        blocks = task.get("query_blocks") or []
        if len(blocks) > 4:
            errors.append(f"search_tasks[{index}] has more than 4 AND blocks")
        for block_index, block in enumerate(blocks):
            terms = block.get("terms", []) if isinstance(block, dict) else []
            if len({str(term).strip().lower() for term in terms if str(term).strip()}) < 2 and not _nonempty(block.get("single_canonical_term_reason") if isinstance(block, dict) else None):
                errors.append(f"search_tasks[{index}].query_blocks[{block_index}] needs at least 2 unique terms")
    for rq_id in payload.get("core_research_question_ids", []) or []:
        if str(rq_id) not in rq_coverage:
            errors.append(f"research question is not mapped to any search task: {rq_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Step 1/2/3 structured output.")
    parser.add_argument("step", choices=["step1", "step2", "step3"])
    parser.add_argument("artifact")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    validators = {"step1": validate_step1, "step2": validate_step2, "step3": validate_step3}
    errors = validators[args.step](Path(args.artifact))
    payload = {"step": args.step, "status": "pass" if not errors else "fail", "errors": errors}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{args.step.upper()}_VALIDATION: {payload['status']}")
        for error in errors:
            print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
