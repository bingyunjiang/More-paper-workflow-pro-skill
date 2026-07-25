#!/usr/bin/env python3
"""Resolve [图: xxx] markers in a writing draft by matching against figure candidates.

Image quality hierarchy (best → worst):
  1. MinerU ZIP with captions     (source_type=caption_plus_text)
  2. MinerU ZIP without captions  (source_type=visual_pending)
  3. figure_index.json figures    (may have captions)
  4. PyMuPDF direct extraction    (pdf_direct, no captions)
  5. No match → keep placeholder + warning

Usage:
  python scripts/resolve_figure_refs.py \\
    --draft draft.md \\
    --cards deep_read_cards.json \\
    --output draft_resolved.md

  # With multiple card files:
  python scripts/resolve_figure_refs.py \\
    --draft draft.md \\
    --cards section1_cards.json --cards section2_cards.json \\
    --output draft_resolved.md
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
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from workflow_contracts import normalize_doi  # noqa: E402
except ImportError:
    normalize_doi = None  # type: ignore[assignment]
from mineru_assets import materialize_mineru_asset  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_json(path: str | Path | None) -> Any:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))


def _load_cards(paths: list[str]) -> list[dict[str, Any]]:
    """Load figure_candidates from one or more deep_read_cards.json files."""
    all_candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        payload = _load_json(path)
        records = payload.get("records") if isinstance(payload, dict) else []
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            for fig in record.get("figure_candidates") or []:
                uid = _clean(fig.get("source_image_path") or fig.get("local_image_path"))
                if uid and uid not in seen:
                    seen.add(uid)
                    # Attach source metadata from the card
                    fig_copy = dict(fig)
                    fig_copy["_image_source"] = record.get("source_trace", {}).get("image_source", "unknown")
                    fig_copy["_text_source"] = record.get("source_trace", {}).get("text_source", "unknown")
                    fig_copy["_citekey"] = _clean(record.get("citekey"))
                    fig_copy["_title"] = _clean(record.get("title"))
                    fig_copy["_reading_depth"] = _clean(record.get("reading_depth"))
                    fig_copy["_source_trace"] = dict(record.get("source_trace") or {})
                    all_candidates.append(fig_copy)
    return all_candidates


def _load_figure_index(path: str | Path | None) -> list[dict[str, Any]]:
    """Load figures from a figure_index.json file."""
    payload = _load_json(path)
    records = payload.get("records") if isinstance(payload, dict) else []
    if isinstance(records, list):
        return [r for r in records if isinstance(r, dict)]
    return []


# ---------------------------------------------------------------------------
# Marker scanning
# ---------------------------------------------------------------------------

_MARKER_PATTERN = re.compile(r"\[图[：:]\s*(.+?)\]")


def _find_markers(text: str) -> list[dict[str, Any]]:
    """Find all [图: xxx] markers in the text.

    Returns list of dicts: {description, start, end, context_before}
    """
    markers: list[dict[str, Any]] = []
    for match in _MARKER_PATTERN.finditer(text):
        desc = match.group(1).strip()
        if not desc:
            continue
        context_start = max(0, match.start() - 300)
        context_before = text[context_start:match.start()]
        markers.append({
            "description": desc,
            "start": match.start(),
            "end": match.end(),
            "context_before": _clean(context_before),
        })
    return markers


# ---------------------------------------------------------------------------
# Figure scoring
# ---------------------------------------------------------------------------

# Keywords that bridge Chinese descriptions to English captions
_DESCRIPTION_BRIDGE: dict[str, list[str]] = {
    "结构": ["structure", "schematic", "diagram", "layout", "internal", "external", "cross section"],
    "示意": ["schematic", "diagram", "overview", "illustration"],
    "流程": ["flow", "process", "pipeline", "workflow", "procedure"],
    "结果": ["result", "comparison", "performance", "experiment", "versus"],
    "对比": ["comparison", "versus", "compare", "baseline"],
    "方法": ["method", "model", "framework", "architecture", "approach"],
    "验证": ["validation", "verification", "experimental", "error"],
    "实验": ["experiment", "experimental", "test", "measurement"],
    "曲线": ["curve", "plot", "trend", "versus"],
    "温度": ["temperature", "thermal", "heat"],
    "气流": ["airflow", "air", "flow", "ventilation"],
    "散热": ["heat dissipation", "thermal", "cooling", "temperature"],
    "充电": ["charging", "charge", "pile"],
    "模块": ["module", "unit", "component"],
    "优化": ["optimization", "optimal", "improve"],
    "网络": ["network", "architecture", "layer"],
    "训练": ["training", "learn", "regression"],
    "分布": ["distribution", "layout", "arrangement"],
    "边界": ["boundary", "edge", "domain"],
    "网格": ["mesh", "grid", "discretization"],
    "模型": ["model", "framework", "schematic"],
    "设计": ["design", "configuration", "layout"],
    "变量": ["variable", "parameter", "factor"],
}


def _description_keywords(description: str, context: str) -> list[str]:
    """Extract matchable keywords from a Chinese description and surrounding context.

    Bridge expansion only uses the description itself (not context) to stay precise.
    Context is only used to find domain-specific English terms already in the text.
    """
    keywords: list[str] = []
    # Phase 1: bridge the Chinese description to English signal terms
    desc_lower = description.lower()
    for chinese_term, english_terms in _DESCRIPTION_BRIDGE.items():
        if chinese_term in desc_lower:
            keywords.extend(english_terms)
    # Phase 2: extract raw English/alphanumeric tokens from description
    for word in re.findall(r"[a-zA-Z0-9._%+\-]{2,}", description):
        keywords.append(word.lower())
    # Phase 3: supplement with domain English terms from surrounding context
    context_en = re.findall(r"[a-zA-Z]{4,}", context.lower())
    from collections import Counter
    context_freq = Counter(context_en)
    # Add top frequent English terms from context (likely domain terms)
    for term, _ in context_freq.most_common(8):
        if term not in {"that", "this", "with", "from", "into", "each", "also"}:
            keywords.append(term)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        if kw.lower() not in seen and len(kw) >= 2:
            seen.add(kw.lower())
            result.append(kw)
    return result


def _figure_search_blob(fig: dict[str, Any]) -> str:
    """Build a searchable text blob from a figure candidate."""
    parts = [
        _clean(fig.get("figure_id")),
        _clean(fig.get("caption")),
    ]
    return " ".join(p for p in parts if p).lower()


def _image_quality_score(fig: dict[str, Any]) -> int:
    """Score image source quality. Higher = better for writing.

    Quality tiers:
      4 = MinerU ZIP with caption (caption_plus_text)
      3 = MinerU ZIP or figure_index with any caption
      2 = MinerU ZIP without caption / PyMuPDF from MinerU-verified paper
      1 = PyMuPDF direct extraction (no caption)
      0 = unknown
    """
    img_src = _clean(fig.get("_image_source", "")).lower()
    caption = _clean(fig.get("caption", ""))

    if "mineru" in img_src and caption:
        return 4
    if caption:
        return 3
    if "mineru" in img_src:
        return 2
    if "pdf_direct" in img_src or "pymupdf" in img_src:
        return 1
    return 0


def _score_figure(fig: dict[str, Any], keywords: list[str]) -> tuple[int, int]:
    """Score a figure candidate against keywords.

    Returns (keyword_score, quality_score) tuple for sorting.
    Higher keyword_score = better content match.
    Higher quality_score = better source quality.
    """
    blob = _figure_search_blob(fig)
    lowered_kw = [k.lower() for k in keywords if k]
    if not lowered_kw:
        return (0, _image_quality_score(fig))
    keyword_score = sum(1 for kw in lowered_kw if kw in blob)
    return (keyword_score, _image_quality_score(fig))


# ---------------------------------------------------------------------------
# Image path resolution (handles MinerU ZIP internal paths)
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _materialize_image(fig: dict[str, Any], figures_dir: Path) -> dict[str, str]:
    """Materialize only the selected candidate and return source lineage.

    Handles:
      - ``local_image_path`` — already on disk, use directly
      - ``source_image_path`` with ``zip::path`` — extract from MinerU ZIP
      - Absolute path — use as-is
      - Relative path — use as-is
    """
    local = _clean(fig.get("local_image_path"))
    source = _clean(fig.get("source_image_path"))
    label = _clean(fig.get("figure_id"))
    figures_dir = figures_dir.resolve()
    figures_dir.mkdir(parents=True, exist_ok=True)

    if "::" in source:
        try:
            return materialize_mineru_asset(source, figures_dir, label=label)
        except (FileNotFoundError, KeyError, OSError, ValueError):
            return {"local_path": "", "source_image_path": source}

    candidate = Path(local or source).expanduser()
    if not candidate.is_absolute():
        candidate = candidate.resolve()
    if not candidate.is_file():
        return {"local_path": "", "source_image_path": source or local}
    data = candidate.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    suffix = candidate.suffix.lower() or ".bin"
    safe_label = re.sub(r"[^\w.-]+", "-", label, flags=re.UNICODE).strip("-")
    stem = safe_label[:48] or candidate.stem[:48] or "figure"
    target = figures_dir / f"{stem}-{digest[:12]}{suffix}"
    if not target.exists():
        target.write_bytes(data)
    return {
        "local_path": target.as_posix(),
        "source_file": candidate.as_posix(),
        "source_image_path": source,
        "source_image_sha256": digest,
        "materialized_sha256": _sha256(target),
    }


# ---------------------------------------------------------------------------
# Figure block generation
# ---------------------------------------------------------------------------

def _build_figure_block(
    fig: dict[str, Any],
    fig_number: int,
    description: str,
    draft_path: Path,
    figures_dir: Path,
) -> tuple[str, dict[str, str]]:
    """Build the minimal text-figure unit: 引出句 + 图 + 图注."""
    provenance = _materialize_image(fig, figures_dir)
    img_path = provenance.get("local_path", "")
    if not img_path:
        return f"[图 {fig_number}：{description} — 图片路径缺失]", provenance

    # Compute relative path from draft location
    rel = img_path
    try:
        p = Path(img_path).resolve()
        draft_parent = draft_path.parent.resolve()
        rel = Path(os.path.relpath(p, draft_parent)).as_posix()
    except Exception:
        rel = Path(img_path).name
    provenance["draft_relative_path"] = rel

    raw_caption = _clean(fig.get("caption")) or ""
    orig_figure_id = _clean(fig.get("figure_id")) or ""

    # Strip redundant figure_id prefix from caption (e.g. "Fig. 1. Internal..." → "Internal...")
    if orig_figure_id and raw_caption.lower().startswith(orig_figure_id.lower()):
        raw_caption = raw_caption[len(orig_figure_id):].lstrip(".,;: ")
    # Also strip generic "Fig. N." prefix
    raw_caption = re.sub(r"^Fig\.?\s*\d+[\.\s]*", "", raw_caption, flags=re.IGNORECASE).strip()

    display_caption = raw_caption or description

    # Build source attribution in skill-required format: 作者, 年份, 图 xxx。已读全文
    citekey = _clean(fig.get("_citekey"))
    reading_depth = _clean(fig.get("_reading_depth"))
    src_label = ""
    if citekey:
        m = re.match(r"([a-z]+)(\d{4})", citekey)
        if m:
            surname = m.group(1).capitalize()
            year = m.group(2)
            depth_map = {
                "full_text": "已读全文",
                "abstract_only": "摘要级证据",
                "zotero_note": "笔记/标注",
                "metadata_only": "元数据",
                "pdf_verified": "已读全文",
            }
            depth_label = depth_map.get(reading_depth, reading_depth or "未标注")
            fig_ref = f"图 {orig_figure_id}" if orig_figure_id else ""
            if fig_ref:
                src_label = f"{surname} 等, {year}, {fig_ref}。{depth_label}"
            else:
                src_label = f"{surname} 等, {year}, {depth_label}"
        else:
            src_label = citekey

    # Note: the writer is responsible for the lead-in sentence (why this figure)
    # and the post-figure explanation per figure-writing-interface.md.
    # This script only inserts the figure + caption + source attribution.

    # Connector line per skill requirement: 如图 X 所示
    connector = f"如图 {fig_number} 所示。"

    # Figure markdown
    figure_md = f"![图 {fig_number}]({rel})"

    # Caption line
    caption_line = f"*图 {fig_number}. {display_caption}*"

    # Source attribution in skill format: 作者, 年份, 图 xxx。阅读深度
    src_line = f"（来源: {src_label}）" if src_label else ""

    return f"{connector}\n\n{figure_md}\n\n{caption_line}\n\n{src_line}", provenance


# ---------------------------------------------------------------------------
# Main resolution logic
# ---------------------------------------------------------------------------

def resolve_figure_refs(
    *,
    draft_path: str | Path,
    cards_paths: list[str],
    figure_index_path: str | None = None,
    output_path: str | Path,
    figures_dir: str | Path | None = None,
    report_json: str | Path | None = None,
    figure_evidence_json: str | Path | None = None,
) -> int:
    draft_p = Path(draft_path).expanduser().resolve()
    if not draft_p.exists():
        raise SystemExit(f"Draft not found: {draft_p}")
    _figures_dir = Path(figures_dir) if figures_dir else (draft_p.parent / "figures")
    text = draft_p.read_text(encoding="utf-8", errors="replace")
    markers = _find_markers(text)
    if not markers:
        print("No [图: xxx] markers found — draft unchanged.")
        Path(output_path).expanduser().write_text(text, encoding="utf-8")
        return 0

    # Load figure candidates from deep_read_cards
    all_candidates = _load_cards(cards_paths)

    # Supplement with figure_index if provided
    if figure_index_path:
        fi_figures = _load_figure_index(figure_index_path)
        seen_imgs: set[str] = {
            _clean(f.get("source_image_path") or f.get("local_image_path"))
            for f in all_candidates
        }
        for fig in fi_figures:
            uid = _clean(fig.get("source_image_path") or fig.get("local_image_path"))
            if uid and uid not in seen_imgs:
                seen_imgs.add(uid)
                fig_copy = dict(fig)
                fig_copy["_image_source"] = "figure_index"
                fig_copy["_text_source"] = "unknown"
                all_candidates.append(fig_copy)

    # Collect all available candidates for display purposes
    available_count = len(all_candidates)

    used_figure_ids: set[str] = set()
    resolved_count = 0
    warnings: list[str] = []
    resolution_records: list[dict[str, Any]] = []

    # Process markers in reverse order to preserve positions
    markers.sort(key=lambda m: m["start"])
    replacements: list[tuple[int, int, str]] = []  # (start, end, replacement)

    for marker in markers:
        desc = marker["description"]
        context = marker["context_before"]
        keywords = _description_keywords(desc, context)

        # Score all candidates
        scored = [(fig, *_score_figure(fig, keywords)) for fig in all_candidates]
        # Filter already-used figures
        available = [
            (fig, kw_score, q_score)
            for fig, kw_score, q_score in scored
            if _clean(fig.get("source_image_path") or fig.get("local_image_path"))
            not in used_figure_ids
        ]
        if not available:
            # All figures used — reuse the best one
            available = scored

        # Sort: keyword_score desc, then quality_score desc
        available.sort(key=lambda x: (-x[1], -x[2]))

        best_fig, best_kw_score, best_q_score = available[0] if available else (None, 0, 0)

        if best_fig and best_kw_score > 0 and best_q_score >= 1:
            fig_number = resolved_count + 1
            block, provenance = _build_figure_block(
                best_fig, fig_number, desc, draft_p, _figures_dir
            )
            if not provenance.get("local_path"):
                replacement = f"[[FIGURE:{desc}|status=materialization_failed]]"
                replacements.append((marker["start"], marker["end"], replacement))
                warnings.append(
                    f"图片物化失败: {desc!r} → {_clean(best_fig.get('figure_id'))}"
                )
                resolution_records.append({
                    "description": desc,
                    "status": "materialization_failed",
                    "figure_id": _clean(best_fig.get("figure_id")),
                    "keyword_score": best_kw_score,
                    "quality_score": best_q_score,
                    "manual_confirmation_required": True,
                    "source_image_path": _clean(best_fig.get("source_image_path")),
                })
                continue
            replacements.append((marker["start"], marker["end"], block))
            used_figure_ids.add(
                _clean(best_fig.get("source_image_path") or best_fig.get("local_image_path"))
            )
            resolved_count += 1
            qual_label = ["?", "PyMuPDF", "MinerU", "captioned", "captioned+MinerU"][
                min(best_q_score, 4)
            ]
            print(f"  [resolved] {desc!r} → {_clean(best_fig.get('figure_id'))} "
                  f"(kw={best_kw_score}, quality={qual_label})")
            resolution_records.append({
                "description": desc,
                "status": "resolved",
                "figure_id": _clean(best_fig.get("figure_id")),
                "figure_type": _clean(best_fig.get("figure_type") or "figure"),
                "page": _clean(best_fig.get("page")),
                "caption": _clean(best_fig.get("caption")),
                "citekey": _clean(best_fig.get("_citekey")),
                "paper_title": _clean(best_fig.get("_title")),
                "reading_depth": _clean(best_fig.get("_reading_depth")),
                "source_item_key": _clean(
                    best_fig.get("source_item_key")
                    or (best_fig.get("_source_trace") or {}).get("zotero_item_key")
                ),
                "source_attachment_key": _clean(best_fig.get("source_attachment_key")),
                "source_stage": _clean(best_fig.get("source_stage")),
                "source_image_path": _clean(best_fig.get("source_image_path")),
                "local_image_path": provenance.get("local_path", ""),
                "draft_relative_path": provenance.get("draft_relative_path", ""),
                "source_zip": provenance.get("source_zip", ""),
                "source_zip_sha256": provenance.get("source_zip_sha256", ""),
                "source_internal_path": provenance.get("source_internal_path", ""),
                "source_image_sha256": provenance.get("source_image_sha256", ""),
                "materialized_sha256": provenance.get("materialized_sha256", ""),
                "keyword_score": best_kw_score,
                "quality_score": best_q_score,
                "manual_confirmation_required": False,
            })
        elif best_fig:
            replacement = f"[[FIGURE:{desc}|status=manual_confirmation_required]]"
            replacements.append((marker["start"], marker["end"], replacement))
            print(f"  [manual confirmation] {desc!r} — best candidate has no keyword overlap")
            warnings.append(f"弱匹配未插入: {desc!r} → {_clean(best_fig.get('figure_id'))}")
            resolution_records.append({
                "description": desc,
                "status": "manual_confirmation_required",
                "figure_id": _clean(best_fig.get("figure_id")),
                "keyword_score": best_kw_score,
                "quality_score": best_q_score,
                "manual_confirmation_required": True,
            })
        else:
            # No figures at all
            replacement = (
                f"[图 {resolved_count + 1}：{desc} — "
                f"未找到匹配图片（候选池 {available_count} 张，均未匹配关键词 "
                f"{', '.join(keywords[:5])}）]"
            )
            replacements.append((marker["start"], marker["end"], replacement))
            warnings.append(f"未匹配: {desc!r}（候选池 {available_count} 张）")
            print(f"  [unresolved] {desc!r} — no matching figure in {available_count} candidates")
            resolution_records.append({
                "description": desc,
                "status": "unresolved",
                "figure_id": "",
                "keyword_score": 0,
                "quality_score": 0,
                "manual_confirmation_required": True,
            })

    # Apply replacements in reverse order
    result = text
    for start, end, repl in reversed(replacements):
        result = result[:start] + repl + result[end:]

    # Add resolution summary at end of document
    summary_lines = [
        "",
        "---",
        "",
        f"<!-- 图表解析报告: {resolved_count}/{len(markers)} 个标记已解析 -->",
    ]
    if warnings:
        summary_lines.append("<!-- 警告:")
        for w in warnings:
            summary_lines.append(f"  - {w}")
        summary_lines.append("-->")
    result = result.rstrip() + "\n" + "\n".join(summary_lines) + "\n"

    output_p = Path(output_path).expanduser()
    output_p.write_text(result, encoding="utf-8")
    report_path = Path(report_json).expanduser() if report_json else output_p.parent / "figure_resolution_report.json"
    unresolved_count = sum(1 for record in resolution_records if record["status"] != "resolved")
    report_path.write_text(json.dumps({
        "schema_version": "figure-resolution.v1",
        "input_draft": str(draft_p),
        "output_draft": str(output_p),
        "output_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "records": resolution_records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_path = (
        Path(figure_evidence_json).expanduser()
        if figure_evidence_json
        else output_p.parent / "figure_evidence_report.json"
    )
    evidence_records = [
        {
            "schema_version": "figure-evidence.v1",
            "figure_id": record.get("figure_id", ""),
            "item_key": record.get("source_item_key", ""),
            "claim_binding": record.get("description", ""),
            "figure_intent": record.get("description", ""),
            "evidence_basis": record.get("source_image_path", ""),
            "candidate_specs": [],
            "human_selected_candidate": record.get("figure_id", ""),
            "figure_risk_note": "",
            "caption_support": record.get("caption", ""),
            "text_support": "",
            "visual_support": "original_asset_inserted",
            "evidence_status": "source_traced_original",
            "recommended_action": "retain_original",
            "generation_backend": "not_applicable",
            "visualspec_path": "",
            "reproduction_bundle": "",
            "manifest_path": "",
            "reproduction_status": "",
            "qa_profile": "",
            "verification_status": "pass",
            "figure_asset_action": "insert_original",
            "figure_transform_authorization": "not_required",
            "extraction_project_path": "",
            "extraction_report_path": "",
            "extraction_status": "",
            "value_delivery_authorized": False,
            "source_zip_sha256": record.get("source_zip_sha256", ""),
            "source_image_sha256": record.get("source_image_sha256", ""),
            "materialized_sha256": record.get("materialized_sha256", ""),
            "local_image_path": record.get("draft_relative_path", ""),
            "page": record.get("page", ""),
            "caption": record.get("caption", ""),
        }
        for record in resolution_records
        if record.get("status") == "resolved"
    ]
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "figure-evidence.v1",
                "metadata": {
                    "input_draft": str(draft_p),
                    "output_draft": str(output_p),
                    "output_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
                },
                "records": evidence_records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"RESOLVED: {resolved_count}/{len(markers)} markers → {output_path}")
    if warnings:
        print(f"WARNINGS: {len(warnings)}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve [图: xxx] markers in a writing draft by matching figure candidates."
    )
    parser.add_argument("--draft", required=True, help="Path to draft .md with [图: xxx] markers")
    parser.add_argument(
        "--cards", action="append", default=[],
        help="Path to deep_read_cards.json (repeat for multiple sections)",
    )
    parser.add_argument(
        "--figure-index",
        default=None,
        help="Optional path to figure_index.json for supplementary candidates",
    )
    parser.add_argument("--output", default=None, help="Output path (default: draft_resolved.md)")
    parser.add_argument("--figures-dir", default=None, help="Directory for extracted figures (default: <draft>/figures)")
    parser.add_argument("--report-json", default=None, help="Structured resolution report (default: output sibling figure_resolution_report.json)")
    parser.add_argument("--figure-evidence-json", default=None, help="Original-figure evidence report (default: output sibling figure_evidence_report.json)")
    args = parser.parse_args()

    if not args.cards and not args.figure_index:
        print("Warning: no --cards or --figure-index provided; all markers will be unresolved.",
              file=sys.stderr)

    output = args.output or str(Path(args.draft).with_suffix("")) + "_resolved.md"

    return resolve_figure_refs(
        draft_path=args.draft,
        cards_paths=args.cards,
        figure_index_path=args.figure_index,
        output_path=output,
        figures_dir=args.figures_dir,
        report_json=args.report_json,
        figure_evidence_json=args.figure_evidence_json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
