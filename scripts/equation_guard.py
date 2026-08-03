#!/usr/bin/env python3
"""Audit paper drafts for missing equations and unrendered math source."""

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
import tempfile
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


AUDIT_SCHEMA = "equation-audit.v1"
REGISTER_SCHEMA = "equation-register.v1"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

GREEK_WORDS = (
    "alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|"
    "omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega"
)
PLAIN_GREEK_RE = re.compile(rf"\b[A-Za-z][A-Za-z0-9]*\s*\(\s*({GREEK_WORDS})\s*\)|\(\s*({GREEK_WORDS})\s*\)", re.I)
NAKED_SUBSCRIPT_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9]*|[a-z])_(?:\{[^}\n]+\}|[A-Za-z0-9]+)")
NONCANONICAL_DELIMITER_RE = re.compile(r"\\\((?:.|\n)*?\\\)|\\\[(?:.|\n)*?\\\]", re.S)
LATEX_COMMAND_RE = re.compile(
    r"\\(?:frac|dfrac|tfrac|sum|prod|int|iint|iiint|sqrt|left|right|cdot|times|"
    r"partial|nabla|mathrm|mathbf|mathit|operatorname|begin|end|label|tag|"
    rf"{GREEK_WORDS})\b"
)
MATRIX_BEGIN_RE = re.compile(r"\\begin\{(bmatrix|Bmatrix|pmatrix|vmatrix|Vmatrix|matrix|array)\}")
MATRIX_BLOCK_RE = re.compile(
    r"\\begin\{(bmatrix|Bmatrix|pmatrix|vmatrix|Vmatrix|matrix|array)\}(.*?)"
    r"\\end\{\1\}",
    re.S,
)
EQUATION_CUE_RE = re.compile(
    r"如下式所示|由下式(?:给出|表示)|可表示为|可写为|目标函数为|"
    r"状态方程为|控制方程为|计算公式为|数学表达式(?:为|定义为)|传递函数为|"
    r"(?:is|can be)\s+(?:expressed|written)\s+as(?:\s+follows)?|"
    r"objective\s+function\s+is|state\s+equation\s+is",
    re.I,
)
EQUATION_REFERENCE_RE = re.compile(
    r"式\s*[（(]\s*(\d+(?:[-.]\d+)*)\s*[）)]|"
    r"Eq(?:uation)?\.?\s*[（(]\s*(\d+(?:[-.]\d+)*)\s*[）)]",
    re.I,
)
EQUATION_TAG_RE = re.compile(r"\\tag\{([^}]+)\}")
NUMBER_ONLY_RE = re.compile(r"^\s*[（(]\s*(\d+(?:[-.]\d+)*)\s*[）)]\s*$")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    source: str
    line: int
    excerpt: str
    message: str
    recommended_action: str


@dataclass
class LoadedDocument:
    path: Path
    source_format: str
    text: str
    native_math_lines: list[int]
    native_math_count: int


@dataclass(frozen=True)
class MathSpan:
    start: int
    end: int
    source: str
    kind: str
    canonical: bool


def infer_format(path: Path, requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".tex":
        return "latex"
    if suffix == ".docx":
        return "docx"
    return "plain"


def _read_docx(path: Path) -> LoadedDocument:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(f"cannot read DOCX document.xml: {exc}") from exc

    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    native_math_lines: list[int] = []
    native_math_count = 0
    paragraph_tag = f"{{{WORD_NS}}}p"
    text_tags = {f"{{{WORD_NS}}}t", f"{{{MATH_NS}}}t"}
    math_tags = {f"{{{MATH_NS}}}oMath", f"{{{MATH_NS}}}oMathPara"}

    for paragraph in root.iter(paragraph_tag):
        line_no = len(paragraphs) + 1
        pieces = [node.text or "" for node in paragraph.iter() if node.tag in text_tags]
        paragraph_math = sum(1 for node in paragraph.iter() if node.tag == f"{{{MATH_NS}}}oMath")
        if paragraph_math:
            native_math_lines.extend([line_no] * paragraph_math)
            native_math_count += paragraph_math
        elif any(node.tag in math_tags for node in paragraph.iter()):
            native_math_lines.append(line_no)
            native_math_count += 1
        paragraphs.append("".join(pieces))

    return LoadedDocument(path, "docx", "\n".join(paragraphs), native_math_lines, native_math_count)


def load_document(path: Path, requested_format: str = "auto") -> LoadedDocument:
    source_format = infer_format(path, requested_format)
    if source_format == "docx":
        return _read_docx(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    return LoadedDocument(path, source_format, text, [], 0)


def _mask_match(text: str, pattern: re.Pattern[str]) -> str:
    chars = list(text)
    for match in pattern.finditer(text):
        for index in range(match.start(), match.end()):
            if chars[index] != "\n":
                chars[index] = " "
    return "".join(chars)


def _mask_nonprose(text: str, source_format: str) -> str:
    masked = text
    if source_format == "markdown":
        masked = _mask_match(masked, re.compile(r"(?ms)^\s*(```|~~~).*?^\s*\1\s*$"))
        masked = _mask_match(masked, re.compile(r"`[^`\n]+`"))
        masked = _mask_match(masked, re.compile(r"!?\[[^\]]*\]\([^)]+\)"))
    masked = _mask_match(masked, re.compile(r"https?://\S+"))
    return masked


def _collect_spans(text: str, patterns: Iterable[tuple[re.Pattern[str], str, bool]]) -> list[MathSpan]:
    candidates: list[MathSpan] = []
    for pattern, kind, canonical in patterns:
        for match in pattern.finditer(text):
            candidates.append(MathSpan(match.start(), match.end(), match.group(0), kind, canonical))
    selected: list[MathSpan] = []
    for candidate in sorted(candidates, key=lambda item: (item.start, -(item.end - item.start))):
        if any(candidate.start < item.end and candidate.end > item.start for item in selected):
            continue
        selected.append(candidate)
    return sorted(selected, key=lambda item: item.start)


def extract_math_spans(text: str, source_format: str = "markdown") -> list[MathSpan]:
    slash_patterns = [
        (re.compile(r"\\\[(?:.|\n)*?\\\]", re.S), "slash_display", source_format == "latex"),
        (re.compile(r"\\\((?:.|\n)*?\\\)", re.S), "slash_inline", source_format == "latex"),
    ]
    dollar_patterns = [
        (re.compile(r"(?<!\\)\$\$(?:.|\n)*?(?<!\\)\$\$", re.S), "display", True),
        (re.compile(r"(?<!\\)(?<!\$)\$(?!\$)(?:\\.|[^$\n])+?(?<!\\)\$(?!\$)"), "inline", True),
    ]
    if source_format == "latex":
        environments = (
            r"equation|equation\*|align|align\*|gather|gather\*|multline|multline\*|"
            r"displaymath|math"
        )
        environment_patterns = [
            (
                re.compile(rf"\\begin\{{({environments})\}}(?:.|\n)*?\\end\{{\1\}}", re.S),
                "environment",
                True,
            )
        ]
        return _collect_spans(text, environment_patterns + slash_patterns + dollar_patterns)
    if source_format == "markdown":
        return _collect_spans(text, dollar_patterns + slash_patterns)
    return _collect_spans(text, slash_patterns)


def _span_contains(spans: list[MathSpan], position: int, *, canonical_only: bool = False) -> bool:
    return any(span.start <= position < span.end and (span.canonical or not canonical_only) for span in spans)


def _line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _excerpt(text: str, position: int, width: int = 120) -> str:
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    if line_end < 0:
        line_end = len(text)
    return re.sub(r"\s+", " ", text[line_start:line_end]).strip()[:width]


def _heading_for_line(text: str, target_line: int) -> str:
    heading = ""
    for line_no, line in enumerate(text.splitlines(), 1):
        if line_no > target_line:
            break
        match = HEADING_RE.match(line)
        if match:
            heading = match.group(1).strip()
    return heading


def _normalize_math_source(source: str) -> str:
    source = source.strip()
    if source.startswith("$$") and source.endswith("$$"):
        source = source[2:-2]
    elif source.startswith("$") and source.endswith("$"):
        source = source[1:-1]
    elif source.startswith(r"\(") and source.endswith(r"\)"):
        source = source[2:-2]
    elif source.startswith(r"\[") and source.endswith(r"\]"):
        source = source[2:-2]
    return source.strip()


def math_signature_counter(text: str, source_format: str = "markdown") -> Counter[str]:
    return Counter(
        re.sub(r"\s+", "", _normalize_math_source(span.source))
        for span in extract_math_spans(_mask_nonprose(text, source_format), source_format)
        if _normalize_math_source(span.source)
    )


def _make_register_records(document: LoadedDocument, spans: list[MathSpan], start_index: int) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for offset, span in enumerate(spans, start=start_index):
        line = _line_number(document.text, span.start)
        records.append({
            "equation_id": f"EQ-{offset:03d}",
            "section_id": _heading_for_line(document.text, line),
            "purpose": "unspecified",
            "latex_source": _normalize_math_source(span.source),
            "plain_language_explanation": "",
            "variables": [],
            "units": [],
            "assumptions": [],
            "evidence_anchor": "",
            "where_referenced": [],
            "derivation_status": "not_audited",
            "validation_status": "pass" if span.canonical else "needs_repair",
            "needs_author_check": not span.canonical,
            "source": str(document.path),
            "location": f"line {line}",
            "source_format": document.source_format,
            "render_target": document.source_format,
        })
    next_index = start_index + len(spans)
    for line in sorted(document.native_math_lines):
        records.append({
            "equation_id": f"EQ-{next_index:03d}",
            "section_id": "",
            "purpose": "unspecified",
            "latex_source": "",
            "plain_language_explanation": "",
            "variables": [],
            "units": [],
            "assumptions": [],
            "evidence_anchor": "",
            "where_referenced": [],
            "derivation_status": "not_audited",
            "validation_status": "needs_author_check",
            "needs_author_check": True,
            "source": str(document.path),
            "location": f"paragraph {line}",
            "source_format": "docx",
            "render_target": "docx_omml",
        })
        next_index += 1
    return records


def audit_document(document: LoadedDocument) -> tuple[list[Finding], list[dict[str, object]]]:
    text = document.text
    visible = _mask_nonprose(text, document.source_format)
    spans = extract_math_spans(visible, document.source_format)
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()

    def add(code: str, match_start: int, message: str, action: str, severity: str = "error") -> None:
        line = _line_number(text, match_start)
        key = (code, line, message)
        if key in seen:
            return
        seen.add(key)
        findings.append(Finding(
            severity=severity,
            code=code,
            source=str(document.path),
            line=line,
            excerpt=_excerpt(text, match_start),
            message=message,
            recommended_action=action,
        ))

    if document.source_format != "latex":
        for match in NONCANONICAL_DELIMITER_RE.finditer(visible):
            add(
                "noncanonical_math_delimiter",
                match.start(),
                r"noncanonical \(...\) or \[...\] math delimiter may remain as text",
                "use $...$ or $$...$$ in Markdown, and a native equation object in DOCX",
            )

    for match in PLAIN_GREEK_RE.finditer(visible):
        add(
            "plain_text_math_leak",
            match.start(),
            f"plain-text Greek name remains in mathematical expression: {match.group(0)}",
            r"replace the Greek name with a rendered symbol such as $\omega$",
        )

    for match in NAKED_SUBSCRIPT_RE.finditer(visible):
        if _span_contains(spans, match.start(), canonical_only=True):
            continue
        add(
            "plain_text_math_leak",
            match.start(),
            f"subscript expression is outside a rendered math span: {match.group(0)}",
            "move the expression into a math span; confirm textual subscripts before rewriting",
        )

    for match in MATRIX_BEGIN_RE.finditer(visible):
        if _span_contains(spans, match.start(), canonical_only=True):
            continue
        add(
            "matrix_source_leak",
            match.start(),
            f"matrix source is outside a rendered math environment: {match.group(0)}",
            "wrap the matrix in a valid target-format equation and verify row separators",
        )

    for match in LATEX_COMMAND_RE.finditer(visible):
        if _span_contains(spans, match.start(), canonical_only=True):
            continue
        if MATRIX_BEGIN_RE.match(visible, match.start()):
            continue
        add(
            "latex_source_leak",
            match.start(),
            f"LaTeX command is outside a rendered math environment: {match.group(0)}",
            "move the command into a valid equation or convert it to a native formula object",
        )

    for match in MATRIX_BLOCK_RE.finditer(visible):
        body = match.group(2)
        body_start = match.start(2)
        for line_match in re.finditer(r"(?m)^.*(?<!\\)\\\s*$", body):
            if line_match.group(0).strip():
                add(
                    "malformed_matrix_rows",
                    body_start + line_match.start(),
                    "matrix row ends with one backslash instead of a double row separator",
                    r"replace the row ending with \\ and re-render the matrix",
                )

    begins = Counter(re.findall(r"\\begin\{([^}]+)\}", visible))
    ends = Counter(re.findall(r"\\end\{([^}]+)\}", visible))
    for environment in sorted(set(begins) | set(ends)):
        if begins[environment] == ends[environment]:
            continue
        position = visible.find(rf"\begin{{{environment}}}")
        if position < 0:
            position = visible.find(rf"\end{{{environment}}}")
        add(
            "unclosed_math_environment",
            max(position, 0),
            f"environment {environment!r} has {begins[environment]} begin and {ends[environment]} end markers",
            "balance the environment markers before delivery",
        )

    for span in spans:
        source = _normalize_math_source(span.source)
        if source.count("{") != source.count("}"):
            add(
                "unclosed_math_environment",
                span.start,
                "equation contains unbalanced braces",
                "balance braces and re-run the audit",
            )

    lines = visible.splitlines()
    line_offsets: list[int] = []
    offset = 0
    for line in visible.splitlines(keepends=True):
        line_offsets.append(offset)
        offset += len(line)
    if len(line_offsets) < len(lines):
        line_offsets.append(offset)

    canonical_lines = {
        _line_number(visible, span.start)
        for span in spans
        if span.canonical
    }
    for line_index, line in enumerate(lines):
        cue = EQUATION_CUE_RE.search(line)
        if not cue:
            continue
        nearby = False
        checked_nonempty = 0
        for candidate_index in range(line_index, min(len(lines), line_index + 5)):
            candidate = lines[candidate_index]
            if candidate.strip():
                checked_nonempty += 1
            line_no = candidate_index + 1
            if line_no in canonical_lines or line_no in document.native_math_lines:
                nearby = True
                break
            if checked_nonempty >= 3:
                break
        if not nearby:
            add(
                "missing_equation",
                line_offsets[line_index] + cue.start(),
                "equation-introducing prose is not followed by a rendered equation",
                "restore the equation from the model/evidence source or mark needs_author_check",
            )

    defined_numbers = set(EQUATION_TAG_RE.findall(visible))
    defined_numbers.update(
        match.group(1)
        for line in lines
        if (match := NUMBER_ONLY_RE.match(line))
    )
    for match in EQUATION_REFERENCE_RE.finditer(visible):
        number = match.group(1) or match.group(2)
        if number not in defined_numbers:
            add(
                "broken_equation_reference",
                match.start(),
                f"equation reference {number} has no matching equation number",
                "add the referenced equation/tag or correct the cross-reference",
            )

    records = _make_register_records(document, spans, 1)
    return findings, records


def _combined_sha256(documents: list[LoadedDocument]) -> str:
    combined = "\n".join(document.text for document in documents)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def audit_paths(paths: Iterable[Path], target_format: str = "auto") -> tuple[dict[str, object], dict[str, object]]:
    documents = [load_document(Path(path), target_format) for path in paths]
    findings: list[Finding] = []
    records: list[dict[str, object]] = []
    equation_index = 1
    for document in documents:
        document_findings, document_records = audit_document(document)
        findings.extend(document_findings)
        for record in document_records:
            record["equation_id"] = f"EQ-{equation_index:03d}"
            equation_index += 1
            records.append(record)

    error_count = sum(1 for finding in findings if finding.severity == "error")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    draft_sha256 = _combined_sha256(documents)
    summary = {
        "schema_version": AUDIT_SCHEMA,
        "status": "fail" if error_count else "warn" if warning_count else "pass",
        "draft_sha256": draft_sha256,
        "source_count": len(documents),
        "equation_count": len(records),
        "native_math_count": sum(document.native_math_count for document in documents),
        "error_count": error_count,
        "warning_count": warning_count,
        "finding_count": len(findings),
    }
    audit = {
        "summary": summary,
        "sources": [
            {"path": str(document.path), "format": document.source_format}
            for document in documents
        ],
        "findings": [asdict(finding) for finding in findings],
    }
    register = {
        "schema_version": REGISTER_SCHEMA,
        "draft_sha256": draft_sha256,
        "record_count": len(records),
        "records": records,
    }
    return audit, register


def render_audit_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "# Equation Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- equation_count: {summary['equation_count']}",
        f"- native_math_count: {summary['native_math_count']}",
        f"- error_count: {summary['error_count']}",
        f"- warning_count: {summary['warning_count']}",
        f"- draft_sha256: `{summary['draft_sha256']}`",
        "",
    ]
    findings = payload["findings"]
    if not findings:
        lines.extend(["## Result", "", "No equation-writing defects detected.", ""])
    else:
        lines.extend([
            "## Findings",
            "",
            "| Severity | Code | Source | Line | Problem |",
            "|----------|------|--------|-----:|---------|",
        ])
        for finding in findings:
            message = str(finding["message"]).replace("|", "\\|")
            source = Path(str(finding["source"])).name.replace("|", "\\|")
            lines.append(
                f"| {finding['severity']} | `{finding['code']}` | `{source}` | "
                f"{finding['line']} | {message} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_register_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Equation Register",
        "",
        f"- record_count: {payload['record_count']}",
        f"- draft_sha256: `{payload['draft_sha256']}`",
        "",
        "| ID | Section | Location | Format | Validation | Author check | Source |",
        "|----|---------|----------|--------|------------|--------------|--------|",
    ]
    for record in payload["records"]:
        source = str(record["latex_source"]).replace("|", "\\|").replace("\n", " ")
        if len(source) > 80:
            source = source[:77] + "..."
        lines.append(
            f"| `{record['equation_id']}` | {record['section_id'] or '-'} | "
            f"{record['location']} | `{record['source_format']}` | "
            f"`{record['validation_status']}` | `{str(record['needs_author_check']).lower()}` | "
            f"`{source or '<native equation object>'}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit missing equations and unrendered math in paper drafts.")
    parser.add_argument("inputs", nargs="+", help="Markdown, LaTeX, text, or DOCX files")
    parser.add_argument("--format", choices=("auto", "markdown", "latex", "plain", "docx"), default="auto")
    parser.add_argument("--output-dir", help="Write standard equation audit/register artifacts to this directory")
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    parser.add_argument("--register-json")
    parser.add_argument("--register-md")
    parser.add_argument("--json", action="store_true", help="Print the audit as JSON")
    args = parser.parse_args()

    paths = [Path(value).expanduser().resolve() for value in args.inputs]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        parser.error("input file not found: " + ", ".join(missing))

    try:
        audit, register = audit_paths(paths, args.format)
    except ValueError as exc:
        parser.error(str(exc))

    output_json = Path(args.output_json) if args.output_json else None
    output_md = Path(args.output_md) if args.output_md else None
    register_json = Path(args.register_json) if args.register_json else None
    register_md = Path(args.register_md) if args.register_md else None
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_json = output_json or output_dir / "equation_audit.json"
        output_md = output_md or output_dir / "equation_audit.md"
        register_json = register_json or output_dir / "equation_register.json"
        register_md = register_md or output_dir / "equation_register.md"

    if output_json:
        _write_json(output_json, audit)
    if output_md:
        _atomic_write_text(output_md, render_audit_markdown(audit))
    if register_json:
        _write_json(register_json, register)
    if register_md:
        _atomic_write_text(register_md, render_register_markdown(register))

    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    elif not any([output_json, output_md, register_json, register_md]):
        print(render_audit_markdown(audit))
    else:
        summary = audit["summary"]
        print(
            f"EQUATION_AUDIT: {summary['status']} "
            f"(equations={summary['equation_count']}, errors={summary['error_count']}, "
            f"warnings={summary['warning_count']})"
        )
    return 0 if audit["summary"]["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
