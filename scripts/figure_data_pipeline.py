from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw


SCHEMA_SPEC = "morepaper.figure_spec.v1"
SCHEMA_SPEC_CONFIRMATION = "morepaper.figure_spec_confirmation.v1"
SCHEMA_QUALITY = "morepaper.figure_candidate_quality.v1"
SCHEMA_REVIEW = "morepaper.figure_review_decisions.v1"
SCHEMA_DATA_PROVENANCE = "morepaper.figure_data_provenance.v1"
SCHEMA_VALIDATION = "morepaper.figure_data_validation.v1"

CANDIDATE_FIELDS = [
    "candidate_id",
    "series",
    "candidate_order",
    "x_px",
    "y_px",
    "x",
    "y",
    "uncertainty_x",
    "uncertainty_y",
    "visibility_status",
    "evidence_segment_break_before",
    "evidence_break_reason",
    "source_sha256",
    "spec_sha256",
    "extractor_id",
    "quality_status",
    "anomaly_codes",
]

OBSERVATION_FIELDS = [
    "observation_id",
    "candidate_id",
    "series",
    "curve_order",
    "x_px",
    "y_px",
    "x",
    "y",
    "uncertainty_x",
    "uncertainty_y",
    "visibility_status",
    "evidence_segment_break_before",
    "evidence_break_reason",
    "review_action",
    "source_sha256",
    "spec_sha256",
    "candidates_sha256",
    "review_decisions_sha256",
]

DATA_FIELDS = [
    "series",
    "curve_order",
    "x",
    "y",
    "formal_segment_id",
    "formal_segment_break_before",
    "evidence_segment_break_before",
    "evidence_break_reason",
    "source_kind",
    "source_observation_ids",
    "source_candidate_ids",
    "uncertainty_x",
    "uncertainty_y",
    "derivation_method",
    "guide_path_sha256",
    "source_sha256",
    "spec_sha256",
    "candidates_sha256",
    "observations_sha256",
    "review_decisions_sha256",
]


class FigureDataError(RuntimeError):
    """Fail-closed error for reviewed figure-data operations."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FigureDataError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise FigureDataError(f"JSON root must be an object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_pipeline_state(directory: Path, **updates: Any) -> dict[str, Any]:
    path = directory / "figure-pipeline-state.json"
    if path.exists():
        state = load_json(path)
    else:
        state = {
            "schema": "morepaper.figure_pipeline_state.v1",
            "extraction_status": "not_run",
            "review_status": "not_started",
            "render_status": "not_run",
            "delivery_status": "working",
            "artifacts": {},
        }
    state.update({key: value for key, value in updates.items() if key != "artifacts"})
    artifacts = dict(state.get("artifacts") or {})
    artifacts.update(updates.get("artifacts") or {})
    state["artifacts"] = artifacts
    write_json(path, state)
    return state


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FigureDataError(f"CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _rel(path: Path, root: Path) -> str:
    return Path(os.path.relpath(path.resolve(), root.resolve())).as_posix()


def _source_from_project(project_path: Path, project: dict[str, Any]) -> Path:
    record = project.get("input")
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise FigureDataError("project input.path is required")
    return (project_path.parent / record["path"]).resolve()


def _validate_source(project_path: Path, project: dict[str, Any]) -> Path:
    source = _source_from_project(project_path, project)
    if not source.is_file():
        raise FigureDataError("source file is missing")
    if sha256_file(source) != project.get("input", {}).get("sha256"):
        raise FigureDataError("source_hash_changed: specification confirmation is invalid")
    return source


def build_spec_review(
    project_path: Path,
    output_dir: Path,
    *,
    plot_bounds: tuple[int, int, int, int],
    x_anchors: Iterable[tuple[float, float]],
    y_anchors: Iterable[tuple[float, float]],
    series: Iterable[tuple[str, str]],
    curve_topology: dict[str, str],
    exclusion_regions: Iterable[tuple[int, int, int, int]] = (),
    x_scale: str = "linear",
    y_scale: str = "linear",
) -> dict[str, Any]:
    project = load_json(project_path)
    source = _validate_source(project_path, project)
    if project.get("input", {}).get("media_type") != "raster_image":
        raise FigureDataError("spec-review currently requires a raster image")
    series_list = list(series)
    if not series_list:
        raise FigureDataError("at least one series is required")
    series_names = [name for name, _ in series_list]
    if set(curve_topology) != set(series_names):
        raise FigureDataError("curve topology must be declared for every series")
    if any(value not in {"continuous", "segmented"} for value in curve_topology.values()):
        raise FigureDataError("curve_topology must be continuous or segmented")
    x_anchor_list = list(x_anchors)
    y_anchor_list = list(y_anchors)
    if len(x_anchor_list) < 2 or len(y_anchor_list) < 2:
        raise FigureDataError("at least two anchors are required per axis")

    with Image.open(source) as original:
        image = original.convert("RGB")
    left, top, right, bottom = plot_bounds
    if left < 0 or top < 0 or right >= image.width or bottom >= image.height:
        raise FigureDataError("plot bounds exceed the original raster")
    exclusions = list(exclusion_regions)
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rectangle(plot_bounds, outline=(255, 0, 255, 255), width=2)
    for pixel, value in x_anchor_list:
        draw.line((pixel, bottom - 6, pixel, bottom + 6), fill=(0, 120, 255, 255), width=2)
        draw.text((pixel + 2, bottom - 18), str(value), fill=(0, 90, 220, 255))
    for pixel, value in y_anchor_list:
        draw.line((left - 6, pixel, left + 6, pixel), fill=(0, 120, 255, 255), width=2)
        draw.text((left + 8, pixel - 9), str(value), fill=(0, 90, 220, 255))
    for region in exclusions:
        draw.rectangle(region, fill=(255, 180, 0, 65), outline=(255, 120, 0, 255), width=2)

    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = output_dir / "spec-review.png"
    overlay.save(overlay_path)
    spec_path = output_dir / "figure-spec.json"
    spec = {
        "schema": SCHEMA_SPEC,
        "source": {
            "path": _rel(source, spec_path.parent),
            "sha256": project["input"]["sha256"],
            "width_px": image.width,
            "height_px": image.height,
            "coordinate_space": "original_raster_pixels",
        },
        "chart_type": project.get("chart", {}).get("chart_type"),
        "plot_bounds_px": list(plot_bounds),
        "axes": {
            "x": {"scale": x_scale, "anchors": [[p, v] for p, v in x_anchor_list]},
            "y": {"scale": y_scale, "anchors": [[p, v] for p, v in y_anchor_list]},
        },
        "series": [
            {
                "name": name,
                "color": color,
                "semantic_role": name,
                "curve_topology": curve_topology[name],
            }
            for name, color in series_list
        ],
        "exclusion_regions_px": [list(region) for region in exclusions],
    }
    write_json(spec_path, spec)
    report = {
        "schema": "morepaper.figure_spec_review.v1",
        "status": "awaiting_user_confirmation",
        "source_measurement_raster": _rel(source, output_dir),
        "source_sha256": project["input"]["sha256"],
        "spec": spec_path.name,
        "spec_sha256": sha256_file(spec_path),
        "overlay": overlay_path.name,
        "overlay_sha256": sha256_file(overlay_path),
        "required_confirmation_items": [
            "plot_bounds",
            "axis_anchors",
            "series_semantics",
            "curve_topology",
            "exclusion_regions",
        ],
    }
    write_json(output_dir / "spec-review-report.json", report)
    return report


def confirm_spec(
    project_path: Path,
    spec_path: Path,
    overlay_path: Path,
    output_path: Path,
    *,
    confirmation: str,
) -> dict[str, Any]:
    if confirmation != "explicit_user_confirmation":
        raise FigureDataError("spec confirmation requires explicit_user_confirmation")
    project = load_json(project_path)
    _validate_source(project_path, project)
    spec = load_json(spec_path)
    if spec.get("schema") != SCHEMA_SPEC:
        raise FigureDataError("invalid figure-spec schema")
    if spec.get("source", {}).get("sha256") != project.get("input", {}).get("sha256"):
        raise FigureDataError("spec source hash does not match the project source")
    if not overlay_path.is_file():
        raise FigureDataError("spec-review overlay is missing")
    payload = {
        "schema": SCHEMA_SPEC_CONFIRMATION,
        "status": "confirmed",
        "confirmation": confirmation,
        "confirmed_items": [
            "plot_bounds",
            "axis_anchors",
            "series_semantics",
            "curve_topology",
            "exclusion_regions",
        ],
        "source_sha256": project["input"]["sha256"],
        "project_sha256": sha256_file(project_path),
        "spec_path": _rel(spec_path, output_path.parent),
        "spec_sha256": sha256_file(spec_path),
        "overlay_path": _rel(overlay_path, output_path.parent),
        "overlay_sha256": sha256_file(overlay_path),
    }
    write_json(output_path, payload)
    return payload


def validate_spec_confirmation(
    project_path: Path,
    confirmation_path: Path,
    *,
    plot_bounds: tuple[int, int, int, int] | None = None,
    x_anchors: Iterable[tuple[float, float]] | None = None,
    y_anchors: Iterable[tuple[float, float]] | None = None,
    series: Iterable[tuple[str, str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project = load_json(project_path)
    _validate_source(project_path, project)
    confirmation = load_json(confirmation_path)
    if confirmation.get("schema") != SCHEMA_SPEC_CONFIRMATION or confirmation.get("status") != "confirmed":
        raise FigureDataError("spec_not_confirmed")
    if confirmation.get("source_sha256") != project.get("input", {}).get("sha256"):
        raise FigureDataError("source_hash_changed: spec confirmation is stale")
    if confirmation.get("project_sha256") != sha256_file(project_path):
        raise FigureDataError("project_spec_changed: spec confirmation is stale")
    spec_path = (confirmation_path.parent / str(confirmation.get("spec_path", ""))).resolve()
    overlay_path = (confirmation_path.parent / str(confirmation.get("overlay_path", ""))).resolve()
    if not spec_path.is_file() or sha256_file(spec_path) != confirmation.get("spec_sha256"):
        raise FigureDataError("project_spec_changed: confirmed figure-spec hash mismatch")
    if not overlay_path.is_file() or sha256_file(overlay_path) != confirmation.get("overlay_sha256"):
        raise FigureDataError("spec_overlay_changed: confirmation is stale")
    spec = load_json(spec_path)
    if plot_bounds is not None and list(plot_bounds) != spec.get("plot_bounds_px"):
        raise FigureDataError("extraction plot bounds differ from confirmed specification")
    if x_anchors is not None and [[p, v] for p, v in x_anchors] != spec.get("axes", {}).get("x", {}).get("anchors"):
        raise FigureDataError("extraction x anchors differ from confirmed specification")
    if y_anchors is not None and [[p, v] for p, v in y_anchors] != spec.get("axes", {}).get("y", {}).get("anchors"):
        raise FigureDataError("extraction y anchors differ from confirmed specification")
    if series is not None:
        expected = [(item.get("name"), str(item.get("color", "")).lower()) for item in spec.get("series", [])]
        if list(series) != expected:
            raise FigureDataError("extraction series differ from confirmed specification")
    return confirmation, spec


def candidate_rows_from_series(
    series_rows: dict[str, list[dict[str, Any]]],
    *,
    source_sha256: str,
    spec_sha256: str,
    extractor_id: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for series, raw_rows in series_rows.items():
        previous_x: float | None = None
        for index, row in enumerate(sorted(raw_rows, key=lambda item: float(item["x_px"])), 1):
            x_px = float(row["x_px"])
            evidence_break = previous_x is not None and x_px - previous_x > 1.5
            gap = int(round(x_px - previous_x - 1)) if evidence_break and previous_x is not None else 0
            anomaly_codes = []
            if evidence_break and gap > 12:
                anomaly_codes.append("long_visible_pixel_gap")
            candidate_id = f"{series}:{index:06d}"
            result.append(
                {
                    "candidate_id": candidate_id,
                    "series": series,
                    "candidate_order": index,
                    "x_px": row["x_px"],
                    "y_px": row["y_px"],
                    "x": row["x"],
                    "y": row["y"],
                    "uncertainty_x": row.get("uncertainty_x", ""),
                    "uncertainty_y": row.get("uncertainty_y", ""),
                    "visibility_status": row.get("status", "visible_supported"),
                    "evidence_segment_break_before": str(evidence_break).lower(),
                    "evidence_break_reason": f"visible_pixel_gap:{gap}px" if evidence_break else "",
                    "source_sha256": source_sha256,
                    "spec_sha256": spec_sha256,
                    "extractor_id": extractor_id,
                    "quality_status": "anomaly" if anomaly_codes else "ordinary",
                    "anomaly_codes": "|".join(anomaly_codes),
                }
            )
            previous_x = x_px
    return result


def assess_candidates(
    candidates_path: Path,
    output_path: Path,
    *,
    safe_reextraction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = read_csv(candidates_path)
    anomalies: list[dict[str, Any]] = []
    ordinary_ids: list[str] = []
    previous_order: dict[str, int] = {}
    for row in rows:
        codes = [item for item in row.get("anomaly_codes", "").split("|") if item]
        series = row.get("series", "")
        try:
            order = int(row.get("candidate_order", ""))
            float(row.get("x", ""))
            float(row.get("y", ""))
        except ValueError:
            codes.append("invalid_numeric_candidate")
            order = previous_order.get(series, 0) + 1
        if order <= previous_order.get(series, 0):
            codes.append("non_monotonic_candidate_order")
        previous_order[series] = order
        if codes or row.get("quality_status") == "anomaly":
            anomalies.append({"candidate_id": row.get("candidate_id"), "series": series, "codes": sorted(set(codes))})
        else:
            ordinary_ids.append(str(row.get("candidate_id")))
    payload = {
        "schema": SCHEMA_QUALITY,
        "status": "no_candidates" if not rows else "needs_anomaly_review" if anomalies else "ordinary_candidates_ready",
        "candidates_path": candidates_path.name,
        "candidates_sha256": sha256_file(candidates_path),
        "candidate_count": len(rows),
        "ordinary_candidate_count": len(ordinary_ids),
        "anomaly_candidate_count": len(anomalies),
        "ordinary_candidate_ids": ordinary_ids,
        "anomalies": anomalies,
        "safe_reextraction": safe_reextraction or {"attempted": False, "reason": "assessment-only command has no source raster; rerun the source-locked extractor for safe re-extraction"},
        "user_review_policy": {
            "ordinary": "may be batch accepted by a user reply continue/下一步",
            "anomaly": "requires an individual accept/reject/correct/reassign decision",
        },
    }
    write_json(output_path, payload)
    return payload


def review_template(candidates_path: Path, quality_path: Path, spec_confirmation_path: Path, output_path: Path) -> dict[str, Any]:
    rows = read_csv(candidates_path)
    quality = load_json(quality_path)
    confirmation = load_json(spec_confirmation_path)
    if quality.get("candidates_sha256") != sha256_file(candidates_path):
        raise FigureDataError("quality assessment candidates hash mismatch")
    spec_path = (spec_confirmation_path.parent / str(confirmation.get("spec_path", ""))).resolve()
    spec = load_json(spec_path)
    anomaly_ids = {str(item.get("candidate_id")) for item in quality.get("anomalies", [])}
    payload = {
        "schema": SCHEMA_REVIEW,
        "review_status": "pending_user_decisions",
        "source_sha256": confirmation.get("source_sha256"),
        "spec_sha256": confirmation.get("spec_sha256"),
        "spec_confirmation_sha256": sha256_file(spec_confirmation_path),
        "candidates_sha256": sha256_file(candidates_path),
        "quality_assessment_sha256": sha256_file(quality_path),
        "normal_batch": {"action": "pending", "user_reply": ""},
        "anomaly_decisions": [
            {"candidate_id": candidate_id, "action": "pending"}
            for candidate_id in sorted(anomaly_ids)
        ],
        "series_topology": {
            str(item["name"]): {
                "curve_topology": item["curve_topology"],
                "confirmed_by_user": False,
                "formal_break_before_candidate_ids": [],
                "curve_data_mode": "observations",
            }
            for item in spec.get("series", [])
        },
        "candidate_count": len(rows),
        "instructions": {
            "normal_batch": "set action=accept and user_reply=continue or 下一步",
            "anomalies": "set each action to accept, reject, correct, or reassign",
            "topology": "set confirmed_by_user=true; only segmented curves may list formal breaks",
        },
    }
    write_json(output_path, payload)
    return payload


def _validate_review_bindings(
    candidates_path: Path,
    decisions_path: Path,
    *,
    quality_path: Path | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any], str]:
    rows = read_csv(candidates_path)
    decisions = load_json(decisions_path)
    candidates_hash = sha256_file(candidates_path)
    if decisions.get("schema") != SCHEMA_REVIEW:
        raise FigureDataError("invalid review-decisions.json schema")
    if decisions.get("candidates_sha256") != candidates_hash:
        raise FigureDataError("review decisions candidates hash mismatch")
    if quality_path is not None:
        if decisions.get("quality_assessment_sha256") != sha256_file(quality_path):
            raise FigureDataError("review decisions quality assessment hash mismatch")
    return rows, decisions, candidates_hash


def build_observations(
    candidates_path: Path,
    quality_path: Path,
    decisions_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    rows, decisions, candidates_hash = _validate_review_bindings(
        candidates_path, decisions_path, quality_path=quality_path
    )
    quality = load_json(quality_path)
    anomaly_ids = {str(item.get("candidate_id")) for item in quality.get("anomalies", [])}
    normal_batch = decisions.get("normal_batch")
    if not isinstance(normal_batch, dict) or normal_batch.get("action") != "accept" or str(normal_batch.get("user_reply", "")).strip().lower() not in {"continue", "next", "下一步", "继续"}:
        raise FigureDataError("ordinary candidates require user batch acceptance via continue/下一步")
    anomaly_decisions = {
        str(item.get("candidate_id")): item
        for item in decisions.get("anomaly_decisions", [])
        if isinstance(item, dict)
    }
    missing_anomalies = [candidate_id for candidate_id in sorted(anomaly_ids) if anomaly_decisions.get(candidate_id, {}).get("action") not in {"accept", "reject", "correct", "reassign"}]
    if missing_anomalies:
        raise FigureDataError("anomaly candidates require individual decisions: " + ", ".join(missing_anomalies[:12]))

    series_names = {str(row.get("series")) for row in rows}
    topology = decisions.get("series_topology")
    if not isinstance(topology, dict) or set(topology) != series_names:
        raise FigureDataError("review decisions must cover topology for every series")
    for series, record in topology.items():
        if not isinstance(record, dict) or record.get("confirmed_by_user") is not True:
            raise FigureDataError(f"curve topology is not user-confirmed for {series}")
        if record.get("curve_topology") not in {"continuous", "segmented"}:
            raise FigureDataError(f"invalid curve_topology for {series}")
        if record.get("curve_topology") == "continuous" and record.get("formal_break_before_candidate_ids"):
            raise FigureDataError(f"continuous curve {series} cannot declare formal segment breaks")
        if record.get("curve_data_mode", "observations") not in {"observations", "guide_constrained"}:
            raise FigureDataError(f"invalid curve_data_mode for {series}")

    decisions_hash = sha256_file(decisions_path)
    accepted: list[dict[str, Any]] = []
    last_accepted_order: dict[str, int] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id"))
        decision = anomaly_decisions.get(candidate_id) if candidate_id in anomaly_ids else {"action": "accept"}
        action = str((decision or {}).get("action"))
        if action == "reject":
            continue
        series = str(row.get("series"))
        x = row.get("x")
        y = row.get("y")
        if action == "correct":
            correction = (decision or {}).get("correction")
            if not isinstance(correction, dict) or "x" not in correction or "y" not in correction:
                raise FigureDataError(f"correct decision lacks x/y correction: {candidate_id}")
            x, y = correction["x"], correction["y"]
        if action == "reassign":
            new_series = (decision or {}).get("series")
            if new_series not in topology:
                raise FigureDataError(f"reassign decision has unknown series: {candidate_id}")
            series = str(new_series)
        order = int(row["candidate_order"])
        evidence_break = _bool(row.get("evidence_segment_break_before"))
        if series in last_accepted_order and order != last_accepted_order[series] + 1:
            evidence_break = True
        accepted.append(
            {
                "observation_id": f"obs:{candidate_id}",
                "candidate_id": candidate_id,
                "series": series,
                "curve_order": order,
                "x_px": row.get("x_px"),
                "y_px": row.get("y_px"),
                "x": x,
                "y": y,
                "uncertainty_x": row.get("uncertainty_x"),
                "uncertainty_y": row.get("uncertainty_y"),
                "visibility_status": row.get("visibility_status"),
                "evidence_segment_break_before": str(evidence_break).lower(),
                "evidence_break_reason": row.get("evidence_break_reason") or ("rejected_or_missing_candidate" if evidence_break else ""),
                "review_action": action,
                "source_sha256": row.get("source_sha256"),
                "spec_sha256": row.get("spec_sha256"),
                "candidates_sha256": candidates_hash,
                "review_decisions_sha256": decisions_hash,
            }
        )
        last_accepted_order[series] = order
    if not accepted:
        raise FigureDataError("review accepted no visible observations")
    write_csv(output_path, OBSERVATION_FIELDS, accepted)
    write_pipeline_state(
        output_path.parent,
        extraction_status="candidate_ready",
        review_status="complete",
        render_status="not_run",
        delivery_status="working",
        artifacts={"observations": output_path.name, "review_decisions": decisions_path.name},
    )
    return {
        "schema": "morepaper.figure_observations_build.v1",
        "status": "reviewed_complete",
        "review_status": "complete",
        "observations_path": output_path.name,
        "observations_sha256": sha256_file(output_path),
        "accepted_observations": len(accepted),
        "evidence_break_count": sum(_bool(row["evidence_segment_break_before"]) for row in accepted),
        "candidates_sha256": candidates_hash,
        "review_decisions_sha256": decisions_hash,
    }


def _data_from_observations(
    rows: list[dict[str, str]],
    decisions: dict[str, Any],
    *,
    source_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["series"])].append(row)
    for series, series_rows in grouped.items():
        series_rows.sort(key=lambda row: int(row["curve_order"]))
        topology = decisions["series_topology"][series]
        formal_break_ids = set(topology.get("formal_break_before_candidate_ids") or [])
        if topology["curve_topology"] == "segmented" and not formal_break_ids:
            raise FigureDataError(f"segmented curve {series} requires user-confirmed formal breaks")
        segment_id = 1
        for index, row in enumerate(series_rows):
            formal_break = index > 0 and row["candidate_id"] in formal_break_ids
            if formal_break:
                segment_id += 1
            output.append(
                {
                    "series": series,
                    "curve_order": index + 1,
                    "x": row["x"],
                    "y": row["y"],
                    "formal_segment_id": segment_id,
                    "formal_segment_break_before": str(formal_break).lower(),
                    "evidence_segment_break_before": row["evidence_segment_break_before"],
                    "evidence_break_reason": row["evidence_break_reason"],
                    "source_kind": "reviewed_visible_observation",
                    "source_observation_ids": row["observation_id"],
                    "source_candidate_ids": row["candidate_id"],
                    "uncertainty_x": row["uncertainty_x"],
                    "uncertainty_y": row["uncertainty_y"],
                    "derivation_method": "reviewed_observations_v1",
                    "guide_path_sha256": "",
                    **source_hashes,
                }
            )
    return output


def _data_from_guide(
    observations: list[dict[str, str]],
    guide_path: Path,
    decisions: dict[str, Any],
    *,
    source_hashes: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    guide_rows = read_csv(guide_path)
    guide_hash = sha256_file(guide_path)
    output: list[dict[str, Any]] = []
    residuals: list[float] = []
    residual_unit = "data_units"
    by_series_obs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in observations:
        by_series_obs[row["series"]].append(row)
    by_series_guide: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in guide_rows:
        if not {"series", "x", "y"}.issubset(row):
            raise FigureDataError("guide path requires series,x,y columns")
        by_series_guide[row["series"]].append(row)
    for series, topology in decisions["series_topology"].items():
        if topology.get("curve_data_mode", "observations") != "guide_constrained":
            continue
        expected_hash = topology.get("guide_path_sha256")
        if expected_hash != guide_hash:
            raise FigureDataError(f"guide path hash is not user-confirmed for {series}")
        rows = sorted(by_series_guide.get(series, []), key=lambda row: float(row.get("curve_order") or row["x"]))
        if not rows:
            raise FigureDataError(f"guide path contains no rows for {series}")
        observations_for_series = by_series_obs.get(series, [])
        for index, row in enumerate(rows, 1):
            x, y = float(row["x"]), float(row["y"])
            nearest = min(
                observations_for_series,
                key=lambda obs: (float(obs["x"]) - x) ** 2 + (float(obs["y"]) - y) ** 2,
            )
            if row.get("x_px") not in {None, ""} and row.get("y_px") not in {None, ""}:
                residual = math.hypot(
                    float(nearest["x_px"]) - float(row["x_px"]),
                    float(nearest["y_px"]) - float(row["y_px"]),
                )
                residual_unit = "original_raster_pixels"
            else:
                residual = math.hypot(float(nearest["x"]) - x, float(nearest["y"]) - y)
            residuals.append(residual)
            formal_break = _bool(row.get("formal_segment_break_before"))
            if topology["curve_topology"] == "continuous" and formal_break:
                raise FigureDataError(f"continuous guide path for {series} contains a formal break")
            output.append(
                {
                    "series": series,
                    "curve_order": index,
                    "x": x,
                    "y": y,
                    "formal_segment_id": int(row.get("formal_segment_id") or 1),
                    "formal_segment_break_before": str(formal_break).lower(),
                    "evidence_segment_break_before": nearest["evidence_segment_break_before"],
                    "evidence_break_reason": nearest["evidence_break_reason"],
                    "source_kind": "guide_constrained",
                    "source_observation_ids": nearest["observation_id"],
                    "source_candidate_ids": nearest["candidate_id"],
                    "uncertainty_x": nearest["uncertainty_x"],
                    "uncertainty_y": nearest["uncertainty_y"],
                    "derivation_method": "user_confirmed_guide_constrained_v1",
                    "guide_path_sha256": guide_hash,
                    **source_hashes,
                }
            )
    report = {
        "guide_path": guide_path.name,
        "guide_path_sha256": guide_hash,
        "visible_pixel_residual": {
            "method": "nearest_reviewed_observation_euclidean",
            "unit": residual_unit,
            "count": len(residuals),
            "max": max(residuals) if residuals else None,
            "mean": sum(residuals) / len(residuals) if residuals else None,
        },
    }
    return output, report


def build_data(
    observations_path: Path,
    decisions_path: Path,
    output_path: Path,
    provenance_path: Path,
    *,
    guide_path: Path | None = None,
) -> dict[str, Any]:
    if not decisions_path.is_file():
        raise FigureDataError("review-decisions.json is required")
    observations = read_csv(observations_path)
    decisions = load_json(decisions_path)
    if not observations:
        raise FigureDataError("observations.csv contains no reviewed observations")
    decisions_hash = sha256_file(decisions_path)
    if any(row.get("review_decisions_sha256") != decisions_hash for row in observations):
        raise FigureDataError("observations.csv is not bound to review-decisions.json")
    if decisions.get("review_status") not in {"complete", "reviewed_complete"}:
        raise FigureDataError("review-decisions.json is incomplete")
    observations_hash = sha256_file(observations_path)
    source_hashes = {
        "source_sha256": observations[0]["source_sha256"],
        "spec_sha256": observations[0]["spec_sha256"],
        "candidates_sha256": observations[0]["candidates_sha256"],
        "observations_sha256": observations_hash,
        "review_decisions_sha256": decisions_hash,
    }
    modes = {record.get("curve_data_mode", "observations") for record in decisions.get("series_topology", {}).values() if isinstance(record, dict)}
    rows = _data_from_observations(observations, decisions, source_hashes=source_hashes)
    guide_report: dict[str, Any] | None = None
    if "guide_constrained" in modes:
        if guide_path is None:
            raise FigureDataError("guide_constrained mode requires --guide-path")
        guide_rows, guide_report = _data_from_guide(observations, guide_path, decisions, source_hashes=source_hashes)
        guide_series = {row["series"] for row in guide_rows}
        rows = [row for row in rows if row["series"] not in guide_series] + guide_rows
    rows.sort(key=lambda row: (str(row["series"]), int(row["formal_segment_id"]), int(row["curve_order"])))
    write_csv(output_path, DATA_FIELDS, rows)
    data_hash = sha256_file(output_path)
    provenance = {
        "schema": SCHEMA_DATA_PROVENANCE,
        "status": "formal_data_ready",
        "data_path": output_path.name,
        "data_sha256": data_hash,
        "row_count": len(rows),
        "series_topology": decisions["series_topology"],
        "lineage": source_hashes,
        "guide_constrained": guide_report,
        "render_stage_interpolation": False,
        "render_stage_bridging": False,
        "style_independent": True,
    }
    write_json(provenance_path, provenance)
    write_pipeline_state(
        output_path.parent,
        extraction_status="formal_data_ready",
        review_status="complete",
        render_status="not_run",
        delivery_status="working",
        artifacts={"data": output_path.name, "data_provenance": provenance_path.name},
    )
    return provenance


def build_visualspec(
    data_path: Path,
    provenance_path: Path,
    output_path: Path,
    *,
    styles_path: Path | None = None,
    width_mm: float = 100.0,
    height_mm: float = 70.0,
    dpi: int = 300,
) -> dict[str, Any]:
    if data_path.name != "data.csv":
        raise FigureDataError("VisualSpec digitization input must be the formal data.csv")
    if data_path.name in {"candidates.csv", "observations.csv", "digitized_lines.csv"}:
        raise FigureDataError("candidate/observation data cannot enter VisualSpec")
    rows = read_csv(data_path)
    provenance = load_json(provenance_path)
    if provenance.get("schema") != SCHEMA_DATA_PROVENANCE or provenance.get("status") != "formal_data_ready":
        raise FigureDataError("formal data provenance is missing or incomplete")
    if provenance.get("data_sha256") != sha256_file(data_path) or provenance.get("row_count") != len(rows):
        raise FigureDataError("formal data hash or row count mismatch")
    styles = load_json(styles_path) if styles_path else {}
    if styles.get("schema") not in {None, "morepaper.figure_styles.v1"}:
        raise FigureDataError("invalid style schema")
    style_map = styles.get("series", styles)
    if not isinstance(style_map, dict):
        raise FigureDataError("styles must map series names to style objects")

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["series"], row["formal_segment_id"])].append(row)
    plots: list[dict[str, Any]] = []
    seen_series: set[str] = set()
    allowed_style = {"color", "line_width_pt", "line_style", "marker", "alpha"}
    for (series, segment_id), segment_rows in grouped.items():
        segment_rows.sort(key=lambda row: int(row["curve_order"]))
        style = dict(style_map.get(series, {})) if isinstance(style_map.get(series, {}), dict) else {}
        unknown = set(style) - allowed_style
        if unknown:
            raise FigureDataError(f"unsupported line style fields for {series}: {sorted(unknown)}")
        style.setdefault("color", "#1f77b4")
        style.setdefault("line_width_pt", 1.2)
        style.setdefault("line_style", "solid")
        if style["line_style"] not in {"solid", "dashed", "dashdot", "dotted"}:
            raise FigureDataError(f"invalid line_style for {series}")
        plots.append(
            {
                "id": f"{series}-segment-{segment_id}",
                "type": "line",
                "label": series if series not in seen_series else None,
                "data": {
                    "x": [float(row["x"]) for row in segment_rows],
                    "y": [float(row["y"]) for row in segment_rows],
                },
                "style": style,
            }
        )
        seen_series.add(series)
    x_values = [float(row["x"]) for row in rows]
    y_values = [float(row["y"]) for row in rows]
    spec = {
        "schema": "scientificfigure.visualspec.v2",
        "figure": {"size_mm": [width_mm, height_mm], "dpi": dpi, "crop_mode": "fixed_canvas", "background": "white"},
        "theme": {"font": {"family_candidates": ["Arial", "Liberation Sans", "DejaVu Sans"], "size_pt": 8}},
        "data_contract": {
            "kind": "formal_data_csv",
            "path": _rel(data_path, output_path.parent),
            "sha256": provenance["data_sha256"],
            "row_count": len(rows),
            "source_sha256": provenance["lineage"]["source_sha256"],
            "spec_sha256": provenance["lineage"]["spec_sha256"],
            "candidates_sha256": provenance["lineage"]["candidates_sha256"],
            "observations_sha256": provenance["lineage"]["observations_sha256"],
            "review_decisions_sha256": provenance["lineage"]["review_decisions_sha256"],
            "style_independent": True,
        },
        "panels": [
            {
                "id": "digitized_panel",
                "bbox_normalized": [0.16, 0.16, 0.78, 0.74],
                "source_strategy": "digitized_raster",
                "representation": "semantic_vector",
                "axes": {"x": {"scale": "linear", "limits": [min(x_values), max(x_values)]}, "y": {"scale": "linear", "limits": [min(y_values), max(y_values)]}},
                "plots": plots,
                "annotations": [],
            }
        ],
    }
    write_json(output_path, spec)
    write_pipeline_state(
        output_path.parent,
        extraction_status="formal_data_ready",
        review_status="complete",
        render_status="not_run",
        delivery_status="working",
        artifacts={"visualspec": output_path.name},
    )
    return {
        "schema": "morepaper.figure_visualspec_build.v1",
        "status": "formal_visualspec_ready",
        "visualspec": output_path.name,
        "visualspec_sha256": sha256_file(output_path),
        "data_sha256": provenance["data_sha256"],
        "data_row_count": len(rows),
        "render_stage_interpolation": False,
        "render_stage_bridging": False,
    }


def validate_visualspec_data_contract(spec_path: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    errors: list[str] = []
    digitized = any(panel.get("source_strategy") == "digitized_raster" for panel in spec.get("panels", []) if isinstance(panel, dict))
    contract = spec.get("data_contract")
    if digitized and not isinstance(contract, dict):
        errors.append("digitized VisualSpec requires formal data_contract")
    if isinstance(contract, dict):
        if contract.get("kind") != "formal_data_csv":
            errors.append("data_contract.kind must be formal_data_csv")
        raw_path = str(contract.get("path", ""))
        if Path(raw_path).name != "data.csv" or Path(raw_path).name in {"candidates.csv", "observations.csv", "digitized_lines.csv"}:
            errors.append("VisualSpec data_contract must reference data.csv, never candidate/observation input")
        data_path = (spec_path.parent / raw_path).resolve()
        if not data_path.is_file():
            errors.append("formal data.csv is missing")
        else:
            if sha256_file(data_path) != contract.get("sha256"):
                errors.append("formal data.csv hash mismatch")
            if len(read_csv(data_path)) != contract.get("row_count"):
                errors.append("formal data.csv row count mismatch")
    for panel in spec.get("panels", []):
        for plot in panel.get("plots", []) if isinstance(panel, dict) else []:
            source = (plot.get("data") or {}).get("source") if isinstance(plot, dict) else None
            if source and Path(str(source)).name in {"candidates.csv", "observations.csv", "digitized_lines.csv"}:
                errors.append("plot data.source cannot reference candidate/observation data")
    return {"schema": SCHEMA_VALIDATION, "status": "pass" if not errors else "failed", "errors": errors}


def validate_delivery(
    *,
    candidates_path: Path,
    observations_path: Path,
    decisions_path: Path,
    data_path: Path,
    provenance_path: Path,
    visualspec_path: Path,
    render_manifest_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        decisions = load_json(decisions_path)
        if decisions.get("review_status") not in {"complete", "reviewed_complete"}:
            errors.append("review_status is incomplete")
        observations = read_csv(observations_path)
        if not observations:
            errors.append("observations.csv is empty")
        provenance = load_json(provenance_path)
        if provenance.get("data_sha256") != sha256_file(data_path):
            errors.append("data.csv hash does not match provenance")
        if provenance.get("lineage", {}).get("candidates_sha256") != sha256_file(candidates_path):
            errors.append("candidate lineage mismatch")
        contract = validate_visualspec_data_contract(visualspec_path)
        errors.extend(contract["errors"])
    except FigureDataError as exc:
        errors.append(str(exc))
    render_status = "not_run"
    if render_manifest_path is not None:
        try:
            render_manifest = load_json(render_manifest_path)
            if render_manifest.get("render_status") == "pass" and render_manifest.get("export_status") == "pass":
                render_status = "validated"
            else:
                errors.append("render manifest did not pass render/export gates")
                render_status = "failed"
        except FigureDataError as exc:
            errors.append(str(exc))
            render_status = "failed"
    formal_ready = not errors
    delivery_ready = formal_ready and render_status == "validated"
    result = {
        "schema": SCHEMA_VALIDATION,
        "status": "pass" if not errors else "failed",
        "extraction_status": "formal_data_ready" if formal_ready else "candidate_only",
        "review_status": "complete" if formal_ready else "incomplete",
        "render_status": render_status,
        "delivery_status": "validated" if delivery_ready else "working",
        "errors": errors,
    }
    if formal_ready:
        write_pipeline_state(
            visualspec_path.parent,
            extraction_status="formal_data_ready",
            review_status="complete",
            render_status=render_status,
            delivery_status=result["delivery_status"],
            artifacts={
                "visualspec": visualspec_path.name,
                **({"render_manifest": render_manifest_path.name} if render_manifest_path else {}),
            },
        )
    return result


def migrate_legacy_digitized_lines(
    legacy_path: Path,
    output_path: Path,
    *,
    source_sha256: str,
    spec_sha256: str,
) -> dict[str, Any]:
    rows = read_csv(legacy_path)
    required = {"series", "x", "y", "x_px", "y_px"}
    if rows and not required.issubset(rows[0]):
        raise FigureDataError("legacy digitized_lines.csv lacks required candidate columns")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["series"])].append(
            {
                "x": row["x"],
                "y": row["y"],
                "x_px": row["x_px"],
                "y_px": row["y_px"],
                "uncertainty_x": row.get("uncertainty_x", ""),
                "uncertainty_y": row.get("uncertainty_y", ""),
                "status": row.get("status", "legacy_visible_candidate"),
            }
        )
    candidates = candidate_rows_from_series(
        grouped,
        source_sha256=source_sha256,
        spec_sha256=spec_sha256,
        extractor_id="legacy_digitized_lines_migration_v1",
    )
    write_csv(output_path, CANDIDATE_FIELDS, candidates)
    return {
        "schema": "morepaper.figure_legacy_migration.v1",
        "status": "candidate_only_not_reviewed",
        "legacy_input": legacy_path.name,
        "legacy_input_sha256": sha256_file(legacy_path),
        "output": output_path.name,
        "output_sha256": sha256_file(output_path),
        "candidate_count": len(candidates),
        "formal_data_authorized": False,
        "visualspec_authorized": False,
    }
