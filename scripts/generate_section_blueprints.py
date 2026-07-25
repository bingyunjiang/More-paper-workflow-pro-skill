#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Section blueprint generator — produces per-section detailed writing plans that
map the paper outline + evidence bank to the target journal's style conventions.

Inspired by PaperSpine's section_blueprints.md and writing_rationale_matrix.md.

Usage:
  python3 generate_section_blueprints.py style_profile.md 大纲关键词.md \\
      --evidence 综述矩阵.csv --output research_dossier/
"""
try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import json
import sys
import os
import re
import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class SectionBlueprint:
    """Detailed writing plan for one section."""
    section_title: str
    section_id: str             # e.g., "1", "2.3"
    section_function: str       # What this section does
    expected_length: str        # e.g., "~1200 words", "3-5 paragraphs"
    key_claims: list[str] = field(default_factory=list)
    evidence_needed: list[str] = field(default_factory=list)
    evidence_basis: list[dict] = field(default_factory=list)
    do_not_write: list[str] = field(default_factory=list)
    figure_needs: list[str] = field(default_factory=list)
    transition_from: str = ""   # How previous section connects
    transition_to: str = ""     # How this leads to next
    style_notes: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)

    def to_schema_dict(self) -> dict:
        return {
            "schema_version": "1.0",
            "section_id": self.section_id,
            "section_title": self.section_title,
            "section_function": self.section_function,
            "key_claims": self.key_claims,
            "evidence_needed": self.evidence_needed,
            "evidence_basis": self.evidence_basis,
            "do_not_write": self.do_not_write,
            "expected_length": self.expected_length,
            "figure_needs": self.figure_needs,
            "transition_from": self.transition_from,
            "transition_to": self.transition_to,
            "style_notes": self.style_notes,
            "risk_flags": self.risk_flags,
        }


# ── Blueprint Generation ─────────────────────────────────────────────────────

def generate_blueprints(
    outline_path: str,
    style_profile_path: str,
    evidence_csv_path: str = "",
) -> list[SectionBlueprint]:
    """Generate section blueprints from outline + style profile + evidence."""

    # Parse outline
    outline_sections = _parse_outline(outline_path)

    # Parse style profile for target conventions
    style_rules = _parse_style_profile(style_profile_path) if os.path.exists(style_profile_path) else {}

    # Parse evidence bank
    evidence = _parse_evidence_csv(evidence_csv_path) if evidence_csv_path and os.path.exists(evidence_csv_path) else {}

    blueprints = []
    for i, section in enumerate(outline_sections):
        bp = SectionBlueprint(
            section_title=section["name"],
            section_id=section["number"],
            section_function=_infer_purpose(section["name"], i, len(outline_sections), style_rules),
            expected_length=_estimate_length(section, style_rules),
            key_claims=_infer_claims(section, evidence, style_rules),
            evidence_needed=_infer_evidence_needed(section, style_rules),
            evidence_basis=_map_evidence(section, evidence),
            do_not_write=_infer_do_not_write(section, style_rules),
            figure_needs=_suggest_figures(section, style_rules),
            transition_from=_transition_from(i, outline_sections),
            transition_to=_transition_to(i, outline_sections),
            style_notes=_style_notes(section, style_rules),
            risk_flags=_infer_risk_flags(section, evidence, style_rules),
        )
        blueprints.append(bp)

    return blueprints


def _sha256(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def build_writing_blueprint_payload(
    blueprints: list[SectionBlueprint],
    *,
    outline_path: Path,
    style_profile_path: Path,
    evidence_path: Path | None = None,
    baseline_path: Path | None = None,
) -> dict:
    """Build a Step 7 derivative without replacing the Step 2 baseline."""
    baseline: dict = {}
    if baseline_path and baseline_path.is_file():
        loaded = json.loads(baseline_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict) or not isinstance(loaded.get("sections"), list):
            raise ValueError("Step 2 baseline must be an object containing sections")
        baseline = loaded
    baseline_sections = {
        str(section.get("section_id")): section
        for section in baseline.get("sections", [])
        if isinstance(section, dict) and section.get("section_id") is not None
    }
    sections = []
    for blueprint in blueprints:
        generated = blueprint.to_schema_dict()
        original = baseline_sections.get(str(blueprint.section_id), {})
        merged = dict(original)
        merged.update(generated)
        if original.get("rq_ids"):
            merged["rq_ids"] = original["rq_ids"]
        sections.append(merged)
    return {
        "schema_version": "section-blueprints.v2",
        "blueprint_state": "writing_derived",
        "outline_state": baseline.get("outline_state", "not_provided"),
        "core_research_question_ids": baseline.get("core_research_question_ids", []),
        "evidence_calibration": baseline.get("evidence_calibration"),
        "keyword_audit": baseline.get("keyword_audit", []),
        "source_lineage": {
            "baseline_path": str(baseline_path) if baseline_path else "",
            "baseline_sha256": _sha256(baseline_path),
            "outline_path": str(outline_path),
            "outline_sha256": _sha256(outline_path),
            "style_profile_path": str(style_profile_path),
            "style_profile_sha256": _sha256(style_profile_path),
            "evidence_path": str(evidence_path) if evidence_path else "",
            "evidence_sha256": _sha256(evidence_path),
        },
        "sections": sections,
    }


# ── Rendering ────────────────────────────────────────────────────────────────

def render_blueprints_md(
    blueprints: list[SectionBlueprint],
    journal: str = "",
) -> str:
    """Render blueprints as Markdown."""
    md = f"""# 章节写作蓝图

"""
    if journal:
        md += f"> 目标期刊：**{journal}**\n\n"

    md += "## 蓝图总览\n\n"
    md += "| 章节 | 用途 | 预估篇幅 | 关键声明 | 图表 |\n"
    md += "|------|------|:---:|------|:---:|\n"
    for bp in blueprints:
        claims_brief = "; ".join(bp.key_claims[:2])
        if len(bp.key_claims) > 2:
            claims_brief += f"...（共{len(bp.key_claims)}条）"
        figs_brief = str(len(bp.figure_needs)) if bp.figure_needs else "—"
        md += f"| {bp.section_id} {bp.section_title} | {bp.section_function[:40]}... | {bp.expected_length} | {claims_brief[:60]} | {figs_brief} |\n"

    md += "\n---\n\n"

    for bp in blueprints:
        md += _render_single_blueprint(bp)

    return md


def _render_single_blueprint(bp: SectionBlueprint) -> str:
    """Render a single section blueprint."""
    md = f"""### {bp.section_id} {bp.section_title}

**用途：** {bp.section_function}

**预估篇幅：** {bp.expected_length}

"""
    if bp.key_claims:
        md += "**关键声明：**\n"
        for c in bp.key_claims:
            md += f"- {c}\n"
        md += "\n"

    if bp.evidence_basis:
        md += "**证据映射：**\n"
        md += "| 声明 | 支撑证据 | 来源 |\n"
        md += "|------|---------|------|\n"
        for em in bp.evidence_basis:
            refs = ", ".join(em.get("evidence_refs", ["待补充"]))
            source = em.get("evidence_source", "—")
            md += f"| {em.get('claim', '')[:50]} | {refs[:50]} | {source} |\n"
        md += "\n"

    if bp.evidence_needed:
        md += "**证据需求：**\n"
        for item in bp.evidence_needed:
            md += f"- {item}\n"
        md += "\n"

    if bp.do_not_write:
        md += "**不应混入：**\n"
        for item in bp.do_not_write:
            md += f"- {item}\n"
        md += "\n"

    if bp.figure_needs:
        md += "**建议图表位置：**\n"
        for fp in bp.figure_needs:
            md += f"- {fp}\n"
        md += "\n"

    if bp.transition_from:
        md += f"**承上：** {bp.transition_from}\n\n"
    if bp.transition_to:
        md += f"**启下：** {bp.transition_to}\n\n"

    if bp.style_notes:
        md += "**期刊风格提示：**\n"
        for sn in bp.style_notes:
            md += f"- {sn}\n"
        md += "\n"

    if bp.risk_flags:
        md += "**风险标签：**\n"
        for flag in bp.risk_flags:
            md += f"- {flag}\n"
        md += "\n"

    md += "---\n\n"
    return md


# ── Parsers ──────────────────────────────────────────────────────────────────

def _parse_outline(path: str) -> list[dict]:
    """Parse outline sections from 大纲关键词.md."""
    sections = []
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match heading lines: "## 1. 引言" or "## 第1章" or "## 1. Introduction"
    heading_pattern = re.compile(
        r'^#{1,3}\s*(\d+(?:\.\d+)*)\s*[\.\s、]?\s*(.+?)$',
        re.MULTILINE,
    )
    for match in heading_pattern.finditer(content):
        num = match.group(1)
        name = match.group(2).strip()
        if name.lower() not in ('references', '参考文献', 'bibliography', 'abstract', '摘要'):
            sections.append({"number": num, "name": name})

    return sections


def _parse_style_profile(path: str) -> dict:
    """Parse key rules from style_profile.md."""
    rules = {}
    if path.endswith(".json"):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rules["target_genre"] = data.get("target_genre", "")
        rules["avg_sentence_length"] = data.get("language_rules", {}).get("avg_sentence_length")
        rules["passive_ratio"] = data.get("language_rules", {}).get("passive_voice_ratio")
        rules["section_order"] = data.get("structure_rules", {}).get("section_order", [])
        return rules
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    m = re.search(r'target_genre:\s*([a-z-]+)', content)
    if m:
        rules["target_genre"] = m.group(1).strip()

    # Extract avg sentence length
    m = re.search(r'平均句长.*?(\d+\.?\d*)\s*words', content)
    if m:
        rules["avg_sentence_length"] = float(m.group(1))

    # Extract reference count range
    m = re.search(r'参考文献数量.*?(\d+)-(\d+)', content)
    if m:
        rules["ref_min"] = int(m.group(1))
        rules["ref_max"] = int(m.group(2))

    # Extract passive voice ratio
    m = re.search(r'被动语态比例.*?(\d+)%', content)
    if m:
        rules["passive_ratio"] = float(m.group(1)) / 100

    # Extract section order
    section_order_section = re.search(
        r'典型章节顺序.*?\n((?:\d+\.\s+.+\n?)+)', content,
    )
    if section_order_section:
        rules["section_order"] = re.findall(
            r'\d+\.\s+(.+)', section_order_section.group(1),
        )

    return rules


def _parse_evidence_csv(path: str) -> dict:
    """Parse evidence from 综述矩阵.csv."""
    evidence = {}
    try:
        import csv
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                author_year = row.get("作者年份", row.get("author_year", ""))
                if author_year:
                    evidence[author_year] = {
                        "findings": row.get("核心发现", row.get("core_findings", "")),
                        "method": row.get("方法", row.get("method", "")),
                        "contribution": row.get("贡献", row.get("contribution", "")),
                        "citation": row.get("可引用摘录", row.get("citable_excerpt", "")),
                        "relevance": row.get("与我的主题关系", row.get("relevance", "")),
                    }
    except Exception:
        pass
    return evidence


MECHANISM_CORE_TERMS = [
    "机理",
    "机制",
    "失效机理",
    "控制机理",
    "损伤机理",
    "调控机制",
    "驱动机制",
    "演化机理",
    "mechanism",
    "mechanistic",
    "failure mechanism",
    "damage mechanism",
    "driving mechanism",
    "governing mechanism",
]

MECHANISM_JUDGEMENT_TERMS = [
    "成因",
    "原因",
    "根本原因",
    "内在原因",
    "主导因素",
    "关键因素",
    "决定因素",
    "竞争关系",
    "判别依据",
    "root cause",
    "governing factor",
    "key determinant",
    "dominant factor",
]

MECHANISM_PATH_TERMS = [
    "影响规律",
    "演化规律",
    "作用路径",
    "演化路径",
    "转变路径",
    "传导路径",
    "传导链",
    "作用链",
    "反馈机制",
    "耦合关系",
    "causal pathway",
    "evolution pathway",
    "transition pathway",
    "transfer path",
    "causal chain",
    "feedback mechanism",
    "interaction effect",
    "coupling",
]

MECHANISM_EVIDENCE_HINTS = [
    "变量传导",
    "边界条件",
    "机理验证",
    "作用路径",
    "演化路径",
]

NON_MECHANISM_SECTION_HINTS = [
    "方法设计",
    "实验装置",
    "数据来源",
    "method design",
    "experimental setup",
    "data source",
]

WEAK_ANALYSIS_TERMS = [
    "影响因素",
    "影响分析",
    "因素研究",
    "effect",
    "analysis",
    "control",
]


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _is_thesis_style(style_rules: dict) -> bool:
    return _clean_style_value(style_rules.get("target_genre")) == "thesis"


def _clean_style_value(value: object) -> str:
    return str(value or "").strip().lower()


def _is_mechanism_candidate(name: str) -> bool:
    return (
        _contains_any(name, MECHANISM_CORE_TERMS)
        or _contains_any(name, MECHANISM_JUDGEMENT_TERMS)
        or _contains_any(name, MECHANISM_PATH_TERMS)
    )


def _is_mechanism_section(name: str) -> bool:
    name_lower = name.lower()
    if _contains_any(name_lower, NON_MECHANISM_SECTION_HINTS):
        return False
    if _contains_any(name_lower, MECHANISM_CORE_TERMS):
        return True
    has_judgement = _contains_any(name_lower, MECHANISM_JUDGEMENT_TERMS)
    has_path = _contains_any(name_lower, MECHANISM_PATH_TERMS)
    if has_judgement and has_path:
        return True
    if _contains_any(name_lower, WEAK_ANALYSIS_TERMS):
        return has_judgement or has_path or _contains_any(name_lower, ["机理", "机制", "反馈", "主导", "演化", "路径"])
    return False


def _infer_evidence_needed(section: dict, style_rules: dict) -> list[str]:
    name = section["name"].lower()
    if _is_mechanism_section(section["name"]):
        evidence = [
            "mechanism_chain",
            "model_or_equation",
            "boundary_condition",
            "validation_evidence",
            "counter_explanation",
            "变量-作用路径证据",
            "机制判别图/表",
            "边界条件证据",
            "验证路径证据",
        ]
        if _is_thesis_style(style_rules):
            evidence.extend([
                "mechanism_type",
                "discriminates_against",
                "thesis_boundary_statement",
                "paragraph-level evidence anchor",
            ])
        return evidence
    if any(w in name for w in ['intro', '引言', '绪论', 'related', '文献综述', '综述']):
        return ["review", "context", "gap"]
    if any(w in name for w in ['method', '方法', '方案']):
        return ["method", "theory", "validation"]
    if any(w in name for w in ['experiment', '实验', '结果']):
        return ["experiment", "data", "comparison"]
    if any(w in name for w in ['discussion', '讨论', 'analysis', '分析']):
        return ["interpretation", "comparison", "limitation"]
    return ["context", "evidence"]


def _infer_do_not_write(section: dict, style_rules: dict) -> list[str]:
    name = section["name"].lower()
    if _is_mechanism_section(section["name"]):
        blocked = ["只堆文献不解释变量传导", "没有边界条件的强机理结论", "把候选相关性写成因果证明"]
        if _is_thesis_style(style_rules):
            blocked.extend([
                "用解释腔替代判定句",
                "先铺垫一大段再迟迟不落机制判断",
                "把概述写成口语化分析",
            ])
        return blocked
    if any(w in name for w in ['method', '方法', '方案']):
        return ["重复大段背景综述", "未定义符号前直接给公式"]
    if any(w in name for w in ['experiment', '实验', '结果']):
        return ["只贴数据不解释", "没有基线的强结论"]
    if any(w in name for w in ['conclusion', '结论']):
        return ["引入新的核心证据", "展开新的方法细节"]
    return ["与本章功能无关的大段内容"]


def _infer_risk_flags(section: dict, evidence: dict, style_rules: dict) -> list[str]:
    flags = []
    if not evidence:
        flags.append("evidence-thin")
    name = section["name"].lower()
    if _is_mechanism_section(section["name"]):
        flags.append("requires-mechanism-chain")
        if not evidence:
            flags.append("mechanism-evidence-thin")
        if _is_thesis_style(style_rules):
            flags.append("thesis-mechanism-style")
    if any(w in name for w in ['experiment', '实验']) and not evidence:
        flags.append("missing-experimental-basis")
    return flags


# ── Inference Helpers ────────────────────────────────────────────────────────

def _infer_purpose(name: str, idx: int, total: int, style_rules: dict) -> str:
    """Infer the purpose of a section from its name and position."""
    name_lower = name.lower()
    if _is_mechanism_section(name):
        if _contains_any(name, ["失效", "failure"]):
            base = "failure_cause_analysis：识别失效诱因、变量传导路径、边界条件与竞争解释，避免把表面现象误写成根因"
        elif _contains_any(name, ["耦合", "coupling", "interaction", "反馈"]):
            base = "interaction_path_analysis：解释变量耦合、反馈机制和作用路径，明确不同机制之间的传导关系与适用边界"
        elif _contains_any(name, MECHANISM_JUDGEMENT_TERMS):
            base = "mechanism_discrimination：解释现象背后的变量传导、主导机制、竞争机制差异、边界条件和验证路径，避免把相关性写成因果结论"
        else:
            base = "mechanism_explanation：解释现象背后的变量传导、模型约束、边界条件和验证路径，避免把相关性写成因果结论"
        if _is_thesis_style(style_rules):
            return base + "；按博士论文章节写法采用判定句优先、解释句收束，减少解释腔"
        return base
    if idx == 0:
        return f"建立研究背景，识别问题差距（gap），明确列出本文的贡献"
    elif idx == total - 1:
        return f"总结全文贡献，诚实说明局限性，提出具体的未来研究方向"
    elif any(w in name_lower for w in ['intro', '引言', '绪论']):
        return "三层递进：大背景 → 子领域现状与 gap → 本文贡献"
    elif any(w in name_lower for w in ['related', '相关工作', '文献综述', '综述']):
        return "按主题分组评述已有工作，每组末尾明确与本文的区别"
    elif any(w in name_lower for w in ['method', '方法', '方案', '设计']):
        return "按逻辑顺序详述研究/实验方法，先定义符号再给出公式，确保可复现"
    elif any(w in name_lower for w in ['experiment', '实验', '结果']):
        return "以研究问题开头，展示数据并分析趋势，每个实验有明确对比基线"
    elif any(w in name_lower for w in ['discussion', '讨论', '分析']):
        return "解释发现的深层含义，与已有工作对比，讨论局限性和适用范围"
    else:
        return f"详细阐述本章的研究内容和方法"


def _estimate_length(section: dict, style_rules: dict) -> str:
    """Estimate appropriate section length based on style conventions."""
    name = section["name"].lower()
    is_thesis = _is_thesis_style(style_rules)
    if any(w in name for w in ['intro', '引言', '绪论']):
        return "~1000-1600 词（4-6 段）" if is_thesis else "~800-1200 词（3-5 段）"
    elif any(w in name for w in ['related', '相关工作', '文献综述']):
        return "~1500-2400 词（6-9 段）" if is_thesis else "~1200-2000 词（5-8 段）"
    elif any(w in name for w in ['method', '方法', '方案']):
        return "~1800-2800 词（7-11 段）" if is_thesis else "~1500-2500 词（6-10 段）"
    elif any(w in name for w in ['experiment', '实验', '结果']):
        return "~2200-3200 词（8-13 段）" if is_thesis else "~2000-3000 词（8-12 段）"
    elif _is_mechanism_section(section["name"]):
        return "~1800-3000 词（7-12 段）" if is_thesis else "~1500-2500 词（6-10 段）"
    elif any(w in name for w in ['discussion', '讨论']):
        return "~1200-1800 词（5-7 段）" if is_thesis else "~1000-1500 词（4-6 段）"
    elif any(w in name for w in ['conclusion', '结论']):
        return "~700-1000 词（3-4 段）" if is_thesis else "~500-800 词（2-3 段）"
    else:
        return "~1000-1500 词（4-6 段）" if is_thesis else "~800-1200 词（3-5 段）"


def _infer_claims(section: dict, evidence: dict, style_rules: dict) -> list[str]:
    """Infer likely claims for a section based on evidence."""
    claims = []
    name = section["name"].lower()
    if any(w in name for w in ['intro', '引言']):
        claims = [
            f"领域当前面临的挑战是...",
            f"已有方法的局限性在于...",
            f"本文的贡献包括...（3-5 条）",
        ]
    elif any(w in name for w in ['method', '方法']):
        claims = [
            f"本文采用的方法框架是...",
            f"方法的关键创新在于...",
            f"方法的设计基于...理论/假设",
        ]
    elif any(w in name for w in ['experiment', '实验']):
        claims = [
            f"实验回答了...研究问题",
            f"与基线相比，方法在...指标上提升了...",
            f"消融实验证明了...组件的重要性",
        ]
    elif _is_mechanism_section(section["name"]):
        claims = [
            "目标现象可由...变量传导路径解释",
            "当前主导机制与竞争机制的区别在于...",
            "关键模型/方程/等效关系约束了...作用边界",
            "实验、仿真或图表证据支持/限制了该机理解释",
        ]
        if _is_thesis_style(style_rules):
            claims.extend([
                "该机制判断与边界条件可被现有证据直接约束",
                "应显式区分主导机制与次级/竞争机制",
            ])
    return claims


def _map_evidence(section: dict, evidence: dict) -> list[dict]:
    """Map claims to evidence from the review matrix."""
    mappings = []
    for author_year, ev in list(evidence.items())[:5]:
        relevance = ev.get("relevance", "")
        if relevance:
            mappings.append({
                "claim": f"相关声明（来自 {author_year}）",
                "evidence_refs": [author_year],
                "evidence_source": ev.get("citation", "")[:80],
            })
    return mappings


def _suggest_figures(section: dict, style_rules: dict) -> list[str]:
    """Suggest figure placements for this section."""
    name = section["name"].lower()
    suggestions = []
    if any(w in name for w in ['intro', '引言']):
        suggestions = ["研究动机示意图（可选）"]
    elif any(w in name for w in ['method', '方法']):
        suggestions = ["系统/方法框架图", "算法流程图（如适用）"]
    elif any(w in name for w in ['experiment', '实验', '结果']):
        suggestions = ["核心对比结果图（柱状图/折线图）", "消融实验结果图", "关键数据分布图（热力图/散点图）"]
    elif _is_mechanism_section(section["name"]):
        suggestions = ["变量-作用路径示意图", "机理验证证据图/表", "边界条件或工况对比图", "主导机制与竞争机制判别图"]
    return suggestions


def _transition_from(idx: int, sections: list[dict]) -> str:
    """Generate transition text from previous section."""
    if idx == 0:
        return ""
    prev = sections[idx - 1]
    return f"承接 {prev['number']} {prev['name']} 的结论/发现"


def _transition_to(idx: int, sections: list[dict]) -> str:
    """Generate transition text to next section."""
    if idx >= len(sections) - 1:
        return "收束全文，呼应引言中的贡献条目"
    next_s = sections[idx + 1]
    return f"引出 {next_s['number']} {next_s['name']} 的论述"


def _style_notes(section: dict, style_rules: dict) -> list[str]:
    """Generate style notes based on journal conventions."""
    notes = []
    avg_sl = style_rules.get("avg_sentence_length", 20)
    notes.append(f"句长保持在 {avg_sl:.0f} 词左右，自然波动")
    if style_rules.get("passive_ratio", 0) < 0.3:
        notes.append("多用主动语态（'We conducted...'），避免过度使用被动态")
    if _is_thesis_style(style_rules) and _is_mechanism_section(section["name"]):
        notes.extend([
            "博士论文章节优先给出机制判断，再补证据与边界",
            "段内避免长解释链堆叠，收束句必须回到本节问题",
            "竞争机制、适用边界和验证路径要显式写出",
        ])
    return notes


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate section-level writing blueprints",
    )
    parser.add_argument("style_profile", help="Path to style_profile.md")
    parser.add_argument("outline", help="Path to 大纲关键词.md")
    parser.add_argument("--evidence", "-e", help="Path to 综述矩阵.csv")
    parser.add_argument("--output", "-o", default="research_dossier/",
                        help="Output directory (default: research_dossier/)")
    parser.add_argument("--journal", help="Target journal name for report header")
    parser.add_argument(
        "--baseline",
        help="Optional immutable Step 2 section_blueprints.json used to preserve RQ and calibration lineage.",
    )

    args = parser.parse_args()

    print(f"📐 生成章节蓝图...")
    blueprints = generate_blueprints(
        args.outline,
        args.style_profile,
        args.evidence or "",
    )

    os.makedirs(args.output, exist_ok=True)

    output_dir = Path(args.output)
    outline_path = Path(args.outline).expanduser().resolve()
    style_profile_path = Path(args.style_profile).expanduser().resolve()
    evidence_path = Path(args.evidence).expanduser().resolve() if args.evidence else None
    baseline_path = Path(args.baseline).expanduser().resolve() if args.baseline else None
    if baseline_path is None:
        candidate = output_dir / "section_blueprints.json"
        baseline_path = candidate.resolve() if candidate.is_file() else None

    # Step 7 derivative; the Step 2 section_blueprints.json baseline remains immutable.
    bp_path = output_dir / "writing_blueprints.md"
    md = render_blueprints_md(blueprints, args.journal or "")
    _atomic_write(bp_path, md)
    print(f"✅ 章节蓝图: {bp_path}")

    payload = build_writing_blueprint_payload(
        blueprints,
        outline_path=outline_path,
        style_profile_path=style_profile_path,
        evidence_path=evidence_path,
        baseline_path=baseline_path,
    )
    bp_json_path = output_dir / "writing_blueprints.json"
    _atomic_write(bp_json_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 章节蓝图JSON: {bp_json_path}")

    # Print summary
    print(f"\n── 蓝图总览 ──")
    for bp in blueprints:
        figs = f" {len(bp.figure_needs)} 图" if bp.figure_needs else ""
        print(f"   {bp.section_id} {bp.section_title}: {bp.expected_length}{figs}")


if __name__ == "__main__":
    main()
