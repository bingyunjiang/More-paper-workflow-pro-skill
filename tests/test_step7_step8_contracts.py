from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read_rel(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class Step7Step8ContractsTest(unittest.TestCase):
    def test_step7_public_modes_are_consistent(self):
        step7 = read_rel("agents/step_7_writing.md")
        skill = read_rel("SKILL.md")
        readme = read_rel("README.md")
        step7_entry = read_rel("agents/step_7_entry.md")

        expected_modes = [
            "full-document",
            "review-only",
            "abstract-only",
            "chapter-only",
            "continue-existing",
            "revision-only",
        ]

        for mode in expected_modes:
            self.assertIn(mode, step7)
            self.assertIn(mode, skill)
            self.assertIn(mode, readme)

        forbidden = ["outline-only", "argument-first"]
        for mode in forbidden:
            self.assertNotIn(f"写作模式（{mode}", skill)

        for internal_role in ["generator", "synthesizer", "reviewer", "auditor"]:
            self.assertNotIn(internal_role, step7_entry)

        self.assertNotIn("- `draft`", step7_entry)
        self.assertNotIn("- `citation-audit`", step7_entry)
        self.assertNotIn("- `figure`", step7_entry)
        self.assertNotIn("- `pre-review`", step7_entry)

    def test_step7_writing_quality_contracts_are_explicit(self):
        text = read_rel("agents/step_7_writing.md")
        for token in [
            "先从 Step 2 不可变 `section_blueprints.json` 派生 `writing_blueprints.json/md`，再写正文",
            "section_function / expected_length / key_claims / evidence_needed / do_not_write / transition_from / transition_to / risk_flags",
            "argument_plan 之后才能进入 7.8 正文流水线",
            "每节只承担一个主要功能",
            "先写 `one_sentence_argument`，再写段落展开",
            "每节都要显式写 `do_not_write`",
            "每节都要保留 `transition_from / transition_to`",
            "`risk_flags` 不是装饰字段",
        ]:
            self.assertIn(token, text)

    def test_step7_execution_card_gate_is_explicit(self):
        step7 = read_rel("agents/step_7_writing.md")
        template = read_rel("references/templates/step7_execution_card.md")
        reference_index = read_rel("references/reference-index.md")
        for token in [
            "正文前硬门控",
            "正文引文格式完成门",
            "step7_execution_card.md",
            "figure_asset_check.md",
            "有 MinerU ZIP 时的 post_write 限制",
            "figure_index.json",
            "[[FIGURE:",
            "scripts/validate_step7_output.py",
            "只有正文草稿",
            "没有 `citation_audit.md`",
            "正文仍残留 Zotero key",
            "机理类任务缺少 `mechanism_trigger_decision`",
            "该脚本只校验工件链和关键字段，不评价文章质量",
        ]:
            self.assertIn(token, step7)
        for token in [
            "writing_scope",
            "target_genre",
            "evidence_entry_mode",
            "mechanism_trigger_decision",
            "figure_mode",
            "allowed_claim_strength",
            "blocked_until",
        ]:
            self.assertIn(token, template)
        self.assertIn("templates/step7_execution_card.md", reference_index)

    def test_step7_internal_pipeline_and_light_readability_guidance_exist(self):
        text = read_rel("agents/step_7_writing.md")
        self.assertIn("### 7.8. 内部写作流水线（用户不可见）", text)
        self.assertIn("生成", text)
        self.assertIn("整合", text)
        self.assertIn("审阅", text)
        self.assertIn("校验", text)
        self.assertIn("段内写作质量底线", text)
        self.assertIn("#### 7.8.1. 轻量可读性整理", text)
        self.assertIn("不应预设用户的写作策略、论证风格或表达审美", text)
        self.assertIn("最小术语统一", text)
        self.assertIn("标记需要后续补证据", text)
        self.assertIn("Step 7 的职责是维持 workflow 与证据边界", text)
        self.assertIn("不得作为用户选项、命令、按钮或对话模式暴露", text)

    def test_step7_terminology_frontloading_is_seeded_not_fully_locked(self):
        text = read_rel("agents/step_7_writing.md")
        for token in [
            "术语状态分三层",
            "`seed`",
            "`provisional`",
            "`locked`",
            "不要求一开始就扫完全部 PDF",
            "`seed` 和 `provisional` 术语可以先用于写作和证据组织",
            "locked 术语才作为全篇标准",
            "先建立可写作、可审计的标准",
        ]:
            self.assertIn(token, text)

    def test_step7_writing_quality_borrowing_plan_is_explicit(self):
        step7 = read_rel("agents/step_7_writing.md")
        style_workflow = read_rel("references/style-learning-workflow.md")
        borrowing_plan = read_rel("references/writing-quality-borrowing-plan.md")

        for token in [
            "writing-quality-borrowing-plan.md",
            "结构、语言和修订模式",
            "style_profile / section_blueprints / writing_rationale_matrix",
            "不得把外部句子或默认体裁直接搬进正文",
        ]:
            self.assertIn(token, step7)
            self.assertIn(token, style_workflow + borrowing_plan)

    def test_step8_is_constrained_revision_not_primary_writing_or_audit_owner(self):
        step8 = read_rel("agents/step_8_polishing.md")
        step8_entry = read_rel("agents/step_8_entry.md")
        architecture = read_rel("docs/workflow-architecture.md")

        self.assertIn("受约束补写", step8)
        self.assertIn("局部补写", step8)
        self.assertIn("不负责主体写作", step8)
        self.assertIn("修订后验证", step8)
        self.assertIn("Step 7 负责主体写作与主论证展开", step8)
        self.assertIn("Step 8 负责局部增强、风险收敛、终稿修订闭环", step8)
        self.assertIn("不负责主体写作", step8_entry)
        self.assertIn("执行受约束补写、直接修改与修订后验证", step8_entry)
        self.assertIn("Step 7 是写作生产层", architecture)
        self.assertIn("Step 8 是成稿级精修与保守修订层", architecture)

    def test_step8_terminology_termination_respects_provisional_terms(self):
        step8 = read_rel("agents/step_8_polishing.md")
        for token in [
            "seed / provisional / locked",
            "`seed` / `provisional` / `locked` 是否与当前证据状态一致",
            "`provisional` 术语只做风险提示和统一建议",
            "不得因为尚未收口就硬删",
            "只有证据足够时才提升为 `locked`",
        ]:
            self.assertIn(token, step8)

    def test_step8_dual_calibration_keeps_polish_conservative(self):
        step8 = read_rel("agents/step_8_polishing.md")
        for token in [
            "双向校准规则",
            "防止润色不足",
            "防止润色过头",
            "过头和不足都要防",
            "优先保护证据边界和章节功能",
            "风格校准只能作为 Level 4 的有限收口",
            "不得升级为全文重写或新的写作目标",
            "术语终验的分层收口",
        ]:
            self.assertIn(token, step8)

    def test_step7_revision_coach_contract_exists(self):
        text = read_rel("agents/step_7_writing.md")
        self.assertIn("#### 7.12.1. 修稿教练", text)
        self.assertIn("revision_roadmap.md", text)
        self.assertIn("response_letter_skeleton.md", text)
        self.assertIn("evidence_gap_list.md", text)
        self.assertIn("rollback_target", text)
        self.assertIn("问题识别、修订动作、证据状态、验证结果、下一步动作", text)
        for token in [
            "comment_id",
            "`E.1 / E.2`",
            "`R1.1 / R1.2 / R2.1`",
            "source_role",
            "original_comment",
            "comment_type",
            "readiness_state",
            "missing_author_input",
            "不得编造 reviewer 身份",
            "不得冒充已完成修改",
            "必须复用 `E.1 / R1.1` 等稳定编号",
        ]:
            self.assertIn(token, text)

    def test_step7_argument_plan_and_rereview_contracts_exist(self):
        text = read_rel("agents/step_7_writing.md")
        self.assertIn("#### 7.7.3. 章节级论证计划", text)
        self.assertIn("argument_plan.md", text)
        self.assertIn("rollback_if_missing", text)
        self.assertIn("### 7.14. 复评", text)
        self.assertIn("rereview_report.md", text)
        self.assertIn("new_issue", text)

    def test_step7_argument_dialogue_does_not_expand_evidence_boundary(self):
        text = read_rel("agents/step_7_writing.md")
        for token in [
            "三步对话公式",
            "他说A -> 我说非A/A+ -> 所以C",
            "核心/支撑/补充",
            "章节权重",
            "什么可以不写",
            "最小对比",
            "对话式论证不得越过证据边界",
            "只能保守表达或输出待补证据",
        ]:
            self.assertIn(token, text)

    def test_step7_heading_numbers_are_ordered_and_clean(self):
        text = read_rel("agents/step_7_writing.md")
        forbidden_numbering = ["7.W", "7.2b", "7.5b", "7.9b", "7.9c"]
        for marker in forbidden_numbering:
            self.assertNotIn(marker, text)

        heading_lines = [
            line
            for line in text.splitlines()
            if line.startswith("### 7.")
        ]
        expected = [f"7.{index}." for index in range(1, 18)]
        actual = [line.split(maxsplit=2)[1] for line in heading_lines]
        self.assertEqual(expected, actual)
        self.assertNotIn("### 7.0", text)
        self.assertNotIn("### 7.1:", text)

    def test_step7_citation_audit_exposes_three_layers(self):
        text = read_rel("agents/step_7_writing.md")
        self.assertIn("format_status", text)
        self.assertIn("mapping_status", text)
        self.assertIn("evidence_status", text)
        self.assertIn("replace_or_remove", text)
        self.assertIn("recommended_action", text)
        self.assertIn("repair_mapping", text)
        for token in [
            "引用对应表契约",
            "claim_segment_id",
            "claim_text",
            "claim_type",
            "claim_strength",
            "required_evidence",
            "insert_position",
            "citekey",
            "zotero_item_key",
            "support_grade",
            "evidence_anchor",
            "downgrade_required",
            "strong / partial / background / contradictory_or_limiting / metadata_only_candidate / not_supported",
            "`support_grade=metadata_only_candidate` 或 `not_supported` 不得进入最终稿的强 claim",
            "同一个 `claim_segment_id` 下的多条记录",
        ]:
            self.assertIn(token, text)

    def test_step7_claim_strength_and_evidence_requirements_are_documented(self):
        step7 = read_rel("agents/step_7_writing.md")
        citation_contract = read_rel("references/citation-audit-contract.md")
        blueprint = read_rel("references/section-blueprint-template.md")

        for token in [
            "background / trend / parameter / numeric_comparison / mechanism / novelty",
            "claim_strength",
            "required_evidence",
            "current_evidence_level",
            "evidence_anchor",
            "downgrade_required",
            "risk_flags",
            "无页码/表格锚点不得写强参数句",
            "无检索覆盖不得写“首次/创新”",
        ]:
            self.assertIn(token, step7 + citation_contract + blueprint)

        for token in [
            "`background`",
            "`trend`",
            "`parameter`",
            "`numeric_comparison`",
            "`mechanism`",
            "`novelty`",
            "证据等级决定 claim 强度",
            "蓝图中 `downgrade_required=true` 的 claim 不能以强结论进入正文",
        ]:
            self.assertIn(token, citation_contract + blueprint)

    def test_step7_multi_entry_evidence_pack_and_docx_policy_exist(self):
        text = read_rel("agents/step_7_writing.md")
        skill = read_rel("SKILL.md")
        policy = read_rel("references/pdf-processing-policy.md")

        for token in [
            "Zotero/MinerU 是推荐资产层，不是 Step 7 的硬依赖",
            "多入口证据 intake",
            "`zotero_full`",
            "`zotero_mineru`",
            "`evidence_pack`",
            "`draft_only`",
            "`mixed`",
            "evidence_pack.json",
            "场景只决定读取路径，证据等级决定能写多强",
            "llm-for-zotero",
            "仍可继续读取 Zotero fulltext",
            "当前写作范围完成后，才提示用户是否导出 DOCX",
            "不得在每个写作增量后自动导出 DOCX",
        ]:
            self.assertIn(token, text)

        self.assertIn("LLM-for-Zotero-MinerU-cache-*.zip", text)
        self.assertIn("manifest.json", text)
        self.assertIn("full.md", text)
        self.assertIn("images/", text)
        self.assertIn("evidence_pack", skill)
        self.assertIn("推荐 Zotero 用户安装 `llm-for-zotero` 插件", skill)
        self.assertIn("parser_confidence: low", policy)

    def test_step7_deep_read_refine_contract_exists(self):
        step7 = read_rel("agents/step_7_writing.md")
        policy = read_rel("references/pdf-processing-policy.md")
        paper_card = read_rel("references/paper-card-contract.md")

        for token in [
            "`deep_read_refine`",
            "当前章节/小节的 1-5 篇核心文献深读",
            "deep_read_cards.json/md",
            "claim_summary",
            "method_summary",
            "experiment_summary",
            "mechanism_hints",
            "usable_for",
            "not_usable_for",
            "reading_depth",
            "zotero_mineru > zotero_fulltext > zotero_note/annotation > PyMuPDF/pdfplumber > abstract_only",
            "MinerU ZIP / Zotero 图文资产 > 主抽图 > preview fallback",
            "`deep_read_refine` 结果不得直接越过 `reading_depth` 规则写入强 claim",
            "`abstract_only` 只能做背景、候选或待补全文提示",
        ]:
            self.assertIn(token, step7)

        for token in [
            "zotero_mineru > zotero_fulltext > zotero_note/annotation > PyMuPDF/pdfplumber > abstract_only",
            "MinerU ZIP / Zotero 图文资产 > 主抽图 > preview fallback",
        ]:
            self.assertIn(token, policy)

        for token in [
            "`deep_read_cards.json/md` 是 Step 7 `deep_read_refine` 的章节级证据整形产物",
            "`mechanism_hints` 只作为 `mechanism_analysis` 的机理链候选输入",
            "不能提高原始 `reading_depth`",
        ]:
            self.assertIn(token, paper_card)

    def test_step7_pdf_only_and_layered_fulltext_contracts_exist(self):
        step7 = read_rel("agents/step_7_writing.md")
        policy = read_rel("references/pdf-processing-policy.md")

        for token in [
            "PDF-only evidence_pack 是 Step 7 的正式入口，不是降级补丁",
            "PDF 文件夹、写作目标，以及可选的大纲、已有草稿或目标期刊/学位论文要求",
            "prepared_pdf_artifacts.json",
            "*.clean.md",
            "*.chunks.json",
            "*.extraction_report.json",
            "扫描件、OCR 差、表格/公式密集、页码锚点缺失",
            "不得自动升级为强证据",
            "分层全文深读链",
            "全文 PDF/MinerU 不作为常驻写作上下文",
            "`metadata-first`",
            "`selective-fulltext`",
            "`argument_plan`：把 `deep_read_cards` 中的 claim、方法、边界、图表证据绑定到章节论证",
            "deep_read_cards + argument_plan + 必要原文回查",
            "未压缩、未定位、未标注读取深度的全文堆料",
        ]:
            self.assertIn(token, step7)

        for token in [
            "PDF-only evidence_pack 是正式入口，不是降级补丁",
            "prepared_pdf_artifacts.json",
            "`*.clean.md`",
            "`*.chunks.json`",
            "`*.extraction_report.json`",
            "must_check_pdf=true",
        ]:
            self.assertIn(token, policy)

    def test_step7_section_evidence_completion_gate_exists(self):
        step7 = read_rel("agents/step_7_writing.md")

        for token in [
            "小节级证据完成门",
            "每个章节/小节写作完成前，必须完成最小证据闭环",
            "每条强 claim 必须绑定 `reading_depth=full_text / pdf_verified / zotero_note`",
            "每条强 claim 必须有 `source_trace`",
            "PDF 路径或 Zotero item、页码/chunk/section、证据等级",
            "摘要级文献只能写背景、问题定义、研究趋势",
            "不能支撑实验结果、参数、机制判断或效果比较",
            "输出 `[待补证据: claim]` 或写入 `evidence_gap_list.md`",
            "PDF-only 入口下，`source_trace` 必须优先落到 `source_pdf + pages/chunk_id/section`",
            "must_check_pdf=true",
        ]:
            self.assertIn(token, step7)

    def test_step7_mechanism_analysis_contract_exists(self):
        step7 = read_rel("agents/step_7_writing.md")
        reference = read_rel("references/mechanism-analysis-writing-contract.md")

        for token in [
            "`mechanism_analysis`",
            "mechanism_trigger_decision",
            "enter_mechanism_analysis",
            "skip_mechanism_analysis",
            "checked_text",
            "candidate_terms_hit",
            "confirmed_triggers",
            "required_artifacts",
            "mechanism_cards.json/md",
            "mechanism_argument_plan.json/md",
            "mechanism_claim_audit.json/md",
            "mechanism_paragraph_audit.json/md",
            "正文生成前必须先产出或刷新 `mechanism_cards.json/md`、`mechanism_argument_plan.json/md` 和 `mechanism_claim_audit.json`",
            "已有草稿续写和 direct-entry 写作也不能跳过",
            "不得先写正文再补工件",
            "scripts/build_mechanism_argument_plan.py",
            "scripts/audit_mechanism_claims.py",
            "scripts/audit_mechanism_paragraphs.py",
            "figure_evidence_status=unavailable_without_mineru_or_manual_pdf_check",
            "MinerU 图表锚点 > PDF 页/段落锚点 > PDF 全文无页码锚点 > 摘要/元数据",
            "不得直接判定“无 MinerU 图表锚点”",
            "LLM-for-Zotero-MinerU-cache-*.zip",
            "mechanism_core_terms",
            "mechanism_judgement_terms",
            "mechanism_path_terms",
            "mechanism_candidate=true",
            "只命中第一段、不满足第二段：保留普通章节写作链",
            "影响因素",
            "方法设计",
            "实验装置",
            "数据来源",
            "mechanism_type",
            "discriminates_against",
            "transfer_risk",
            "figure_claim_binding",
            "mechanism_discrimination_not_explicit",
            "判定句优先、解释句收束",
            "机制判别句 -> 图文/全文证据 -> 边界句 -> 收束句",
            "phenomenon",
            "state_variables",
            "causal_chain",
            "governing_model",
            "boundary_conditions",
            "evidence_anchor",
            "alternative_explanations",
            "validation_path",
            "claim_limit",
            "现象 -> 状态量/控制量 -> 作用路径 -> 证据锚点 -> 适用边界 -> 回扣本节问题",
            "没有实验、仿真或对比验证时，不得把相关性写成因果证明",
        ]:
            self.assertIn(token, reference)

        for token in [
            "`mechanism_analysis`",
            "mechanism_trigger_decision",
            "mechanism_cards.json/md",
            "mechanism_argument_plan.json/md",
            "mechanism_claim_audit.json/md",
            "references/mechanism-analysis-writing-contract.md",
        ]:
            self.assertIn(token, step7)

    def test_materials_mechanics_domain_pack_is_wired_to_step7(self):
        step7 = read_rel("agents/step_7_writing.md")
        reference = read_rel("references/mechanism-analysis-writing-contract.md")
        domain_pack = read_rel("references/domain-packs/materials-mechanics-writing.md")

        self.assertIn("references/domain-packs/materials-mechanics-writing.md", step7)
        self.assertIn("材料/机械/工程写作领域增强包", domain_pack)

        for token in [
            "materials_system_card",
            "thermomechanical_process_card",
            "microstructure_evidence_card",
            "mechanism_discrimination_card",
            "figure_claim_panel_card",
            "journal_style_card",
            "CDRX",
            "DDRX",
            "DRV",
            "Zener pinning",
            "CNT pinning",
            "load transfer",
            "EBSD",
            "TEM",
            "KAM",
            "GOS",
            "HAGB",
            "LAGB",
            "只在任务命中材料、机械、热变形、显微组织或工程机理时加载",
        ]:
            self.assertIn(token, domain_pack)

        for token in [
            "materials_system",
            "thermomechanical_path",
            "microstructure_evidence",
            "competing_mechanisms",
            "discrimination_evidence",
            "insufficient_basis",
            "discrimination_matrix_used",
            "evidence_modality",
        ]:
            self.assertIn(token, reference)

    def test_materials_mechanics_discrimination_matrices_are_actionable(self):
        domain_pack = read_rel("references/domain-packs/materials-mechanics-writing.md")
        figure_contract = read_rel("references/figure-writing-interface.md")

        for token in [
            "DRX_discrimination_matrix",
            "EBSD_claim_evidence_matrix",
            "TEM_SEM_XRD_claim_boundary",
            "CNT_Al_strengthening_mechanism_matrix",
            "mechanism_overclaim_examples",
            "只有晶粒尺寸变小，不得写“证明发生 DRX”",
            "只有 HAGB 比例升高，不得区分 CDRX/DDRX",
            "只有 KAM 降低，不得把 DRV 写成 DRX",
            "load transfer",
            "Orowan strengthening",
            "CTE mismatch strengthening",
            "Zener/CNT pinning",
            "EBSD 证明发生 CDRX",
            "CNTs 钉扎晶界导致细晶稳定",
        ]:
            self.assertIn(token, domain_pack)

        for token in [
            "evidence_modality",
            "EBSD|TEM|SEM|XRD|flow_curve|mechanical_test|simulation|user_data",
        ]:
            self.assertIn(token, figure_contract)

    def test_materials_journal_style_pack_is_optional_and_specific(self):
        step7 = read_rel("agents/step_7_writing.md")
        style_pack = read_rel("references/domain-packs/materials-journal-style.md")
        domain_pack = read_rel("references/domain-packs/materials-mechanics-writing.md")

        self.assertIn("references/domain-packs/materials-journal-style.md", step7)
        self.assertIn("仅在目标期刊或体裁明确时加载", step7)
        self.assertIn("不得作为所有论文的全局默认写作规则", style_pack)
        self.assertIn("不作为材料领域的全局默认风格", domain_pack)

        for token in [
            "Scripta Materialia",
            "Acta Materialia",
            "Materials Science and Engineering A (MSEA)",
            "Journal of Materials Processing Technology (JMPT)",
            "中文核心材料/机械论文",
            "学位论文材料/机械章节",
            "processing-structure-property",
            "processing -> microstructure -> mechanical properties -> mechanism",
            "目标期刊风格只能约束结构密度、证据呈现、图表说明和讨论深度",
            "如果目标期刊风格与当前证据等级冲突，以证据等级为准",
        ]:
            self.assertIn(token, style_pack)

    def test_scientific_writing_quality_rubric_is_wired_and_bounded(self):
        step7 = read_rel("agents/step_7_writing.md")
        step8 = read_rel("agents/step_8_polishing.md")
        rubric = read_rel("references/scientific-writing-quality-rubric.md")

        self.assertIn("references/scientific-writing-quality-rubric.md", step7)
        self.assertIn("references/scientific-writing-quality-rubric.md", step8)

        for token in [
            "subject_action_audit",
            "old_new_flow_audit",
            "paragraph_function_audit",
            "figure_first_argument_plan",
            "phrasebank_guardrail",
            "不改变 claim 强度",
            "不替代引用审计",
            "不能把候选证据包装成强证据",
            "topic_shift_intentional",
            "stress_position",
        ]:
            self.assertIn(token, rubric + step8)

    def test_power_electronics_ev_energy_domain_pack_is_wired_to_step7(self):
        step7 = read_rel("agents/step_7_writing.md")
        mechanism_contract = read_rel("references/mechanism-analysis-writing-contract.md")
        figure_contract = read_rel("references/figure-writing-interface.md")
        domain_pack = read_rel("references/domain-packs/power-electronics-ev-energy-writing.md")

        self.assertIn("references/domain-packs/power-electronics-ev-energy-writing.md", step7)
        self.assertIn("电力电子 / 充电 / V2G / 能源系统写作领域包", domain_pack)
        self.assertIn("不作为材料论文默认规则", domain_pack + step7 + mechanism_contract)

        for token in [
            "power_topology_card",
            "control_and_stability_card",
            "efficiency_loss_thermal_card",
            "EMS_optimization_card",
            "V2G_grid_claim_card",
            "wireless_fast_charging_card",
            "充电桩",
            "储能",
            "电力电子",
            "EMS",
            "V2G",
            "快充",
            "无线充电",
            "超级电容",
        ]:
            self.assertIn(token, domain_pack + step7)

        for token in [
            "waveform",
            "efficiency_curve",
            "loss_breakdown",
            "thermal_map",
            "grid_metric",
            "optimization_result",
            "hardware_prototype",
            "HIL",
            "field_data",
            "standard",
        ]:
            self.assertIn(token, domain_pack + mechanism_contract + figure_contract)

    def test_power_energy_journal_style_pack_is_optional_and_specific(self):
        step7 = read_rel("agents/step_7_writing.md")
        style_pack = read_rel("references/domain-packs/power-energy-journal-style.md")

        self.assertIn("references/domain-packs/power-energy-journal-style.md", step7)
        self.assertIn("仅在目标期刊或体裁明确时加载", step7)
        self.assertIn("不得作为所有电力电子/能源论文的全局默认风格", style_pack)

        for token in [
            "IEEE Transactions / IEEE Access",
            "Applied Energy / Energy",
            "工程中文核心",
            "学位论文电力电子 / 能源系统章节",
            "application need -> technical gap -> proposed method -> contributions",
            "系统边界",
            "仿真和实验必须分清",
            "如果目标期刊风格与当前证据等级冲突，以证据等级为准",
        ]:
            self.assertIn(token, style_pack)

    def test_section_quality_gates_and_reviewer_defect_taxonomy_are_wired(self):
        step7 = read_rel("agents/step_7_writing.md")
        step8 = read_rel("agents/step_8_polishing.md")
        gates = read_rel("references/section-quality-gates.md")
        defects = read_rel("references/reviewer-defect-taxonomy.md")

        for token in [
            "references/section-quality-gates.md",
            "references/reviewer-defect-taxonomy.md",
            "scientific_writing_quality_audit.json",
            "engineering_claim_audit.json",
            "scripts/audit_scientific_writing_quality.py",
            "scripts/audit_engineering_claims.py",
            "reviewer_defect_report.md",
        ]:
            self.assertIn(token, step7 + step8)

        for token in [
            "abstract_quality_gate",
            "introduction_quality_gate",
            "discussion_quality_gate",
            "conclusion_quality_gate",
            "missing_quantified_result",
            "generic_gap",
            "mechanism_jump",
            "new_claim_in_conclusion",
        ]:
            self.assertIn(token, gates)

        for token in [
            "novelty_and_positioning_defects",
            "method_and_reproducibility_defects",
            "result_and_figure_defects",
            "power_energy_specific_defects",
            "stability_claim_without_stability_evidence",
            "efficiency_without_test_conditions",
            "only_simulation_no_hardware_for_hardware_claim",
            "ems_optimization_without_constraints",
            "wireless_charging_without_misalignment_or_emc",
            "不得冒充真实审稿意见",
        ]:
            self.assertIn(token, defects + step7 + step8)

    def test_step7_section_scoped_writing_and_thesis_depth_rules_exist(self):
        text = read_rel("agents/step_7_writing.md")
        command = read_rel("commands/write.md")
        mapping = read_rel("references/zotero-outline-mapping.md")
        readme = read_rel("README.md")

        for token in [
            "大纲-集合锁定取证",
            "不扫整个 Zotero 文库",
            "只读取当前节号对应的集合、子集合、条目和附件",
            "不得因为“文库里还有很多相关文献”就提前读取后续小节集合",
            "每次只写一个当前请求的小节",
            "不提前展开后续小节",
            "问题推进式叙述",
            "target_genre=thesis",
            "博士论文深度",
            "工程场景 -> 需求来源 -> 机理约束 -> 制造约束 -> 研究必要性",
            "英文基础/国际研究 + 中文工程场景文献",
            "重要判断默认不只挂 1 篇文献",
            "判定句优先、解释句收束",
            "减少“如果说……那么……”“换言之”“这个判断也说明了”等解释腔连接句",
            "试写阶段默认保持作者-年份格式",
        ]:
            self.assertIn(token, text)

        for token in ["doctoral_thesis_map.json", "prepare -> write -> close -> incremental audit", "原子回写", "doctoral_ready", "不补跑 Step 1-6", "必须记录作者确认"]:
            self.assertIn(token, text)

        self.assertIn("按大纲对应的 Zotero 子集合取证；不扫整个 Zotero 文库", command)
        self.assertIn("每次只写一个当前小节，不提前展开后续小节", command)
        self.assertIn("写 `1.1` 就只读 `1.1` 对应集合", mapping)
        self.assertIn("按大纲对应的 Zotero 子集合逐节读取证据，不扫整个文库", readme)

    def test_step8_remains_conservative_and_does_not_add_evidence(self):
        text = read_rel("agents/step_8_polishing.md")
        command = read_rel("commands/polish.md")

        for token in [
            "Step 8 不得替换 Step 7 的引用审计结论",
            "不得新增未经确认的证据",
            "只负责保守修订",
            "改善衔接、压缩或扩展局部表达",
            "凡涉及新增论据、补全文献、扩大章节范围，必须回退 Step 7",
        ]:
            self.assertIn(token, text)

        for token in [
            "Step 8 只做保守修订，不新增未经确认的证据",
            "Step 8 不替代 Step 7 的引用审计，不重写章节主体，不扩大写作范围",
        ]:
            self.assertIn(token, command)

    def test_direct_entry_artifact_graph_contracts_are_documented(self):
        step5 = read_rel("agents/step_5_download.md")
        step6 = read_rel("agents/step_6_zotero.md")
        step7 = read_rel("agents/step_7_entry.md")
        step8 = read_rel("agents/step_8_entry.md")
        gates = read_rel("references/completion-gates.md")
        readme = read_rel("README.md")

        for token in [
            "Artifact Passport / Direct-entry Graph",
            "unlinked_pdf",
            "source_unlinked",
            "不得宣称下载来源链完整",
        ]:
            self.assertIn(token, step5)

        for token in [
            "matched_attachment",
            "missing_attachment",
            "unlinked_pdf",
            "duplicate_candidate",
            "缺 Step 4/5 不是阻塞项",
        ]:
            self.assertIn(token, step6)

        for token in [
            "Artifact graph 只负责登记当前可用材料和可确认关系",
            "reading_depth",
            "trace_status",
            "metadata_only",
            "unlinked",
            "当前入口可继续版本",
        ]:
            self.assertIn(token, step7)

        for token in [
            "trace_status=unlinked",
            "confidence=inferred",
            "不得把弱证据升级为 confirmed",
            "不要求完整 Step 4-7 链路",
        ]:
            self.assertIn(token, step8)

        for token in [
            "direct-entry 入口敏感",
            "`inferred`、`unlinked`、`conflict` 关系不得说成 `confirmed`",
            "当前入口可继续版本；全链路仍有以下 gaps/risks",
        ]:
            self.assertIn(token, gates)

        self.assertIn("artifact_passport.json", readme)
        self.assertIn("direct-entry artifact graph", readme)

    def test_step8_degraded_entry_rules_remain_non_blocking(self):
        text = read_rel("agents/step_8_polishing.md")
        self.assertIn("评审依据不足", text)
        self.assertIn("引用安全提醒", text)
        self.assertIn("不能要求用户回跑 Step 7", text)
        self.assertIn("默认以这些 JSON 为**约束源**", text)
        self.assertIn("diagnostic_summary.md", text)
        self.assertIn("evidence_gap", text)
        self.assertIn("structure_drift", text)
        self.assertIn("language_mechanical", text)
        self.assertIn("contribution_overclaim", text)
        self.assertIn("citation_misalignment", text)
        self.assertIn("ready_for_finalize", text)
        self.assertIn("ready_with_warnings", text)
        self.assertIn("not_ready_requires_rollback", text)
        self.assertIn("return_to_step_7_revision_only", text)
        self.assertIn("return_to_step_7_citation_audit", text)
        self.assertIn("return_to_step_7_argument_plan", text)
        self.assertIn("return_to_step_4_or_6", text)

    def test_step8_ai_trace_diagnostics_contract_exists(self):
        text = read_rel("agents/step_8_polishing.md")
        command = read_rel("commands/polish.md")
        readme = read_rel("README.md")
        reference = read_rel("references/deterministic-writing-diagnostics.md")

        self.assertIn("AI 味确定性检查", text)
        self.assertIn("language_mechanical", text)
        self.assertIn("diagnostic_summary.md", text)
        self.assertIn("revision_ledger.json", text)
        self.assertIn("revision_ledger.md", text)
        self.assertIn("润色质量报告.md", text)
        self.assertIn("单纯词表或模式命中不得直接升格为 `evidence_gap / structure_drift / contribution_overclaim`", text)
        self.assertIn("风格类命中默认不触发 rollback", text)
        self.assertIn("Step 8 不因“AI 味”要求用户回跑主写作", text)
        self.assertIn("AI 味确定性检查", command)
        self.assertIn("AI 味确定性检查", readme)
        self.assertIn("载体清洁度检查", readme)
        for token in ["authorial_revision_record.json", "editorial_only / author_confirmed / requires_author_input", "不承诺检测结果", "不得承诺“通过 AIGC 检测”", "不要求补跑 Step 7"]:
            self.assertIn(token, text)

        for token in [
            "套话短语规则",
            "机械连接词堆积规则",
            "伪洞见与悬垂表达规则",
            "空泛归因规则",
            "句长节奏过匀规则",
            "冗余破折号与插入语规则",
            "可在 Step 8 直接修订",
            "可修但需轻量含义审计",
            "只提醒，不在 Step 8 内硬修",
        ]:
            self.assertIn(token, text)
            self.assertIn(token, reference)

    def test_step8_writing_read_and_protected_spans_contract_exists(self):
        step8 = read_rel("agents/step_8_polishing.md")
        entry = read_rel("agents/step_8_entry.md")
        command = read_rel("commands/polish.md")
        reference_index = read_rel("references/reference-index.md")
        rewrite_scope = read_rel("references/step8-rewrite-scope.md")
        protected_spans = read_rel("references/protected-spans.md")
        ai_trace_index = read_rel("references/academic-ai-trace-index.md")

        for token in [
            "references/step8-rewrite-scope.md",
            "references/protected-spans.md",
            "references/academic-ai-trace-index.md",
            "Writing Read",
            "protected spans",
            "保真回读",
            "残留味回读",
            "rewrite_scope",
            "rewrite_level",
        ]:
            self.assertIn(token, step8 + entry + command + reference_index)

        for token in [
            "bounded + standard",
            "in-place",
            "structural",
            "保真回读优先级高于残留味回读",
        ]:
            self.assertIn(token, step8 + rewrite_scope + command)

        for token in [
            "引用与文献标识",
            "图表与公式锚点",
            "实验/仿真参数",
            "证据边界",
            "责任主体",
        ]:
            self.assertIn(token, protected_spans)

        for token in [
            "路标词堆积",
            "空泛价值拔高",
            "无源归因",
            "伪洞见尾句",
            "Top 5-10",
        ]:
            self.assertIn(token, ai_trace_index)

    def test_step8_scientific_bluff_diagnostics_are_constrained(self):
        step8 = read_rel("agents/step_8_polishing.md")
        antipatterns = read_rel("references/writing-antipatterns.md")
        mechanism_contract = read_rel("references/mechanism-analysis-writing-contract.md")

        for token in [
            "mechanism_bluff",
            "科学空话诊断",
            "mechanism_without_state_variables",
            "causal_jump_without_validation",
            "visual_claim_without_panel",
            "proof_verb_without_evidence",
            "generic_strengthening_list",
            "不能新增文献、补图号、补实验解释或替代 Step 7 引用审计",
            "不新增机理证据，不补图号，不替代 Step 7 机理审计",
        ]:
            self.assertIn(token, step8 + antipatterns + mechanism_contract)

        self.assertIn("Step 8：只做 `mechanism_bluff` 诊断、降强度、补边界句或提示回退，不新增证据", antipatterns)

    def test_figure_claim_panel_binding_contract_exists(self):
        step7 = read_rel("agents/step_7_writing.md")
        figure_contract = read_rel("references/figure-writing-interface.md")
        blueprint = read_rel("references/section-blueprint-template.md")

        for token in [
            "figure_table_panel_binding",
            "claim_id",
            "claim_text",
            "claim_strength",
            "figure_id",
            "table_id",
            "panel_id",
            "caption_anchor",
            "support_type",
            "support_status",
            "downgrade_required",
            "没有 figure/table/panel 绑定时，不得自动写",
            "三者必须回答同一条 claim",
        ]:
            self.assertIn(token, step7 + figure_contract + blueprint)

    def test_step8_revision_ledger_and_minimum_validation_contracts_exist(self):
        text = read_rel("agents/step_8_polishing.md")
        command = read_rel("commands/polish.md")
        output_contract = read_rel("static/core/output-contract.md")

        self.assertIn("revision_ledger.json", text)
        self.assertIn("revision_ledger.md", text)
        self.assertIn("issue_id", text)
        self.assertIn("category", text)
        self.assertIn("issue_type", text)
        self.assertIn("severity", text)
        self.assertIn("location", text)
        self.assertIn("problem", text)
        self.assertIn("evidence_basis", text)
        self.assertIn("allowed_action", text)
        self.assertIn("proposed_revision", text)
        self.assertIn("verification", text)
        self.assertIn("final_status", text)
        self.assertIn("next_action", text)

        self.assertIn("术语一致性验证", text)
        self.assertIn("核心含义漂移验证", text)
        self.assertIn("论断强度验证", text)
        self.assertIn("引用/指代/衔接验证", text)
        self.assertIn("PASS / WARN / FAIL", text)
        self.assertIn("含义漂移", text)
        self.assertIn("论断意外增强", text)
        self.assertIn("硬门槛", text)

        self.assertIn("revision_ledger.json/md", command)
        self.assertIn("revision_ledger", output_contract)

    def test_step8_heading_numbers_are_ordered_and_clean(self):
        text = read_rel("agents/step_8_polishing.md")

        self.assertIn("### 8.3. 最小验证规程", text)
        self.assertIn("### 8.4. revision_ledger 双层工件契约", text)
        self.assertIn("#### 8.4.1. 轻量含义审计触发", text)
        self.assertIn("### 8.9. 日志回写", text)
        self.assertNotIn("### 8.0", text)
        self.assertNotIn("### 4.1 PDF 提取结果", text)
        self.assertNotIn("## 7. 最小验证规程", text)
        self.assertNotIn("## 8. revision_ledger 双层工件契约", text)
        self.assertNotIn("### 8.2.1. 轻量含义审计触发", text)

    def test_step7_step8_methodology_details_are_referenced_not_hardcoded(self):
        step7 = read_rel("agents/step_7_writing.md")
        step8 = read_rel("agents/step_8_polishing.md")

        self.assertIn("统一放到 `references/writing-modes.md`", step7)
        self.assertIn("`references/citation-audit-guide.md`", step7)
        self.assertIn("`references/reviewer-protocol.md`", step7)
        self.assertIn("`references/ai-trace-taxonomy.md`", step8)
        self.assertIn("`references/polish-modes.md`", step8)
        self.assertIn("`references/writing-antipatterns.md`", step8)

    def test_step7_figure_assets_use_project_figures_dir(self):
        step7 = read_rel("agents/step_7_writing.md")
        self.assertIn("只有被选入正文的图片才复制到项目 `figures/`", read_rel("references/pdf-processing-policy.md"))
        self.assertIn("确保正文图片引用的是项目内 `figures/` 的相对路径", step7)

    def test_revision_artifacts_share_minimum_lifecycle_fields(self):
        step7 = read_rel("agents/step_7_writing.md")
        step8 = read_rel("agents/step_8_polishing.md")
        command = read_rel("commands/revision-roadmap.md")

        for field in [
            "issue_id",
            "chapter_binding",
            "claim_binding",
            "problem_summary",
            "action_type",
            "evidence_status",
            "verification_result",
            "next_action",
            "issue_state",
            "state_reason",
        ]:
            self.assertIn(field, step7)
            self.assertIn(field, step8)
            self.assertIn(field, command)

        for state in [
            "identified",
            "routed",
            "in_revision",
            "verification_pending",
            "closed",
            "blocked_author_decision",
            "blocked_evidence",
            "invalid_or_not_applied",
        ]:
            self.assertIn(state, step7)
            self.assertIn(state, step8)
            self.assertIn(state, command)

        self.assertIn("只约束问题生命周期", step7)
        self.assertIn("不规定具体写作策略", step7)
        self.assertIn("不约束作者的写作策略", read_rel("static/core/output-contract.md"))

    def test_step8_chinese_three_way_categories_and_action_boundaries_exist(self):
        text = read_rel("agents/step_8_polishing.md")
        readme = read_rel("README.md")

        for label in ["可直接修订", "需作者决定", "当前依据不足"]:
            self.assertIn(label, text)
            self.assertIn(label, readme)

        self.assertIn("直接修改", text)
        self.assertIn("局部补写", text)
        self.assertIn("桥接句", text)
        self.assertIn("限定句", text)
        self.assertIn("解释句", text)
        self.assertIn("引证配套句", text)
        self.assertIn("局部支撑句", text)

        self.assertIn("新增外部证据或引用来源", text)
        self.assertIn("重写章节主体", text)
        self.assertIn("重定义贡献点/研究问题", text)
        self.assertIn("新增实验", text)

    def test_step7_step8_do_not_hardcode_writing_style_preferences(self):
        step7 = read_rel("agents/step_7_writing.md")
        step8 = read_rel("agents/step_8_polishing.md")
        readme = read_rel("README.md")

        self.assertIn("不应限制用户的创造性组织方式", step7)
        self.assertIn("强行统一用户风格", step8)
        self.assertIn("用户仍保留自己的写作策略和表达风格", step8)
        self.assertIn("用户仍保留自己的写作策略和表达风格", readme)

    def test_abstract_only_subtypes_are_documented(self):
        text = read_rel("agents/step_7_writing.md")
        self.assertIn("journal-abstract", text)
        self.assertIn("thesis-abstract", text)
        self.assertIn("bilingual-abstract", text)

    def test_step7_reading_depth_labels_and_claim_boundaries_are_documented(self):
        step7 = read_rel("agents/step_7_writing.md")
        paper_card = read_rel("references/paper-card-contract.md")

        for token in [
            "已读深度标注规则",
            "（已读全文）",
            "（已读摘要）",
            "（仅元数据）",
            "reading_depth=full_text / pdf_verified / zotero_note",
            "reading_depth=abstract_only",
            "reading_depth=metadata_only",
            "具体结论、方法细节、实验设置、结果比较、机制判断和强 claim，只能引用 `（已读全文）` 文献",
        ]:
            self.assertIn(token, step7)

        for token in [
            "正文引用必须显式暴露已读深度",
            "`metadata_only` 不得承载具体结论",
            "`abstract_only` 不得承载实验结果、参数、机制、效果比较或强 claim",
        ]:
            self.assertIn(token, paper_card)

    def test_commands_and_showcase_exist(self):
        for rel in [
            "commands/topic.md",
            "commands/search.md",
            "commands/download.md",
            "commands/zotero.md",
            "commands/write.md",
            "commands/polish.md",
            "commands/citation-audit.md",
            "commands/revision-roadmap.md",
            "examples/showcase/README.md",
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_deep_research_borrowings_are_wired_into_steps(self):
        step1 = read_rel("agents/step_1_topic.md")
        step3 = read_rel("agents/step_3_search_plan.md")
        step4 = read_rel("agents/step_4_search_score.md")
        step7 = read_rel("agents/step_7_writing.md")

        self.assertIn("research_intent_type", step1)
        self.assertIn("research_question_candidates", step1)
        self.assertIn("primary_rq", step1)
        self.assertIn("scope_boundaries", step1)
        self.assertIn("methodology_blueprint", step1)
        self.assertIn("devils_advocate_challenge", step1)

        self.assertIn("review_protocol", step3)
        self.assertIn("inclusion_criteria", step3)
        self.assertIn("exclusion_criteria", step3)

        self.assertIn("证据层级提示", step4)
        self.assertIn("screening rationale", step4)
        self.assertIn("exclusion buckets", step4)
        self.assertIn("references/reviewer-protocol.md", step7)

    def test_rag_candidate_layer_is_documented_as_non_authoritative(self):
        step7 = read_rel("agents/step_7_writing.md")
        step8 = read_rel("agents/step_8_polishing.md")
        readme = read_rel("README.md")

        self.assertIn("retrieval_index_manifest.json", step7)
        self.assertIn("retrieval_candidates.json", step7)
        self.assertIn("retrieved_candidate", step7)
        self.assertIn("按章节→claim 组织", step7)
        self.assertIn("章节级候选证据层", step7)
        self.assertIn("claim_id", step7)
        self.assertIn("claim_text", step7)
        self.assertIn("evidence_question_id", step7)
        self.assertIn("query_variant", step7)
        self.assertIn("source_page_hint", step7)
        self.assertIn("negative_or_conflicting_evidence", step7)
        self.assertIn("不得直接升级为 `VERIFIED` / `VERIFIED_LOCAL`", step7)
        self.assertIn("必要时可读取 `retrieval_candidates.json`", step8)
        self.assertIn("不得把候选层内容直接当作正文证据", step8)
        self.assertIn("候选定位加速层", readme)

    def test_argument_plan_evidence_confirmation_block_exists(self):
        step7 = read_rel("agents/step_7_writing.md")
        self.assertIn("`argument_plan` 证据确认区块", step7)
        self.assertIn("confirmed_evidence", step7)
        self.assertIn("unresolved_evidence", step7)
        self.assertIn("candidate_evidence_used", step7)
        self.assertIn("confirmation_status", step7)
        self.assertIn("rollback_if_unconfirmed", step7)

    def test_step7_writing_axes_and_confirmation_gate_exist(self):
        step7 = read_rel("agents/step_7_writing.md")

        for token in [
            "writing_axes",
            "paper_type",
            "section_role",
            "language_mode",
            "style_target",
            "不替代 `target_genre / writing_mode / evidence_entry_mode`",
            "不得把 Nature 风格设为默认目标",
            "one_sentence_argument",
            "paragraph_job_map",
            "每段只标一个主任务",
            "claim / evidence / boundary",
            "本节不得直接进入完整正文生成",
            "确认门（claim / evidence / boundary 不清时）",
            "先输出 `one_sentence_argument`、`paragraph_job_map`、关键假设和 `unresolved_evidence`，停止完整正文生成",
            "不得把未确认内容写成确定性结论",
        ]:
            self.assertIn(token, step7)

    def test_step8_failure_mode_priority_and_output_modes_exist(self):
        step8 = read_rel("agents/step_8_polishing.md")

        for token in [
            "quick-polish",
            "audited-polish",
            "润色稿 + 3-5 条修改说明",
            "diagnostic_summary.md",
            "revision_ledger.json/md",
            "若 `quick-polish` 过程中发现 `evidence_gap / structure_drift / citation_misalignment / contribution_overclaim`",
            "不能继续把结构或证据问题包装成句子润色",
            "诊断优先级固定为：`章节功能 -> 段落逻辑 -> claim/evidence/boundary -> 句子润色`",
            "先判断当前段落是否服务正确章节功能",
            "最后才做词句层面的润色",
            "优先标记 `structure_drift` 并回退 `step_7_argument_plan`",
            "优先标记 `evidence_gap / citation_misalignment / contribution_overclaim`",
        ]:
            self.assertIn(token, step8)

    def test_step8_fixed_issue_action_table_and_ledger_fields_exist(self):
        step8 = read_rel("agents/step_8_polishing.md")

        for token in [
            "固定诊断动作表",
            "`term_consistency`",
            "可在 Step 8 直接修，并记录术语一致性报告",
            "默认回退 Step 7 `argument_plan`",
            "不靠润色硬修章节功能",
            "默认回退 Step 7 `citation_audit` 或证据补强",
            "Step 8 不新增外部证据",
            "只记录引用安全提醒",
            "完整处理回 Step 7 引用审计",
            "允许降强度或补边界句",
            "若仍需新证据，回 Step 7，不在 Step 8 新增文献",
        ]:
            self.assertIn(token, step8)

        for token in [
            "| `before` | 修订前文本或问题片段 |",
            "| `after` | 修订后文本；未修订时记录为空并说明原因 |",
            "| `rollback_target` |",
            "| `evidence_status` | 当前证据状态",
            "| `verification_result` | `PASS / WARN / FAIL`",
        ]:
            self.assertIn(token, step8)

    def test_step7_existing_draft_three_entry_paths_are_explicit(self):
        step7 = read_rel("agents/step_7_writing.md")
        step7_entry = read_rel("agents/step_7_entry.md")
        write_cmd = read_rel("commands/write.md")
        readme = read_rel("README.md")

        for label in ["continue-existing", "chapter-only", "revision-only"]:
            self.assertIn(label, step7)
            self.assertIn(label, step7_entry)
            self.assertIn(label, write_cmd)
            self.assertIn(label, readme)

        self.assertIn("existing-draft 可以跳过前链，但不能跳过证据确认", step7)
        self.assertIn("三者都允许 direct-entry，但都不能跳过证据确认", write_cmd)

    def test_figure_evidence_subchain_is_documented(self):
        step7 = read_rel("agents/step_7_writing.md")
        readme = read_rel("README.md")
        interface = read_rel("references/figure-writing-interface.md")

        self.assertIn("figure_index.json", step7)
        self.assertIn("figure_evidence_report.md/json", step7)
        self.assertIn("figure_claim", step7)
        self.assertIn("figure_overinterpretation", step7)
        self.assertIn("caption_only", step7)
        self.assertIn("text_caption_aligned", step7)
        self.assertIn("visual_confirmed", step7)
        self.assertIn("figure_not_supported", step7)
        self.assertIn("need_visual_check", step7)
        self.assertIn("supplement_text_evidence", step7)
        self.assertIn("figure_intent", step7)
        self.assertIn("evidence_basis", step7)
        self.assertIn("candidate_specs", step7)
        self.assertIn("human_selected_candidate", step7)
        self.assertIn("figure_risk_note", step7)
        self.assertIn("图表意图与证据约束", step7)
        self.assertIn("图表证据子链", readme)
        for token in [
            "figure_source",
            "figure_asset_mode",
            "replacement_hint",
            "正文引出句",
            "图后解释句",
            "auto_insert_figures=true",
            "LLM-for-Zotero-MinerU-cache-*.zip",
            "没有 MinerU ZIP 但本地 PDF 可读时，允许通过 PyMuPDF 直接抽取 `pdf_direct` 候选图",
            "没有 MinerU ZIP 且 PDF 不可读或无候选图时，才只保留正文图位占位，不自动选图",
        ]:
            self.assertIn(token, interface)

    def test_step7_auto_insert_figures_degrades_without_mineru_zip(self):
        step7_entry = read_rel("agents/step_7_entry.md")
        step7 = read_rel("agents/step_7_writing.md")
        figure_contract = read_rel("references/figure-writing-interface.md")

        for token in [
            "## figure_mode 轴",
            "- `auto_insert`",
            "- `post_write`",
            "- `skip`",
        ]:
            self.assertIn(token, step7_entry)

        for token in [
            "| MinerU 图文资产 | Zotero 附件 / 用户提供 | `LLM-for-Zotero-MinerU-cache-*.zip` 或等价图文资产包 | `auto_insert_figures=true` 时必选 |",
        ]:
            self.assertIn(token, step7)

        for token in [
            "没有 MinerU ZIP 但本地 PDF 可读时，允许先进入 `post_write`，用 PyMuPDF 生成 `pdf_direct` 低置信候选图",
            "- `skip`",
        ]:
            self.assertIn(token, step7_entry)

        self.assertIn("没有 MinerU ZIP 但本地 PDF 可读时，允许用 PyMuPDF 直接抽取 `pdf_direct` 候选图", step7)
        self.assertIn("figure_evidence_status=pdf_direct_candidate_pending_manual_check", figure_contract)

    def test_step7_zotero_paper_writing_requires_minimum_illustrated_delivery(self):
        step7 = read_rel("agents/step_7_writing.md")
        figure_contract = read_rel("references/figure-writing-interface.md")

        for token in [
            "图文并茂完成门",
            "默认交付不能只有纯文字",
            "`figures/` 相对路径图片已插入正文",
            "正文保留可解析图位标记并生成 `figure_evidence_report.md/json`",
            "`draft_risk_summary.md` 明确记录 `figure_mode=skip`、已检查资产范围、不可插图原因和后续补图动作",
            "没有这三者之一，不得宣称 Step 7 写作完成",
            "more-paper 写作入口默认是图文稿，而不是 text-only",
            "figure_asset_check",
        ]:
            self.assertIn(token, step7)

        for token in [
            "默认交付物应当图文并茂",
            "Markdown 不是纯文字豁免",
            "已插入的项目内 `figures/` 相对路径图片，或可解析图位标记 + `figure_evidence_report.md/json`，或带 `figure_mode=skip` 原因的 `draft_risk_summary.md`",
            "`figure_asset_check` 必须覆盖 Zotero child attachments、MinerU ZIP、已有 `figure_index.json`、本地图片目录和可读 PDF",
            "没有执行该检查时，不得把无图初稿标记为完成",
            "纯文字降级只允许两种情况",
        ]:
            self.assertIn(token, figure_contract)

    def test_original_figure_insertion_reminds_without_authorizing_redraw(self):
        step7_entry = read_rel("agents/step_7_entry.md")
        step7 = read_rel("agents/step_7_writing.md")
        figure_contract = read_rel("references/figure-writing-interface.md")
        reminder = (
            "已按论文原图插入。本 skill 也支持图表重绘、曲线数字化、可编辑"
        )

        self.assertIn(reminder, step7_entry)
        self.assertIn(reminder, step7)
        self.assertIn("提醒不构成授权", step7_entry)
        self.assertIn("不得因为已提醒而运行绘图代码", step7)
        self.assertIn("提醒只出现一次且不构成重绘授权", figure_contract)

    def test_step8_light_meaning_audit_trigger_exists(self):
        step8 = read_rel("agents/step_8_polishing.md")

        self.assertIn("meaning_audit_required", step8)
        self.assertIn("meaning_audit_reason", step8)
        self.assertIn("轻量含义审计触发", step8)
        self.assertIn("claim、引用、限定词、比较词", step8)
        self.assertIn("不把普通润色升级成重审稿", step8)
        self.assertIn("转人工复核", step8)


if __name__ == "__main__":
    unittest.main()
