#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Post-writing citation audit tool — verifies that every cited paper actually
supports the claim it's attached to, not just that the paper exists.

Inspired by CiteCheck's thematic scoring pipeline, stripped of the redundant
"does this paper exist?" verification (Step 4 already ensures papers exist).
The real value is catching "title sounds relevant but abstract doesn't match
the claim" misattributions that LLMs are prone to during writing.

Usage:
  # Audit citations in a manuscript
  python3 citation_audit.py 论文初稿.md --output 引用审计报告.md

  # Audit with Zotero enrichment (reads full abstracts from Zotero if available)
  python3 citation_audit.py 论文初稿.md --zotero --output 引用审计报告.md

  # Audit with a specific literature table for cross-reference
  python3 citation_audit.py 论文初稿.md --lit-table 检索文献表.md

  # Dry-run: just extract citations, don't fetch abstracts
  python3 citation_audit.py 论文初稿.md --extract-only
"""
try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import time
import sys
import re
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

from workflow_contracts import normalize_doi

# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class CitationRef:
    """A single in-text citation found in the manuscript."""
    index: int              # Citation number [N]
    marker: str             # The raw marker e.g. "[1]", "[2,5]", "(Zhang, 2023)"
    claim_sentence: str     # The sentence containing this citation
    claim_context: str      # Surrounding paragraph (for context in scoring)
    line_number: int        # Approximate line number in manuscript
    claim_occurrence_id: str = ""  # Stable ID for this citation position/claim occurrence
    bib_entry: str = ""     # Matching bibliography entry text
    doi: str = ""           # Extracted DOI from bib entry
    title: str = ""         # Paper title from bib entry or API


@dataclass
class AuditResult:
    """Audit result for one citation."""
    citation: CitationRef
    support_level: str      # "✅ 支撑" | "🟡 弱支撑" | "❌ 不支撑" | "⚠️ 无法判断"
    abstract: str           # Retrieved abstract (truncated)
    reasoning: str          # Why this support level was assigned
    suggestion: str = ""    # What the user should do (e.g. "check full text")
    pdf_risk_note: str = "" # PDF-derived warning from prepared chunks / mapping


# ── Manuscript Parsing ───────────────────────────────────────────────────────

def extract_citations_from_manuscript(md_text: str) -> list[CitationRef]:
    """Extract every citation occurrence and its surrounding claim.

    A bibliography identity may appear against multiple claims.  Those
    occurrences must remain independent so a weak background use cannot hide
    a later strong causal claim that cites the same paper.
    """
    citations = []
    lines = md_text.split('\n')

    # Find the references section boundary
    ref_section_start = _find_reference_section(lines)

    # Pattern for numbered citations: [1], [2,5], [3-7], [1, 3, 5]
    cite_pattern = re.compile(r'\[(\d+(?:[,，\-\s]+\d+)*)\]')

    # Also match author-year citations: (Author, 2023), (Author et al., 2023)
    auth_year_pattern = re.compile(
        r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?,?\s*\d{4}[a-z]?)\)'
    )

    for i, line in enumerate(lines):
        if i >= ref_section_start:
            break  # Stop at references section

        # Numbered citations
        for match in cite_pattern.finditer(line):
            # Parse individual citation numbers from the group
            raw = match.group(1)
            numbers = _parse_cite_numbers(raw)
            for n in numbers:
                context = _get_context(lines, i, window=3)
                citations.append(CitationRef(
                    index=n,
                    marker=match.group(0),
                    claim_sentence=line.strip(),
                    claim_context=context,
                    line_number=i + 1,
                    claim_occurrence_id=_claim_occurrence_id(
                        line_number=i + 1,
                        column=match.start() + 1,
                        reference_identity=str(n),
                        claim_sentence=line.strip(),
                    ),
                ))

        # Author-year citations
        for match in auth_year_pattern.finditer(line):
            key = match.group(1)
            context = _get_context(lines, i, window=3)
            citations.append(CitationRef(
                index=-1,  # No numeric index for author-year
                marker=match.group(0),
                claim_sentence=line.strip(),
                claim_context=context,
                line_number=i + 1,
                claim_occurrence_id=_claim_occurrence_id(
                    line_number=i + 1,
                    column=match.start() + 1,
                    reference_identity=key,
                    claim_sentence=line.strip(),
                ),
            ))

    return citations


def extract_bibliography(md_text: str) -> dict[int, str]:
    """Extract bibliography entries from the references section.
    Returns dict mapping citation number -> full bib entry text."""
    lines = md_text.split('\n')
    ref_start = _find_reference_section(lines)
    if ref_start >= len(lines):
        return {}

    bib = {}
    # Match entries like "[1] Authors. Title. Journal, Year..."
    # or "1. Authors. Title. Journal, Year..."
    entry_pattern = re.compile(r'^(?:\[(\d+)\]\s*|(\d+)\.\s*)(.*)$')

    current_num = None
    current_entry = []

    for line in lines[ref_start:]:
        m = entry_pattern.match(line.strip())
        if m:
            # Save previous entry
            if current_num is not None and current_entry:
                bib[current_num] = ' '.join(current_entry)
            # Start new entry
            num = int(m.group(1) or m.group(2))
            current_num = num
            current_entry = [m.group(3)]
        elif current_num is not None and line.strip():
            current_entry.append(line.strip())

    # Save last entry
    if current_num is not None and current_entry:
        bib[current_num] = ' '.join(current_entry)

    return bib


def extract_dois_from_bib(bib_entries: dict[int, str]) -> dict[int, str]:
    """Extract DOIs from bibliography entries."""
    dois = {}
    for num, entry in bib_entries.items():
        doi = _extract_doi(entry)
        if doi:
            dois[num] = doi
    return dois


# ── API: Abstract Retrieval ─────────────────────────────────────────────────

def fetch_abstract_crossref(doi: str, timeout: int = 10) -> Optional[str]:
    """Fetch abstract from Crossref API by DOI."""
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CitationAudit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            msg = data.get("message", {})
            abstract = msg.get("abstract", "")
            return abstract.strip() if abstract else None
    except Exception:
        return None


def fetch_abstract_semantic_scholar(doi: str, timeout: int = 10) -> Optional[str]:
    """Fetch abstract from Semantic Scholar API by DOI."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=abstract"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            abstract = data.get("abstract", "")
            return abstract.strip() if abstract else None
    except Exception:
        return None


def fetch_title_crossref(doi: str, timeout: int = 10) -> Optional[str]:
    """Fetch paper title from Crossref API by DOI."""
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CitationAudit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            title = data.get("message", {}).get("title", [""])[0]
            return title.strip() if title else None
    except Exception:
        return None


def fetch_abstract_zotero(item_key: str) -> Optional[str]:
    """
    Placeholder — Zotero abstract retrieval is done through the MCP tools
    (zotero_get_item_metadata) rather than direct HTTP, since the Zotero API
    requires authentication. Returns None as a signal to the caller to use MCP.
    """
    return None


# ── Claim-Abstract Matching ──────────────────────────────────────────────────

def score_citation_support(
    citation: CitationRef,
    abstract: str,
    title: str = "",
) -> AuditResult:
    """Score how well the cited paper's abstract supports the claim.

    Uses keyword overlap + structural heuristics. The host agent's LLM
    (Claude) does the final interpretive scoring when used as a skill;
    this function provides the structured data the LLM needs to decide.
    """
    if not abstract:
        return AuditResult(
            citation=citation,
            support_level="⚠️ 无法判断",
            abstract="（未获取到摘要）",
            reasoning="无法获取被引论文摘要，无法判断引用是否恰当。建议通过 Zotero 或手动查看 PDF 全文确认。",
            suggestion="用 zotero_get_item_fulltext 读取全文后重新审计",
        )

    # Extract key terms from the claim sentence
    claim_terms = _extract_key_terms(citation.claim_sentence)
    abstract_lower = abstract.lower()
    title_lower = title.lower() if title else ""

    # Count how many claim terms appear in the abstract
    term_hits = sum(1 for t in claim_terms if t.lower() in abstract_lower)
    term_ratio = term_hits / max(len(claim_terms), 1)

    # Check for key evidence indicators in abstract
    has_data = bool(re.search(
        r'\d+\s*%|\d+\s*per\s*cent|n\s*[=＝]\s*\d+|'
        r'sample\s*size|p\s*[<≤]\s*0\.\d|'
        r'significant|experiment|measured|observed',
        abstract_lower
    ))
    has_method = bool(re.search(
        r'method|approach|algorithm|model|framework|'
        r'simulation|experiment|survey|analysis',
        abstract_lower
    ))
    has_conclusion = bool(re.search(
        r'result|finding|conclusion|show|demonstrate|'
        r'indicate|suggest|reveal|find',
        abstract_lower
    ))

    # Scoring logic
    if term_ratio >= 0.6 and has_data:
        level = "✅ 支撑"
        reasoning = (
            f"摘要与引用声明高度匹配（术语重叠率 {term_ratio:.0%}），"
            f"且摘要包含数据/实验证据。"
        )
        suggestion = "引用恰当，无需修改"
    elif term_ratio >= 0.4 and (has_method or has_conclusion):
        level = "🟡 弱支撑"
        reasoning = (
            f"摘要主题相关（术语重叠率 {term_ratio:.0%}），"
            f"但匹配度不够高——摘要讨论的方向可能与你的声明不完全一致。"
        )
        suggestion = "建议核对全文，确认该论文确实得出你引用的结论"
    elif term_ratio >= 0.2:
        level = "🟡 弱支撑"
        reasoning = (
            f"摘要部分相关（术语重叠率 {term_ratio:.0%}），"
            f"但关键术语匹配不足，可能引用了主题相关但内容不直接支撑的论文。"
        )
        suggestion = "强烈建议核对全文，或替换为更直接支撑该声明的论文"
    elif _contains_cjk(citation.claim_sentence) or _contains_cjk(abstract):
        level = "⚠️ 无法判断"
        reasoning = (
            f"中文或跨语言声明的词面重叠率为 {term_ratio:.0%}；"
            "轻量关键词启发式不足以据此判定科学上“不支撑”。"
        )
        suggestion = "需要人工核对摘要语义或回到 PDF 全文确认"
    else:
        level = "❌ 不支撑"
        reasoning = (
            f"摘要与引用声明几乎不匹配（术语重叠率 {term_ratio:.0%}）。"
            f"该论文可能标题相关但内容不支撑你的具体声明。"
        )
        suggestion = "建议移除该引用或替换为确实支撑该声明的论文"

    return AuditResult(
        citation=citation,
        support_level=level,
        abstract=abstract[:500] + ("..." if len(abstract) > 500 else ""),
        reasoning=reasoning,
        suggestion=suggestion,
    )


# ── Report Generation ────────────────────────────────────────────────────────

def generate_audit_report(
    results: list[AuditResult],
    manuscript_path: str,
    total_citations: int,
) -> str:
    """Generate a structured Markdown audit report."""
    counts = {"✅ 支撑": 0, "🟡 弱支撑": 0, "❌ 不支撑": 0, "⚠️ 无法判断": 0}
    for r in results:
        counts[r.support_level] = counts.get(r.support_level, 0) + 1

    report = f"""# 引用审计报告

> 审计对象：`{manuscript_path}`
> 审计时间：{time.strftime("%Y-%m-%d %H:%M")}
> 引用总数：{total_citations}
> 已审计：{len(results)}

## 总览

| 级别 | 数量 | 占比 |
|------|:---:|:---:|
| ✅ 支撑 — 引用恰当 | {counts["✅ 支撑"]} | {_pct(counts["✅ 支撑"], len(results))} |
| 🟡 弱支撑 — 需核对全文 | {counts["🟡 弱支撑"]} | {_pct(counts["🟡 弱支撑"], len(results))} |
| ❌ 不支撑 — 可能引用不当 | {counts["❌ 不支撑"]} | {_pct(counts["❌ 不支撑"], len(results))} |
| ⚠️ 无法判断 — 缺摘要或需语义复核 | {counts["⚠️ 无法判断"]} | {_pct(counts["⚠️ 无法判断"], len(results))} |

"""

    # 🟢 Passed citations (brief list)
    passed = [r for r in results if r.support_level == "✅ 支撑"]
    if passed:
        report += "## ✅ 引用恰当的文献\n\n"
        for r in passed:
            report += f"- **[{r.citation.index}]** {r.citation.marker} → {r.reasoning}\n"
        report += "\n"

    # 🟡 Weak citations (detailed)
    weak = [r for r in results if r.support_level == "🟡 弱支撑"]
    if weak:
        report += "## 🟡 需核对的文献\n\n"
        for r in weak:
            report += f"""### [{r.citation.index}] {r.citation.marker}

**引用声明：** {r.citation.claim_sentence[:200]}

**被引论文摘要：** {r.citation.abstract}

**判断：** {r.reasoning}

**PDF 风险提醒：** {r.pdf_risk_note or "无"}

**建议：** {r.suggestion}

---
"""
        report += "\n"

    # ❌ Problematic citations (full detail)
    bad = [r for r in results if r.support_level == "❌ 不支撑"]
    if bad:
        report += "## ❌ 可能引用不当的文献\n\n"
        for r in bad:
            report += f"""### [{r.citation.index}] {r.citation.marker}

**引用声明：** {r.citation.claim_sentence[:200]}

**被引论文摘要：** {r.citation.abstract}

**判断：** {r.reasoning}

**PDF 风险提醒：** {r.pdf_risk_note or "无"}

**建议：** {r.suggestion}

---
"""
        report += "\n"

    # ⚠️ Unable to judge
    unknown = [r for r in results if r.support_level == "⚠️ 无法判断"]
    if unknown:
        report += "## ⚠️ 无法判断的引用（缺摘要或需人工语义复核）\n\n"
        for r in unknown:
            extra = f"；PDF 风险：{r.pdf_risk_note}" if r.pdf_risk_note else ""
            report += f"- **[{r.citation.index}]** {r.citation.marker} → {r.suggestion}{extra}\n"
        report += "\n"

    # Summary
    if bad:
        report += f"""## ⚠️ 审计结论

发现 **{counts['❌ 不支撑']}** 条可能引用不当的文献，**{counts['🟡 弱支撑']}** 条需要核对全文。

建议在进入 Step 8（润色）之前：
1. 优先处理 ❌ 不支撑的引用 — 移除或替换为真正支撑该声明的论文
2. 逐一核对 🟡 弱支撑的引用 — 打开 PDF 全文确认
3. 对 ⚠️ 无法判断的引用，通过 Zotero MCP 获取摘要后重新审计
"""
    elif weak:
        report += "## 审计结论\n\n未发现明显引用不当，但有少量引用建议核对全文确认。可以进入 Step 8 润色。\n"
    elif unknown:
        report += "## ⚠️ 审计结论\n\n当前引用未发现明确不当项，但存在无法判断的条目；在补摘要或回 PDF 全文核验前，不应视为“全部通过审计”。\n"
    else:
        report += "## ✅ 审计结论\n\n所有引用通过审计，未发现引用不当问题。可以进入 Step 8 润色。\n"

    return report


def load_mapping_records(path: str | None) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return [r for r in data["records"] if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def load_prepared_chunks(path: str | None) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def enrich_citations_with_mapping(
    citations: list[CitationRef],
    mapping_records: list[dict],
) -> None:
    """Use mapping JSON to fill citekey/title/doi/zotero_item_key hints."""
    by_title = {}
    for rec in mapping_records:
        title = str(rec.get("title", "")).strip().lower()
        if title:
            by_title[title] = rec

    for cit in citations:
        if cit.index > 0 and cit.bib_entry:
            title_guess = _extract_title_from_bib(cit.bib_entry).lower()
            rec = by_title.get(title_guess)
            if rec:
                cit.title = rec.get("title", "") or cit.title
                cit.doi = normalize_doi(cit.doi or rec.get("doi", ""))


def build_pdf_risk_note(citation: CitationRef, prepared_chunks: list[dict]) -> str:
    """Find prepared chunk warnings matching the citation title or citekey."""
    title = citation.title.strip().lower()
    if not title:
        title = _extract_title_from_bib(citation.bib_entry).lower()
    notes = []
    for chunk in prepared_chunks:
        chunk_title = str(chunk.get("paper_title", "")).strip().lower()
        if title and chunk_title and title != chunk_title:
            continue
        if chunk.get("must_check_pdf"):
            flags = chunk.get("risk_flags") or []
            if flags:
                notes.extend(flags)
            else:
                notes.append("must_check_pdf")
    if not notes:
        return ""
    uniq = sorted(set(notes))
    return "该引用关联的 PDF 提取结果包含高风险内容，需要回原 PDF 核验：" + ", ".join(uniq)


# ── Helpers ──────────────────────────────────────────────────────────────────

DOI_PATTERN = re.compile(
    r"(?i)(?:https?://(?:dx\.)?doi\.org/|doi\s*:?\s*)?"
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)"
)


def _extract_doi(text: str) -> str:
    """Extract and normalize a DOI without truncating dots in its suffix."""
    match = DOI_PATTERN.search(text or "")
    if not match:
        return ""
    return normalize_doi(match.group(1).rstrip(",;:]}>"))


def _claim_occurrence_id(
    *,
    line_number: int,
    column: int,
    reference_identity: str,
    claim_sentence: str,
) -> str:
    seed = f"{line_number}|{column}|{reference_identity}|{claim_sentence}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"occ-L{line_number:05d}-C{column:04d}-{digest}"


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text or ""))

def _find_reference_section(lines: list[str]) -> int:
    """Find the line index where the references section starts."""
    ref_patterns = [
        r'^#+\s*参考',
        r'^#+\s*References?$',
        r'^#+\s*Bibliography$',
        r'^#+\s*文献',
    ]
    for i, line in enumerate(lines):
        for pat in ref_patterns:
            if re.match(pat, line.strip(), re.IGNORECASE):
                return i
    return len(lines)


def _parse_cite_numbers(raw: str) -> list[int]:
    """Parse citation numbers from raw string like '2,5' or '3-7' or '1, 3, 5'."""
    numbers = []
    # Split by common delimiters
    parts = re.split(r'[,，\s]+', raw.strip())
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            # Range: "3-7"
            try:
                a, b = part.split('-', 1)
                numbers.extend(range(int(a), int(b) + 1))
            except ValueError:
                pass
        else:
            try:
                numbers.append(int(part))
            except ValueError:
                pass
    return numbers


def _get_context(lines: list[str], line_idx: int, window: int = 3) -> str:
    """Get surrounding paragraph context for a citation."""
    start = max(0, line_idx - window)
    end = min(len(lines), line_idx + window + 1)
    return '\n'.join(lines[start:end])


def _extract_key_terms(text: str, min_len: int = 3) -> list[str]:
    """Extract key technical terms from text for matching."""
    # Remove punctuation and split
    cleaned = re.sub(r'[^\w\s\-]', ' ', text)
    words = cleaned.split()
    # Filter short words and common stop words
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'shall',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'this', 'that', 'these', 'those', 'it', 'its', 'and', 'or',
        'but', 'not', 'as', 'than', 'we', 'our', '等', '的', '了',
        '在', '是', '有', '和', '与', '及', '或', '对',
    }
    terms = []
    for w in words:
        if len(w) >= min_len and w.lower() not in stop_words:
            terms.append(w)
    # Add bigrams for better matching
    for i in range(len(terms) - 1):
        terms.append(f"{terms[i]} {terms[i+1]}")
    return list(set(terms))


def _pct(n: int, total: int) -> str:
    """Format percentage."""
    if total == 0:
        return "0%"
    return f"{n / total:.0%}"


def _resolve_doi_for_citation(
    bib_entry: str,
    lit_table_dois: dict[int, str] = None,
) -> str:
    """Try to find a DOI for a citation from the bib entry or literature table."""
    # Try to extract DOI directly from bib entry
    doi = _extract_doi(bib_entry)
    if doi:
        return doi

    # Try literature table lookup
    if lit_table_dois:
        return lit_table_dois.get(-1, "")
    return ""


def classify_claim_requirement(claim: str) -> tuple[str, str]:
    lowered = claim.lower()
    if re.search(r"首次|首创|创新|first|novel|state[- ]of[- ]the[- ]art", lowered):
        return "novelty", "search_coverage"
    if re.search(r"机理|机制|因果|主导|作用路径|mechanism|causal|dominant", lowered):
        return "mechanism", "full_text"
    if re.search(r"\d+(?:\.\d+)?\s*(?:%|°c|℃|k|v|a|w|pa|hz|mm|cm)", lowered):
        return "numeric_comparison", "page_or_table"
    if re.search(r"普遍|总体|趋势|多数|generally|trend|most studies", lowered):
        return "trend", "multi_source"
    return "background", "abstract_ok"


def _chunk_anchor(citation: CitationRef, prepared_chunks: list[dict]) -> tuple[str, str]:
    doi = citation.doi.lower().strip()
    title = (citation.title or _extract_title_from_bib(citation.bib_entry)).lower().strip()
    if not doi and not title:
        return "", ""
    for chunk in prepared_chunks:
        blob = json.dumps(chunk, ensure_ascii=False).lower()
        if doi and doi not in blob:
            continue
        if not doi and title not in blob:
            continue
        anchor = chunk.get("chunk_id") or chunk.get("id") or chunk.get("pages") or chunk.get("page")
        return "full_text", str(anchor or "prepared_chunk_unanchored")
    return "", ""


def build_claim_evidence_payload(manuscript_text: str, results: list[AuditResult], prepared_chunks: list[dict]) -> dict:
    records: list[dict] = []
    unresolved = 0
    for index, result in enumerate(results, 1):
        citation = result.citation
        claim_strength, required_evidence = classify_claim_requirement(citation.claim_sentence)
        chunk_depth, chunk_anchor = _chunk_anchor(citation, prepared_chunks)
        reading_depth = chunk_depth or ("abstract_only" if result.abstract and not result.abstract.startswith("（") else "metadata_only")
        evidence_anchor = chunk_anchor or (f"abstract:{citation.doi}" if reading_depth == "abstract_only" and citation.doi else "")
        if result.support_level == "❌ 不支撑":
            support_grade = "not_supported"
            action = "replace_or_remove"
        elif result.support_level == "⚠️ 无法判断":
            support_grade = "metadata_only_candidate"
            action = "supplement_pdf_or_fulltext"
        elif result.support_level == "🟡 弱支撑":
            support_grade = "partial"
            action = "supplement_pdf_or_fulltext"
        elif required_evidence == "abstract_ok":
            support_grade = "background"
            action = "retain"
        else:
            support_grade = "partial"
            action = "supplement_pdf_or_fulltext"
        downgrade_required = action != "retain"
        resolution_status = "closed" if not downgrade_required else "open"
        if resolution_status != "closed":
            unresolved += 1
        records.append({
            "claim_segment_id": f"S{index:03d}",
            "claim_occurrence_id": citation.claim_occurrence_id or f"legacy-S{index:03d}",
            "claim_text": citation.claim_sentence,
            "claim_strength": claim_strength,
            "required_evidence": required_evidence,
            "citation_marker": citation.marker,
            "doi": citation.doi,
            "support_grade": support_grade,
            "reading_depth": reading_depth,
            "evidence_anchor": evidence_anchor,
            "downgrade_required": downgrade_required,
            "recommended_action": action,
            "resolution_status": resolution_status,
            "automated_assessment_boundary": "abstract_screening_plus_available_chunk_trace",
        })
    return {
        "schema_version": "claim-evidence-audit.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "draft_sha256": hashlib.sha256(manuscript_text.encode("utf-8")).hexdigest(),
        "assessment_boundary": "Automated screening does not replace interpretive full-text review for strong claims.",
        "summary": {"record_count": len(records), "unresolved_count": unresolved},
        "records": records,
    }


def _extract_title_from_bib(bib_entry: str) -> str:
    if not bib_entry:
        return ""
    parts = [p.strip() for p in re.split(r"\.\s+", bib_entry) if p.strip()]
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else ""


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Post-writing citation audit — verify cited papers support their claims",
    )
    parser.add_argument(
        "manuscript",
        nargs="?",
        help="Path to manuscript .md file",
    )
    parser.add_argument(
        "--output", "-o",
        default="引用审计报告.md",
        help="Output audit report path (default: 引用审计报告.md)",
    )
    parser.add_argument(
        "--output-json",
        default="claim_evidence_audit.json",
        help="Structured claim-level audit JSON (default: claim_evidence_audit.json)",
    )
    parser.add_argument(
        "--lit-table",
        help="Path to 检索文献表.md for DOI cross-reference",
    )
    parser.add_argument(
        "--mapping",
        help="Path to 文献-Zotero架构对照.json",
    )
    parser.add_argument(
        "--pdf-index",
        help="Path to pdf-附件池索引.json (currently informational only)",
    )
    parser.add_argument(
        "--prepared-chunks",
        help="Path to prepared PDF chunks JSON from prepare_pdf_for_llm.py",
    )
    parser.add_argument(
        "--zotero",
        action="store_true",
        help="Use Zotero MCP for abstract retrieval (requires Zotero MCP server)",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only extract citations, don't fetch abstracts or score",
    )
    parser.add_argument(
        "--max-abstracts",
        type=int,
        default=50,
        help="Max number of abstracts to fetch (default: 50)",
    )

    args = parser.parse_args()

    if not args.manuscript:
        parser.print_help()
        return

    if not os.path.exists(args.manuscript):
        print(f"❌ 文件不存在: {args.manuscript}")
        return

    print(f"📄 读取稿件: {args.manuscript}")
    with open(args.manuscript, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Step 1: Extract citations
    print("🔍 提取引用标记...")
    citations = extract_citations_from_manuscript(md_text)
    print(f"   找到 {len(citations)} 处引用")

    # Step 2: Extract bibliography
    print("📚 解析参考文献列表...")
    bib_entries = extract_bibliography(md_text)
    dois = extract_dois_from_bib(bib_entries)
    print(f"   提取 {len(bib_entries)} 条参考文献条目，{len(dois)} 个 DOI")

    mapping_records = load_mapping_records(args.mapping)
    prepared_chunks = load_prepared_chunks(args.prepared_chunks)
    if mapping_records:
        print(f"🗂 读取映射记录: {len(mapping_records)}")
    if prepared_chunks:
        print(f"🧩 读取 prepared chunks: {len(prepared_chunks)}")

    # Step 3: Enrich citations with bib data
    for cit in citations:
        if cit.index > 0 and cit.index in bib_entries:
            cit.bib_entry = bib_entries[cit.index]
            if cit.index in dois:
                cit.doi = dois[cit.index]
    enrich_citations_with_mapping(citations, mapping_records)

    if args.extract_only:
        print("\n── 引用清单 ──")
        for cit in citations:
            print(f"  [{cit.index}] L{cit.line_number}: {cit.claim_sentence[:100]}...")
        print(f"\n共 {len(citations)} 处引用")
        return

    # Step 4: Fetch abstracts and score
    print(f"\n🌐 获取摘要并评分（最多 {args.max_abstracts} 篇）...")
    results = []
    fetch_count = 0

    for cit in citations:
        if fetch_count >= args.max_abstracts:
            break

        abstract = None
        title = ""

        if cit.doi:
            fetch_count += 1
            print(f"   [{cit.index}] DOI: {cit.doi} ...", end=" ")
            # Try Crossref first, then Semantic Scholar
            title = fetch_title_crossref(cit.doi) or ""
            abstract = fetch_abstract_crossref(cit.doi) or fetch_abstract_semantic_scholar(cit.doi)
            if abstract:
                print("✅ 摘要获取成功")
            else:
                print("⚠️ 无摘要")
        else:
            # No DOI — mark as unable to judge
            print(f"   [{cit.index}] 无 DOI — 跳过")

        result = score_citation_support(cit, abstract or "", title)
        result.pdf_risk_note = build_pdf_risk_note(cit, prepared_chunks)
        if result.pdf_risk_note and result.support_level == "✅ 支撑":
            result.suggestion = "摘要层支撑成立，但涉及高风险 PDF 内容，仍建议回原 PDF 核验"
        results.append(result)

        # Rate limit
        time.sleep(0.3)

    # Handle remaining citations without abstract fetch
    for cit in citations[len(results):]:
        results.append(AuditResult(
            citation=cit,
            support_level="⚠️ 无法判断",
            abstract="（未获取摘要，超出批次限制）",
            reasoning="摘要获取批次已满，该引用未审计",
            suggestion="减少审计范围或分批运行",
        ))

    # Step 5: Generate report
    print(f"\n📊 生成审计报告...")
    report = generate_audit_report(results, args.manuscript, len(citations))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    claim_payload = build_claim_evidence_payload(md_text, results, prepared_chunks)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(claim_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ 审计报告已保存: {args.output}")
    print(f"✅ Claim evidence audit saved: {args.output_json}")

    # Print summary
    counts = {"✅ 支撑": 0, "🟡 弱支撑": 0, "❌ 不支撑": 0, "⚠️ 无法判断": 0}
    for r in results:
        counts[r.support_level] = counts.get(r.support_level, 0) + 1
    print(f"   ✅ 支撑: {counts['✅ 支撑']}  |  🟡 弱支撑: {counts['🟡 弱支撑']}  |  ❌ 不支撑: {counts['❌ 不支撑']}  |  ⚠️ 无法判断: {counts['⚠️ 无法判断']}")


if __name__ == "__main__":
    main()
