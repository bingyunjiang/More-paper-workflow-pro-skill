#!/usr/bin/env python3
"""Audit whether Step 8 polishing preserved protected academic content."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from equation_guard import math_signature_counter


PRESERVED_PATTERNS = {
    "numeric_unit": re.compile(
        r"[-+]?\d+(?:\.\d+)?\s*(?:%|°C|℃|K|kV|V|mA|A|MW|kW|W|MHz|kHz|Hz|GPa|MPa|Pa|mm|cm|ms|rpm)"
    ),
    "citation": re.compile(r"\[\d+(?:\s*[-–,，]\s*\d+)*\]"),
    "doi": re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE),
    "figure_formula_anchor": re.compile(
        r"(?:图|表|式)\s*\d+(?:[-.]\d+)*|(?:Fig(?:ure)?|Table|Eq(?:uation)?)\.?\s*\(?\d+(?:[-.]\d+)*\)?",
        re.IGNORECASE,
    ),
}

QUALIFIER_RE = re.compile(
    r"可能|或许|初步(?:表明|显示)?|在[^，。；;]{0,30}条件下|仅(?:限于|适用于|讨论)|"
    r"may|might|possibly|preliminary|under\s+[^,.;]{1,40}\s+conditions?|limited\s+to",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(r"不|未|无|不能|不得|并非|not|no|without|cannot|neither", re.IGNORECASE)
RESPONSIBILITY_RE = re.compile(
    r"本文|本研究|本实验|作者|该研究|该文献|文献\s*[A-Za-z0-9一二三四五六七八九十]+|"
    r"this\s+(?:work|study)|the\s+authors?|previous\s+studies",
    re.IGNORECASE,
)
STRENGTHENING_RE = re.compile(
    r"证明|证实|显著|首次|首创|普遍|必然|完全|决定性|"
    r"prove[sd]?|demonstrat(?:e|es|ed)|significant(?:ly)?|first|novel|universally|decisive",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"(?m)^#{1,6}\s+[^\n]+$")
PLACEHOLDER_RE = re.compile(r"\[\[TODO:[^\]]+\]\]|\[(?:待补证据|待核验|待补文献|图表待补)[^\]]*\]", re.IGNORECASE)
ARGUMENT_MARKER_RE = re.compile(
    r"然而|但是|但|尽管|相比之下|因此|由此|这表明|结果表明|需要指出|"
    r"however|although|despite|in contrast|therefore|thus|this (?:shows|suggests|indicates)",
    re.IGNORECASE,
)
CLAIM_VERB_RE = re.compile(
    r"表明|显示|发现|证明|证实|支持|说明|suggest(?:s|ed)?|show(?:s|ed)?|indicat(?:e|es|ed)|demonstrat(?:e|es|ed)",
    re.IGNORECASE,
)


def _counter(pattern: re.Pattern[str], text: str) -> Counter[str]:
    return Counter(re.sub(r"\s+", "", match.group(0)).lower() for match in pattern.finditer(text))


def _delta(before: Counter[str], after: Counter[str]) -> tuple[list[str], list[str]]:
    return sorted((before - after).elements()), sorted((after - before).elements())


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip() and not part.lstrip().startswith("#")]


def audit_fidelity(before: str, after: str) -> dict:
    issues: list[dict[str, object]] = []

    removed_equations, added_equations = _delta(
        math_signature_counter(before),
        math_signature_counter(after),
    )
    if removed_equations or added_equations:
        issues.append({
            "rule_id": "protected_span.equation_signature",
            "severity": "hard",
            "problem": "Rendered equation content or structure changed during polishing",
            "removed": removed_equations,
            "added": added_equations,
            "recommended_action": "restore the original formula or verify the mathematical change in Step 7",
        })

    for rule_id, pattern in PRESERVED_PATTERNS.items():
        removed, added = _delta(_counter(pattern, before), _counter(pattern, after))
        if removed or added:
            issues.append({
                "rule_id": f"protected_span.{rule_id}",
                "severity": "hard",
                "problem": f"Protected {rule_id} tokens changed",
                "removed": removed,
                "added": added,
                "recommended_action": "restore the protected token or verify the change manually",
            })

    for rule_id, pattern, severity in [
        ("heading", HEADING_RE, "hard"),
        ("evidence_placeholder", PLACEHOLDER_RE, "hard"),
        ("argument_marker", ARGUMENT_MARKER_RE, "warning"),
        ("claim_verb", CLAIM_VERB_RE, "warning"),
    ]:
        removed, added = _delta(_counter(pattern, before), _counter(pattern, after))
        if removed or added:
            issues.append({
                "rule_id": f"argument_fidelity.{rule_id}",
                "severity": severity,
                "problem": f"Academic argument {rule_id} markers changed",
                "removed": removed,
                "added": added,
                "recommended_action": "verify that section function, claim boundary, and logical relation are preserved",
            })

    for rule_id, pattern, severity in [
        ("evidence_qualifier", QUALIFIER_RE, "hard"),
        ("negation", NEGATION_RE, "hard"),
        ("responsibility_subject", RESPONSIBILITY_RE, "warning"),
    ]:
        removed, added = _delta(_counter(pattern, before), _counter(pattern, after))
        if removed or added:
            issues.append({
                "rule_id": f"meaning_drift.{rule_id}",
                "severity": severity,
                "problem": f"{rule_id} markers changed",
                "removed": removed,
                "added": added,
                "recommended_action": "verify subject, scope, direction, and evidence boundary",
            })

    _, strengthening_added = _delta(_counter(STRENGTHENING_RE, before), _counter(STRENGTHENING_RE, after))
    if strengthening_added:
        issues.append({
            "rule_id": "claim_strength.new_strengthening_language",
            "severity": "hard",
            "problem": "Polishing introduced stronger claim language",
            "removed": [],
            "added": strengthening_added,
            "recommended_action": "remove the strengthening language or return to Step 7 evidence review",
        })

    before_paragraphs = len(_paragraphs(before))
    after_paragraphs = len(_paragraphs(after))
    if before_paragraphs >= 3 and after_paragraphs < max(1, int(before_paragraphs * 0.65)):
        issues.append({
            "rule_id": "argument_fidelity.paragraph_collapse",
            "severity": "hard",
            "problem": "Polishing collapsed too many paragraph-level argument units",
            "removed": [str(before_paragraphs)],
            "added": [str(after_paragraphs)],
            "recommended_action": "restore paragraph jobs or verify the merge against the argument plan",
        })
    length_ratio = len(after) / max(len(before), 1)
    if length_ratio < 0.60 or length_ratio > 1.40:
        issues.append({
            "rule_id": "argument_fidelity.scope_change",
            "severity": "hard",
            "problem": "Polishing changed document scope beyond the conservative boundary",
            "removed": [str(len(before))],
            "added": [str(len(after))],
            "recommended_action": "return substantive additions/deletions to Step 7 revision rather than Step 8 polishing",
        })
    elif length_ratio < 0.75 or length_ratio > 1.25:
        issues.append({
            "rule_id": "argument_fidelity.scope_change",
            "severity": "warning",
            "problem": "Document length changed materially during polishing",
            "removed": [str(len(before))],
            "added": [str(len(after))],
            "recommended_action": "manually confirm that no argument unit was removed or introduced",
        })

    hard_count = sum(1 for item in issues if item["severity"] == "hard")
    warning_count = sum(1 for item in issues if item["severity"] == "warning")
    status = "fail" if hard_count else "warn" if warning_count else "pass"
    return {
        "summary": {
            "schema_version": "polish-fidelity-audit.v1",
            "status": status,
            "hard_failure_count": hard_count,
            "warning_count": warning_count,
            "issue_count": len(issues),
            "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
            "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            "before_paragraph_count": before_paragraphs,
            "after_paragraph_count": after_paragraphs,
            "length_ratio": round(length_ratio, 4),
        },
        "issues": issues,
    }


def render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Polish Fidelity Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- hard_failure_count: {summary['hard_failure_count']}",
        f"- warning_count: {summary['warning_count']}",
        "",
    ]
    for index, issue in enumerate(payload["issues"], start=1):
        lines.extend([
            f"## FID-{index:03d}",
            "",
            f"- rule_id: `{issue['rule_id']}`",
            f"- severity: `{issue['severity']}`",
            f"- problem: {issue['problem']}",
            f"- removed: {issue['removed'] or []}",
            f"- added: {issue['added'] or []}",
            f"- recommended_action: {issue['recommended_action']}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Step 8 before/after fidelity.")
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    before = Path(args.before).read_text(encoding="utf-8", errors="replace")
    after = Path(args.after).read_text(encoding="utf-8", errors="replace")
    payload = audit_fidelity(before, after)
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(render_markdown(payload), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not args.output_json and not args.output_md:
        print(render_markdown(payload))
    return 0 if payload["summary"]["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
