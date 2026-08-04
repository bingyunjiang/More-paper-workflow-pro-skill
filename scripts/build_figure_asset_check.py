from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mineru_assets import IMAGE_SUFFIXES, enumerate_mineru_assets


SCHEMA = "figure-asset-check.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_figure_index(path: Path | None) -> tuple[int, str]:
    if path is None or not path.is_file():
        return 0, ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0, "invalid_json"
    records = payload.get("records") if isinstance(payload, dict) else None
    return (len(records), "") if isinstance(records, list) else (0, "records_missing")


def build_asset_check(
    *,
    mineru_zips: list[Path],
    figure_index: Path | None,
    image_dirs: list[Path],
    pdfs: list[Path],
    figure_action: str,
    figure_mode: str,
    transform_authorization: str,
    figure_kind: str = "auto",
) -> dict[str, Any]:
    zip_records: list[dict[str, Any]] = []
    for zip_path in mineru_zips:
        resolved = zip_path.expanduser().resolve()
        assets = enumerate_mineru_assets(resolved)
        zip_records.append(
            {
                "path": resolved.as_posix(),
                "exists": resolved.is_file(),
                "sha256": _sha256(resolved) if resolved.is_file() else "",
                "candidate_count": len(assets),
            }
        )

    figure_index_count, figure_index_error = _load_figure_index(figure_index)
    local_images: list[str] = []
    for image_dir in image_dirs:
        resolved = image_dir.expanduser().resolve()
        if not resolved.is_dir():
            continue
        local_images.extend(
            path.as_posix()
            for path in sorted(resolved.rglob("*"))
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    pdf_records = [
        {
            "path": path.expanduser().resolve().as_posix(),
            "exists": path.expanduser().resolve().is_file(),
        }
        for path in pdfs
    ]

    direct_original_candidates = bool(
        any(record["candidate_count"] > 0 for record in zip_records)
        or figure_index_count > 0
        or local_images
    )
    readable_pdf_available = any(record["exists"] for record in pdf_records)
    original_assets_available = direct_original_candidates or readable_pdf_available
    action = figure_action
    if action == "auto":
        action = "insert_original" if original_assets_available else "none"

    if action == "insert_original":
        backend = "not_applicable"
        authorization = "not_required"
    elif action == "generate_new":
        backend = "diagram" if figure_kind == "diagram" else "quick"
        authorization = "not_required"
    elif action in {"redraw", "digitize"}:
        backend = "reproduction"
        authorization = transform_authorization
    else:
        backend = "not_applicable"
        authorization = "not_required"

    mode = figure_mode
    if mode == "auto":
        if action == "insert_original" and direct_original_candidates:
            mode = "auto_insert"
        elif action == "insert_original" and readable_pdf_available:
            mode = "post_write"
        elif action in {"generate_new", "redraw", "digitize"}:
            mode = "post_write"
        else:
            mode = "skip"

    errors: list[str] = []
    if action == "insert_original" and not original_assets_available:
        errors.append("insert_original_requested_without_available_assets")
    if action in {"redraw", "digitize"} and authorization != "explicit_user_request":
        errors.append("figure_transform_requires_explicit_user_request")
    if figure_index_error:
        errors.append(f"figure_index_{figure_index_error}")

    return {
        "schema_version": SCHEMA,
        "status": "blocked" if errors else "ready",
        "figure_mode": mode,
        "figure_asset_action": action,
        "figure_backend": backend,
        "figure_transform_authorization": authorization,
        "figure_kind": figure_kind,
        "original_assets_available": original_assets_available,
        "direct_original_candidates": direct_original_candidates,
        "pdf_direct_fallback_available": readable_pdf_available,
        "checked_assets": {
            "mineru_zips": zip_records,
            "figure_index": {
                "path": figure_index.expanduser().resolve().as_posix()
                if figure_index is not None
                else "",
                "record_count": figure_index_count,
            },
            "local_images": {
                "directories": [
                    path.expanduser().resolve().as_posix() for path in image_dirs
                ],
                "count": len(local_images),
                "paths": local_images,
            },
            "pdfs": pdf_records,
        },
        "routing_reason": (
            "existing_original_assets"
            if action == "insert_original" and direct_original_candidates
            else "pdf_direct_candidate_pending_manual_check"
            if action == "insert_original" and readable_pdf_available
            else "explicit_new_diagram_request"
            if action == "generate_new" and figure_kind == "diagram"
            else "explicit_new_figure_request"
            if action == "generate_new"
            else "explicit_transform_request"
            if action in {"redraw", "digitize"}
            else "no_figure_assets_or_figure_request"
        ),
        "errors": errors,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    checked = payload["checked_assets"]
    return "\n".join(
        [
            "# Figure Asset Check",
            "",
            f"- status: {payload['status']}",
            f"- figure_mode: {payload['figure_mode']}",
            f"- figure_asset_action: {payload['figure_asset_action']}",
            f"- figure_backend: {payload['figure_backend']}",
            "- figure_transform_authorization: "
            + payload["figure_transform_authorization"],
            f"- figure_kind: {payload['figure_kind']}",
            f"- original_assets_available: {str(payload['original_assets_available']).lower()}",
            f"- mineru_zip_count: {len(checked['mineru_zips'])}",
            f"- mineru_candidate_count: {sum(item['candidate_count'] for item in checked['mineru_zips'])}",
            f"- figure_index_record_count: {checked['figure_index']['record_count']}",
            f"- local_image_count: {checked['local_images']['count']}",
            f"- readable_pdf_count: {sum(1 for item in checked['pdfs'] if item['exists'])}",
            f"- routing_reason: {payload['routing_reason']}",
            "",
            "## Errors",
            "",
            *([f"- {item}" for item in payload["errors"]] or ["- none"]),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Step 7 figure assets and derive a deterministic figure route."
    )
    parser.add_argument("--mineru-zip", action="append", default=[], type=Path)
    parser.add_argument("--figure-index", type=Path)
    parser.add_argument("--images-dir", action="append", default=[], type=Path)
    parser.add_argument("--pdf", action="append", default=[], type=Path)
    parser.add_argument(
        "--figure-action",
        choices=["auto", "insert_original", "generate_new", "redraw", "digitize"],
        default="auto",
    )
    parser.add_argument(
        "--figure-mode",
        choices=["auto", "auto_insert", "post_write", "skip"],
        default="auto",
    )
    parser.add_argument(
        "--transform-authorization",
        choices=["not_required", "explicit_user_request"],
        default="not_required",
    )
    parser.add_argument(
        "--figure-kind",
        choices=["auto", "chart", "diagram"],
        default="auto",
    )
    parser.add_argument("--output-json", default="figure_asset_check.json", type=Path)
    parser.add_argument("--output-md", default="figure_asset_check.md", type=Path)
    args = parser.parse_args()

    payload = build_asset_check(
        mineru_zips=args.mineru_zip,
        figure_index=args.figure_index,
        image_dirs=args.images_dir,
        pdfs=args.pdf,
        figure_action=args.figure_action,
        figure_mode=args.figure_mode,
        transform_authorization=args.transform_authorization,
        figure_kind=args.figure_kind,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(f"FIGURE_ASSET_CHECK_JSON: {args.output_json}")
    print(f"FIGURE_ASSET_CHECK_MD: {args.output_md}")
    print(f"FIGURE_ROUTE_STATUS: {payload['status']}")
    return 0 if payload["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
