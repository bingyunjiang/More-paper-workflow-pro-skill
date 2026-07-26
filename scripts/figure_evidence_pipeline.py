from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw

from figure_data_pipeline import (
    CANDIDATE_FIELDS,
    FigureDataError,
    assess_candidates,
    build_data,
    build_observations,
    build_spec_review,
    build_visualspec,
    candidate_rows_from_series,
    confirm_spec,
    migrate_legacy_digitized_lines,
    review_template,
    validate_delivery,
    validate_spec_confirmation,
    validate_visualspec_data_contract,
    write_csv as write_pipeline_csv,
    write_pipeline_state,
)


SCHEMA_PROJECT = "morepaper.figure_project.v1"
SCHEMA_EXTRACTION = "morepaper.figure_extraction_evidence.v1"
SCHEMA_VALIDATION = "morepaper.figure_project_validation.v1"
RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
CHART_ROUTES: dict[str, dict[str, str]] = {
    "line": {"support": "candidate", "extractor": "native_color_line_v1"},
    "scatter": {"support": "candidate", "extractor": "native_color_scatter_v1"},
    "simple_bar": {"support": "candidate", "extractor": "native_color_bar_v1"},
    "grouped_bar": {"support": "candidate", "extractor": "native_color_bar_v1"},
    "stacked_bar": {"support": "planned", "extractor": "not_implemented"},
    "histogram": {"support": "candidate", "extractor": "native_color_bar_v1"},
    "boxplot": {"support": "planned", "extractor": "not_implemented"},
    "heatmap": {"support": "planned", "extractor": "not_implemented"},
    "labelled_pie": {"support": "planned", "extractor": "not_implemented"},
    "aligned_lattice": {"support": "planned", "extractor": "not_implemented"},
}


class FigureEvidenceError(RuntimeError):
    """Fail-closed error for figure evidence operations."""


@dataclass(frozen=True)
class AxisCalibration:
    scale: str
    slope: float
    intercept: float
    anchors: tuple[tuple[float, float], ...]
    residuals: tuple[float, ...]
    normalized_max_residual: float

    def map_pixel(self, pixel: float) -> float:
        transformed = self.slope * pixel + self.intercept
        if self.scale == "log10":
            return 10.0**transformed
        return transformed

    def as_dict(self) -> dict[str, Any]:
        return {
            "scale": self.scale,
            "model": "transformed_value = slope * pixel + intercept",
            "slope": self.slope,
            "intercept": self.intercept,
            "anchors": [
                {
                    "pixel": pixel,
                    "value": value,
                    "residual_transformed_value": residual,
                }
                for (pixel, value), residual in zip(self.anchors, self.residuals)
            ],
            "normalized_max_residual": self.normalized_max_residual,
            "status": "pass" if self.normalized_max_residual <= 0.02 else "failed",
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_relpath(path: Path, root: Path) -> str:
    return Path(os.path.relpath(path.resolve(), root.resolve())).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FigureEvidenceError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise FigureEvidenceError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def inspect_source(input_path: Path, chart_type: str | None, output_project: Path) -> dict[str, Any]:
    source = input_path.resolve()
    if not source.is_file():
        raise FigureEvidenceError(f"input does not exist: {input_path}")

    suffix = source.suffix.lower()
    input_record: dict[str, Any] = {
        "path": portable_relpath(source, output_project.parent),
        "display_name": source.name,
        "sha256": sha256_file(source),
        "size_bytes": source.stat().st_size,
    }
    if suffix in RASTER_SUFFIXES:
        with Image.open(source) as image:
            width, height = image.size
            mode = image.mode
        input_record.update(
            {
                "media_type": "raster_image",
                "width_px": width,
                "height_px": height,
                "pixel_mode": mode,
                "coordinate_space": "original_raster_pixels",
            }
        )
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise FigureEvidenceError("PDF inspection requires pypdf") from exc
        reader = PdfReader(str(source))
        input_record.update(
            {
                "media_type": "pdf",
                "page_count": len(reader.pages),
                "coordinate_space": "pdf_points",
            }
        )
    else:
        raise FigureEvidenceError(
            f"unsupported input suffix {suffix!r}; supported raster images and PDF"
        )

    normalized_chart_type = (chart_type or "").strip().lower()
    if not normalized_chart_type:
        route_status = "needs_chart_type_confirmation"
        route = {"support": "unknown", "extractor": "not_selected"}
        extraction_status = "needs_configuration"
    elif normalized_chart_type not in CHART_ROUTES:
        route_status = "unsupported_chart_type"
        route = {"support": "unsupported", "extractor": "not_available"}
        extraction_status = "not_extracted"
    else:
        route = CHART_ROUTES[normalized_chart_type]
        if route["support"] == "candidate" and input_record["media_type"] == "raster_image":
            route_status = "ready_for_configuration"
            extraction_status = "needs_configuration"
        elif input_record["media_type"] == "pdf":
            route_status = "pdf_requires_panel_and_representation_review"
            extraction_status = "needs_configuration"
        else:
            route_status = "recognized_not_implemented"
            extraction_status = "not_extracted"

    payload = {
        "schema": SCHEMA_PROJECT,
        "project_root": ".",
        "input": input_record,
        "chart": {
            "chart_type": normalized_chart_type or "unknown",
            "chart_type_verified": bool(normalized_chart_type in CHART_ROUTES),
        },
        "routing": {
            "status": route_status,
            "support_level": route["support"],
            "extractor": route["extractor"],
            "value_delivery_authorized": False,
        },
        "evidence_contract": {
            "source_identity_required": True,
            "measure_original_coordinates_only": True,
            "minimum_axis_anchors_per_axis": 2,
            "missing_values_are_not_interpolated_during_extraction": True,
            "render_stage_interpolation_forbidden": True,
            "render_stage_bridging_forbidden": True,
            "spec_review_confirmation_required_before_extraction": True,
            "candidate_review_required_before_formal_data": True,
            "formal_data_required_before_visualspec": True,
            "overlay_review_required": True,
            "official_source_data_validation_is_separate": True,
        },
        "extraction_status": extraction_status,
        "review_status": "not_started",
        "render_status": "not_run",
        "delivery_status": "working",
    }
    _write_json(output_project, payload)
    return payload


def resolve_project_source(project_path: Path, project: dict[str, Any]) -> Path:
    input_record = project.get("input")
    if not isinstance(input_record, dict) or not isinstance(input_record.get("path"), str):
        raise FigureEvidenceError("project input.path is required")
    return (project_path.parent / input_record["path"]).resolve()


def validate_project(project_path: Path, *, verify_source: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    try:
        project = _load_json(project_path)
    except FigureEvidenceError as exc:
        return {
            "schema": SCHEMA_VALIDATION,
            "status": "failed",
            "errors": [str(exc)],
        }

    if project.get("schema") != SCHEMA_PROJECT:
        errors.append(f"schema must be {SCHEMA_PROJECT}")
    for field in (
        "input",
        "chart",
        "routing",
        "evidence_contract",
        "extraction_status",
        "review_status",
        "render_status",
        "delivery_status",
    ):
        if field not in project:
            errors.append(f"missing required field: {field}")

    input_record = project.get("input")
    if isinstance(input_record, dict):
        for field in ("path", "sha256", "media_type", "coordinate_space"):
            if not input_record.get(field):
                errors.append(f"missing input.{field}")
        if input_record.get("media_type") == "raster_image":
            for field in ("width_px", "height_px"):
                if not isinstance(input_record.get(field), int) or input_record[field] <= 0:
                    errors.append(f"input.{field} must be a positive integer")
    else:
        errors.append("input must be an object")

    if verify_source and isinstance(input_record, dict) and input_record.get("path"):
        try:
            source = resolve_project_source(project_path, project)
            if not source.is_file():
                errors.append(f"source file missing: {input_record['path']}")
            else:
                actual_hash = sha256_file(source)
                if actual_hash != input_record.get("sha256"):
                    errors.append("source SHA-256 mismatch")
                if input_record.get("media_type") == "raster_image":
                    with Image.open(source) as image:
                        actual_size = image.size
                    expected_size = (
                        input_record.get("width_px"),
                        input_record.get("height_px"),
                    )
                    if actual_size != expected_size:
                        errors.append(
                            f"source dimensions mismatch: expected {expected_size}, got {actual_size}"
                        )
        except (OSError, FigureEvidenceError) as exc:
            errors.append(str(exc))

    return {
        "schema": SCHEMA_VALIDATION,
        "project": project_path.name,
        "status": "pass" if not errors else "failed",
        "source_identity_verified": verify_source and not any(
            "source" in error.lower() for error in errors
        ),
        "errors": errors,
    }


def parse_bounds(value: str) -> tuple[int, int, int, int]:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise FigureEvidenceError("plot bounds must be left,top,right,bottom integers") from exc
    if len(parts) != 4:
        raise FigureEvidenceError("plot bounds must contain four integers")
    left, top, right, bottom = parts
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise FigureEvidenceError("plot bounds must satisfy 0 <= left < right and 0 <= top < bottom")
    return left, top, right, bottom


def parse_anchor(value: str) -> tuple[float, float]:
    try:
        pixel_text, value_text = value.split(",", 1)
        return float(pixel_text.strip()), float(value_text.strip())
    except ValueError as exc:
        raise FigureEvidenceError("axis anchor must be pixel,value") from exc


def parse_series(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise FigureEvidenceError("series must be name=#RRGGBB")
    name, color = (part.strip() for part in value.split("=", 1))
    if not name:
        raise FigureEvidenceError("series name cannot be empty")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise FigureEvidenceError("series color must be #RRGGBB")
    return name, color.lower()


def parse_topology(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise FigureEvidenceError("series topology must be name=continuous|segmented")
    name, topology = (part.strip() for part in value.split("=", 1))
    if not name or topology not in {"continuous", "segmented"}:
        raise FigureEvidenceError("series topology must be name=continuous|segmented")
    return name, topology


def hex_rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def fit_axis(anchors: Iterable[tuple[float, float]], scale: str) -> AxisCalibration:
    anchor_list = tuple(anchors)
    if len(anchor_list) < 2:
        raise FigureEvidenceError("at least two anchors are required per axis")
    pixels = np.asarray([item[0] for item in anchor_list], dtype=float)
    values = np.asarray([item[1] for item in anchor_list], dtype=float)
    if len(set(float(item) for item in pixels)) < 2:
        raise FigureEvidenceError("axis anchors require at least two distinct pixel positions")
    if scale == "log10":
        if np.any(values <= 0):
            raise FigureEvidenceError("log10 axis anchors require positive values")
        transformed = np.log10(values)
    elif scale == "linear":
        transformed = values
    else:
        raise FigureEvidenceError("axis scale must be linear or log10")

    matrix = np.column_stack([pixels, np.ones_like(pixels)])
    slope, intercept = np.linalg.lstsq(matrix, transformed, rcond=None)[0]
    predicted = slope * pixels + intercept
    residuals = transformed - predicted
    span = float(np.ptp(transformed))
    denominator = span if span > 0 else 1.0
    normalized = float(np.max(np.abs(residuals)) / denominator)
    if not math.isfinite(float(slope)) or abs(float(slope)) < 1e-15:
        raise FigureEvidenceError("axis calibration slope is invalid")
    return AxisCalibration(
        scale=scale,
        slope=float(slope),
        intercept=float(intercept),
        anchors=anchor_list,
        residuals=tuple(float(item) for item in residuals),
        normalized_max_residual=normalized,
    )


def _validate_bounds(
    bounds: tuple[int, int, int, int], width: int, height: int
) -> None:
    left, top, right, bottom = bounds
    if right >= width or bottom >= height:
        raise FigureEvidenceError(
            f"plot bounds {bounds} exceed source canvas {width}x{height}"
        )


def _line_points_for_color(
    rgb: np.ndarray,
    bounds: tuple[int, int, int, int],
    target_rgb: tuple[int, int, int],
    tolerance: float,
    max_vertical_span_px: int,
) -> tuple[list[tuple[int, float]], dict[str, int]]:
    left, top, right, bottom = bounds
    crop = rgb[top : bottom + 1, left : right + 1].astype(np.int32)
    target = np.asarray(target_rgb, dtype=np.int32)
    distances = np.sqrt(np.sum((crop - target) ** 2, axis=2))
    mask = distances <= tolerance

    accepted: list[tuple[int, float]] = []
    counts = {"accepted": 0, "missing": 0, "ambiguous_vertical_span": 0}
    for column_index, x_pixel in enumerate(range(left, right + 1)):
        local_y = np.flatnonzero(mask[:, column_index])
        if local_y.size == 0:
            counts["missing"] += 1
            continue
        span = int(local_y[-1] - local_y[0])
        if span > max_vertical_span_px:
            counts["ambiguous_vertical_span"] += 1
            continue
        y_pixel = float(np.median(local_y) + top)
        accepted.append((x_pixel, y_pixel))
        counts["accepted"] += 1
    return accepted, counts


def _color_mask(
    rgb: np.ndarray,
    bounds: tuple[int, int, int, int],
    target_rgb: tuple[int, int, int],
    tolerance: float,
) -> np.ndarray:
    left, top, right, bottom = bounds
    crop = rgb[top : bottom + 1, left : right + 1].astype(np.int32)
    target = np.asarray(target_rgb, dtype=np.int32)
    distances = np.sqrt(np.sum((crop - target) ** 2, axis=2))
    return distances <= tolerance


def _connected_components(
    mask: np.ndarray,
    *,
    left: int,
    top: int,
) -> list[dict[str, Any]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[dict[str, Any]] = []
    for y0 in range(height):
        for x0 in range(width):
            if not mask[y0, x0] or visited[y0, x0]:
                continue
            queue: deque[tuple[int, int]] = deque([(x0, y0)])
            visited[y0, x0] = True
            pixels: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                pixels.append((x + left, y + top))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and mask[ny, nx]
                            and not visited[ny, nx]
                        ):
                            visited[ny, nx] = True
                            queue.append((nx, ny))
            xs = [pixel[0] for pixel in pixels]
            ys = [pixel[1] for pixel in pixels]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            components.append(
                {
                    "pixels": pixels,
                    "area_px": len(pixels),
                    "bbox_px": [min_x, min_y, max_x, max_y],
                    "width_px": box_width,
                    "height_px": box_height,
                    "fill_ratio": len(pixels) / (box_width * box_height),
                    "centroid_x_px": float(np.mean(xs)),
                    "centroid_y_px": float(np.mean(ys)),
                }
            )
    return components


def _pixel_uncertainty(axis: AxisCalibration, pixel: float) -> float:
    center = axis.map_pixel(pixel)
    return max(
        abs(axis.map_pixel(pixel - 0.5) - center),
        abs(axis.map_pixel(pixel + 0.5) - center),
    )


def _visualspec_from_series(
    width: int,
    height: int,
    x_axis: AxisCalibration,
    y_axis: AxisCalibration,
    series_rows: dict[str, list[dict[str, Any]]],
    colors: dict[str, str],
) -> dict[str, Any]:
    plots: list[dict[str, Any]] = []
    for name, rows in series_rows.items():
        plots.append(
            {
                "type": "line",
                "label": name,
                "data": {
                    "x": [row["x"] for row in rows],
                    "y": [row["y"] for row in rows],
                },
                "style": {"color": colors[name], "line_width_pt": 1.2},
            }
        )

    x_values = [anchor[1] for anchor in x_axis.anchors]
    y_values = [anchor[1] for anchor in y_axis.anchors]
    return {
        "schema": "scientificfigure.visualspec.v2",
        "figure": {
            "size_mm": [100.0, round(100.0 * height / width, 3)],
            "dpi": 300,
            "crop_mode": "fixed_canvas",
            "background": "white",
        },
        "theme": {
            "font": {
                "family_candidates": ["Arial", "Liberation Sans", "DejaVu Sans"],
                "size_pt": 8,
            }
        },
        "panels": [
            {
                "id": "digitized_panel",
                "bbox_normalized": [0.16, 0.16, 0.78, 0.74],
                "source_strategy": "digitized_raster",
                "representation": "semantic_vector",
                "axes": {
                    "x": {
                        "scale": "log" if x_axis.scale == "log10" else "linear",
                        "limits": [min(x_values), max(x_values)],
                    },
                    "y": {
                        "scale": "log" if y_axis.scale == "log10" else "linear",
                        "limits": [min(y_values), max(y_values)],
                    },
                },
                "plots": plots,
                "annotations": [],
            }
        ],
    }


def _visualspec_from_points(
    width: int,
    height: int,
    x_axis: AxisCalibration,
    y_axis: AxisCalibration,
    series_rows: dict[str, list[dict[str, Any]]],
    colors: dict[str, str],
) -> dict[str, Any]:
    plots = [
        {
            "type": "scatter",
            "label": name,
            "data": {
                "x": [row["x"] for row in rows],
                "y": [row["y"] for row in rows],
            },
            "style": {"color": colors[name], "marker_size_pt2": 18},
        }
        for name, rows in series_rows.items()
    ]
    return _visualspec_base(width, height, x_axis, y_axis, plots)


def _visualspec_from_bars(
    width: int,
    height: int,
    x_axis: AxisCalibration,
    y_axis: AxisCalibration,
    series_rows: dict[str, list[dict[str, Any]]],
    colors: dict[str, str],
) -> dict[str, Any]:
    plots: list[dict[str, Any]] = []
    for name, rows in series_rows.items():
        plots.append(
            {
                "type": "grouped_bar",
                "label": name,
                "data": {
                    "x": [row["x"] for row in rows],
                    "groups": [
                        {
                            "label": name,
                            "color": colors[name],
                            "y": [row["y"] - row["baseline_y"] for row in rows],
                        }
                    ],
                },
                "style": {"bar_width": 0.6},
            }
        )
    return _visualspec_base(width, height, x_axis, y_axis, plots)


def _visualspec_base(
    width: int,
    height: int,
    x_axis: AxisCalibration,
    y_axis: AxisCalibration,
    plots: list[dict[str, Any]],
) -> dict[str, Any]:
    x_values = [anchor[1] for anchor in x_axis.anchors]
    y_values = [anchor[1] for anchor in y_axis.anchors]
    return {
        "schema": "scientificfigure.visualspec.v2",
        "figure": {
            "size_mm": [100.0, round(100.0 * height / width, 3)],
            "dpi": 300,
            "crop_mode": "fixed_canvas",
            "background": "white",
        },
        "theme": {
            "font": {
                "family_candidates": ["Arial", "Liberation Sans", "DejaVu Sans"],
                "size_pt": 8,
            }
        },
        "panels": [
            {
                "id": "digitized_panel",
                "bbox_normalized": [0.16, 0.16, 0.78, 0.74],
                "source_strategy": "digitized_raster",
                "representation": "semantic_vector",
                "axes": {
                    "x": {
                        "scale": "log" if x_axis.scale == "log10" else "linear",
                        "limits": [min(x_values), max(x_values)],
                    },
                    "y": {
                        "scale": "log" if y_axis.scale == "log10" else "linear",
                        "limits": [min(y_values), max(y_values)],
                    },
                },
                "plots": plots,
                "annotations": [],
            }
        ],
    }


def extract_color_lines(
    project_path: Path,
    output_dir: Path,
    *,
    plot_bounds: tuple[int, int, int, int],
    x_anchors: Iterable[tuple[float, float]],
    y_anchors: Iterable[tuple[float, float]],
    series: Iterable[tuple[str, str]],
    x_scale: str = "linear",
    y_scale: str = "linear",
    color_tolerance: float = 36.0,
    minimum_coverage: float = 0.65,
    max_vertical_span_px: int = 12,
    overlay_review_status: str = "pending",
    spec_confirmation_path: Path | None = None,
) -> dict[str, Any]:
    project = _load_json(project_path)
    validation = validate_project(project_path, verify_source=True)
    if validation["status"] != "pass":
        raise FigureEvidenceError("; ".join(validation["errors"]))
    if project.get("chart", {}).get("chart_type") != "line":
        raise FigureEvidenceError("native_color_line_v1 requires chart.chart_type=line")
    if project.get("input", {}).get("media_type") != "raster_image":
        raise FigureEvidenceError("native_color_line_v1 requires a raster image")
    if spec_confirmation_path is None:
        raise FigureEvidenceError("spec_not_confirmed: --spec-confirmation is required before extraction")

    x_anchor_list = list(x_anchors)
    y_anchor_list = list(y_anchors)
    series_list = list(series)
    try:
        confirmation, confirmed_spec = validate_spec_confirmation(
            project_path,
            spec_confirmation_path,
            plot_bounds=plot_bounds,
            x_anchors=x_anchor_list,
            y_anchors=y_anchor_list,
            series=series_list,
        )
        if confirmed_spec.get("axes", {}).get("x", {}).get("scale") != x_scale or confirmed_spec.get("axes", {}).get("y", {}).get("scale") != y_scale:
            raise FigureDataError("extraction axis scales differ from confirmed specification")
    except FigureDataError as exc:
        raise FigureEvidenceError(str(exc)) from exc

    source = resolve_project_source(project_path, project)
    with Image.open(source) as original:
        image = original.convert("RGB")
    width, height = image.size
    _validate_bounds(plot_bounds, width, height)

    if not series_list:
        raise FigureEvidenceError("at least one --series name=#RRGGBB is required")
    if len({name for name, _ in series_list}) != len(series_list):
        raise FigureEvidenceError("series names must be unique")

    x_axis = fit_axis(x_anchor_list, x_scale)
    y_axis = fit_axis(y_anchor_list, y_scale)
    rgb = np.asarray(image)
    series_rows: dict[str, list[dict[str, Any]]] = {}
    coverage_ledger: list[dict[str, Any]] = []
    colors = dict(series_list)
    total_columns = plot_bounds[2] - plot_bounds[0] + 1
    exclusion_regions = [tuple(int(value) for value in region) for region in confirmed_spec.get("exclusion_regions_px", [])]
    safe_reextraction_ledger: list[dict[str, Any]] = []

    for name, color in series_list:
        points, counts = _line_points_for_color(
            rgb,
            plot_bounds,
            hex_rgb(color),
            color_tolerance,
            max_vertical_span_px,
        )
        excluded_points = [
            (x_pixel, y_pixel)
            for x_pixel, y_pixel in points
            if any(left <= x_pixel <= right and top <= y_pixel <= bottom for left, top, right, bottom in exclusion_regions)
        ]
        if excluded_points:
            excluded_set = set(excluded_points)
            points = [point for point in points if point not in excluded_set]
            counts["excluded_by_confirmed_region"] = len(excluded_points)
        original_points = list(points)
        retry_tolerance = min(96.0, max(color_tolerance + 8.0, color_tolerance * 1.25))
        retry_points, retry_counts = _line_points_for_color(
            rgb,
            plot_bounds,
            hex_rgb(color),
            retry_tolerance,
            max_vertical_span_px,
        )
        retry_points = [
            point
            for point in retry_points
            if not any(left <= point[0] <= right and top <= point[1] <= bottom for left, top, right, bottom in exclusion_regions)
        ]
        original_by_x = {x: y for x, y in original_points}
        original_x = sorted(original_by_x)
        safe_added: list[tuple[int, float]] = []
        for x_pixel, y_pixel in retry_points:
            if x_pixel in original_by_x:
                continue
            left_x = max((value for value in original_x if value < x_pixel), default=None)
            right_x = min((value for value in original_x if value > x_pixel), default=None)
            if left_x is None or right_x is None or right_x - left_x > 12:
                continue
            fraction = (x_pixel - left_x) / (right_x - left_x)
            predicted_y = original_by_x[left_x] + fraction * (original_by_x[right_x] - original_by_x[left_x])
            if abs(y_pixel - predicted_y) <= max(2.0, max_vertical_span_px / 2):
                safe_added.append((x_pixel, y_pixel))
        if safe_added:
            points = sorted(original_points + safe_added)
        safe_reextraction_ledger.append(
            {
                "series": name,
                "attempted": True,
                "method": "bounded_color_tolerance_retry_with_two_sided_path_residual_gate_v1",
                "original_tolerance": color_tolerance,
                "retry_tolerance": retry_tolerance,
                "original_points": len(original_points),
                "retry_visible_points": len(retry_points),
                "accepted_additional_points": len(safe_added),
                "retry_ambiguous_columns": retry_counts["ambiguous_vertical_span"],
                "status": "adopted_safe_visible_points" if safe_added else "no_safe_additions",
            }
        )
        rows: list[dict[str, Any]] = []
        for x_pixel, y_pixel in points:
            rows.append(
                {
                    "series": name,
                    "x": x_axis.map_pixel(x_pixel),
                    "y": y_axis.map_pixel(y_pixel),
                    "x_px": x_pixel,
                    "y_px": y_pixel,
                    "uncertainty_x": _pixel_uncertainty(x_axis, x_pixel),
                    "uncertainty_y": _pixel_uncertainty(y_axis, y_pixel),
                    "status": "visible_color_supported",
                }
            )
        series_rows[name] = rows
        coverage = len(rows) / total_columns
        coverage_ledger.append(
            {
                "series": name,
                "declared_columns": total_columns,
                "accepted_columns": len(rows),
                "missing_columns": counts["missing"],
                "ambiguous_columns": counts["ambiguous_vertical_span"],
                "excluded_columns": counts.get("excluded_by_confirmed_region", 0),
                "coverage": coverage,
                "status": "pass" if coverage >= minimum_coverage else "failed",
            }
        )

    calibration_pass = (
        x_axis.normalized_max_residual <= 0.02
        and y_axis.normalized_max_residual <= 0.02
    )
    coverage_pass = all(item["status"] == "pass" for item in coverage_ledger)
    any_rows = any(series_rows.values())
    candidate_gates_pass = calibration_pass and coverage_pass and any_rows
    authorized = False
    if candidate_gates_pass:
        extraction_status = "candidate_ready"
    elif any_rows:
        extraction_status = "partial_visible"
    else:
        extraction_status = "not_extracted"

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "candidates.csv"
    candidate_rows = candidate_rows_from_series(
        series_rows,
        source_sha256=project["input"]["sha256"],
        spec_sha256=str(confirmation["spec_sha256"]),
        extractor_id="native_color_line_v1",
    )
    write_pipeline_csv(csv_path, CANDIDATE_FIELDS, candidate_rows)

    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    left, top, right, bottom = plot_bounds
    draw.rectangle((left, top, right, bottom), outline=(255, 0, 255), width=1)
    for name, color in series_list:
        overlay_color = hex_rgb(color)
        for row in series_rows[name]:
            x_pixel = int(row["x_px"])
            y_pixel = int(round(row["y_px"]))
            draw.ellipse(
                (x_pixel - 1, y_pixel - 1, x_pixel + 1, y_pixel + 1),
                outline=overlay_color,
            )
    overlay_path = output_dir / "digitization_overlay.png"
    overlay.save(overlay_path)

    quality_path = output_dir / "quality-assessment.json"
    quality = assess_candidates(
        csv_path,
        quality_path,
        safe_reextraction={
            "attempted": True,
            "source_sha256": project["input"]["sha256"],
            "spec_sha256": confirmation["spec_sha256"],
            "series": safe_reextraction_ledger,
        },
    )

    report = {
        "schema": SCHEMA_EXTRACTION,
        "extractor": {
            "id": "native_color_line_v1",
            "support_level": "candidate",
            "claim": "visible color-supported curve coordinates only",
        },
        "input_contract": {
            "path": project["input"]["path"],
            "sha256": project["input"]["sha256"],
            "width_px": width,
            "height_px": height,
            "coordinate_space": "original_raster_pixels",
            "source_identity_verified": True,
        },
        "plot_bounds_px": list(plot_bounds),
        "calibration": {"x": x_axis.as_dict(), "y": y_axis.as_dict()},
        "configuration": {
            "color_tolerance": color_tolerance,
            "minimum_coverage": minimum_coverage,
            "max_vertical_span_px": max_vertical_span_px,
            "confirmed_exclusion_regions_px": [list(region) for region in exclusion_regions],
            "missing_values_interpolated": False,
            "legacy_overlay_review_status_ignored": overlay_review_status,
            "spec_confirmation_sha256": sha256_file(spec_confirmation_path),
        },
        "coverage_ledger": coverage_ledger,
        "safe_reextraction": safe_reextraction_ledger,
        "residual_audit": {
            "status": "pass" if calibration_pass else "failed",
            "x_normalized_max_residual": x_axis.normalized_max_residual,
            "y_normalized_max_residual": y_axis.normalized_max_residual,
        },
        "artifacts": {
            "csv": csv_path.name,
            "overlay": overlay_path.name,
            "quality_assessment": quality_path.name,
            "visualspec": None,
        },
        "candidate_generation_succeeded": bool(candidate_rows),
        "value_delivery_authorized": False,
        "review_status": "not_reviewed",
        "extraction_status": extraction_status,
        "render_status": "not_run",
        "delivery_status": "working",
        "limitations": [
            "candidate extractor; candidates.csv is not formal data",
            "quality assessment does not replace user review decisions",
            "does not recover hidden observations or author fit parameters",
            "same-color legends, annotations, crossings, and thick vertical strokes "
            "require a tighter verified plot ROI",
        ],
    }
    report_path = output_dir / "extraction_report.json"
    _write_json(report_path, report)

    result_project = dict(project)
    result_project["extraction_status"] = extraction_status
    result_project["review_status"] = "not_reviewed"
    result_project["render_status"] = "not_run"
    result_project["delivery_status"] = "working"
    result_project["routing"] = dict(project["routing"])
    result_project["routing"]["value_delivery_authorized"] = authorized
    result_project["artifacts"] = {
        "extraction_report": report_path.name,
        "candidates_csv": csv_path.name,
        "quality_assessment": quality_path.name,
        "overlay": overlay_path.name,
        "visualspec": None,
    }
    _write_json(output_dir / "figure_project.result.json", result_project)
    write_pipeline_state(
        output_dir,
        extraction_status=extraction_status,
        review_status="not_reviewed",
        render_status="not_run",
        delivery_status="working",
        artifacts={"candidates": csv_path.name, "quality_assessment": quality_path.name},
    )
    return report


def _load_raster_project(
    project_path: Path,
    *,
    allowed_chart_types: set[str],
    extractor_id: str,
    plot_bounds: tuple[int, int, int, int],
    x_anchors: Iterable[tuple[float, float]],
    y_anchors: Iterable[tuple[float, float]],
    x_scale: str,
    y_scale: str,
) -> tuple[dict[str, Any], Image.Image, np.ndarray, AxisCalibration, AxisCalibration]:
    project = _load_json(project_path)
    validation = validate_project(project_path, verify_source=True)
    if validation["status"] != "pass":
        raise FigureEvidenceError("; ".join(validation["errors"]))
    chart_type = project.get("chart", {}).get("chart_type")
    if chart_type not in allowed_chart_types:
        raise FigureEvidenceError(
            f"{extractor_id} requires chart.chart_type in {sorted(allowed_chart_types)}"
        )
    if project.get("input", {}).get("media_type") != "raster_image":
        raise FigureEvidenceError(f"{extractor_id} requires a raster image")
    source = resolve_project_source(project_path, project)
    with Image.open(source) as original:
        image = original.convert("RGB")
    _validate_bounds(plot_bounds, image.width, image.height)
    x_axis = fit_axis(x_anchors, x_scale)
    y_axis = fit_axis(y_anchors, y_scale)
    return project, image, np.asarray(image), x_axis, y_axis


def _extraction_state(
    *,
    calibration_pass: bool,
    grammar_pass: bool,
    any_rows: bool,
    overlay_review_status: str,
) -> tuple[bool, str]:
    candidate_gates_pass = calibration_pass and grammar_pass and any_rows
    # Overlay review is retained as a deprecated compatibility argument, but
    # candidate extraction can never authorize formal values.
    del overlay_review_status
    if candidate_gates_pass:
        return False, "candidate_ready"
    if any_rows:
        return False, "partial_visible"
    return False, "not_extracted"


def _write_component_result(
    *,
    project_path: Path,
    project: dict[str, Any],
    output_dir: Path,
    report: dict[str, Any],
    csv_name: str,
    fieldnames: list[str],
    rows_by_series: dict[str, list[dict[str, Any]]],
    series_order: list[str],
    overlay: Image.Image,
    visualspec: dict[str, Any] | None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    del csv_name, fieldnames, visualspec
    normalized_rows: dict[str, list[dict[str, Any]]] = {}
    for name in series_order:
        normalized_rows[name] = []
        for row in rows_by_series[name]:
            normalized = dict(row)
            if "y_px" not in normalized and "top_y_px" in normalized:
                normalized["y_px"] = normalized["top_y_px"]
            normalized_rows[name].append(normalized)
    csv_path = output_dir / "candidates.csv"
    candidate_rows = candidate_rows_from_series(
        normalized_rows,
        source_sha256=str(report["input_contract"]["sha256"]),
        spec_sha256=str(report["configuration"]["spec_sha256"]),
        extractor_id=str(report["extractor"]["id"]),
    )
    write_pipeline_csv(csv_path, CANDIDATE_FIELDS, candidate_rows)
    overlay_path = output_dir / "digitization_overlay.png"
    overlay.save(overlay_path)
    quality_path = output_dir / "quality-assessment.json"
    assess_candidates(csv_path, quality_path)

    report["artifacts"] = {
        "csv": csv_path.name,
        "overlay": overlay_path.name,
        "quality_assessment": quality_path.name,
        "visualspec": None,
    }
    report["candidate_generation_succeeded"] = bool(candidate_rows)
    report["value_delivery_authorized"] = False
    report["review_status"] = "not_reviewed"
    report["extraction_status"] = "candidate_ready" if candidate_rows else "not_extracted"
    report_path = output_dir / "extraction_report.json"
    _write_json(report_path, report)
    result_project = dict(project)
    result_project["extraction_status"] = report["extraction_status"]
    result_project["review_status"] = "not_reviewed"
    result_project["render_status"] = "not_run"
    result_project["delivery_status"] = "working"
    result_project["routing"] = dict(project["routing"])
    result_project["routing"]["value_delivery_authorized"] = report[
        "value_delivery_authorized"
    ]
    result_project["artifacts"] = {
        "extraction_report": report_path.name,
        "candidates_csv": csv_path.name,
        "quality_assessment": quality_path.name,
        "overlay": overlay_path.name,
        "visualspec": None,
    }
    _write_json(output_dir / "figure_project.result.json", result_project)
    write_pipeline_state(
        output_dir,
        extraction_status=report["extraction_status"],
        review_status="not_reviewed",
        render_status="not_run",
        delivery_status="working",
        artifacts={"candidates": csv_path.name, "quality_assessment": quality_path.name},
    )
    return report


def extract_color_scatter(
    project_path: Path,
    output_dir: Path,
    *,
    plot_bounds: tuple[int, int, int, int],
    x_anchors: Iterable[tuple[float, float]],
    y_anchors: Iterable[tuple[float, float]],
    series: Iterable[tuple[str, str]],
    x_scale: str = "linear",
    y_scale: str = "linear",
    color_tolerance: float = 36.0,
    min_component_area: int = 6,
    max_component_area: int = 400,
    min_fill_ratio: float = 0.35,
    max_aspect_ratio: float = 2.0,
    minimum_points_per_series: int = 1,
    overlay_review_status: str = "pending",
    spec_confirmation_path: Path | None = None,
) -> dict[str, Any]:
    project, image, rgb, x_axis, y_axis = _load_raster_project(
        project_path,
        allowed_chart_types={"scatter"},
        extractor_id="native_color_scatter_v1",
        plot_bounds=plot_bounds,
        x_anchors=x_anchors,
        y_anchors=y_anchors,
        x_scale=x_scale,
        y_scale=y_scale,
    )
    series_list = list(series)
    if not series_list:
        raise FigureEvidenceError("at least one --series name=#RRGGBB is required")
    if len({name for name, _ in series_list}) != len(series_list):
        raise FigureEvidenceError("series names must be unique")
    if spec_confirmation_path is None:
        raise FigureEvidenceError("spec_not_confirmed: --spec-confirmation is required before extraction")
    try:
        confirmation, _ = validate_spec_confirmation(
            project_path,
            spec_confirmation_path,
            plot_bounds=plot_bounds,
            x_anchors=x_anchors,
            y_anchors=y_anchors,
            series=series_list,
        )
    except FigureDataError as exc:
        raise FigureEvidenceError(str(exc)) from exc

    rows_by_series: dict[str, list[dict[str, Any]]] = {}
    component_ledger: list[dict[str, Any]] = []
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(plot_bounds, outline=(255, 0, 255), width=1)

    for name, color in series_list:
        mask = _color_mask(rgb, plot_bounds, hex_rgb(color), color_tolerance)
        components = _connected_components(
            mask,
            left=plot_bounds[0],
            top=plot_bounds[1],
        )
        rows: list[dict[str, Any]] = []
        rejected = 0
        for component in components:
            width_px = int(component["width_px"])
            height_px = int(component["height_px"])
            aspect = max(width_px, height_px) / max(1, min(width_px, height_px))
            if not (
                min_component_area <= component["area_px"] <= max_component_area
                and component["fill_ratio"] >= min_fill_ratio
                and aspect <= max_aspect_ratio
            ):
                rejected += 1
                continue
            x_pixel = float(component["centroid_x_px"])
            y_pixel = float(component["centroid_y_px"])
            rows.append(
                {
                    "series": name,
                    "x": x_axis.map_pixel(x_pixel),
                    "y": y_axis.map_pixel(y_pixel),
                    "x_px": x_pixel,
                    "y_px": y_pixel,
                    "area_px": component["area_px"],
                    "width_px": width_px,
                    "height_px": height_px,
                    "uncertainty_x": _pixel_uncertainty(x_axis, x_pixel),
                    "uncertainty_y": _pixel_uncertainty(y_axis, y_pixel),
                    "status": "visible_component_supported",
                }
            )
            x0, y0, x1, y1 = component["bbox_px"]
            draw.rectangle((x0, y0, x1, y1), outline=hex_rgb(color), width=1)
        rows.sort(key=lambda row: (row["x_px"], row["y_px"]))
        rows_by_series[name] = rows
        component_ledger.append(
            {
                "series": name,
                "detected_components": len(components),
                "accepted_components": len(rows),
                "rejected_components": rejected,
                "minimum_required": minimum_points_per_series,
                "status": "pass"
                if len(rows) >= minimum_points_per_series
                else "failed",
            }
        )

    calibration_pass = (
        x_axis.normalized_max_residual <= 0.02
        and y_axis.normalized_max_residual <= 0.02
    )
    grammar_pass = all(item["status"] == "pass" for item in component_ledger)
    any_rows = any(rows_by_series.values())
    authorized, extraction_status = _extraction_state(
        calibration_pass=calibration_pass,
        grammar_pass=grammar_pass,
        any_rows=any_rows,
        overlay_review_status=overlay_review_status,
    )
    colors = dict(series_list)
    # Candidate extraction never constructs VisualSpec. Formal data.csv is the
    # only allowed digitized input to the VisualSpec stage.
    visualspec = None
    report = {
        "schema": SCHEMA_EXTRACTION,
        "extractor": {
            "id": "native_color_scatter_v1",
            "support_level": "candidate",
            "claim": "visible compact filled color components only",
        },
        "input_contract": {
            "path": project["input"]["path"],
            "sha256": project["input"]["sha256"],
            "width_px": image.width,
            "height_px": image.height,
            "coordinate_space": "original_raster_pixels",
            "source_identity_verified": True,
        },
        "plot_bounds_px": list(plot_bounds),
        "calibration": {"x": x_axis.as_dict(), "y": y_axis.as_dict()},
        "configuration": {
            "spec_sha256": confirmation["spec_sha256"],
            "color_tolerance": color_tolerance,
            "min_component_area": min_component_area,
            "max_component_area": max_component_area,
            "min_fill_ratio": min_fill_ratio,
            "max_aspect_ratio": max_aspect_ratio,
            "minimum_points_per_series": minimum_points_per_series,
            "overlay_review_status": overlay_review_status,
        },
        "component_ledger": component_ledger,
        "value_delivery_authorized": authorized,
        "extraction_status": extraction_status,
        "render_status": "not_run",
        "delivery_status": "working",
        "limitations": [
            "candidate extractor for compact filled markers only",
            "touching, hollow, bubble-sized, occluded, or same-color annotation components are rejected or require a tighter ROI",
        ],
    }
    return _write_component_result(
        project_path=project_path,
        project=project,
        output_dir=output_dir,
        report=report,
        csv_name="digitized_scatter.csv",
        fieldnames=[
            "series",
            "x",
            "y",
            "x_px",
            "y_px",
            "area_px",
            "width_px",
            "height_px",
            "uncertainty_x",
            "uncertainty_y",
            "status",
        ],
        rows_by_series=rows_by_series,
        series_order=[name for name, _ in series_list],
        overlay=overlay,
        visualspec=visualspec,
    )


def extract_color_bars(
    project_path: Path,
    output_dir: Path,
    *,
    plot_bounds: tuple[int, int, int, int],
    x_anchors: Iterable[tuple[float, float]],
    y_anchors: Iterable[tuple[float, float]],
    series: Iterable[tuple[str, str]],
    baseline_pixel: int,
    x_scale: str = "linear",
    y_scale: str = "linear",
    color_tolerance: float = 36.0,
    baseline_tolerance_px: int = 3,
    min_component_area: int = 20,
    min_fill_ratio: float = 0.75,
    minimum_bars_per_series: int = 1,
    overlay_review_status: str = "pending",
    spec_confirmation_path: Path | None = None,
) -> dict[str, Any]:
    project, image, rgb, x_axis, y_axis = _load_raster_project(
        project_path,
        allowed_chart_types={"simple_bar", "grouped_bar", "histogram"},
        extractor_id="native_color_bar_v1",
        plot_bounds=plot_bounds,
        x_anchors=x_anchors,
        y_anchors=y_anchors,
        x_scale=x_scale,
        y_scale=y_scale,
    )
    if not plot_bounds[1] <= baseline_pixel <= plot_bounds[3]:
        raise FigureEvidenceError("baseline pixel must lie inside plot bounds")
    series_list = list(series)
    if not series_list:
        raise FigureEvidenceError("at least one --series name=#RRGGBB is required")
    if len({name for name, _ in series_list}) != len(series_list):
        raise FigureEvidenceError("series names must be unique")
    if spec_confirmation_path is None:
        raise FigureEvidenceError("spec_not_confirmed: --spec-confirmation is required before extraction")
    try:
        confirmation, _ = validate_spec_confirmation(
            project_path,
            spec_confirmation_path,
            plot_bounds=plot_bounds,
            x_anchors=x_anchors,
            y_anchors=y_anchors,
            series=series_list,
        )
    except FigureDataError as exc:
        raise FigureEvidenceError(str(exc)) from exc

    rows_by_series: dict[str, list[dict[str, Any]]] = {}
    component_ledger: list[dict[str, Any]] = []
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(plot_bounds, outline=(255, 0, 255), width=1)
    draw.line(
        (plot_bounds[0], baseline_pixel, plot_bounds[2], baseline_pixel),
        fill=(0, 160, 255),
        width=1,
    )
    baseline_y = y_axis.map_pixel(baseline_pixel)
    y_anchor_values = [value for _, value in y_axis.anchors]
    y_span = max(y_anchor_values) - min(y_anchor_values)
    zero_tolerance = max(abs(y_span) * 1e-6, 1e-12)
    if abs(baseline_y) > zero_tolerance:
        raise FigureEvidenceError(
            "native_color_bar_v1 requires a verified zero baseline"
        )

    for name, color in series_list:
        mask = _color_mask(rgb, plot_bounds, hex_rgb(color), color_tolerance)
        components = _connected_components(
            mask,
            left=plot_bounds[0],
            top=plot_bounds[1],
        )
        rows: list[dict[str, Any]] = []
        rejected = 0
        for component in components:
            x0, y0, x1, y1 = component["bbox_px"]
            if not (
                component["area_px"] >= min_component_area
                and component["fill_ratio"] >= min_fill_ratio
                and abs(y1 - baseline_pixel) <= baseline_tolerance_px
                and component["height_px"] > component["width_px"]
            ):
                rejected += 1
                continue
            x_pixel = (x0 + x1) / 2
            top_pixel = float(y0)
            rows.append(
                {
                    "series": name,
                    "x": x_axis.map_pixel(x_pixel),
                    "y": y_axis.map_pixel(top_pixel),
                    "baseline_y": baseline_y,
                    "x_px": x_pixel,
                    "top_y_px": top_pixel,
                    "baseline_y_px": baseline_pixel,
                    "width_px": component["width_px"],
                    "height_px": component["height_px"],
                    "area_px": component["area_px"],
                    "uncertainty_x": _pixel_uncertainty(x_axis, x_pixel),
                    "uncertainty_y": _pixel_uncertainty(y_axis, top_pixel),
                    "status": "visible_rectangle_supported",
                }
            )
            draw.rectangle((x0, y0, x1, y1), outline=hex_rgb(color), width=1)
        rows.sort(key=lambda row: row["x_px"])
        rows_by_series[name] = rows
        component_ledger.append(
            {
                "series": name,
                "detected_components": len(components),
                "accepted_bars": len(rows),
                "rejected_components": rejected,
                "minimum_required": minimum_bars_per_series,
                "status": "pass"
                if len(rows) >= minimum_bars_per_series
                else "failed",
            }
        )

    calibration_pass = (
        x_axis.normalized_max_residual <= 0.02
        and y_axis.normalized_max_residual <= 0.02
    )
    grammar_pass = all(item["status"] == "pass" for item in component_ledger)
    any_rows = any(rows_by_series.values())
    authorized, extraction_status = _extraction_state(
        calibration_pass=calibration_pass,
        grammar_pass=grammar_pass,
        any_rows=any_rows,
        overlay_review_status=overlay_review_status,
    )
    colors = dict(series_list)
    # Candidate extraction never constructs VisualSpec. Formal data.csv is the
    # only allowed digitized input to the VisualSpec stage.
    visualspec = None
    report = {
        "schema": SCHEMA_EXTRACTION,
        "extractor": {
            "id": "native_color_bar_v1",
            "support_level": "candidate",
            "claim": "visible vertical solid-color rectangles sharing a declared baseline",
        },
        "input_contract": {
            "path": project["input"]["path"],
            "sha256": project["input"]["sha256"],
            "width_px": image.width,
            "height_px": image.height,
            "coordinate_space": "original_raster_pixels",
            "source_identity_verified": True,
        },
        "plot_bounds_px": list(plot_bounds),
        "calibration": {"x": x_axis.as_dict(), "y": y_axis.as_dict()},
        "configuration": {
            "spec_sha256": confirmation["spec_sha256"],
            "color_tolerance": color_tolerance,
            "baseline_pixel": baseline_pixel,
            "baseline_tolerance_px": baseline_tolerance_px,
            "min_component_area": min_component_area,
            "min_fill_ratio": min_fill_ratio,
            "minimum_bars_per_series": minimum_bars_per_series,
            "overlay_review_status": overlay_review_status,
        },
        "component_ledger": component_ledger,
        "value_delivery_authorized": authorized,
        "extraction_status": extraction_status,
        "render_status": "not_run",
        "delivery_status": "working",
        "limitations": [
            "candidate extractor for vertical solid-color rectangles only",
            "gradients, 3D effects, horizontal bars, stacked segments, touching bars, and legend swatches require refusal or a project-level extractor",
        ],
    }
    return _write_component_result(
        project_path=project_path,
        project=project,
        output_dir=output_dir,
        report=report,
        csv_name="digitized_bars.csv",
        fieldnames=[
            "series",
            "x",
            "y",
            "baseline_y",
            "x_px",
            "top_y_px",
            "baseline_y_px",
            "width_px",
            "height_px",
            "area_px",
            "uncertainty_x",
            "uncertainty_y",
            "status",
        ],
        rows_by_series=rows_by_series,
        series_order=[name for name, _ in series_list],
        overlay=overlay,
        visualspec=visualspec,
    )


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Native source-locked figure evidence pipeline for more-paper-workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Fingerprint an image/PDF and create a fail-closed figure project."
    )
    inspect_parser.add_argument("--input", required=True, type=Path)
    inspect_parser.add_argument("--chart-type", choices=sorted(CHART_ROUTES))
    inspect_parser.add_argument("--output-project", required=True, type=Path)

    validate_parser = subparsers.add_parser(
        "validate-project", help="Validate a figure project and recheck source identity."
    )
    validate_parser.add_argument("--project", required=True, type=Path)
    validate_parser.add_argument("--json-out", type=Path)

    spec_parser = subparsers.add_parser(
        "spec-review",
        help="Create figure-spec.json and spec-review.png before any extraction.",
    )
    spec_parser.add_argument("--project", required=True, type=Path)
    spec_parser.add_argument("--plot-bounds", required=True)
    spec_parser.add_argument("--x-anchor", action="append", required=True)
    spec_parser.add_argument("--y-anchor", action="append", required=True)
    spec_parser.add_argument("--series", action="append", required=True)
    spec_parser.add_argument("--series-topology", action="append", required=True)
    spec_parser.add_argument("--exclude-region", action="append", default=[])
    spec_parser.add_argument("--x-scale", choices=["linear", "log10"], default="linear")
    spec_parser.add_argument("--y-scale", choices=["linear", "log10"], default="linear")
    spec_parser.add_argument("--output-dir", required=True, type=Path)

    confirm_parser = subparsers.add_parser(
        "confirm-spec", help="Bind explicit user confirmation to the source, project, spec, and overlay hashes."
    )
    confirm_parser.add_argument("--project", required=True, type=Path)
    confirm_parser.add_argument("--spec", required=True, type=Path)
    confirm_parser.add_argument("--overlay", required=True, type=Path)
    confirm_parser.add_argument("--confirmation", choices=["explicit_user_confirmation"], required=True)
    confirm_parser.add_argument("--output", required=True, type=Path)

    extract_parser = subparsers.add_parser(
        "extract-line",
        help="Candidate extraction of color-distinct raster lines with explicit calibration.",
    )
    extract_parser.add_argument("--project", required=True, type=Path)
    extract_parser.add_argument("--plot-bounds", required=True)
    extract_parser.add_argument("--x-anchor", action="append", required=True)
    extract_parser.add_argument("--y-anchor", action="append", required=True)
    extract_parser.add_argument("--series", action="append", required=True)
    extract_parser.add_argument("--spec-confirmation", required=True, type=Path)
    extract_parser.add_argument("--x-scale", choices=["linear", "log10"], default="linear")
    extract_parser.add_argument("--y-scale", choices=["linear", "log10"], default="linear")
    extract_parser.add_argument("--color-tolerance", type=float, default=36.0)
    extract_parser.add_argument("--minimum-coverage", type=float, default=0.65)
    extract_parser.add_argument("--max-vertical-span-px", type=int, default=12)
    extract_parser.add_argument(
        "--overlay-review",
        choices=["pending", "accepted"],
        default="pending",
        help="Set accepted only after inspecting the generated overlay at original resolution.",
    )
    extract_parser.add_argument("--output-dir", required=True, type=Path)

    scatter_parser = subparsers.add_parser(
        "extract-scatter",
        help="Candidate extraction of compact filled color scatter markers.",
    )
    scatter_parser.add_argument("--project", required=True, type=Path)
    scatter_parser.add_argument("--plot-bounds", required=True)
    scatter_parser.add_argument("--x-anchor", action="append", required=True)
    scatter_parser.add_argument("--y-anchor", action="append", required=True)
    scatter_parser.add_argument("--series", action="append", required=True)
    scatter_parser.add_argument("--spec-confirmation", required=True, type=Path)
    scatter_parser.add_argument("--x-scale", choices=["linear", "log10"], default="linear")
    scatter_parser.add_argument("--y-scale", choices=["linear", "log10"], default="linear")
    scatter_parser.add_argument("--color-tolerance", type=float, default=36.0)
    scatter_parser.add_argument("--min-component-area", type=int, default=6)
    scatter_parser.add_argument("--max-component-area", type=int, default=400)
    scatter_parser.add_argument("--min-fill-ratio", type=float, default=0.35)
    scatter_parser.add_argument("--max-aspect-ratio", type=float, default=2.0)
    scatter_parser.add_argument("--minimum-points-per-series", type=int, default=1)
    scatter_parser.add_argument(
        "--overlay-review",
        choices=["pending", "accepted"],
        default="pending",
    )
    scatter_parser.add_argument("--output-dir", required=True, type=Path)

    bar_parser = subparsers.add_parser(
        "extract-bars",
        help="Candidate extraction of vertical solid-color bars or histogram bins.",
    )
    bar_parser.add_argument("--project", required=True, type=Path)
    bar_parser.add_argument("--plot-bounds", required=True)
    bar_parser.add_argument("--x-anchor", action="append", required=True)
    bar_parser.add_argument("--y-anchor", action="append", required=True)
    bar_parser.add_argument("--series", action="append", required=True)
    bar_parser.add_argument("--spec-confirmation", required=True, type=Path)
    bar_parser.add_argument("--baseline-pixel", required=True, type=int)
    bar_parser.add_argument("--x-scale", choices=["linear", "log10"], default="linear")
    bar_parser.add_argument("--y-scale", choices=["linear", "log10"], default="linear")
    bar_parser.add_argument("--color-tolerance", type=float, default=36.0)
    bar_parser.add_argument("--baseline-tolerance-px", type=int, default=3)
    bar_parser.add_argument("--min-component-area", type=int, default=20)
    bar_parser.add_argument("--min-fill-ratio", type=float, default=0.75)
    bar_parser.add_argument("--minimum-bars-per-series", type=int, default=1)
    bar_parser.add_argument(
        "--overlay-review",
        choices=["pending", "accepted"],
        default="pending",
    )
    bar_parser.add_argument("--output-dir", required=True, type=Path)

    assess_parser = subparsers.add_parser(
        "assess-candidates", help="Run automatic quality assessment and anomaly diagnosis on candidates.csv."
    )
    assess_parser.add_argument("--candidates", required=True, type=Path)
    assess_parser.add_argument("--output", required=True, type=Path)

    review_parser = subparsers.add_parser(
        "init-review", help="Create a hash-bound review-decisions.json template."
    )
    review_parser.add_argument("--candidates", required=True, type=Path)
    review_parser.add_argument("--quality", required=True, type=Path)
    review_parser.add_argument("--spec-confirmation", required=True, type=Path)
    review_parser.add_argument("--output", required=True, type=Path)

    observations_parser = subparsers.add_parser(
        "build-observations", help="Apply complete user review decisions to visible observations.csv."
    )
    observations_parser.add_argument("--candidates", required=True, type=Path)
    observations_parser.add_argument("--quality", required=True, type=Path)
    observations_parser.add_argument("--review-decisions", required=True, type=Path)
    observations_parser.add_argument("--output", required=True, type=Path)

    data_parser = subparsers.add_parser(
        "build-data", help="Build topology-confirmed, style-independent formal data.csv."
    )
    data_parser.add_argument("--observations", required=True, type=Path)
    data_parser.add_argument("--review-decisions", required=True, type=Path)
    data_parser.add_argument("--guide-path", type=Path)
    data_parser.add_argument("--output", required=True, type=Path)
    data_parser.add_argument("--provenance", required=True, type=Path)

    visualspec_parser = subparsers.add_parser(
        "build-visualspec", help="Build VisualSpec only from formal data.csv and its provenance."
    )
    visualspec_parser.add_argument("--data", required=True, type=Path)
    visualspec_parser.add_argument("--provenance", required=True, type=Path)
    visualspec_parser.add_argument("--styles", type=Path)
    visualspec_parser.add_argument("--output", required=True, type=Path)
    visualspec_parser.add_argument("--width-mm", type=float, default=100.0)
    visualspec_parser.add_argument("--height-mm", type=float, default=70.0)
    visualspec_parser.add_argument("--dpi", type=int, default=300)

    contract_parser = subparsers.add_parser(
        "validate-visualspec-data", help="Reject digitized VisualSpec inputs that bypass formal data.csv."
    )
    contract_parser.add_argument("--visualspec", required=True, type=Path)

    delivery_parser = subparsers.add_parser(
        "validate-data-chain", help="Validate candidates-to-delivery lineage without promoting render state."
    )
    delivery_parser.add_argument("--candidates", required=True, type=Path)
    delivery_parser.add_argument("--observations", required=True, type=Path)
    delivery_parser.add_argument("--review-decisions", required=True, type=Path)
    delivery_parser.add_argument("--data", required=True, type=Path)
    delivery_parser.add_argument("--provenance", required=True, type=Path)
    delivery_parser.add_argument("--visualspec", required=True, type=Path)
    delivery_parser.add_argument("--render-manifest", type=Path)
    delivery_parser.add_argument("--json-out", type=Path)

    migration_parser = subparsers.add_parser(
        "migrate-legacy", help="Migrate legacy digitized_lines.csv to candidate-only candidates.csv."
    )
    migration_parser.add_argument("--legacy", required=True, type=Path)
    migration_parser.add_argument("--source-sha256", required=True)
    migration_parser.add_argument("--spec-sha256", required=True)
    migration_parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            payload = inspect_source(args.input, args.chart_type, args.output_project)
            _print(payload)
            return 0
        if args.command == "validate-project":
            payload = validate_project(args.project, verify_source=True)
            if args.json_out:
                _write_json(args.json_out, payload)
            _print(payload)
            return 0 if payload["status"] == "pass" else 2
        if args.command == "spec-review":
            topology = dict(parse_topology(value) for value in args.series_topology)
            payload = build_spec_review(
                args.project,
                args.output_dir,
                plot_bounds=parse_bounds(args.plot_bounds),
                x_anchors=[parse_anchor(value) for value in args.x_anchor],
                y_anchors=[parse_anchor(value) for value in args.y_anchor],
                series=[parse_series(value) for value in args.series],
                curve_topology=topology,
                exclusion_regions=[parse_bounds(value) for value in args.exclude_region],
                x_scale=args.x_scale,
                y_scale=args.y_scale,
            )
            _print(payload)
            return 0
        if args.command == "confirm-spec":
            payload = confirm_spec(
                args.project,
                args.spec,
                args.overlay,
                args.output,
                confirmation=args.confirmation,
            )
            _print(payload)
            return 0
        if args.command == "extract-line":
            if not 0 < args.minimum_coverage <= 1:
                raise FigureEvidenceError("minimum coverage must be in (0, 1]")
            if args.color_tolerance < 0:
                raise FigureEvidenceError("color tolerance must be non-negative")
            if args.max_vertical_span_px < 0:
                raise FigureEvidenceError("max vertical span must be non-negative")
            payload = extract_color_lines(
                args.project,
                args.output_dir,
                plot_bounds=parse_bounds(args.plot_bounds),
                x_anchors=[parse_anchor(value) for value in args.x_anchor],
                y_anchors=[parse_anchor(value) for value in args.y_anchor],
                series=[parse_series(value) for value in args.series],
                x_scale=args.x_scale,
                y_scale=args.y_scale,
                color_tolerance=args.color_tolerance,
                minimum_coverage=args.minimum_coverage,
                max_vertical_span_px=args.max_vertical_span_px,
                overlay_review_status=args.overlay_review,
                spec_confirmation_path=args.spec_confirmation,
            )
            _print(payload)
            return 0 if payload.get("candidate_generation_succeeded") else 3
        if args.command == "extract-scatter":
            if args.color_tolerance < 0:
                raise FigureEvidenceError("color tolerance must be non-negative")
            if not 0 < args.min_fill_ratio <= 1:
                raise FigureEvidenceError("min fill ratio must be in (0, 1]")
            if args.min_component_area <= 0 or args.max_component_area < args.min_component_area:
                raise FigureEvidenceError("component area bounds are invalid")
            if args.max_aspect_ratio < 1:
                raise FigureEvidenceError("max aspect ratio must be at least 1")
            payload = extract_color_scatter(
                args.project,
                args.output_dir,
                plot_bounds=parse_bounds(args.plot_bounds),
                x_anchors=[parse_anchor(value) for value in args.x_anchor],
                y_anchors=[parse_anchor(value) for value in args.y_anchor],
                series=[parse_series(value) for value in args.series],
                x_scale=args.x_scale,
                y_scale=args.y_scale,
                color_tolerance=args.color_tolerance,
                min_component_area=args.min_component_area,
                max_component_area=args.max_component_area,
                min_fill_ratio=args.min_fill_ratio,
                max_aspect_ratio=args.max_aspect_ratio,
                minimum_points_per_series=args.minimum_points_per_series,
                overlay_review_status=args.overlay_review,
                spec_confirmation_path=args.spec_confirmation,
            )
            _print(payload)
            return 0 if payload.get("candidate_generation_succeeded") else 3
        if args.command == "extract-bars":
            if args.color_tolerance < 0:
                raise FigureEvidenceError("color tolerance must be non-negative")
            if not 0 < args.min_fill_ratio <= 1:
                raise FigureEvidenceError("min fill ratio must be in (0, 1]")
            if args.min_component_area <= 0:
                raise FigureEvidenceError("min component area must be positive")
            if args.baseline_tolerance_px < 0:
                raise FigureEvidenceError("baseline tolerance must be non-negative")
            payload = extract_color_bars(
                args.project,
                args.output_dir,
                plot_bounds=parse_bounds(args.plot_bounds),
                x_anchors=[parse_anchor(value) for value in args.x_anchor],
                y_anchors=[parse_anchor(value) for value in args.y_anchor],
                series=[parse_series(value) for value in args.series],
                baseline_pixel=args.baseline_pixel,
                x_scale=args.x_scale,
                y_scale=args.y_scale,
                color_tolerance=args.color_tolerance,
                baseline_tolerance_px=args.baseline_tolerance_px,
                min_component_area=args.min_component_area,
                min_fill_ratio=args.min_fill_ratio,
                minimum_bars_per_series=args.minimum_bars_per_series,
                overlay_review_status=args.overlay_review,
                spec_confirmation_path=args.spec_confirmation,
            )
            _print(payload)
            return 0 if payload.get("candidate_generation_succeeded") else 3
        if args.command == "assess-candidates":
            payload = assess_candidates(args.candidates, args.output)
            _print(payload)
            return 0
        if args.command == "init-review":
            payload = review_template(args.candidates, args.quality, args.spec_confirmation, args.output)
            _print(payload)
            return 0
        if args.command == "build-observations":
            payload = build_observations(args.candidates, args.quality, args.review_decisions, args.output)
            _print(payload)
            return 0
        if args.command == "build-data":
            payload = build_data(args.observations, args.review_decisions, args.output, args.provenance, guide_path=args.guide_path)
            _print(payload)
            return 0
        if args.command == "build-visualspec":
            payload = build_visualspec(
                args.data,
                args.provenance,
                args.output,
                styles_path=args.styles,
                width_mm=args.width_mm,
                height_mm=args.height_mm,
                dpi=args.dpi,
            )
            _print(payload)
            return 0
        if args.command == "validate-visualspec-data":
            payload = validate_visualspec_data_contract(args.visualspec)
            _print(payload)
            return 0 if payload["status"] == "pass" else 2
        if args.command == "validate-data-chain":
            payload = validate_delivery(
                candidates_path=args.candidates,
                observations_path=args.observations,
                decisions_path=args.review_decisions,
                data_path=args.data,
                provenance_path=args.provenance,
                visualspec_path=args.visualspec,
                render_manifest_path=args.render_manifest,
            )
            if args.json_out:
                _write_json(args.json_out, payload)
            _print(payload)
            return 0 if payload["status"] == "pass" else 2
        if args.command == "migrate-legacy":
            payload = migrate_legacy_digitized_lines(
                args.legacy,
                args.output,
                source_sha256=args.source_sha256,
                spec_sha256=args.spec_sha256,
            )
            _print(payload)
            return 0
        parser.error(f"unknown command: {args.command}")
    except (FigureEvidenceError, FigureDataError) as exc:
        _print(
            {
                "schema": "morepaper.figure_pipeline_error.v1",
                "status": "failed",
                "error": str(exc),
            }
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
