# More Paper 写作质量提升研究备忘录

日期：2026-06-27

来源：

- 用户附件：`$HOME/Desktop/MorePaper改进建议与写作资料参考整理.docx`
- 当前仓库：`SKILL.md`、`agents/step_7_writing.md`、`agents/step_8_polishing.md`、`references/mechanism-analysis-writing-contract.md`、`references/figure-writing-interface.md`、`references/writing-quality-borrowing-plan.md`
- 外部链接：见本文末尾。

## 0. 结论先行

附件的核心判断成立：More Paper 下一轮写作质量提升，不应继续堆 prompt，而应把写作质量拆成可执行、可审计、可回退的质量门。

最值得落地的方向是：

1. 把 `claim_strength`、`evidence_requirement`、`figure_table_panel_binding`、`mechanism_discrimination` 写入 Step 7 的结构化工件。
2. 把材料/机械/工程类学科审查包做成 Step 7 的领域增强规则，而不是全局默认写作风格。
3. 把 Step 8 的 AI 味检查扩展为“科学空话诊断”，但只诊断表达和论证风险，不新增证据、不替代引用审计。
4. 把外部科学写作资料转成 `clarity_audit`、`argument_plan_first`、`figure_claim_binding`、`journal_submission_audit`、`scientific_style_format`，不要搬运句式。
5. 公共文档和入口元数据中的 Sci-Hub 宣传口径需要改成合规访问优先；当前附件提出的 “SKILL.md front matter 格式损坏” 在本仓库现状下不是事实，`SKILL.md` 已经是标准 front matter。

## 1. 附件建议的消化与取舍

### 1.1 已经具备的能力

当前仓库已经覆盖：

- Step 7 的多入口证据 intake：`zotero_full`、`zotero_mineru`、`evidence_pack`、`deep_read_refine`、`mechanism_analysis`、`draft_only`、`mixed`。
- Step 7 的证据等级和阅读深度边界：摘要/元数据不能支撑强 claim，全文/PDF/笔记/标注才可支撑具体结论。
- Step 7 的机理分析链：`deep_read_cards -> mechanism_cards -> mechanism_argument_plan -> mechanism_claim_audit -> mechanism_paragraph_audit -> 正文`。
- Step 7 的图表接口雏形：已有 `figure_id`、`purpose`、`claim_supported`、`evidence_basis`、`figure_risk_note` 等字段。
- Step 8 的保守修订边界：不新增外部证据，不替代 Step 7 引用审计，不重写主论证。

### 1.2 附件中需要修正的判断

- `SKILL.md front matter`：当前文件已是标准 `---` front matter。附件中示例可能来自旧版本或外部整理误读。下一步不应把它列为第一优先级。
- `/write-section`、`/deep-read`、`/mechanism-audit`、`/figure-claim-audit`：不建议新增 slash 命令式公开入口。仓库当前治理原则是“一个主入口 + direct-entry + step contracts”。更稳妥做法是在 `references/entry-guide.md` 和 `agents/step_7_entry.md` 中增强意图路由，而不是新增并行入口。
- 材料/机械/工程学科包：建议做，但不要全局默认。它应由关键词、目标学科、用户项目材料或目标期刊触发。
- 下载合规模式：附件提醒合理。当前 README 和 SKILL 描述中仍存在大量 Sci-Hub 宣传语，应收敛为 “OA / publisher / institutional access / author copy / user-provided PDF first; Sci-Hub as user-risk optional legacy fallback if retained locally”。这属于公共文档和 Step 5 路由口径治理，不是 Step 7 写作质量本体。

## 2. 外部资料可转化的质量门

### 2.1 Stanford / Coursera Writing in the Sciences

可借鉴为：

- `clarity_audit`: 删除冗余、减少名词堆叠、检查主语和动作是否清楚。
- `abstract_intro_discussion_check`: 摘要、引言、讨论的章节功能检查。
- `sentence_action_check`: 强制识别句子中的真实动作，避免“研究表明/具有重要意义”占位。

不建议：

- 不把课程句式直接做成模板。
- 不把主动语态作为硬规则；科学写作中被动语态仍有合理场景。

### 2.2 Duke Scientific Writing Resource

Duke 资源的关键价值是“让读者准确理解作者意图”，而不是语法纠错。它适合落到：

- `reader_expectation_audit`: 主题、动作、重心、强调位置是否符合读者预期。
- `cohesion_coherence_audit`: 句间已知信息到未知信息的推进是否断裂。
- `smart_revision_pass`: 先诊断再修订，避免 Step 8 只做表面润色。

### 2.3 Gopen & Swan: The Science of Scientific Writing

可借鉴为：

- `topic_stress_position`: 检查句首是否承接已知信息，句末是否放置重点信息。
- `old_to_new_flow`: 检查段落是否从已知到未知推进。
- `paragraph_expectation_map`: 每段标注“读者此处期待什么信息”。

这套规则最适合补强 Step 8 的可读性和 Step 7 的段落自检，而不是替代证据审计。

### 2.4 MIT Communication Lab

MIT Communication Lab 对 More Paper 的价值在工程写作和视觉沟通：

- `figure_claim_binding`: 每条图表相关 claim 必须绑定 figure/table/panel、图注、正文位置、支撑类型和风险。
- `visual_story_check`: 图表是否承担明确的科学问题，而不是作为装饰。
- `engineering_audience_fit`: 论文面向工程读者时，优先清楚说明变量、约束、系统边界、评价指标和可复现条件。

### 2.5 Whitesides: Writing a Paper

核心可转化原则是“先数据/图表/结论/大纲，后正文”：

- `argument_plan_first`: 写正文前先生成 `argument_plan`，包含图表、数据、结论、证据缺口。
- `figure_first_discussion`: 结果与讨论章节先锁定图表叙事，再写段落。
- `claim_order_check`: 检查正文 claim 顺序是否跟图表和证据顺序一致。

### 2.6 Nature Masterclasses

该链接当前跳转登录授权页。可保守吸收其公开定位：科学写作、投稿、出版、同行评审训练。适合转成：

- `journal_submission_audit`: 目标期刊、cover letter、投稿材料、伦理声明、数据可用性、图表规范。
- `reviewer_lens_check`: 从编辑/审稿视角检查贡献、证据、边界和可读性。

### 2.7 Elsevier Researcher Academy

Elsevier Researcher Academy 页面可访问，主要覆盖研究准备、写作、出版、伦理、同行评审和沟通。可转成：

- `publication_ethics_check`: 伦理、数据、署名、掠夺性期刊风险。
- `journal_selection_check`: 选刊和目标读者匹配。
- `peer_review_readiness_check`: 投稿前风险扫描。

### 2.8 Academic Phrasebank

Phrasebank 适合做表达功能候选，而不是直接进入正文模板：

- 可用于 `academic_phrase_control`：引出研究空白、引用文献、报告结果、讨论发现、写结论。
- 必须加限制：候选表达只有在 claim 和证据已经成立后才能使用。
- 禁止把 Phrasebank 变成“AI 腔句式注入器”。

### 2.9 Purdue OWL Academic Writing

适合补基础写作和段落组织：

- `paragraph_coherence_check`
- `argument_logic_check`
- `conciseness_check`
- `active_passive_choice_check`

它更适合作为 Step 8 的低风险语言/结构规则，不适合直接决定学术 claim 强度。

### 2.10 ACS Guide / CSE Scientific Style and Format

ACS 链接当前被 Cloudflare 挑战拦截；CSE 在线站点当前返回 403。仍可作为规范方向保守吸收：

- `scientific_style_format`: 单位、符号、缩写、图表说明、参考文献格式、化学/材料术语一致性。
- 对应 Step 8 的术语终验和格式终验；不要把它与论证强度审计混合。

## 3. 面向材料/机械/工程论文的领域增强包

附件中材料类建议很有价值，但应做成可触发的领域包。

### 3.1 建议新增 `references/domain-packs/materials-mechanics-writing.md`

最小内容：

- `materials_system_card`: 合金/基体、增强相、制备工艺、热处理、初始组织。
- `thermomechanical_process_card`: 温度、应变速率、真应变、应力状态、压缩/剪切/轧制路径。
- `microstructure_evidence_card`: EBSD、TEM、SEM、XRD、KAM、GOS、HAGB/LAGB、织构、标尺、取样位置。
- `mechanism_discrimination_card`: CDRX、DDRX、DRV、PSN、Zener pinning、load transfer 的候选机制、必要证据、反证边界。
- `figure_claim_panel_card`: claim 与 figure/table/panel 的绑定。
- `journal_style_card`: MSEA、Acta、Scripta、JMPT、中文核心/学位论文的目标体裁差异。

### 3.2 竞争机制判别矩阵

建议不要写死在 prompt 里，而是作为 `mechanism_cards` 的字段增强：

| 观察 | 候选机制 | 必要证据 | 禁止依据 |
|---|---|---|---|
| 晶粒细化 | CDRX | LAGB 到 HAGB、亚晶旋转、KAM/GOS 演化、取向差连续增加 | 只看晶粒变小 |
| 原晶界新晶粒 | DDRX | 原晶界鼓出、项链状组织、迁移晶界、HAGB 新晶粒 | 只看 HAGB fraction |
| KAM 降低 | DRV 或再结晶后软化 | KAM、亚晶、流变软化和空间对应 | 把恢复直接等同于再结晶 |
| 细晶区稳定 | Zener/CNT pinning | CNT 位于晶界、TEM/EDS/SAED、尺寸稳定统计 | 只因加入 CNT 就推断钉扎 |

### 3.3 图-表-正文 claim 绑定字段

建议新增或扩展字段：

```json
{
  "claim_id": "C-001",
  "claim_text": "",
  "claim_strength": "background|trend|parameter|numeric_comparison|mechanism|novelty",
  "required_evidence": ["full_text", "figure_panel", "method_table"],
  "evidence_anchor": {
    "source_id": "",
    "page": null,
    "figure": "",
    "panel": "",
    "table": "",
    "caption": ""
  },
  "support_status": "support|weak_support|not_supported|cannot_judge",
  "risk_flags": []
}
```

## 4. 句子强度分级

附件中的“句子强度分级”应并入 `citation-audit-contract.md` 和 `section_blueprints`。

| 句子类型 | 允许证据 | 默认动作 |
|---|---|---|
| 背景句 | 综述、摘要、元数据 | 可写，但标低风险背景 |
| 趋势句 | 多篇文献或系统性证据 | 要求至少两个来源或一个综述级来源 |
| 参数句 | PDF 原文、方法、表格、用户数据 | 无全文锚点则降级 |
| 数值比较句 | 页码/图/表级证据 | 必须给锚点 |
| 机理判断句 | 全文证据 + 图表/实验/仿真优先 | 无竞争机制判别则降级 |
| 创新性声明 | 检索覆盖 + 对比文献 | 无检索覆盖不得写强创新 |

## 5. Step 8 的科学空话诊断

建议在现有 `deterministic_writing_diagnostics.py` 的规则族之外，新增 `mechanism_bluff` 诊断族。

候选规则：

- `mechanism_without_state_variables`: 只有“促进/抑制/改善”，没有状态量。
- `causal_jump_without_validation`: 从性能变化直接跳到微观机制。
- `visual_claim_without_panel`: 写“图中可见”，但无图号/panel/图注锚点。
- `proof_verb_without_evidence`: “证明/验证/揭示”缺少全文或实验锚点。
- `generic_strengthening_list`: 晶粒细化、位错强化、第二相强化等套话并列但无具体证据。

边界：该诊断只能标风险和建议降强度，不能新增文献、补图号或替 Step 7 做完整引用审计。

## 6. 推荐实施顺序

### P0：口径和入口清理

- 确认 `SKILL.md` front matter 无需修复。
- 把 README / SKILL / Step 5 中公开宣传的 Sci-Hub 口径收敛为合规访问优先。
- 补一个测试，防止公开文档继续把 Sci-Hub 作为默认卖点。

### P1：写作质量 schema 增强

- 扩展 `citation-audit-contract.md`：加入 `claim_strength` 和 `required_evidence`。
- 扩展 `figure-writing-interface.md`：加入 figure/table/panel 绑定矩阵。
- 扩展 `mechanism-analysis-writing-contract.md`：加入材料机制判别字段和 `mechanism_bluff` 降级规则。

### P2：领域包

- 新增 `references/domain-packs/materials-mechanics-writing.md`。
- 先只做材料/机械一个包，不做泛化插件系统。
- 通过关键词触发，不全局默认。

### P3：可运行检查

- 在 `scripts/audit_mechanism_claims.py` 或新脚本中加入 claim strength 审计。
- 在 `scripts/deterministic_writing_diagnostics.py` 中加入 `mechanism_bluff` 规则族。
- 用 `tests/test_step7_step8_contracts.py` 锁住新增合同。

## 7. 外部链接研究记录

- Stanford/Coursera Writing in the Sciences: https://www.coursera.org/learn/sciwrite
- Writing-in-the-Sciences GitHub 整理版: https://github.com/quanghuy0497/Writing-in-the-Sciences
- Duke Scientific Writing Resource: https://sites.duke.edu/scientificwriting/
- Gopen & Swan PDF: https://cseweb.ucsd.edu/~swanson/papers/science-of-writing.pdf
- MIT Communication Lab: https://mitcommlab.mit.edu/
- Whitesides Group Writing a Paper: https://www.gmwgroup.harvard.edu/publications/whitesides-group-writing-paper
- Nature Masterclasses course: https://www.nature.com/masterclasses/online-course-in-scientific-writing-and-publishing/16507840
- Nature Masterclasses home: https://www.nature.com/masterclasses/
- Elsevier Researcher Academy: https://researcheracademy.elsevier.com/
- Academic Phrasebank: https://www.phrasebank.manchester.ac.uk/
- Purdue OWL Academic Writing: https://owl.purdue.edu/owl/general_writing/academic_writing/index.html
- ACS Guide book: https://pubs.acs.org/doi/book/10.1021/acsguide
- ACS Guide page: https://pubs.acs.org/page/acsguide
- ACS Style Quick Guide: https://pubs.acs.org/doi/10.1021/acsguide.40303
- CSE Scientific Style and Format: https://www.scientificstyleandformat.org/

访问状态：

- Duke、MIT、Elsevier、Phrasebank、Purdue、Coursera 可访问或可确认页面。
- Whitesides Harvard 页面当前返回 Access Denied，但标题和用途可由附件保留，后续可用浏览器或替代 PDF 再核验。
- Nature course 当前跳转登录授权页。
- ACS 当前被 Cloudflare challenge 拦截。
- CSE 当前返回 403。

## 8. 下一步验收标准

这轮研究真正落地，应满足：

1. Step 7 写作前能明确每条强 claim 属于哪种句子强度。
2. 图表相关 claim 不能只写“如图所示”，必须绑定图/表/panel 或降级。
3. 机理段落必须包含状态量、因果链、证据锚点、竞争机制或边界句。
4. Step 8 能识别科学空话和过强机制动词，但不越权补证据。
5. 公共文档不再把非合规下载路径作为默认宣传卖点。
