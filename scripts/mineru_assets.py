from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable

from workflow_contracts import inspect_mineru_zip


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _internal_path(value: str) -> str:
    path = value.strip().strip("<>").split("#", 1)[0]
    while path.startswith("./"):
        path = path[2:]
    return path


def _asset_key(asset: dict[str, Any]) -> tuple[str, str]:
    path = _clean(asset.get("internal_path")).lower()
    kind = _clean(asset.get("figure_type") or "figure").lower()
    return kind, path


def _prefer_asset(current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    current_score = (
        bool(_clean(current.get("caption"))),
        bool(_clean(current.get("page"))),
        bool(_clean(current.get("section_id"))),
    )
    candidate_score = (
        bool(_clean(candidate.get("caption"))),
        bool(_clean(candidate.get("page"))),
        bool(_clean(candidate.get("section_id"))),
    )
    return candidate if candidate_score > current_score else current


def _manifest_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []

    def add_items(
        items: Any,
        *,
        figure_type: str,
        section_id: str = "",
        section_heading: str = "",
    ) -> None:
        if not isinstance(items, list):
            return
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            internal = _internal_path(
                _clean(item.get("path") or item.get("img_path") or item.get("source_image_path"))
            )
            if not internal:
                continue
            label = _clean(
                item.get("label")
                or item.get("figure_id")
                or item.get("table_id")
                or f"{figure_type}-{index}"
            )
            caption_value = item.get("caption")
            if isinstance(caption_value, list):
                caption = " ".join(_clean(part) for part in caption_value if _clean(part))
            else:
                caption = _clean(
                    caption_value or item.get("image_caption") or item.get("table_caption")
                )
            assets.append(
                {
                    "figure_id": label,
                    "figure_type": figure_type,
                    "page": _clean(item.get("page") or item.get("page_idx")),
                    "caption": caption,
                    "internal_path": internal,
                    "section_id": section_id,
                    "section_heading": section_heading,
                    "source_stage": "manifest",
                }
            )

    sections = manifest.get("sections")
    if isinstance(sections, list):
        for section_index, section in enumerate(sections, 1):
            if not isinstance(section, dict):
                continue
            section_id = _clean(section.get("id")) or f"section-{section_index:02d}"
            section_heading = _clean(section.get("heading"))
            add_items(
                section.get("figures"),
                figure_type="figure",
                section_id=section_id,
                section_heading=section_heading,
            )
            add_items(
                section.get("tables"),
                figure_type="table",
                section_id=section_id,
                section_heading=section_heading,
            )
    add_items(manifest.get("allFigures"), figure_type="figure")
    add_items(manifest.get("allTables"), figure_type="table")
    return assets


def _markdown_assets(text: str) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for index, match in enumerate(MARKDOWN_IMAGE_RE.finditer(text), 1):
        internal = _internal_path(match.group(2))
        if not internal or Path(internal).suffix.lower() not in IMAGE_SUFFIXES:
            continue
        caption = _clean(match.group(1))
        assets.append(
            {
                "figure_id": Path(internal).stem or f"image-{index}",
                "figure_type": "figure",
                "page": "",
                "caption": caption,
                "internal_path": internal,
                "section_id": "",
                "section_heading": "",
                "source_stage": "full_md",
            }
        )
    return assets


def enumerate_mineru_assets(zip_path: str | Path) -> list[dict[str, Any]]:
    path = Path(zip_path).expanduser().resolve()
    summary = inspect_mineru_zip(path)
    if "zip_missing" in summary.warnings or "bad_zip" in summary.warnings:
        return []

    candidates: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        if summary.has_manifest_json:
            try:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8", errors="replace"))
            except (KeyError, json.JSONDecodeError):
                manifest = {}
            if isinstance(manifest, dict):
                candidates.extend(_manifest_assets(manifest))

        if summary.has_full_md:
            try:
                full_md = archive.read("full.md").decode("utf-8", errors="replace")
            except KeyError:
                full_md = ""
            candidates.extend(_markdown_assets(full_md))

        for name in archive.namelist():
            internal = _internal_path(name)
            if (
                internal.startswith("images/")
                and not internal.endswith("/")
                and Path(internal).suffix.lower() in IMAGE_SUFFIXES
            ):
                candidates.append(
                    {
                        "figure_id": Path(internal).stem,
                        "figure_type": "figure",
                        "page": "",
                        "caption": "",
                        "internal_path": internal,
                        "section_id": "",
                        "section_heading": "",
                        "source_stage": "images_scan",
                    }
                )

    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for asset in candidates:
        key = _asset_key(asset)
        if not key[1]:
            continue
        if key in deduplicated:
            deduplicated[key] = _prefer_asset(deduplicated[key], asset)
        else:
            deduplicated[key] = asset

    records: list[dict[str, Any]] = []
    for asset in deduplicated.values():
        record = dict(asset)
        record.update(
            {
                "zip_path": path.as_posix(),
                "source_image_path": f"{path.as_posix()}::{asset['internal_path']}",
                "source_item_key": summary.parent_item_key,
                "source_attachment_key": summary.attachment_key,
                "source_filename": summary.source_filename,
                "source_type": "caption_plus_text"
                if _clean(asset.get("caption"))
                else "visual_pending",
            }
        )
        records.append(record)
    return records


def match_mineru_zip(
    record: dict[str, Any],
    zip_paths: Iterable[Path],
) -> Path | None:
    paths = [Path(path).expanduser().resolve() for path in zip_paths]
    item_key = _clean(record.get("zotero_item_key") or record.get("item_key"))
    attachment_key = _clean(
        record.get("zotero_attachment_key") or record.get("attachment_key")
    )

    summaries = [(path, inspect_mineru_zip(path)) for path in paths]
    if item_key:
        exact = [path for path, summary in summaries if summary.parent_item_key == item_key]
        if len(exact) == 1:
            return exact[0]
        if attachment_key:
            exact_attachment = [
                path
                for path, summary in summaries
                if summary.parent_item_key == item_key
                and summary.attachment_key == attachment_key
            ]
            if len(exact_attachment) == 1:
                return exact_attachment[0]
    if attachment_key:
        exact = [path for path, summary in summaries if summary.attachment_key == attachment_key]
        if len(exact) == 1:
            return exact[0]

    identity_values = [
        _clean(record.get("record_id")),
        _clean(record.get("citekey")),
        _clean(record.get("title")),
        _clean(record.get("paper_title")),
        _clean(record.get("pdf_path") or record.get("source_pdf")),
    ]
    record_words: set[str] = set()
    for value in identity_values:
        for word in re.findall(r"[a-z0-9]+", value.lower()):
            if len(word) > 3 and not word.isdigit():
                record_words.add(word)
    if not record_words:
        return None

    best_path: Path | None = None
    best_score = 0.0
    for path, summary in summaries:
        zip_words = {
            word
            for word in re.findall(r"[a-z0-9]+", summary.source_filename.lower())
            if len(word) > 3 and not word.isdigit()
        }
        if not zip_words:
            continue
        overlap = len(record_words & zip_words)
        if overlap < 3:
            continue
        score = overlap / max(len(record_words), len(zip_words))
        if score >= 0.35 and score > best_score:
            best_path = path
            best_score = score
    return best_path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def materialize_mineru_asset(
    source_image_path: str,
    figures_dir: Path,
    *,
    label: str = "",
) -> dict[str, str]:
    if "::" not in source_image_path:
        raise ValueError("MinerU source path must use <zip>::<internal_path>")
    zip_text, internal = source_image_path.split("::", 1)
    zip_path = Path(zip_text).expanduser().resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        data = archive.read(internal)
    digest = sha256_bytes(data)
    suffix = Path(internal).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        suffix = ".bin"
    stem = re.sub(r"[^\w.-]+", "-", label.strip(), flags=re.UNICODE).strip("-")
    stem = stem[:48] or Path(internal).stem[:48] or "figure"
    figures_dir.mkdir(parents=True, exist_ok=True)
    target = figures_dir / f"{stem}-{digest[:12]}{suffix}"
    if not target.exists():
        target.write_bytes(data)
    return {
        "local_path": target.resolve().as_posix(),
        "source_zip": zip_path.as_posix(),
        "source_zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "source_internal_path": internal,
        "source_image_sha256": digest,
        "materialized_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
