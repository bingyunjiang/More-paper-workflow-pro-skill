#!/usr/bin/env python3
"""Compile Step 3 queries and evaluate optional pilot-search results."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from search_query_compilers import compile_source_query


ENGLISH_SOURCES = {"openalex", "crossref", "semantic_scholar", "semantic_scholar_bulk", "arxiv", "pubmed"}


def _quote(term: str) -> str:
    term = term.strip()
    return f'"{term}"' if " " in term else term


def _compile(blocks: list[dict], exclusions: list[str], source: str) -> str:
    return compile_source_query(blocks, exclusions, source)["query"]


def _sources(task: dict) -> list[str]:
    route = task.get("route") if isinstance(task.get("route"), dict) else {}
    values = []
    for level in ("l1", "l2", "l3"):
        for source in route.get(level, []) or []:
            normalized = str(source).strip().lower()
            if normalized and normalized not in values:
                values.append(normalized)
    return values


def _normalized_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower().replace("-", " ")).strip()


def _term_matches(term: str, text: str) -> bool:
    return _normalized_text(term) in text


def _pilot_metrics(task: dict, pilot: list[dict], seeds: list[dict]) -> dict:
    blocks = [block for block in task.get("query_blocks", []) if isinstance(block, dict)]
    required_indexes = [index for index, block in enumerate(blocks) if block.get("required", True)]
    record_checks = []
    block_match_counts = [0] * len(blocks)
    title_relevant = 0
    relevant = 0
    for record in pilot:
        title = _normalized_text(record.get("title"))
        combined = _normalized_text(" ".join([str(record.get("title") or ""), str(record.get("abstract") or "")]))
        title_hits = []
        combined_hits = []
        for index, block in enumerate(blocks):
            terms = [str(item) for item in block.get("terms", []) if str(item).strip()]
            title_hit = any(_term_matches(term, title) for term in terms)
            combined_hit = any(_term_matches(term, combined) for term in terms)
            title_hits.append(title_hit)
            combined_hits.append(combined_hit)
            if combined_hit:
                block_match_counts[index] += 1
        title_ok = all(title_hits[index] for index in required_indexes) if required_indexes else False
        combined_ok = all(combined_hits[index] for index in required_indexes) if required_indexes else False
        title_relevant += int(title_ok)
        relevant += int(combined_ok)
        record_checks.append({
            "record_id": record.get("record_id") or record.get("doi") or record.get("source_id") or record.get("title"),
            "required_blocks_matched": sum(combined_hits[index] for index in required_indexes),
            "required_blocks_total": len(required_indexes),
            "relevant": combined_ok,
        })

    hit_count = len(pilot)
    block_coverage = {
        str(block.get("name") or f"block_{index}"): round(block_match_counts[index] / hit_count, 3) if hit_count else 0.0
        for index, block in enumerate(blocks)
    }
    pilot_dois = {_normalized_text(record.get("doi")) for record in pilot if record.get("doi")}
    pilot_titles = {_normalized_text(record.get("title")) for record in pilot if record.get("title")}
    matched_seeds = []
    for seed in seeds:
        seed_id = seed.get("doi") or seed.get("source_id") or seed.get("title")
        if (_normalized_text(seed.get("doi")) in pilot_dois if seed.get("doi") else False) or (
            _normalized_text(seed.get("title")) in pilot_titles if seed.get("title") else False
        ):
            matched_seeds.append(seed_id)
    seed_recall = round(len(matched_seeds) / len(seeds), 3) if seeds else None
    return {
        "hit_count": hit_count,
        "title_relevance_ratio": round(title_relevant / hit_count, 3) if hit_count else 0.0,
        "title_abstract_precision_proxy": round(relevant / hit_count, 3) if hit_count else 0.0,
        "required_block_coverage": block_coverage,
        "record_checks": record_checks,
        "seed_count": len(seeds),
        "matched_seed_count": len(matched_seeds),
        "matched_seeds": matched_seeds,
        "seed_recall": seed_recall,
    }


def lint_and_compile(plan: dict, pilot_results: object | None = None) -> dict:
    tasks = plan.get("search_tasks", []) if isinstance(plan, dict) else []
    pilot_records = []
    if isinstance(pilot_results, list):
        pilot_records = [item for item in pilot_results if isinstance(item, dict)]
    elif isinstance(pilot_results, dict):
        pilot_records = [item for item in pilot_results.get("records", []) if isinstance(item, dict)]
    pilot_by_task: dict[str, list[dict]] = defaultdict(list)
    for record in pilot_records:
        pilot_by_task[str(record.get("search_task_id") or "")].append(record)

    outputs = []
    all_errors = 0
    for task in tasks:
        task_id = str(task.get("id") or "")
        # `entry_mode` used to carry lifecycle routing values in early plans.
        # Prefer the global `route_mode` axis while accepting that legacy alias.
        route_mode = str(
            task.get("route_mode")
            or plan.get("route_mode")
            or task.get("entry_mode")
            or plan.get("entry_mode")
            or "normal_chain"
        )
        execution_context = str(task.get("execution_context") or plan.get("execution_context") or "step3_planning")
        basis_origin = str(task.get("basis_origin") or plan.get("basis_origin") or (
            "step4_reconstructed" if execution_context == "step4_direct_entry"
            else "step3_reconstructed" if route_mode in {"direct_entry", "partial_artifact", "repair"}
            else "step2_handoff"
        ))
        blocks = task.get("query_blocks", []) if isinstance(task.get("query_blocks"), list) else []
        exclusions = [str(item).strip() for item in task.get("exclusion_terms", []) if str(item).strip()]
        errors = []
        warnings = []
        if len(blocks) > 4:
            errors.append("and_block_count_exceeds_4")
        positive_terms = []
        for index, block in enumerate(blocks):
            terms = [str(item).strip() for item in block.get("terms", []) if str(item).strip()] if isinstance(block, dict) else []
            normalized = [term.lower() for term in terms]
            positive_terms.extend(terms)
            canonical_reason = block.get("single_canonical_term_reason") if isinstance(block, dict) else None
            if len(set(normalized)) < 2 and not str(canonical_reason or "").strip():
                errors.append(f"block_{index}_needs_two_unique_terms")
            if len(normalized) != len(set(normalized)):
                warnings.append(f"block_{index}_duplicate_terms")
        collisions = sorted(set(term.lower() for term in positive_terms) & set(term.lower() for term in exclusions))
        if collisions:
            errors.append("exclusion_collision_with_positive:" + ",".join(collisions))

        compiled = {}
        source_compilation = {}
        for source in _sources(task):
            if source in ENGLISH_SOURCES and positive_terms and all(re.search(r"[\u4e00-\u9fff]", term) for term in positive_terms):
                errors.append(f"english_source_has_only_chinese_terms:{source}")
            result = compile_source_query(blocks, exclusions, source)
            compiled[source] = result["query"]
            source_compilation[source] = result
            if result["compile_status"] == "invalid":
                errors.append(f"source_compile_invalid:{source}")
            elif result["compile_status"] == "degraded":
                warnings.append(f"source_compile_degraded:{source}")
            elif result["compile_status"] == "manual_required":
                warnings.append(f"source_compile_manual_required:{source}")

        pilot = pilot_by_task.get(task_id, [])
        pilot_summary = {"status": "not_run", "hit_count": 0, "title_relevance_ratio": None}
        if pilot_results is not None:
            seeds = [item for item in task.get("known_relevant_records", plan.get("known_relevant_records", [])) if isinstance(item, dict)]
            metrics = _pilot_metrics(task, pilot, seeds)
            criteria = task.get("pilot_acceptance_criteria") if isinstance(task.get("pilot_acceptance_criteria"), dict) else {}
            min_precision = float(criteria.get("min_title_abstract_precision_proxy", criteria.get("min_precision_proxy", 0.5)))
            min_seed_recall = float(criteria.get("min_seed_recall", 0.8))
            required_names = [str(block.get("name") or f"block_{index}") for index, block in enumerate(blocks) if block.get("required", True)]
            dropped_blocks = [name for name in required_names if metrics["required_block_coverage"].get(name, 0) == 0]
            if not pilot:
                status = "zero-result"
            elif dropped_blocks:
                status = "concept_block_dropout"
            elif metrics["seed_recall"] is not None and metrics["seed_recall"] < min_seed_recall:
                status = "seed_miss"
            elif metrics["title_abstract_precision_proxy"] < min_precision:
                status = "low_precision"
            else:
                status = "ok"
            pilot_summary = {"status": status, **metrics, "dropped_required_blocks": dropped_blocks}
            if status != "ok":
                errors.append(f"pilot_{status}")

        all_errors += len(errors)
        repair_required = pilot_summary["status"] in {"zero-result", "concept_block_dropout", "seed_miss", "low_precision"}
        repair_actions = {
            "zero-result": ["expand_synonyms", "relax_one_concept_block", "check_source_route"],
            "concept_block_dropout": ["expand_dropped_block_terms", "check_field_strategy", "check_source_coverage"],
            "seed_miss": ["inspect_seed_vocabulary", "expand_synonyms", "check_year_language_document_filters"],
            "low_precision": ["qualify_ambiguous_terms", "tighten_object_or_context", "revise_exclusions"],
        }.get(pilot_summary["status"], [])
        outputs.append({
            "search_task_id": task_id,
            "execution_context": execution_context,
            "route_mode": route_mode,
            "basis_origin": basis_origin,
            "compiled_queries": compiled,
            "source_compilation": source_compilation,
            "lint_errors": errors,
            "lint_warnings": warnings,
            "pilot": pilot_summary,
            "repair": {
                "required": repair_required,
                "repair_location": ("step4" if execution_context == "step4_direct_entry" else "step3") if repair_required else "none",
                "requires_prior_step_rerun": False,
                "recommended_actions": repair_actions,
            },
        })
    return {
        "schema_version": "compiled-search-plan.v1",
        "summary": {"task_count": len(outputs), "error_count": all_errors, "status": "pass" if all_errors == 0 else "fail"},
        "tasks": outputs,
    }


def run_pilot(plan: dict, limit: int = 10, search_functions: dict | None = None) -> dict:
    if search_functions is None:
        from search_by_topic import SOURCE_FUNCTIONS

        search_functions = SOURCE_FUNCTIONS
    records = []
    errors = []
    for task in plan.get("search_tasks", []) if isinstance(plan, dict) else []:
        task_id = str(task.get("id") or "")
        sources = _sources(task)
        if not sources:
            errors.append({"search_task_id": task_id, "error": "no_routed_source"})
            continue
        source = sources[0]
        search = search_functions.get(source)
        if not search:
            errors.append({"search_task_id": task_id, "error": f"source_not_available:{source}"})
            continue
        query = _compile(task.get("query_blocks", []), task.get("exclusion_terms", []), source)
        try:
            results = search(query, limit, use_cache=False)
        except Exception as exc:
            errors.append({"search_task_id": task_id, "error": f"pilot_failed:{type(exc).__name__}"})
            continue
        for result in results[:limit]:
            if isinstance(result, dict):
                record = dict(result)
                record["search_task_id"] = task_id
                record["pilot_source"] = source
                records.append(record)
    return {"schema_version": "pilot-search-results.v1", "records": records, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint and compile Step 3 search plan.")
    parser.add_argument("search_plan")
    parser.add_argument("--pilot-results")
    parser.add_argument("--run-pilot", action="store_true", help="Execute a small search against each task's L1 source.")
    parser.add_argument("--pilot-limit", type=int, default=10)
    parser.add_argument("--pilot-output", default="pilot_search_results.json")
    parser.add_argument("--output", default="compiled_queries.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan = json.loads(Path(args.search_plan).read_text(encoding="utf-8"))
    pilot = json.loads(Path(args.pilot_results).read_text(encoding="utf-8")) if args.pilot_results else None
    if args.run_pilot:
        pilot = run_pilot(plan, limit=max(1, min(args.pilot_limit, 20)))
        Path(args.pilot_output).write_text(json.dumps(pilot, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = lint_and_compile(plan, pilot)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["summary"]["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
