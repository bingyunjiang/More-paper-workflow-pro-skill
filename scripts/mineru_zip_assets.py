#!/usr/bin/env python3
"""Scan a Zotero MinerU ZIP cache and prepare Step 7 figure assets."""

from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from workflow_contracts import FigureIndexRecord, inspect_mineru_zip, write_figure_index  # noqa: E402
from mineru_assets import enumerate_mineru_assets, materialize_mineru_asset  # noqa: E402


def scan_mineru_zip(zip_path: Path, output: Path, figures_dir: Path | None, copy_images: bool) -> int:
    summary = inspect_mineru_zip(zip_path)
    if "bad_zip" in summary.warnings or "zip_missing" in summary.warnings:
        payload = {
            "available": False,
            "reason": "zip_missing_or_bad",
            "zip_path": zip_path.as_posix(),
            "summary": summary.__dict__,
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"FIGURE_ASSET_STATUS: {output}")
        print("AUTO_INSERT_FIGURES: false")
        return 0

    records: list[FigureIndexRecord] = []
    copied: list[str] = []
    assets = enumerate_mineru_assets(zip_path)
    for index, asset in enumerate(assets, start=1):
        source_image_path = str(asset.get("source_image_path") or "")
        label = str(asset.get("figure_id") or f"image-{index}")
        local_image_path = ""
        if copy_images and figures_dir and source_image_path:
            try:
                materialized = materialize_mineru_asset(
                    source_image_path,
                    figures_dir,
                    label=label,
                )
                local_image_path = materialized["local_path"]
                copied.append(local_image_path)
            except (FileNotFoundError, KeyError, OSError, ValueError):
                local_image_path = ""

        records.append(FigureIndexRecord(
            item_key=summary.parent_item_key,
            figure_id=label,
            figure_type=str(asset.get("figure_type") or "figure"),
            page=str(asset.get("page") or ""),
            caption=str(asset.get("caption") or ""),
            mentions_in_text=[],
            source_type=str(asset.get("source_type") or "visual_pending"),
            source_item_key=summary.parent_item_key,
            source_attachment_key=summary.attachment_key,
            source_image_path=source_image_path,
            local_image_path=local_image_path,
            section_id=str(asset.get("section_id") or ""),
            claim_binding="",
        ))

    metadata = {
        "source_zip": zip_path.as_posix(),
        "mineru_zip_summary": summary.__dict__,
        "copied_images": copied,
        "auto_insert_figures": bool(records),
        "notes": [
            "MinerU images are candidates only until bound to a claim.",
            "Candidate order is manifest.json, full.md image references, then images/ scan.",
            "PDF remains the truth source for captions, tables, equations, and strong claims.",
        ],
    }
    write_figure_index(output, records, metadata)
    print(f"FIGURE_INDEX: {output}")
    print(f"FIGURES: {len(records)}")
    if copied:
        print(f"COPIED_IMAGES: {len(copied)}")
    print(f"AUTO_INSERT_FIGURES: {bool(records)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Step 7 figure_index.json from a Zotero MinerU ZIP cache.")
    parser.add_argument("--zip", required=True, dest="zip_path", help="Path to LLM-for-Zotero-MinerU-cache-*.zip")
    parser.add_argument("--output", default="figure_index.json", help="Output figure_index.json path")
    parser.add_argument("--figures-dir", default="figures", help="Directory for selected/copied images")
    parser.add_argument("--copy-images", action="store_true", help="Copy all manifest figures into --figures-dir")
    args = parser.parse_args()

    return scan_mineru_zip(
        zip_path=Path(args.zip_path).expanduser().resolve(),
        output=Path(args.output).expanduser(),
        figures_dir=Path(args.figures_dir).expanduser() if args.figures_dir else None,
        copy_images=args.copy_images,
    )


if __name__ == "__main__":
    raise SystemExit(main())
