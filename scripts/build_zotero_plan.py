#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""Build Step 6 Zotero planning artifacts without writing to Zotero.

This script intentionally produces intermediate state only:
  - 文献-Zotero架构对照.json
  - 文献-Zotero架构对照.md
  - pdf-附件池索引.json

It never calls Zotero MCP and never mutates a Zotero library.
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
from pathlib import Path
from typing import Any

try:
    from workflow_contracts import load_search_records
except ImportError:
    load_search_records = None

SCHEMA_VERSION = "1.2"
WORKFLOW_CONTRACT_SCHEMA = "workflow-contracts.v1"
DEFAULT_ROOT = "论文文献库"
CONFIRM_COLLECTION = "待确认集合"
PDF_EXTS = {".pdf"}
ITEM_STATES = {
    "planned", "existing_confirmed", "imported", "duplicate_candidate",
    "metadata_conflict", "import_failed", "rejected_do_not_import",
    "manual_confirmation_required",
}
ATTACHMENT_STATES = {
    "matched_attachment", "missing_attachment", "unlinked_pdf",
    "duplicate_attachment", "invalid_attachment", "attachment_conflict",
    "manual_attach_required", "rejected",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"[{}]", "", str(value))
    value = value.replace(r"\_", "_")
    value = re.sub(r"\\[a-zA-Z]+\s*", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_key(value: str | None) -> str:
    value = normalize_text(value).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)


def normalize_doi(value: str | None) -> str:
    value = normalize_text(value)
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
    return value.strip().rstrip(".")


def stable_record_id(record: dict[str, Any]) -> str:
    doi = normalize_doi(record.get("doi"))
    source_id = normalize_key(record.get("source_id"))
    title = normalize_key(record.get("title"))
    authors = record.get("authors") or []
    first_author = normalize_key(authors[0] if authors else "")
    year = normalize_key(record.get("year"))
    citekey = normalize_key(record.get("citekey"))
    identity = f"doi:{doi.lower()}" if doi else f"source:{source_id}" if source_id else f"tay:{title}|{first_author}|{year}" if title else f"citekey:{citekey}"
    instance = citekey or f"{title}|{first_author}|{year}"
    return "zrec-" + hashlib.sha256(f"{identity}|{instance}".encode("utf-8")).hexdigest()[:16]


def parse_authors(value: str | None) -> list[str]:
    value = normalize_text(value)
    if not value:
        return []
    parts = re.split(r"\s+and\s+|;|；", value)
    return [p.strip() for p in parts if p.strip()]


def read_json(path: str | None, warnings: list[str]) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        warnings.append(f"Optional JSON not found: {path}")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"Could not parse JSON {path}: {exc}")
        return None


def load_direct_records(path: str | None, warnings: list[str]) -> list[dict[str, Any]]:
    payload = read_json(path, warnings)
    if payload is None:
        return []
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("records") or payload.get("items") or payload.get("search_results") or []
    else:
        rows = []
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            warnings.append(f"Direct record {index} is not an object")
            continue
        authors = row.get("authors") or row.get("author") or []
        if isinstance(authors, list):
            authors = [
                normalize_text(author.get("family") or author.get("literal") or author.get("name")) if isinstance(author, dict) else normalize_text(author)
                for author in authors
            ]
        else:
            authors = parse_authors(str(authors))
        records.append({
            **row,
            "citekey": row.get("citekey") or row.get("id") or f"direct-{index:03d}",
            "title": normalize_text(row.get("title")),
            "authors": [author for author in authors if author],
            "doi": normalize_doi(row.get("doi") or row.get("DOI")),
            "publication_title": row.get("publication_title") or row.get("container-title") or "",
            "verification_status": row.get("verification_status") or "WARN",
        })
    return records


def load_prepared_pdf_artifacts(path: str | None, warnings: list[str]) -> list[dict[str, Any]]:
    data = read_json(path, warnings)
    if data is None:
        return []
    if isinstance(data, dict) and isinstance(data.get("artifacts"), list):
        return [item for item in data["artifacts"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    warnings.append(f"Prepared PDF artifacts has unsupported format: {path}")
    return []


def load_workflow_index(path: str | None, warnings: list[str]) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    if load_search_records is None:
        warnings.append("workflow_contracts.load_search_records unavailable")
        return {}
    p = Path(path)
    if not p.exists():
        warnings.append(f"Workflow results not found: {path}")
        return {}
    try:
        records = load_search_records(p)
    except Exception as exc:
        warnings.append(f"Could not read workflow results {path}: {exc}")
        return {}
    index: dict[str, dict[str, Any]] = {}
    for rec in records:
        keys = []
        if rec.doi:
            keys.append(normalize_doi(rec.doi))
        if rec.source_id:
            keys.append(normalize_key(rec.source_id))
        if rec.title:
            keys.append(normalize_key(rec.title))
        payload = {
            "search_task_id": rec.search_task_id,
            "chapter_id": rec.chapter_id,
            "chapter_title": rec.chapter_title,
            "secondary_search_task_ids": rec.secondary_search_task_ids,
            "secondary_chapter_ids": rec.secondary_chapter_ids,
            "secondary_chapter_titles": rec.secondary_chapter_titles,
            "evidence_type": rec.evidence_type,
            "paper_card": rec.paper_card.__dict__ if hasattr(rec.paper_card, "__dict__") else {},
        }
        for key in keys:
            if key and key not in index:
                index[key] = payload
    return index


def split_bib_entries(text: str) -> list[tuple[str, str, str]]:
    entries = []
    i = 0
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        m = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[at:])
        if not m:
            i = at + 1
            continue
        entry_type = m.group(1)
        citekey = m.group(2)
        body_start = at + m.end()
        depth = 1
        j = body_start
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[body_start:j - 1]
        entries.append((entry_type, citekey, body))
        i = j
    return entries


def parse_bib_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    while i < len(body):
        while i < len(body) and body[i] in " \n\r\t,":
            i += 1
        m = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", body[i:])
        if not m:
            i += 1
            continue
        key = m.group(1).lower()
        i += m.end()
        while i < len(body) and body[i].isspace():
            i += 1
        if i >= len(body):
            break
        if body[i] in "{\"":
            opener = body[i]
            closer = "}" if opener == "{" else "\""
            i += 1
            start = i
            depth = 1 if opener == "{" else 0
            while i < len(body):
                ch = body[i]
                if opener == "{" and ch == "{":
                    depth += 1
                elif opener == "{" and ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
                elif opener == "\"" and ch == closer and body[i - 1] != "\\":
                    break
                i += 1
            fields[key] = normalize_text(body[start:i])
            i += 1
        else:
            start = i
            while i < len(body) and body[i] != ",":
                i += 1
            fields[key] = normalize_text(body[start:i])
    return fields


def parse_bib(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    records = []
    for entry_type, citekey, body in split_bib_entries(text):
        fields = parse_bib_fields(body)
        note = fields.get("note", "")
        tier = extract_note_value(note, "tier")
        score = extract_note_value(note, "score")
        subtopic = extract_note_value(note, "subtopic")
        source = fields.get("source") or extract_note_value(note, "source")
        source_id = fields.get("source_id") or extract_note_value(note, "source id") or extract_note_value(note, "source_id")
        verification_status = extract_note_value(note, "verification_status")
        verification_confidence = extract_note_value(note, "verification_confidence")
        warn_class = extract_note_value(note, "warn_class")
        verified_sources = extract_note_value(note, "verified_sources")
        records.append({
            "entry_type": entry_type,
            "citekey": citekey,
            "title": fields.get("title", ""),
            "authors": parse_authors(fields.get("author", "")),
            "year": fields.get("year", ""),
            "publication_title": fields.get("journal") or fields.get("booktitle") or fields.get("publisher", ""),
            "doi": normalize_doi(fields.get("doi", "")),
            "article_url": fields.get("url", ""),
            "abstract": fields.get("abstract", ""),
            "tier": tier,
            "score": score,
            "subtopic": subtopic,
            "source": source,
            "source_id": source_id,
            "verification_status": verification_status or "WARN",
            "verification_confidence": verification_confidence or ("low" if not verification_status else ""),
            "warn_class": warn_class or ("legacy-unverified" if not verification_status else ""),
            "verified_sources": verified_sources,
            "note": note,
        })
    return records


def extract_note_value(note: str, key: str) -> str:
    if not note:
        return ""
    patterns = [
        rf"{re.escape(key)}\s*[:=]\s*([^|;\n]+)",
        rf"{re.escape(key.replace(' ', '_'))}\s*[:=]\s*([^|;\n]+)",
    ]
    for pat in patterns:
        m = re.search(pat, note, flags=re.IGNORECASE)
        if m:
            return normalize_text(m.group(1))
    return ""


def load_chinese_metadata(path: str | None, warnings: list[str]) -> dict[str, dict[str, Any]]:
    data = read_json(path, warnings)
    if data is None:
        return {}
    if isinstance(data, dict):
        if isinstance(data.get("papers"), list):
            items = data["papers"]
        elif isinstance(data.get("records"), list):
            items = data["records"]
        else:
            items = list(data.values()) if all(isinstance(v, dict) for v in data.values()) else []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        keys = [
            item.get("citekey"),
            item.get("source_id"),
            item.get("id"),
            normalize_key(item.get("title")),
        ]
        for key in keys:
            if key:
                index[str(key)] = item
    return index


def merge_chinese_metadata(record: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    keys = [
        record.get("citekey"),
        record.get("source_id"),
        normalize_key(record.get("title")),
    ]
    match = next((index[k] for k in keys if k and k in index), None)
    if not match:
        return record
    merged = dict(record)
    field_map = {
        "citekey": ["citekey"],
        "title": ["title", "题名", "标题"],
        "year": ["year", "年份"],
        "publication_title": ["publication_title", "journal", "期刊", "来源"],
        "article_url": ["article_url", "url", "URL", "文章链接"],
        "abstract": ["abstract", "摘要"],
        "source": ["source"],
        "source_id": ["source_id", "id"],
        "verification_status": ["verification_status", "可信度状态", "验证状态"],
        "verification_confidence": ["verification_confidence", "可信度置信", "验证置信"],
        "warn_class": ["warn_class", "风险类别", "警告类别"],
        "verified_sources": ["verified_sources", "验证来源", "可信来源"],
    }
    for target, aliases in field_map.items():
        if merged.get(target) and not (target == "citekey" and str(merged.get(target, "")).lower().endswith("_unknown")):
            continue
        for alias in aliases:
            if match.get(alias):
                merged[target] = normalize_text(match.get(alias))
                break
    if not merged.get("authors"):
        authors = match.get("authors") or match.get("作者") or match.get("author")
        if isinstance(authors, list):
            merged["authors"] = [normalize_text(a) for a in authors if normalize_text(a)]
        else:
            merged["authors"] = parse_authors(authors)
    if match.get("language"):
        merged["language"] = match.get("language")
    return merged


def load_structure(path: str | None, warnings: list[str]) -> tuple[str, list[dict[str, Any]], bool]:
    if not path:
        warnings.append("Missing structure JSON; records will use 待确认集合.")
        return CONFIRM_COLLECTION, [], False
    p = Path(path)
    if not p.exists():
        warnings.append(f"Structure JSON not found: {path}; records will use 待确认集合.")
        return CONFIRM_COLLECTION, [], False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"Could not parse structure JSON {path}: {exc}")
        return CONFIRM_COLLECTION, [], False
    root = normalize_text(data.get("name")) if isinstance(data, dict) else ""
    return root or DEFAULT_ROOT, flatten_structure(data), True


def flatten_structure(node: Any, prefix: list[str] | None = None) -> list[dict[str, Any]]:
    if not isinstance(node, dict):
        return []
    prefix = prefix or []
    name = normalize_text(node.get("name"))
    path = prefix + ([name] if name else [])
    tags = node.get("tags") if isinstance(node.get("tags"), list) else []
    rows = [{"path": path, "name": name, "tags": tags}]
    for child in node.get("children") or []:
        rows.extend(flatten_structure(child, path))
    return rows


def choose_collection(record: dict[str, Any], root: str, structure_rows: list[dict[str, Any]], has_structure: bool) -> list[str]:
    if not has_structure:
        return [CONFIRM_COLLECTION]
    chapter_title = normalize_text(record.get("chapter_title"))
    chapter_id = normalize_text(record.get("chapter_id"))
    if chapter_title or chapter_id:
        for row in structure_rows:
            path = row.get("path") or []
            if len(path) <= 1:
                continue
            row_name = normalize_text(row.get("name"))
            hay = normalize_key(" ".join(path + [row_name]))
            if chapter_title and normalize_key(chapter_title) in hay:
                return path
            if chapter_id and normalize_key(chapter_id) in hay:
                return path
    hay = " ".join([
        record.get("subtopic", ""),
        record.get("title", ""),
        record.get("abstract", ""),
        record.get("note", ""),
    ])
    hay_key = normalize_key(hay)
    best_path: list[str] | None = None
    best_score = 0
    for row in structure_rows:
        path = row.get("path") or []
        if len(path) <= 1:
            continue
        candidates = [row.get("name", "")]
        for tag in row.get("tags") or []:
            if isinstance(tag, dict):
                candidates.append(str(tag.get("tag", "")))
                candidates.append(str(tag.get("desc", "")))
        score = 0
        for candidate in candidates:
            ck = normalize_key(candidate)
            if ck and ck in hay_key:
                score += max(1, min(5, len(ck) // 4))
        if score > best_score:
            best_score = score
            best_path = path
    return best_path or [root, CONFIRM_COLLECTION]


def choose_secondary_collections(record: dict[str, Any], root: str, structure_rows: list[dict[str, Any]], has_structure: bool) -> list[list[str]]:
    if not has_structure:
        return []
    chapter_titles = [normalize_text(x) for x in record.get("secondary_chapter_titles", []) if normalize_text(x)]
    chapter_ids = [normalize_text(x) for x in record.get("secondary_chapter_ids", []) if normalize_text(x)]
    if not chapter_titles and not chapter_ids:
        return []
    selected: list[list[str]] = []
    for row in structure_rows:
        path = row.get("path") or []
        if len(path) <= 1:
            continue
        hay = normalize_key(" ".join(path + [row.get("name", "")]))
        if any(normalize_key(x) in hay for x in chapter_titles + chapter_ids if x):
            if path not in selected:
                selected.append(path)
    return selected


def merge_workflow_mapping(record: dict[str, Any], workflow_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    keys = []
    if record.get("doi"):
        keys.append(normalize_doi(record.get("doi")))
    if record.get("source_id"):
        keys.append(normalize_key(record.get("source_id")))
    if record.get("title"):
        keys.append(normalize_key(record.get("title")))
    for key in keys:
        payload = workflow_index.get(key)
        if payload:
            merged = dict(record)
            merged.update({
                "search_task_id": payload.get("search_task_id", merged.get("search_task_id", "")),
                "chapter_id": payload.get("chapter_id", merged.get("chapter_id", "")),
                "chapter_title": payload.get("chapter_title", merged.get("chapter_title", "")),
                "secondary_search_task_ids": payload.get("secondary_search_task_ids", merged.get("secondary_search_task_ids", [])),
                "secondary_chapter_ids": payload.get("secondary_chapter_ids", merged.get("secondary_chapter_ids", [])),
                "secondary_chapter_titles": payload.get("secondary_chapter_titles", merged.get("secondary_chapter_titles", [])),
                "evidence_type": payload.get("evidence_type", merged.get("evidence_type", "")),
            })
            return merged
    return record


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_pdf(path: Path) -> tuple[str, str]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return "invalid", f"read_error:{type(exc).__name__}"
    head = data[:512].lstrip().lower()
    if head.startswith((b"<html", b"<!doctype html")):
        return "invalid", "html_saved_as_pdf"
    if not data.lstrip().startswith(b"%PDF"):
        return "invalid", "not_pdf_magic"
    if len(data) < 5000:
        return "invalid", "too_small"
    if b"/Type /Page" not in data and b"/Type/Page" not in data:
        return "invalid", "no_readable_pages"
    return "verified", "ok"


def scan_pdf_dirs(pdf_dirs: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    for raw_dir in pdf_dirs:
        base = Path(raw_dir)
        if not base.exists() or not base.is_dir():
            warnings.append(f"PDF directory not found: {raw_dir}")
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in PDF_EXTS:
                continue
            try:
                digest = file_md5(path)
                verification_status, verification_reason = inspect_pdf(path)
                status = "unmatched" if verification_status == "verified" else "invalid_attachment"
                duplicate_of = ""
                if digest in seen_hashes:
                    status = "duplicate_candidate"
                    duplicate_of = seen_hashes[digest]
                else:
                    seen_hashes[digest] = str(path.resolve())
                items.append({
                    "path": str(path.resolve()),
                    "filename": path.name,
                    "source_dir": str(base.resolve()),
                    "size_bytes": path.stat().st_size,
                    "md5": digest,
                    "match_status": status,
                    "duplicate_of": duplicate_of,
                    "matched_record_id": "",
                    "attachment_state": "unlinked_pdf" if verification_status == "verified" else "invalid_attachment",
                    "verification_status": verification_status,
                    "verification_reason": verification_reason,
                })
            except Exception as exc:
                warnings.append(f"Could not index PDF {path}: {exc}")
    return items


def candidate_score(record: dict[str, Any], pdf: dict[str, Any]) -> tuple[int, list[str]]:
    filename_key = normalize_key(Path(pdf["filename"]).stem)
    reasons = []
    score = 0
    doi = normalize_doi(record.get("doi"))
    if doi:
        doi_key = normalize_key(doi)
        if doi_key and doi_key in filename_key:
            score += 100
            reasons.append("doi_in_filename")
    source_id = normalize_key(record.get("source_id"))
    if source_id and source_id in filename_key:
        score += 90
        reasons.append("source_id_in_filename")
    title_key = normalize_key(record.get("title"))
    if title_key and len(title_key) >= 12:
        if title_key in filename_key or filename_key in title_key:
            score += 80
            reasons.append("title_filename_match")
        else:
            title_tokens = set(re.findall(r"[0-9a-z\u4e00-\u9fff]{2,}", title_key))
            file_tokens = set(re.findall(r"[0-9a-z\u4e00-\u9fff]{2,}", filename_key))
            overlap = len(title_tokens & file_tokens)
            if overlap >= 3:
                score += 30 + overlap
                reasons.append("title_token_overlap")
    citekey = normalize_key(record.get("citekey"))
    if citekey and citekey in filename_key:
        score += 50
        reasons.append("citekey_in_filename")
    return score, reasons


def match_pdfs(record: dict[str, Any], pdfs: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]], str, str]:
    candidates = []
    for pdf in pdfs:
        score, reasons = candidate_score(record, pdf)
        if score <= 0:
            continue
        if score >= 80:
            confidence = "high"
        elif score >= 45:
            confidence = "medium"
        else:
            confidence = "low"
        candidates.append({
            "path": pdf["path"],
            "filename": pdf["filename"],
            "size_bytes": pdf["size_bytes"],
            "md5": pdf["md5"],
            "match_score": score,
            "match_confidence": confidence,
            "reasons": reasons,
            "duplicate_pdf_candidate": pdf.get("match_status") == "duplicate_candidate",
            "invalid_pdf_candidate": pdf.get("verification_status") != "verified",
        })
    candidates.sort(key=lambda c: c["match_score"], reverse=True)
    if not candidates:
        return "", "", [], "missing", "none"
    top = candidates[0]
    highish = [c for c in candidates if c["match_score"] >= max(45, top["match_score"] - 10)]
    if len(highish) > 1:
        return "", "", candidates, "conflict", "none"
    if top.get("invalid_pdf_candidate"):
        return top["path"], "manual", candidates, "invalid", "replace_invalid_pdf"
    if top.get("duplicate_pdf_candidate"):
        return top["path"], "manual", candidates, "duplicate_candidate", "skip"
    return top["path"], "manual", candidates, "found", "manual_drag"


def normalize_item_state(import_status: str) -> str:
    return {
        "ready": "planned",
        "metadata_incomplete": "metadata_conflict",
        "manual_required": "manual_confirmation_required",
        "rejected_do_not_import": "rejected_do_not_import",
        "imported": "imported",
        "existing": "existing_confirmed",
        "failed": "import_failed",
    }.get(import_status, "manual_confirmation_required")


def normalize_attachment_state(attachment_status: str, confidence: str) -> str:
    if attachment_status == "found":
        return "matched_attachment" if confidence == "high" else "manual_attach_required"
    return {
        "missing": "missing_attachment",
        "conflict": "attachment_conflict",
        "duplicate_candidate": "duplicate_attachment",
        "invalid": "invalid_attachment",
        "already_attached": "matched_attachment",
        "rejected": "rejected",
        "unknown": "unlinked_pdf",
    }.get(attachment_status, "unlinked_pdf")


def apply_duplicate_states(records: list[dict[str, Any]]) -> None:
    seen: dict[str, str] = {}
    for record in records:
        doi = normalize_doi(record.get("doi"))
        source_id = normalize_key(record.get("source_id"))
        title = normalize_key(record.get("title"))
        authors = record.get("authors") or []
        author = normalize_key(authors[0] if authors else "")
        year = normalize_key(record.get("year"))
        if doi:
            key = f"doi:{doi.lower()}"
        elif source_id:
            key = f"source:{source_id}"
        elif title and author and year:
            key = f"tay:{title}|{author}|{year}"
        else:
            continue
        if key in seen:
            record["item_state"] = "duplicate_candidate"
            record["duplicate_of_record_id"] = seen[key]
            record["duplicate_match_key"] = key.split(":", 1)[0]
        else:
            seen[key] = record.get("record_id", "")


def ensure_unique_record_ids(records: list[dict[str, Any]]) -> None:
    occurrences: dict[str, int] = {}
    for record in records:
        base = str(record.get("record_id") or stable_record_id(record))
        occurrences[base] = occurrences.get(base, 0) + 1
        record["record_id"] = base if occurrences[base] == 1 else f"{base}-dup{occurrences[base]}"


def match_prepared_artifact(record: dict[str, Any], prepared_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    record_pdf = str(record.get("pdf_path", "")).strip()
    citekey = normalize_key(record.get("citekey"))
    title = normalize_key(record.get("title"))
    for item in prepared_artifacts:
        source_pdf = str(item.get("source_pdf", "")).strip()
        if record_pdf and source_pdf and record_pdf == source_pdf:
            return item
        item_citekey = normalize_key(item.get("citekey"))
        if citekey and item_citekey and citekey == item_citekey:
            return item
        item_title = normalize_key(item.get("paper_title"))
        if title and item_title and title == item_title:
            return item
    return {}


def import_method(record: dict[str, Any], metadata_incomplete: bool) -> tuple[str, str]:
    source = (record.get("source") or "").lower()
    language = record.get("language", "")
    if metadata_incomplete:
        return "manual", "metadata_incomplete"
    if source in {"cnki", "wanfang"} or language == "zh-CN":
        return "csl_json", "ready"
    if record.get("doi"):
        return "doi", "ready"
    return "bibtex", "ready"


def build_records(
    bib_records: list[dict[str, Any]],
    chinese_index: dict[str, dict[str, Any]],
    workflow_index: dict[str, dict[str, Any]],
    root: str,
    structure_rows: list[dict[str, Any]],
    has_structure: bool,
    pdfs: list[dict[str, Any]],
    prepared_artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for idx, raw in enumerate(bib_records, start=1):
        record = merge_workflow_mapping(merge_chinese_metadata(raw, chinese_index), workflow_index)
        source = (record.get("source") or "").lower()
        source_id = record.get("source_id", "")
        language = record.get("language") or ("zh-CN" if source in {"cnki", "wanfang"} or source_id.startswith(("cnki.", "wanfang.")) else "")
        chinese_like = language == "zh-CN" or source in {"cnki", "wanfang"}
        metadata_incomplete = bool(chinese_like and not (source_id and record.get("article_url") and record.get("authors") and record.get("year") and record.get("publication_title")))
        method, import_status = import_method({**record, "language": language}, metadata_incomplete)
        verification_status = (record.get("verification_status") or "WARN").upper()
        if verification_status == "REJECT":
            method, import_status = "none", "rejected_do_not_import"
        pdf_path, pdf_source, candidates, attachment_status, attachment_action = match_pdfs(record, pdfs)
        prepared = match_prepared_artifact({"pdf_path": pdf_path, **record}, prepared_artifacts)
        if verification_status == "REJECT":
            attachment_status, attachment_action = "rejected", "none"
        confidence = candidates[0]["match_confidence"] if candidates else "none"
        primary_collection_path = choose_collection(record, root, structure_rows, has_structure)
        secondary_collection_paths = choose_secondary_collections(record, root, structure_rows, has_structure)
        records.append({
            "record_id": stable_record_id(record),
            "citekey": record.get("citekey", ""),
            "source": source,
            "source_id": source_id,
            "language": language,
            "title": record.get("title", ""),
            "authors": record.get("authors", []),
            "year": record.get("year", ""),
            "publication_title": record.get("publication_title", ""),
            "doi": record.get("doi", "") if record.get("doi", "").startswith("10.") else "",
            "article_url": record.get("article_url", ""),
            "abstract": record.get("abstract", ""),
            "tier": record.get("tier", ""),
            "score": record.get("score", ""),
            "subtopic": record.get("subtopic", ""),
            "verification_status": verification_status,
            "verification_confidence": record.get("verification_confidence", "low"),
            "warn_class": record.get("warn_class", "legacy-unverified"),
            "verified_sources": record.get("verified_sources", ""),
            "collection_path": primary_collection_path,
            "primary_collection_path": primary_collection_path,
            "secondary_collection_paths": secondary_collection_paths,
            "collection_key": "",
            "tags": infer_tags(record, structure_rows),
            "import_method": method,
            "import_status": import_status,
            "item_state": normalize_item_state(import_status),
            "duplicate_of_record_id": "",
            "duplicate_match_key": "",
            "pdf_path": pdf_path,
            "pdf_source": pdf_source,
            "pdf_match_confidence": confidence,
            "matched_pdf_candidates": candidates,
            "prepared_pdf_artifacts": {
                "raw_md": prepared.get("raw_md", ""),
                "clean_md": prepared.get("clean_md", ""),
                "chunks_json": prepared.get("chunks_json", ""),
                "extraction_report_json": prepared.get("extraction_report_json", ""),
                "evidence_level": prepared.get("evidence_level", ""),
                "must_check_pdf": prepared.get("must_check_pdf", False),
                "risk_flags": prepared.get("risk_flags", []),
            },
            "zotero_item_key": "",
            "attachment_status": attachment_status,
            "attachment_state": normalize_attachment_state(attachment_status, confidence),
            "attachment_action": attachment_action,
            "existing_attachment_keys": [],
            "notes": "中文元数据待补全" if metadata_incomplete else "",
        })
    ensure_unique_record_ids(records)
    apply_duplicate_states(records)
    apply_pdf_assignment_conflicts(records)
    return records


def apply_pdf_assignment_conflicts(records: list[dict[str, Any]]) -> None:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        path = str(record.get("pdf_path") or "").strip()
        if path and record.get("attachment_state") not in {"invalid_attachment", "duplicate_attachment", "rejected"}:
            by_path.setdefault(path, []).append(record)
    for path, owners in by_path.items():
        distinct = {record.get("record_id") for record in owners}
        if len(distinct) <= 1:
            continue
        for record in owners:
            record["attachment_status"] = "conflict"
            record["attachment_state"] = "attachment_conflict"
            record["attachment_action"] = "manual_review_shared_pdf"
            record["shared_pdf_record_ids"] = sorted(str(item) for item in distinct if item)


def infer_tags(record: dict[str, Any], structure_rows: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    subtopic = normalize_text(record.get("subtopic"))
    if subtopic:
        tags.append(subtopic.split(":", 1)[0].strip())
    hay = normalize_key(" ".join([record.get("title", ""), record.get("abstract", ""), record.get("subtopic", "")]))
    for row in structure_rows:
        for tag in row.get("tags") or []:
            if not isinstance(tag, dict):
                continue
            tag_name = normalize_text(tag.get("tag"))
            if tag_name and normalize_key(tag_name) in hay and tag_name not in tags:
                tags.append(tag_name)
    return tags[:8]


def compute_readiness(records: list[dict[str, Any]], blocking: list[str], nonblocking: list[str], warnings: list[str], *, has_pdf_inventory: bool = False) -> tuple[str, bool, str]:
    if blocking:
        return "blocked", False, "先补齐阻塞输入，再重跑 Step 6 计划生成。"
    if not records and has_pdf_inventory:
        return "partial", True, "PDF 附件清单已建立；可补充 Zotero/BibTeX/JSON 后继续匹配，或保留为 unlinked_pdf。"
    if not records:
        return "blocked", False, "未解析到文献记录，请检查 文献库.bib。"
    if nonblocking or warnings:
        return "partial", True, "可继续人工审阅对照表；缺失项可后续补齐。"
    if any(r.get("attachment_state") in {"attachment_conflict", "duplicate_attachment", "manual_attach_required"} or r.get("item_state") != "planned" for r in records):
        return "partial", True, "先处理缺 PDF、重复候选、冲突和元数据待补全项。"
    return "complete", True, "可进入 6c 创建/复用 Zotero 集合，并按 JSON 分步写入。"


def update_pdf_index_matches(pdfs: list[dict[str, Any]], records: list[dict[str, Any]]) -> None:
    by_path = {pdf["path"]: pdf for pdf in pdfs}
    for rec in records:
        for cand in rec.get("matched_pdf_candidates") or []:
            pdf = by_path.get(cand.get("path", ""))
            if not pdf:
                continue
            current = pdf.get("match_status", "unmatched")
            if current == "duplicate_candidate":
                continue
            pdf["match_status"] = rec.get("attachment_state", "unlinked_pdf")
            pdf["attachment_state"] = rec.get("attachment_state", "unlinked_pdf")
            pdf["matched_record_id"] = rec.get("record_id", "")
            pdf["matched_citekey"] = rec.get("citekey", "")
            pdf["match_confidence"] = cand.get("match_confidence", "")


def plan_fingerprint(records: list[dict[str, Any]], root_collection: str) -> str:
    material = {
        "root_collection": root_collection,
        "records": [{
            "record_id": record.get("record_id"),
            "import_method": record.get("import_method"),
            "collection_path": record.get("collection_path"),
            "pdf_path": record.get("pdf_path"),
            "attachment_action": record.get("attachment_action"),
        } for record in sorted(records, key=lambda item: str(item.get("record_id") or ""))],
    }
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "zplan-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def write_json(path: str, data: Any) -> None:
    p = Path(path)
    if p.parent and str(p.parent) != ".":
        p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def truncate(value: Any, limit: int = 80) -> str:
    text = normalize_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return text if len(text) <= limit else text[:limit - 1] + "…"


def write_review(path: str, plan: dict[str, Any]) -> None:
    lines = [
        "# 文献-Zotero架构对照",
        "",
        f"- schema_version: `{plan['schema_version']}`",
        f"- root_collection: `{plan['root_collection']}`",
        f"- readiness: `{plan['readiness']}`",
        f"- can_continue: `{plan['can_continue']}`",
        f"- recommended_next_step: {plan['recommended_next_step']}",
        "",
    ]
    if plan["blocking_missing"]:
        lines += ["## 阻塞缺失", "", *[f"- {x}" for x in plan["blocking_missing"]], ""]
    if plan["nonblocking_missing"]:
        lines += ["## 非阻塞缺失", "", *[f"- {x}" for x in plan["nonblocking_missing"]], ""]
    if plan["warnings"]:
        lines += ["## Warnings", "", *[f"- {x}" for x in plan["warnings"]], ""]

    lines += [
        "## 对照表",
        "",
        "| 序号 | citekey | 标题 | 可信度 | 风险类别 | 主集合路径 | 次集合路径 | 导入方式 | 导入状态 | PDF状态 | 附件动作 | PDF文件 |",
        "|------|---------|------|--------|----------|------------|------------|----------|----------|---------|----------|---------|",
    ]
    for i, rec in enumerate(plan["records"], start=1):
        secondary = "；".join(" / ".join(path) for path in rec.get("secondary_collection_paths") or [])
        lines.append(
            "| {i} | {citekey} | {title} | {verification} | {warn_class} | {collection} | {secondary} | {method} | {import_status} | {att_status} | {att_action} | {pdf} |".format(
                i=i,
                citekey=truncate(rec.get("citekey"), 28),
                title=truncate(rec.get("title"), 60),
                verification=truncate(rec.get("verification_status"), 18),
                warn_class=truncate(rec.get("warn_class"), 28),
                collection=truncate(" / ".join(rec.get("collection_path") or []), 60),
                secondary=truncate(secondary, 60),
                method=rec.get("import_method", ""),
                import_status=rec.get("import_status", ""),
                att_status=rec.get("attachment_status", ""),
                att_action=rec.get("attachment_action", ""),
                pdf=truncate(Path(rec.get("pdf_path", "")).name if rec.get("pdf_path") else "未找到", 40),
            )
        )
    p = Path(path)
    if p.parent and str(p.parent) != ".":
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Step 6 Zotero planning artifacts without writing to Zotero.")
    parser.add_argument("--bib", help="Step 4 文献库.bib")
    parser.add_argument("--structure", help="zotero-架构.json")
    parser.add_argument("--pdf-dir", action="append", default=[], help="PDF 附件池目录，可重复传入")
    parser.add_argument("--prepared-pdf-artifacts", help="prepared_pdf_artifacts.json from prepare_pdf_for_llm.py")
    parser.add_argument("--chinese", help="中文论文元数据.json (legacy: chinese_papers.json / chinese_metadata.json)")
    parser.add_argument("--workflow-results", help="workflow_search_results.json for chapter/secondary-chapter mapping")
    parser.add_argument("--records-json", help="Direct-entry CSL JSON, workflow JSON, prior plan, or Zotero read-only scan")
    parser.add_argument("--output", default="文献-Zotero架构对照.json")
    parser.add_argument("--review", default="文献-Zotero架构对照.md")
    parser.add_argument("--pdf-index", default="pdf-附件池索引.json")
    args = parser.parse_args()

    warnings: list[str] = []
    blocking: list[str] = []
    nonblocking: list[str] = []

    root, structure_rows, has_structure = load_structure(args.structure, warnings)
    if not has_structure:
        nonblocking.append("zotero-架构.json")

    chinese_index = load_chinese_metadata(args.chinese, warnings) if args.chinese else {}
    if not args.chinese:
        nonblocking.append("中文论文元数据.json")

    workflow_index = load_workflow_index(args.workflow_results, warnings) if args.workflow_results else {}
    if not args.workflow_results:
        nonblocking.append("workflow_search_results.json")

    pdfs = scan_pdf_dirs(args.pdf_dir, warnings)
    prepared_artifacts = load_prepared_pdf_artifacts(args.prepared_pdf_artifacts, warnings)
    if not args.pdf_dir:
        nonblocking.append("PDF 附件池目录")
    if args.prepared_pdf_artifacts and not prepared_artifacts:
        nonblocking.append("Prepared PDF artifacts")

    bib_records: list[dict[str, Any]] = load_direct_records(args.records_json, warnings) if args.records_json else []
    if args.bib and Path(args.bib).exists():
        try:
            bib_records.extend(parse_bib(Path(args.bib)))
        except Exception as exc:
            blocking.append("文献库.bib")
            warnings.append(f"Could not parse BibTeX: {exc}")
    elif args.bib:
        blocking.append("文献库.bib")
    elif not bib_records and not pdfs:
        blocking.append("可读取的 Zotero/BibTeX/JSON/PDF 输入")

    records = [] if blocking else build_records(
        bib_records,
        chinese_index,
        workflow_index,
        root,
        structure_rows,
        has_structure,
        pdfs,
        prepared_artifacts,
    )
    update_pdf_index_matches(pdfs, records)
    readiness, can_continue, next_step = compute_readiness(records, blocking, nonblocking, warnings, has_pdf_inventory=bool(pdfs))
    completion_state = "plan_ready" if can_continue else "blocked"

    plan = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "zotero_plan",
        "workflow_contract_schema": WORKFLOW_CONTRACT_SCHEMA,
        "plan_only": True,
        "execution_profile": "plan-only",
        "execution_mode": "plan-only",
        "completion_state": completion_state,
        "direct_entry": bool(args.records_json or (args.pdf_dir and not args.bib)),
        "root_collection": root,
        "plan_fingerprint": plan_fingerprint(records, root),
        "readiness": readiness,
        "can_continue": can_continue,
        "blocking_missing": blocking,
        "nonblocking_missing": nonblocking,
        "warnings": warnings,
        "recommended_next_step": next_step,
        "records": records,
        "state_counts": {
            "items": {state: sum(1 for record in records if record.get("item_state") == state) for state in sorted(ITEM_STATES)},
            "attachments": {state: sum(1 for record in records if record.get("attachment_state") == state) for state in sorted(ATTACHMENT_STATES)},
        },
        "exceptions": {
            "duplicate_records": [record["record_id"] for record in records if record.get("item_state") == "duplicate_candidate"],
            "metadata_conflicts": [record["record_id"] for record in records if record.get("item_state") == "metadata_conflict"],
            "missing_attachments": [record["record_id"] for record in records if record.get("attachment_state") == "missing_attachment"],
            "attachment_conflicts": [record["record_id"] for record in records if record.get("attachment_state") in {"attachment_conflict", "duplicate_attachment", "invalid_attachment"}],
            "manual_confirmation": [record["record_id"] for record in records if record.get("item_state") == "manual_confirmation_required" or record.get("attachment_state") == "manual_attach_required"],
        },
    }
    pdf_index = {
        "schema_version": SCHEMA_VERSION,
        "pdf_count": len(pdfs),
        "warnings": warnings,
        "pdfs": pdfs,
        "unlinked_pdf_count": sum(1 for pdf in pdfs if not pdf.get("matched_record_id")),
    }

    write_json(args.output, plan)
    write_json(args.pdf_index, pdf_index)
    write_review(args.review, plan)

    print(f"Zotero plan JSON saved to: {args.output}", flush=True)
    print(f"Zotero review Markdown saved to: {args.review}", flush=True)
    print(f"PDF index saved to: {args.pdf_index}", flush=True)
    print(f"readiness={readiness} can_continue={can_continue}", flush=True)
    return 0 if can_continue else 2


if __name__ == "__main__":
    raise SystemExit(main())
