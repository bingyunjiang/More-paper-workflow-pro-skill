# Step 7 Drafting Contract

正文生成以章节功能、argument plan 和证据矩阵为先，不以流畅感覆盖证据不足。

## Writing axes

`writing_axes` 至少包含 `paper_type / section_role / language_mode / style_target`。它们不替代 `target_genre / writing_mode / evidence_entry_mode`。不得把 Nature 风格设为默认目标，也不得用任何期刊 prestige 代替任务定义。

`abstract-only` 细分为 `journal-abstract / thesis-abstract-zh / thesis-abstract-en / bilingual-abstract`。中英文摘要共享事实、数值和边界，但不要求逐句直译。

## 蓝图到正文

先从可用的 `section_blueprints.json` 派生 `writing_blueprints.json/md`，再生成 `argument_plan.json/md`，最后进入正文。Direct-entry 没有 Step 2 蓝图时可以独立生成，但要记录 lineage。

每节至少定义：`section_function / expected_length / key_claims / evidence_needed / do_not_write / transition_from / transition_to / risk_flags / one_sentence_argument / paragraph_job_map`。每段只标一个主任务，并按 `claim / evidence / boundary` 展开。

`argument_plan` 证据确认区块必须记录：

- `confirmed_evidence`
- `unresolved_evidence`
- `candidate_evidence_used`
- `confirmation_status`
- `rollback_if_unconfirmed`

确认门：claim、evidence 或 boundary 不清时，先输出 `one_sentence_argument`、`paragraph_job_map`、关键假设和 `unresolved_evidence`，本节不得直接进入完整正文生成，也不得把未确认内容写成确定性结论。

## 写作规则

- 每节只承担一个主要功能，先写 one-sentence argument，再做段落展开。
- `do_not_write` 和 `risk_flags` 是硬边界，不是装饰字段。
- 对话式论证可使用“他说 A -> 我说非 A/A+ -> 所以 C”和核心/支撑/补充的章节权重，但不得越过证据边界；证据不足只能保守表达或输出待补证据。
- 强 claim 绑定 confirmed evidence；candidate evidence 只生成候选表述或待核验占位。
- 学位论文要求更完整的方法、边界、跨章回扣和反证讨论；期刊论文按目标体裁压缩，但不得压缩证据链。
- `chapter-only / continue-existing / revision-only` 只处理用户指定范围。
- 按大纲对应的 Zotero 子集合取证，不扫整个 Zotero 文库；每次只写一个当前请求的小节，不提前展开后续小节。
- `target_genre=thesis` 时按博士论文深度组织“工程场景 -> 需求来源 -> 机理约束 -> 制造约束 -> 研究必要性”，并维护 `doctoral_thesis_map.json` 与 `doctoral_ready`，但不补跑 Step 1-6。

## 术语与风格

术语状态分三层：`seed`、`provisional`、`locked`。不要求一开始扫完全部 PDF；seed 和 provisional 可用于写作与证据组织，只有 locked 才是全篇标准。先建立可写作、可审计的最小术语标准。

按需加载 `references/writing-quality-borrowing-plan.md` 和 `references/style-learning-workflow.md`，只学习结构、语言和修订模式，生成 `style_profile / section_blueprints / writing_rationale_matrix`；不得把外部句子或默认体裁直接搬入正文。

## 内部写作流水线

内部依次执行生成、整合、审阅、校验和轻量可读性整理。段内写作质量底线包括最小术语统一、删除明显重复、局部过渡和标记需要后续补证据。

该流水线不得作为用户选项、命令、按钮或对话模式暴露。Step 7 的职责是维持 workflow 与证据边界，不应预设用户的写作策略、论证风格或表达审美；成稿级 polish 属于 Step 8。

## DOCX 时机

当前写作范围完成并通过相应门后，才提示是否导出 DOCX；不得在每个写作增量后自动导出 DOCX。公式任务同时遵守 `references/equation-writing-contract.md`。
