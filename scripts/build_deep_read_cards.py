#!/usr/bin/env python3
"""Build Step 7 deep-read cards for a single section from existing artifacts."""

from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF

    _HAS_FITZ = True
except ImportError:  # pragma: no cover
    _HAS_FITZ = False

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from workflow_contracts import (  # noqa: E402
    PAPER_CARD_READING_DEPTHS,
    DeepReadCardRecord,
    PaperCard,
    inspect_mineru_zip,
    write_deep_read_cards,
)
from mineru_assets import enumerate_mineru_assets, match_mineru_zip  # noqa: E402


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_clean(v) for v in value if _clean(v)]
    if isinstance(value, tuple):
        return [_clean(v) for v in value if _clean(v)]
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r";|；|\n", text) if part.strip()]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", _normalize_text(text))
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？!?\.])\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _pick_sentence(text: str, keywords: list[str]) -> str:
    sentences = _split_sentences(text)
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    if not lowered_keywords:
        return sentences[0] if sentences else ""
    _re_citation = re.compile(r"^\[\d+\]")
    scored = []
    for sentence in sentences:
        lowered = sentence.lower()
        # skip reference/citation lines and heavily-cited boilerplate
        if _re_citation.match(sentence) or "doi:" in lowered or lowered.count("[") > 2:
            continue
        score = sum(1 for kw in lowered_keywords if kw in lowered)
        if score > 0 and len(sentence) >= 15:
            scored.append((score, len(sentence), sentence))
    if scored:
        # prefer multi-keyword matches; tie-break on sentence length (medium preferred)
        scored.sort(key=lambda x: (-x[0], abs(x[1] - 200)))
        return scored[0][2]
    for s in sentences:
        if len(s) >= 15:
            return s
    return sentences[0] if sentences else ""


def _pick_sentences(text: str, keywords: list[str], limit: int = 2) -> list[str]:
    sentences = _split_sentences(text)
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    matches: list[tuple[int, int, str]] = []
    for sentence in sentences:
        lowered = sentence.lower()
        score = sum(1 for keyword in lowered_keywords if keyword in lowered)
        if score > 0 and len(sentence) >= 12:
            matches.append((score, len(sentence), sentence))
    matches.sort(key=lambda x: (-x[0], abs(x[1] - 180)))
    return [item[2] for item in matches[:limit]]


def _truncate(text: str, limit: int = 220) -> str:
    text = _clean(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _extract_mechanism_hints(
    text: str,
    record: dict[str, Any],
    figure_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    mechanism_terms = ["mechanism", "机理", "机制", "causal", "因果", "影响规律", "耦合", "传导", "pathway", "transition", "driven"]
    model_terms = ["equation", "model", "formula", "公式", "方程", "模型", "等效", "control law", "computed", "framework"]
    boundary_terms = ["condition", "scenario", "boundary", "assumption", "工况", "边界", "假设", "约束", "load", "temperature", "strain rate"]
    validation_terms = ["experiment", "experiments", "test", "tests", "simulation", "validate", "validated", "ablation", "实验", "仿真", "验证", "对比", "消融"]
    alternative_terms = ["however", "limitation", "alternative", "conflict", "但", "然而", "局限", "反例", "矛盾"]

    title = _clean(record.get("title"))
    phenomenon = _truncate(
        _pick_sentence(text, mechanism_terms + ["result", "show", "导致", "提高", "降低"]) or title,
        180,
    )
    causal_chain = [_truncate(s, 180) for s in _pick_sentences(text, mechanism_terms, 2)]
    governing_model = [_truncate(s, 180) for s in _pick_sentences(text, model_terms, 2)]
    boundary_conditions = [_truncate(s, 180) for s in _pick_sentences(text, boundary_terms, 2)]
    validation_path = [_truncate(s, 180) for s in _pick_sentences(text, validation_terms, 2)]
    alternative_explanations = [_truncate(s, 180) for s in _pick_sentences(text, alternative_terms, 2)]

    state_variables: list[str] = []
    variable_patterns: list[tuple[str, int]] = [
        (r"\b(?:CDRX|DDRX|DRV|DRX|WH|GF|GR|GBM|CA|CPFE|CPFEM|VPSC|LABs|MABs|HABs|PSC|UC|TR|EBSD|TEM|TKD|SOC|SOH)\b", 0),
        (r"\b(?:voltage|current|power|temperature|load|frequency|efficiency|strain rate|stress state|stored energy|dislocation density|misorientation|transformation fraction|grain boundary migration|subgrain rotation|grain fragmentation|activation energy)\b", re.IGNORECASE),
        (r"(?:电压|电流|功率|温度|负载|频率|效率|荷电状态|热阻|阻抗|电容|应力状态|应变速率|储能|位错密度|取向差|转变分数|晶界迁移|亚晶旋转|晶粒破碎|激活能)", 0),
    ]
    for pattern, flags in variable_patterns:
        for match in re.findall(pattern, text, flags=flags):
            value = _clean(match)
            if value and value not in state_variables:
                state_variables.append(value)
            if len(state_variables) >= 8:
                break
        if len(state_variables) >= 8:
            break

    anchors = []
    pdf_path = _clean(record.get("pdf_path"))
    if pdf_path:
        anchors.append({"type": "pdf", "value": pdf_path})
    for fig in figure_candidates[:3]:
        label = _clean(fig.get("figure_id") or fig.get("caption") or fig.get("source_image_path"))
        if label:
            anchors.append({"type": "figure_or_table", "value": label, "page": _clean(fig.get("page"))})

    evidence_is_thin = not (causal_chain or governing_model or boundary_conditions or validation_path)
    return {
        "phenomenon": phenomenon,
        "state_variables": state_variables,
        "causal_chain": causal_chain,
        "governing_model": governing_model,
        "boundary_conditions": boundary_conditions,
        "evidence_anchor": anchors,
        "alternative_explanations": alternative_explanations,
        "validation_path": validation_path,
        "claim_limit": (
            "可作为机理候选解释，写强机制判断前需补全文、图表或实验锚点。"
            if evidence_is_thin
            else "可进入 mechanism_argument_plan；强 claim 仍需逐条绑定全文、图表或实验锚点。"
        ),
    }


def _load_json(path: str | Path | None) -> Any:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))


def _load_mapping_records(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = _load_json(path)
    if isinstance(payload, dict):
        records = payload.get("records")
        metadata = payload.get("metadata") or {}
        if isinstance(records, list):
            return [r for r in records if isinstance(r, dict)], metadata
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)], {}
    raise SystemExit(f"Unsupported mapping JSON shape: {path}")


def _load_text_map(path: str | Path | None) -> dict[str, str]:
    payload = _load_json(path)
    result: dict[str, str] = {}
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        payload = payload["records"]
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, str):
                result[_clean(key)] = _normalize_text(value)
            elif isinstance(value, dict):
                text = _clean(value.get("text") or value.get("content") or value.get("fulltext"))
                if text:
                    result[_clean(key)] = _normalize_text(text)
        return result
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            text = _clean(item.get("text") or item.get("content") or item.get("fulltext"))
            if not text:
                continue
            for key in _record_keys(item):
                result[key] = _normalize_text(text)
        return result
    return result


def _load_prepared_index(path: str | Path | None) -> list[dict[str, Any]]:
    payload = _load_json(path)
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    if isinstance(artifacts, list):
        return [a for a in artifacts if isinstance(a, dict)]
    return []


def _load_figure_records(path: str | Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = _load_json(path)
    if isinstance(payload, dict):
        records = payload.get("records")
        metadata = payload.get("metadata") or {}
        if isinstance(records, list):
            return [r for r in records if isinstance(r, dict)], metadata
    return [], {}


def _record_keys(record: dict[str, Any]) -> list[str]:
    keys = [
        _clean(record.get("record_id")),
        _clean(record.get("citekey")),
        _clean(record.get("zotero_item_key")),
        _clean(record.get("title")),
        _clean(record.get("paper_title")),
        _clean(record.get("source_pdf")),
    ]
    pdf_path = _clean(record.get("pdf_path") or record.get("source_pdf"))
    if pdf_path:
        pdf = Path(pdf_path)
        keys.extend([pdf.name, pdf.stem])
    return [key for key in keys if key]


def _match_text(record: dict[str, Any], text_map: dict[str, str]) -> str:
    for key in _record_keys(record):
        if key in text_map:
            return text_map[key]
    return ""


def _find_prepared_artifact(record: dict[str, Any], prepared_index: list[dict[str, Any]]) -> dict[str, Any]:
    direct = record.get("prepared_pdf_artifacts")
    if isinstance(direct, dict) and direct:
        return direct
    keys = set(_record_keys(record))
    for artifact in prepared_index:
        artifact_keys = set(_record_keys(artifact))
        if keys & artifact_keys:
            return artifact
    return {}


def _read_chunks_text(chunks_path: str) -> str:
    payload = _load_json(chunks_path)
    if not isinstance(payload, list):
        return ""
    chunks = []
    for item in payload:
        if isinstance(item, dict):
            text = _clean(item.get("text"))
            if text:
                chunks.append(text)
    return "\n\n".join(chunks).strip()


def _read_mineru_text(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        try:
            return _normalize_text(zf.read("full.md").decode("utf-8", errors="replace"))
        except KeyError:
            return ""


def _read_mineru_figure_candidates(zip_path: Path, limit: int = 30) -> list[dict[str, Any]]:
    return [
        {
            "figure_id": _clean(item.get("figure_id")),
            "figure_type": _clean(item.get("figure_type")),
            "page": _clean(item.get("page")),
            "caption": _clean(item.get("caption")),
            "source_image_path": _clean(item.get("source_image_path")),
            "local_image_path": "",
            "source_item_key": _clean(item.get("source_item_key")),
            "source_attachment_key": _clean(item.get("source_attachment_key")),
            "source_stage": _clean(item.get("source_stage")),
        }
        for item in enumerate_mineru_assets(zip_path)[:limit]
    ]


def _extract_pdf_images(
    pdf_path: str | Path,
    figures_dir: Path,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Extract embedded images from a PDF using PyMuPDF (fitz) and save to `figures_dir`.

    Returns a list of figure candidate dicts with ``local_image_path`` populated.
    Used as a fallback when no MinerU ZIP is available.
    """
    if not _HAS_FITZ:
        return []
    pdf = Path(pdf_path)
    if not pdf.exists():
        return []
    figures_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    seen_xrefs: set[int] = set()
    try:
        doc = fitz.open(str(pdf))
    except Exception:
        return []

    try:
        page_count = doc.page_count
        for page_idx in range(page_count):
            if len(candidates) >= limit:
                break
            page = doc[page_idx]
            image_infos = page.get_images(full=True)
            for img_info in image_infos:
                if len(candidates) >= limit:
                    break
                xref = img_info[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue
                image_bytes = base_image.get("image")
                ext = base_image.get("ext", "jpg")
                if not image_bytes:
                    continue
                # Skip very small images (likely icons, dots, etc.)
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)
                if width < 80 and height < 80:
                    continue
                pdf_stem = pdf.stem[:40]
                safe_name = _slug(f"{pdf_stem}-xref{xref}")
                img_filename = f"{safe_name}.{ext}"
                img_path = figures_dir / img_filename
                img_path.write_bytes(image_bytes)
                candidates.append({
                    "figure_id": f"pdf-img-{xref}",
                    "page": str(page_idx + 1),
                    "caption": "",
                    "source_image_path": f"{pdf_path}::xref-{xref}",
                    "local_image_path": str(img_path),
                })
    finally:
        doc.close()
    return candidates


def _read_pdf_figure_candidates(
    pdf_path: str | Path,
    figures_dir: Path,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Thin wrapper for symmetry with ``_read_mineru_figure_candidates``."""
    return _extract_pdf_images(pdf_path, figures_dir, limit)


def _match_mineru_zip(record: dict[str, Any], zip_paths: list[Path]) -> Path | None:
    """Match exact Zotero lineage first, then use conservative filename overlap."""
    return match_mineru_zip(record, zip_paths)


def _match_figure_candidates(record: dict[str, Any], figure_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    record_item_key = _clean(record.get("zotero_item_key"))
    for fig in figure_records:
        source_item_key = _clean(fig.get("source_item_key") or fig.get("item_key"))
        if record_item_key and source_item_key and record_item_key == source_item_key:
            matches.append(fig)
        elif not record_item_key and len(figure_records) == 1:
            matches.append(fig)
    return matches


def _select_records(
    records: list[dict[str, Any]],
    section_id: str,
    section_title: str,
    max_records: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for record in records:
        chapter_id = _clean(record.get("chapter_id"))
        secondary_ids = set(_clean_list(record.get("secondary_chapter_ids")))
        collection_text = " / ".join(_clean_list(record.get("collection_path")))
        if section_id and (chapter_id == section_id or section_id in secondary_ids):
            selected.append(record)
            continue
        if section_title and section_title in collection_text:
            selected.append(record)
            continue
    if not selected and len(records) <= max_records:
        selected = list(records)
    return selected[:max_records]


def _render_markdown(records: list[DeepReadCardRecord], metadata: dict[str, Any]) -> str:
    lines = [
        "# Deep Read Cards",
        "",
        f"- section_id: {metadata.get('section_id', '')}",
        f"- section_title: {metadata.get('section_title', '')}",
        f"- selected_records: {len(records)}",
        "",
    ]
    for card in records:
        cite_label = card.citekey or card.record_id or "unknown-record"
        lines.extend([
            f"## {cite_label} - {card.title}",
            "",
            f"- reading_depth: {card.reading_depth}",
            f"- evidence_role: {card.evidence_role}",
            f"- content_fit: {card.content_fit}",
            f"- text_source: {card.source_trace.get('text_source', '')}",
            f"- image_source: {card.source_trace.get('image_source', '')}",
            "",
            "### Claim Summary",
            card.claim_summary or "待补全文确认。",
            "",
            "### Method Summary",
            card.method_summary or "待补全文确认方法细节。",
            "",
            "### Experiment Summary",
            card.experiment_summary or "待补全文确认实验设置与结果。",
            "",
            "### Usable For",
        ])
        usable = card.usable_for or ["待人工补充"]
        lines.extend([f"- {item}" for item in usable])
        lines.extend([
            "",
            "### Not Usable For",
        ])
        blocked = card.not_usable_for or ["未声明"]
        lines.extend([f"- {item}" for item in blocked])
        if card.mechanism_hints:
            lines.extend([
                "",
                "### Mechanism Hints",
                f"- phenomenon: {card.mechanism_hints.get('phenomenon', '')}",
                f"- state_variables: {'; '.join(card.mechanism_hints.get('state_variables', [])) or '待补充'}",
                f"- claim_limit: {card.mechanism_hints.get('claim_limit', '')}",
            ])
            for field_name in [
                "causal_chain",
                "governing_model",
                "boundary_conditions",
                "validation_path",
                "alternative_explanations",
            ]:
                values = card.mechanism_hints.get(field_name, [])
                if values:
                    lines.append(f"- {field_name}:")
                    lines.extend([f"  - {item}" for item in values])
            anchors = card.mechanism_hints.get("evidence_anchor", [])
            if anchors:
                lines.append("- evidence_anchor:")
                for anchor in anchors:
                    lines.append(f"  - {anchor.get('type', '')}: {anchor.get('value', '')} page={anchor.get('page', '')}")
        if card.risk_flags:
            lines.extend([
                "",
                "### Risk Flags",
            ])
            lines.extend([f"- {flag}" for flag in card.risk_flags])
        if card.figure_candidates:
            lines.extend([
                "",
                "### Figure Candidates",
            ])
            for fig in card.figure_candidates:
                label = _clean(fig.get("figure_id") or fig.get("caption") or fig.get("source_image_path"))
                page = _clean(fig.get("page"))
                path = _clean(fig.get("local_image_path") or fig.get("source_image_path"))
                lines.append(f"- {label} | page={page} | path={path}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_cards(
    *,
    mapping_json: Path,
    section_id: str,
    section_title: str,
    max_records: int,
    output_json: Path,
    output_md: Path,
    fulltext_json: str | None,
    notes_json: str | None,
    prepared_pdf_artifacts: str | None,
    figure_index: str | None,
    mineru_zips: list[str],
    figures_dir: Path | None = None,
) -> int:
    records, input_metadata = _load_mapping_records(mapping_json)
    selected = _select_records(records, section_id, section_title, max_records)
    if not selected:
        raise SystemExit(f"No records matched section {section_id!r} / {section_title!r}")

    fulltext_map = _load_text_map(fulltext_json)
    notes_map = _load_text_map(notes_json)
    prepared_index = _load_prepared_index(prepared_pdf_artifacts)
    figure_records, figure_metadata = _load_figure_records(figure_index)
    zip_paths = [Path(path).expanduser().resolve() for path in mineru_zips]

    cards: list[DeepReadCardRecord] = []
    warnings: list[str] = []
    for record in selected:
        raw_paper_card = record.get("paper_card")
        paper_card = PaperCard.from_value(raw_paper_card)
        mineru_zip = _match_mineru_zip(record, zip_paths)
        mineru_summary = inspect_mineru_zip(mineru_zip) if mineru_zip else None
        mineru_text = _read_mineru_text(mineru_zip) if mineru_zip else ""
        fulltext = _match_text(record, fulltext_map)
        notes_text = _match_text(record, notes_map)
        prepared = _find_prepared_artifact(record, prepared_index)
        chunks_text = _read_chunks_text(_clean(prepared.get("chunks_json"))) if prepared else ""

        text_source = "abstract_only"
        text_body = ""
        if mineru_text:
            text_source = "zotero_mineru"
            text_body = mineru_text
        elif fulltext:
            text_source = "zotero_fulltext"
            text_body = fulltext
        elif notes_text:
            text_source = "zotero_note/annotation"
            text_body = notes_text
        elif chunks_text:
            text_source = "PyMuPDF/pdfplumber"
            text_body = chunks_text
        else:
            text_body = _clean(record.get("abstract"))

        raw_reading_depth = ""
        if isinstance(raw_paper_card, dict):
            raw_reading_depth = _clean(raw_paper_card.get("reading_depth")).lower().replace("-", "_")

        if raw_reading_depth in PAPER_CARD_READING_DEPTHS:
            reading_depth = paper_card.reading_depth
            reading_depth_locked = True
        elif notes_text:
            reading_depth = "zotero_note"
            reading_depth_locked = False
        elif text_source != "abstract_only" and text_body:
            reading_depth = "full_text"
            reading_depth_locked = False
        elif _clean(record.get("abstract")):
            reading_depth = "abstract_only"
            reading_depth_locked = False
        else:
            reading_depth = "metadata_only"
            reading_depth_locked = False

        figure_candidates = _match_figure_candidates(record, figure_records)
        _figures_from = "figure_index" if figure_candidates else None
        if not figure_candidates and mineru_zip:
            figure_candidates = _read_mineru_figure_candidates(mineru_zip)
            _figures_from = "mineru_manifest"
        # PyMuPDF direct extraction from PDF — last-resort fallback when no MinerU ZIP
        pdf_path_for_images: str = _clean(record.get("pdf_path"))
        if not figure_candidates and pdf_path_for_images and figures_dir:
            figure_candidates = _read_pdf_figure_candidates(pdf_path_for_images, figures_dir)
            _figures_from = "pdf_direct"
        image_source = "none"
        if mineru_zip and mineru_summary and mineru_summary.image_count > 0:
            image_source = "MinerU ZIP / Zotero 图文资产"
        elif not figure_candidates:
            pass  # stays "none"
        elif _figures_from == "pdf_direct":
            image_source = "pdf_direct (PyMuPDF)"
        else:
            has_preview_only = all("preview" in _clean(fig.get("source_image_path") or fig.get("local_image_path")).lower() for fig in figure_candidates)
            image_source = "preview fallback" if has_preview_only else "主抽图"

        method_text = "；".join(paper_card.main_methods_or_baselines)
        claim_summary = _truncate(
            paper_card.primary_claim
            or _pick_sentence(text_body or _clean(record.get("abstract")), ["propose", "提出", "show", "demonstrate", "result"])
            or _clean(record.get("abstract"))
        )
        method_summary = _truncate(
            method_text
            or _pick_sentence(text_body, ["method", "approach", "framework", "模型", "方法", "network", "algorithm"])
        )
        experiment_summary = _truncate(
            _pick_sentence(text_body, ["experiment", "result", "ablation", "实验", "结果", "improve", "improvement"])
        )
        mechanism_hints = _extract_mechanism_hints(text_body, record, figure_candidates)

        risk_flags = list(dict.fromkeys(_clean_list(prepared.get("risk_flags")) + (["reading_depth_locked"] if reading_depth_locked else [])))
        if text_source == "abstract_only":
            risk_flags.append("abstract_only_candidate")
        if not mechanism_hints.get("causal_chain") and not mechanism_hints.get("governing_model"):
            risk_flags.append("mechanism_chain_missing")
        if not figure_candidates and image_source == "none":
            risk_flags.append("figure_candidates_missing")
        if mineru_summary and mineru_summary.warnings:
            risk_flags.extend(mineru_summary.warnings)
        risk_flags = list(dict.fromkeys([flag for flag in risk_flags if flag]))

        if text_source == "abstract_only":
            warnings.append(f"{_clean(record.get('citekey') or record.get('title'))}: abstract_only")

        cards.append(
            DeepReadCardRecord(
                record_id=_clean(record.get("record_id")),
                citekey=_clean(record.get("citekey")),
                title=_clean(record.get("title")),
                section_id=section_id,
                section_title=section_title,
                reading_depth=reading_depth,
                evidence_role=paper_card.evidence_role,
                content_fit=paper_card.content_fit,
                claim_summary=claim_summary,
                method_summary=method_summary,
                experiment_summary=experiment_summary,
                mechanism_hints=mechanism_hints,
                usable_for=paper_card.usable_for,
                not_usable_for=paper_card.not_usable_for,
                risk_flags=risk_flags,
                figure_candidates=[
                    {
                        "figure_id": _clean(fig.get("figure_id")),
                        "figure_type": _clean(fig.get("figure_type")),
                        "page": _clean(fig.get("page")),
                        "caption": _clean(fig.get("caption")),
                        "source_image_path": _clean(fig.get("source_image_path")),
                        "local_image_path": _clean(fig.get("local_image_path")),
                        "source_item_key": _clean(fig.get("source_item_key")),
                        "source_attachment_key": _clean(fig.get("source_attachment_key")),
                        "source_stage": _clean(fig.get("source_stage")),
                    }
                    for fig in figure_candidates
                ],
                source_trace={
                    "text_source": text_source,
                    "image_source": image_source,
                    "mapping_json": str(mapping_json),
                    "source_pdf": _clean(record.get("pdf_path")),
                    "zotero_item_key": _clean(record.get("zotero_item_key")),
                    "chunks_json": _clean(prepared.get("chunks_json")) if prepared else "",
                    "mineru_zip": str(mineru_zip) if mineru_zip else "",
                    "figure_index": str(figure_index or ""),
                },
            )
        )

    metadata = {
        "entry_mode": "deep_read_refine",
        "section_id": section_id,
        "section_title": section_title,
        "selected_records": len(cards),
        "input_artifact": str(mapping_json),
        "figure_index_metadata": figure_metadata,
        "warnings": warnings,
        "text_priority": "zotero_mineru > zotero_fulltext > zotero_note/annotation > PyMuPDF/pdfplumber > abstract_only",
        "image_priority": "MinerU ZIP / Zotero 图文资产 > 主抽图 > preview fallback",
    }
    write_deep_read_cards(output_json, cards, metadata)
    output_md.write_text(_render_markdown(cards, metadata), encoding="utf-8")
    print(f"DEEP_READ_CARDS: {output_json}")
    print(f"DEEP_READ_MARKDOWN: {output_md}")
    print(f"SELECTED_RECORDS: {len(cards)}")
    if warnings:
        print(f"WARNINGS: {len(warnings)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Step 7 deep_read_refine cards from existing mapping and evidence artifacts.")
    parser.add_argument("--mapping-json", required=True, help="Path to 文献-Zotero架构对照.json or equivalent records JSON")
    parser.add_argument("--section-id", required=True, help="Current section/chapter id")
    parser.add_argument("--section-title", default="", help="Current section/chapter title")
    parser.add_argument("--max-records", type=int, default=5, help="Maximum records to include")
    parser.add_argument("--output-json", default="deep_read_cards.json", help="Output deep_read_cards.json path")
    parser.add_argument("--output-md", default="deep_read_cards.md", help="Output deep_read_cards.md path")
    parser.add_argument("--fulltext-json", help="Optional exported Zotero fulltext JSON or key->text map")
    parser.add_argument("--notes-json", help="Optional exported Zotero notes/annotations JSON or key->text map")
    parser.add_argument("--prepared-pdf-artifacts", help="Optional prepared_pdf_artifacts.json from prepare_pdf_for_llm.py")
    parser.add_argument("--figure-index", help="Optional figure_index.json for image candidates")
    parser.add_argument("--mineru-zip", action="append", default=[], help="Optional MinerU ZIP paths; can be repeated")
    parser.add_argument("--figures-dir", default=None, help="Directory to save PDF-extracted images (PyMuPDF fallback)")
    args = parser.parse_args()

    figures_dir = Path(args.figures_dir) if args.figures_dir else None

    return build_cards(
        mapping_json=Path(args.mapping_json).expanduser().resolve(),
        section_id=args.section_id,
        section_title=args.section_title,
        max_records=args.max_records,
        output_json=Path(args.output_json).expanduser(),
        output_md=Path(args.output_md).expanduser(),
        fulltext_json=args.fulltext_json,
        notes_json=args.notes_json,
        prepared_pdf_artifacts=args.prepared_pdf_artifacts,
        figure_index=args.figure_index,
        mineru_zips=args.mineru_zip,
        figures_dir=figures_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
