from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .model import DiagramSpecError, load_spec, sha256_file
from .render import build_scene, publication_profile, render_png, render_svg, validate_cjk_font_coverage


CHECK_SCHEMA = "morepaper.diagram-check.v1"


def _write_atomic(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8"}
    with tempfile.NamedTemporaryFile(mode=mode, dir=path.parent, delete=False, **kwargs) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _update_evidence(project_root: Path, record: dict[str, Any]) -> Path:
    path = project_root / "figure_evidence_report.json"
    payload: dict[str, Any] = {"schema_version": "figure-evidence.v1", "records": []}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and existing.get("schema_version") == "figure-evidence.v1" and isinstance(existing.get("records"), list):
                payload = existing
        except (OSError, json.JSONDecodeError):
            pass
    records = [item for item in payload["records"] if not (isinstance(item, dict) and item.get("figure_id") == record["figure_id"])]
    records.append(record)
    payload["records"] = records
    _write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def render_from_file(spec_path: str | Path, output_dir: str | Path, *, inspect: bool = False) -> dict[str, Any]:
    spec = load_spec(spec_path)
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    project_root = output.parent
    base = output / spec.figure_id
    svg_path = base.with_suffix(".svg")
    png_path = base.with_suffix(".png")
    check_path = output / f"{spec.figure_id}.diagram-check.json"
    inspect_path = output / f"{spec.figure_id}.inspect.svg"

    scene = build_scene(spec)
    if any(item["severity"] == "fail" for item in scene.findings):
        report = {
            "schema_version": CHECK_SCHEMA,
            "figure_id": spec.figure_id,
            "status": "fail",
            "diagram_type": spec.diagram_type,
            "diagram_style": spec.style,
            "spec_path": _relative(spec.source_path, project_root),
            "spec_sha256": spec.source_sha256,
            "composition_score": scene.score,
            "publication_profile": publication_profile(spec),
            "findings": scene.findings,
        }
        _write_atomic(check_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        raise DiagramSpecError("composition_failed", "diagram composition failed; inspect the check report")

    try:
        validate_cjk_font_coverage(spec)
    except DiagramSpecError as error:
        report = {
            "schema_version": CHECK_SCHEMA,
            "figure_id": spec.figure_id,
            "status": "fail",
            "diagram_type": spec.diagram_type,
            "diagram_style": spec.style,
            "spec_path": _relative(spec.source_path, project_root),
            "spec_sha256": spec.source_sha256,
            "composition_score": scene.score,
            "publication_profile": publication_profile(spec),
            "findings": [{"severity": "fail", "code": error.code, "message": str(error)}],
        }
        _write_atomic(check_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        raise

    svg = render_svg(scene)
    _write_atomic(svg_path, svg + "\n")
    render_png(scene, png_path)
    if inspect:
        _write_atomic(inspect_path, render_svg(scene, inspect=True) + "\n")

    svg_hash = sha256_file(svg_path)
    png_hash = sha256_file(png_path)
    report = {
        "schema_version": CHECK_SCHEMA,
        "figure_id": spec.figure_id,
        "status": "pass",
        "diagram_type": spec.diagram_type,
        "diagram_style": spec.style,
        "spec_path": _relative(spec.source_path, project_root),
        "spec_sha256": spec.source_sha256,
        "svg_path": _relative(svg_path, project_root),
        "svg_sha256": svg_hash,
        "png_path": _relative(png_path, project_root),
        "png_sha256": png_hash,
        "inspect_path": _relative(inspect_path, project_root) if inspect else "",
        "node_count": len(spec.nodes),
        "edge_count": len(spec.edges),
        "composition_score": scene.score,
        "publication_profile": publication_profile(spec),
        "findings": scene.findings,
    }
    _write_atomic(check_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    check_hash = sha256_file(check_path)
    evidence = {
        "schema_version": "figure-evidence.v1",
        "figure_id": spec.figure_id,
        "figure_intent": spec.title or spec.diagram_type,
        "evidence_basis": "author_provided_structure",
        "evidence_status": "rendered_from_reviewable_spec",
        "recommended_action": "insert_generated_diagram",
        "generation_backend": "diagram",
        "figure_asset_action": "generate_new",
        "figure_transform_authorization": "not_required",
        "diagram_type": spec.diagram_type,
        "diagram_style": spec.style,
        "diagram_spec_path": _relative(spec.source_path, project_root),
        "diagram_spec_sha256": spec.source_sha256,
        "diagram_svg_path": _relative(svg_path, project_root),
        "diagram_svg_sha256": svg_hash,
        "diagram_png_path": _relative(png_path, project_root),
        "diagram_png_sha256": png_hash,
        "diagram_validation_report": _relative(check_path, project_root),
        "diagram_validation_report_sha256": check_hash,
        "diagram_validation_status": "pass",
        "verification_status": "pass",
    }
    evidence_path = _update_evidence(project_root, evidence)
    return {
        "status": "pass",
        "figure_id": spec.figure_id,
        "svg": str(svg_path),
        "png": str(png_path),
        "check": str(check_path),
        "inspect": str(inspect_path) if inspect else "",
        "evidence": str(evidence_path),
    }


def failure_report(spec_path: str | Path, output_dir: str | Path, error: DiagramSpecError) -> Path:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(spec_path)
    figure_id = source.stem
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict) and isinstance(payload.get("figure_id"), str):
            figure_id = payload["figure_id"]
    except (OSError, json.JSONDecodeError):
        pass
    path = output / f"{figure_id}.diagram-check.json"
    report = {
        "schema_version": CHECK_SCHEMA,
        "figure_id": figure_id,
        "status": "needs_author_check" if error.needs_author_check else "fail",
        "findings": [{"severity": "fail", "code": error.code, "message": str(error)}],
    }
    _write_atomic(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return path
