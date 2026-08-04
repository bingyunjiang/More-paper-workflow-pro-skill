# Step 7: 论文写作

> 利用 Step 1-6 的所有产出，以 Zotero 条目、PDF 附件池和 `文献-Zotero架构对照.json` 作为推荐证据底座，撰写正式学术论文。
> **核心原则：每处引用必须能追溯到 Zotero 条目、PDF 原文、笔记、标注或用户提供的可核验证据，抑制大模型幻觉。Zotero/MinerU 是推荐资产层，不是 Step 7 的硬依赖。**

---

## 启动前读取 (Pre-read Checklist)

执行本步骤前，必须确认以下文件已加载：

- [ ] `研究主题.md` — Step 1 产出（研究方向 + 预审结论）
- [ ] `大纲关键词.md` — Step 2 产出（章节结构） + `.skill-state/term_aliases.md` 🆕
- [ ] `检索文献表.md` — Step 4 产出（参考文献 + 评分）
- [ ] `文献库.bib` — Step 4 产出（筛选后 BibTeX 文献库）
- [ ] `zotero-架构.md` — Step 6 产出（Zotero 集合结构）
- [ ] `文献-Zotero架构对照.json` — Step 6 产出（文献到集合、Zotero 条目、PDF 附件的完整机器映射；如直接基于 Zotero 写作，可由 Zotero MCP 动态生成最小映射）
- [ ] `文献-Zotero架构对照.md` — Step 6 产出（人工审阅版，可截断，不作为机器执行源；直接 Zotero 写作时可缺省）
- [ ] `pdf-附件池索引.json` — Step 6 产出（多来源 PDF 附件池、匹配状态、完整路径；直接 Zotero 写作时可缺省）
- [ ] `evidence_pack.json` — 本地证据包索引（可选；无 Zotero/MinerU 时推荐生成）
- [ ] `retrieval_index_manifest.json` — 🆕 RAG 候选定位索引说明（可缺省；仅内部加速层）
- [ ] `retrieval_candidates.json` — 🆕 章节级 claim 候选证据包（可缺省；不可直接当证据）
- [ ] `.skill-state/term_aliases.md` — 🆕 术语标准化映射（确保写作用词与检索一致）
- [ ] `references/literature-review-matrix-schema.md` — 综述矩阵 schema
- [ ] `references/journal-style-learning-guide.md` — 目标体裁/文档风格学习方法论（期刊、学位论文、会议论文、既有草稿均可适配）
- [ ] `references/gbt7714-2015-citation-format.md` — 引用格式规范
- [ ] `references/genre-style-axis.md` — target_genre 轴：thesis / journal / review / report / proposal / conference / course-paper
- [ ] `references/section-function-matrix.md` — 🆕 章节-功能-证据需求矩阵
- [ ] `references/section-blueprint-workflow.md` — 🆕 章节蓝图工作流
- [ ] `references/section-blueprint-template.md` — 章节蓝图字段规范，含 `claim_strength / required_evidence / evidence_anchor`
- [ ] `references/scientific-writing-quality-rubric.md` — 通用科学写作质量 rubric；用于句子主谓、旧新信息、段落功能和图表先行论证顺序检查
- [ ] `references/section-quality-gates.md` — 摘要/引言/讨论/结论专项写作门；仅检查章节功能，不替代引用审计
- [ ] `references/mechanism-analysis-writing-contract.md` / `references/equation-writing-contract.md` — 机理分析与公式登记、渲染、审计契约
- [ ] `references/domain-packs/materials-mechanics-writing.md` — 材料/机械/工程领域增强包；仅在任务命中材料、机械、热变形、显微组织或工程机理时加载
- [ ] `references/domain-packs/materials-journal-style.md` — 材料/机械目标期刊与体裁风格包；仅在目标期刊或体裁明确时加载
- [ ] `references/domain-packs/power-electronics-ev-energy-writing.md` — 电力电子/充电/储能/EMS/V2G/快充/无线充电/超级电容领域增强包；仅在任务命中这些方向时加载
- [ ] `references/domain-packs/power-energy-journal-style.md` — 电力电子/能源系统目标期刊与体裁风格包；仅在目标期刊或体裁明确时加载
- [ ] `references/writing-antipatterns.md` — 🆕 写作反模式库
- [ ] `references/reviewer-protocol.md` — 🆕 reviewer-style 预审输出格式
- [ ] `references/reviewer-defect-taxonomy.md` — 审稿人视角缺陷库；用于 pre-review、revision-roadmap 和 review-style polish 的问题分类
- [ ] `references/citation-audit-contract.md` — 🆕 写作后引用审计契约
- [ ] `references/figure-writing-interface.md` — 图表与写作接口
- [ ] `.skill-state/error_log.md` — 已知错误及修复规则

---

## 写作前先答 (Before You Write)

先把下面四个问题答清楚，再开始写正文：

1. 这一轮要写的具体范围是什么：全文、指定章节、已有草稿续写，还是 revision-only？
2. 当前章节的功能是什么：问题陈述、综述综合、方法定义、结果讨论，还是机理解释？
3. 这一节可用的证据层是什么：Zotero、PDF、笔记、标注、证据包，还是只有摘要/元数据？
4. 这一轮的输出契约是什么：先大纲、再正文、再自检、再 claim/evidence 对照，还是只做章节蓝图？

若答案还不稳定，先补 `section_blueprints`、`argument_plan` 或 `evidence_gap_list`，不要直接进入正文。

---

## 适用任务 (Applicable Tasks)

- 撰写完整学术论文（paper_type × language × target_genre）
- 写文献综述（review 类型专属 8 节骨架 + 7 条纪律）
- 写中英文双边摘要
- 撰写或续写学位论文、课程论文、会议论文、期刊论文的指定章节
- 基于已有草稿补写、改写、扩写其中一部分章节
- 解读审稿意见并生成修稿路线图、逐条回应骨架、证据缺口清单
- 实时引文支撑（7.10）
- 同行评审仿真 + Rebuttal 预演（7.12）
- 科研图表生成（7.15）
- 写后引用审计（7.16）

---

## 不适用任务 (Non-applicable Tasks)

- 大纲生成 → 路由到 `agents/step_2_outline.md`
- 文献检索 → 路由到 `agents/step_4_search_score.md`
- 成稿级精修、全文一致性、表达风险收口、修订后验证 → 路由到 `agents/step_8_polishing.md`

## When to use this Step

- 用户要生成、续写、补写或改写正文，且需要把章节功能、证据、引用和图表意图一起纳入写作判断。
- 用户已有 Zotero、PDF、BibTeX、证据包、草稿或指定章节，希望直接构造最小证据映射后写作。
- 用户要做写作前预审、章节蓝图、claim/evidence 对照、引用审计、rebuttal 预演或修稿路线图。

## When NOT to use this Step

- 任务只是下载 PDF、恢复登录或处理 publisher access，去 Step 5。
- 任务只是 Zotero 条目、集合或附件挂回，去 Step 6。
- 任务只是对已有成稿做保守润色、术语终验、机械化表达清理或修订后验证，去 Step 8。
- 任务需要新增外部文献证据但当前证据不足，先回 Step 4/5/6 补材料，不在 Step 7 中臆造。

---

## 输入要求 (Input Requirements)

| 输入 | 来源 | 格式 | 必选 |
|------|------|------|:--:|
| 研究主题 | Step 1 | .md | ✅ |
| 大纲关键词 | Step 2 | .md | ✅ |
| 检索文献表 | Step 4 | .md | ✅ |
| BibTeX 文献库 | Step 4 | .bib | ✅ |
| Zotero 架构 | Step 6 | .md/.json | ✅ |
| 文献-Zotero架构对照 | Step 6 / Zotero MCP 动态生成 | .json + .md | 推荐 |
| PDF 附件池索引 | Step 6 / Zotero MCP 动态生成 | .json | 可选 |
| Prepared PDF artifacts | Step 6 / `prepare_pdf_for_llm.py` | `.json` + `.md` | 可选；全文提取后的带锚点工作层 |
| Zotero 条目/PDF 附件 | Zotero 文库 | Zotero MCP | 推荐；非硬依赖 |
| MinerU ZIP 缓存 | Zotero 附件 / 用户提供 | `LLM-for-Zotero-MinerU-cache-*.zip` | 可选；图文增强层 |
| 证据包 | 用户提供 / 项目目录 | PDF、BibTeX、CSL JSON、报告、数据、草稿、标准文件、图片目录 | 无 Zotero/MinerU 时推荐 |
| 已有草稿/指定章节 | 用户提供 | .md/.docx/章节文本 | 可选 |
| 综述矩阵 | Step 7.2 | .csv/.md | 写作前生成 |
| 目标体裁/文档风格画像 | Step 7.3 | `.md` / `.json` | 🆕 |
| 章节蓝图 | Step 7.3 | `.md` / `.json` | 🆕 |
| `section_blueprints.json` / `writing_blueprints` | Step 2 / Step 7.3 | `.json` / `.md` | 前者是可选不可变结构基线；后者是保留 lineage 的写作派生层，direct-entry 可独立生成 |
| MinerU 图文资产 | Zotero 附件 / 用户提供 | `LLM-for-Zotero-MinerU-cache-*.zip` 或等价图文资产包 | `auto_insert_figures=true` 时必选 |

> Step 7 不再直接把 `paper-temp/*.pdf` 当作唯一知识库。PDF 可以来自 Step 5、原有文件、后续补下载、手动整理目录、Zotero 条目附件或用户证据包。若 `pdf-附件池索引.json` 不存在，但 Zotero 条目已带 PDF 附件，则以 Zotero MCP 的 `zotero_get_item_children` / `zotero_get_attachment_path` / `zotero_get_item_fulltext` 为准，必要时再生成临时 `pdf-附件池索引.json` 供审计复用。

**多入口证据 intake：**

Step 7 先识别证据入口，再构造最小证据映射。场景只决定读取路径，证据等级决定能写多强。

| evidence_entry_mode | 适用场景 | 默认处理 |
|------------|----------|----------|
| `zotero_full` | 有 Zotero 条目、PDF、notes/annotations | 读取 Zotero 元数据、notes、annotations、fulltext，构造 claim 证据映射 |
| `zotero_mineru` | Zotero 条目下有 MinerU ZIP | 在 `zotero_full` 外读取 ZIP 的 `full.md`、`manifest.json`、`images/` 作为图文增强层 |
| `evidence_pack` | 无 Zotero/MinerU 或用户指定本地材料 | 读取 PDF、文献库、报告、数据、草稿、标准文件、图片目录，生成 `evidence_pack.json` |
| `deep_read_refine` | 当前章节/小节需要对 1-5 篇核心文献做深读后再写 | 只在当前小节证据范围内生成 `deep_read_cards.json/md`，不直接生成最终正文 |
| `mechanism_analysis` | 当前章节需要解释机理、机制、影响规律、耦合关系或作用路径 | 先把 `deep_read_cards` 整形为 `mechanism_cards` 与 `mechanism_argument_plan`，再写正文 |
| `draft_only` | 只有草稿或写作需求 | 只生成低风险结构稿、待补引用和 `evidence_gap_list.md`，不写强 claim |
| `mixed` | Zotero、证据包、草稿混合 | 以 claim 为中心合并证据，不以文件来源堆材料 |

**PDF-only evidence_pack 正式入口：**

PDF-only evidence_pack 是 Step 7 的正式入口，不是降级补丁。没有 Zotero/MinerU 的读者只需提供 PDF 文件夹、写作目标，以及可选的大纲、已有草稿或目标期刊/学位论文要求；Agent 应先生成或刷新 `evidence_pack.json`，再进入深读和写作，不要求用户补跑 Step 1-6 或先安装 Zotero。

PDF-only 入口的默认处理：

1. 扫描用户指定 PDF 文件夹，建立本地证据清单。
2. 为每个 PDF 记录 `source_path / source_type / evidence_level / claim_scope / risk_flags / verification_action`。
3. 对可读 PDF 生成或复用 `prepared_pdf_artifacts.json`、`*.clean.md`、`*.chunks.json`、`*.extraction_report.json`。
4. 将扫描件、OCR 差、表格/公式密集、页码锚点缺失的 PDF 标记为候选或需人工核验，不得自动升级为强证据。
5. 只在核心文献、关键 claim、方法细节、实验/仿真参数、机制解释或引用审计需要时进入全文深读；背景性概述可停留在低风险证据层。

**证据包最小字段：**

`evidence_pack.json` 中每个来源至少记录：

| 字段 | 说明 |
|------|------|
| `source_path` | PDF、报告、数据、草稿、标准文件、图片或 MinerU ZIP 路径 |
| `source_type` | `pdf / mineru_zip / bibliography / report / data / draft / standard / image / unknown` |
| `evidence_level` | `pdf_fulltext_supported / author_provided / source_document_supported / metadata_only / visual_candidate / candidate_only` |
| `claim_scope` | 可支撑范围，如 `strong_claim_if_traceable` 或 `background_or_candidate` |
| `risk_flags` | 候选层、需回 PDF、图文未确认、字段缺失等风险 |
| `verification_action` | 进入正文前的核验动作 |

无 Zotero/MinerU 时不阻塞 Step 7，但必须要求用户指定证据包或证据目录。没有 PDF、全文、实验报告、可核验数据或标准文件支撑时，只能写背景、结构和待补证据草稿。

**Zotero-MinerU ZIP 规则：**

- 若 Zotero 条目只有 PDF、没有 MinerU ZIP，Step 7 仍可继续读取 Zotero fulltext、notes、annotations 或 PDF 原文；只有当本轮需要图文综述、图表候选或 Word 图文稿时，才建议用户先用 `llm-for-zotero` + MinerU 解析核心 PDF。
- Zotero 中 MinerU 缓存的正式附件形态是 `.zip`，通常命名为 `LLM-for-Zotero-MinerU-cache-*.zip`。
- ZIP 内 `manifest.json` 是图文映射首选索引，`full.md` 是图文阅读层，`images/` 是图像素材，`_llm_source.json` 记录 `parentItemKey / attachmentKey / sourceFilename`。
- MinerU ZIP 是增强缓存，不替代 PDF 原文、Zotero notes 或 annotations 的最终核验地位。
- 如果发现同名已展开目录，只能作为临时缓存复用，不能作为契约前提。
- 若 `auto_insert_figures=true` 且 MinerU ZIP 缺失，应明确降级为 `figure_mode=post_write`；若连正文占位都不适合，则退回 `figure_mode=skip`，不得静默失败。
- 用户要求“撰写论文 / 完整写作 / 章节写作 / 重写这篇”且输入来自 Zotero 集合时，若任一候选文献存在 MinerU ZIP、`figure_index.json` 或等价图文资产，默认视为 `auto_insert_figures=true`，进入 `figure_mode=auto_insert` 或 `figure_mode=post_write`；除非用户明确要求“纯文字稿 / 不要插图 / 先不插图”。
- Markdown-first 不等于 text-only。启用图文联合时，Markdown 初稿中应包含项目内 `figures/` 相对路径图片，或至少包含可解析的图位标记与图表证据缺口；不得在已有图文资产时静默输出无图正文。
- 若本轮决定不插图，必须在状态卡或 `draft_risk_summary.md` 中记录 `figure_mode=skip`、跳过原因、已检查的 Zotero child attachments / 本地资产范围，以及后续补图动作。

**独立入口规则：**
如果用户已有 Zotero 文库、已有草稿、已有参考文献、已有 PDF 目录或只要求撰写/续写指定章节，可直接从 Step 7 开始，不要求补跑 Step 1-6。Agent 应先构造最小证据映射：目标章节、大纲片段、可用 Zotero/PDF/笔记证据、引用风险；只有证据不足影响关键 claim 时，才触发 `CP-CITATION-WARN` 或建议回退补证据。

对已有草稿的 direct-entry，应优先判定为以下三类之一：
- `continue-existing`：已有草稿，继续写主体内容
- `chapter-only`：已有草稿或目录，只处理指定章节
- `revision-only`：已有草稿 + 审稿意见/修订目标，只做定向修订

existing-draft 可以跳过前链，但不能跳过证据确认。

**Direct-entry input contract：**

| 可接受输入 | 最小处理 | 降级规则 |
|------------|----------|----------|
| `文献-Zotero架构对照.json` | 作为机器主索引读取 tier、collection、item_key、pdf_path | 缺字段时动态查 Zotero |
| Zotero 集合/标签/条目 key | 只读生成最小映射 | 不要求先跑 Step 6 |
| PDF 目录 / `pdf-附件池索引.json` | 建立附件池和可读证据列表 | 无 Zotero key 时标为本地证据 |
| MinerU ZIP | 读取 `manifest.json`、`full.md`、`images/`，生成图文候选 | 只能作为增强工作层，强 claim 仍需回 PDF/笔记/标注核验 |
| 本地证据包 | 生成 `evidence_pack.json` 最小映射 | 无可核验证据时只写背景或结构稿 |
| `prepared_pdf_artifacts.json` / `*.chunks.json` | 作为全文工作层输入，保留 `chunk_id/pages/evidence_level/must_check_pdf` | 无锚点时只作辅助阅读，不能直接升级为强证据 |
| workflow search results JSON / BibTeX | 构造参考文献候选和证据等级 | 只能作为元数据/摘要级证据，除非补到 PDF/笔记 |
| `paper_card` / Zotero `More-Paper Evidence Card` child note | 恢复文献级证据角色、读取深度和内容贴合边界 | JSON 为主源；Zotero note 只作人类可读副本和 direct-entry 辅助线索 |
| 已有草稿/指定章节 | 识别写作模式和目标章节 | 缺引用审计时标记风险，不阻塞非关键改写 |

Step 7 的成功标准是完成当前写作任务的最小证据闭环，不是补齐 Step 1-6 全套产物。缺少上游产物时必须在输出中标注 evidence_level 和缺口，不得把摘要级证据升级为全文/PDF 证据。

**工件读取优先级：**

从本版开始，Step 7 对统一写作工件采用：

1. `style_profile.json`
2. `writing_blueprints.json`（Step 7 派生；旧项目可兼容读取 `section_blueprints.json`）
3. `writing_rationale_matrix.json`
4. `workflow_search_results.json` / `文献-Zotero架构对照.json` 中的 `paper_card`，以及 Zotero `More-Paper Evidence Card` child note 辅助线索

作为**机器优先输入**；对应的 `.md` 文件是人工审阅、展示和手工修订层。  
如果 JSON 缺失但 Markdown 存在，可以降级读取 Markdown；如果两者同时存在，以 JSON 为准。

**结构化写作与预审子模式：**

Step 7 可以借用“导师式预审”的组织方式，但必须服务于本工作流的证据闭环。所有子模式都消费同一套 `section_blueprints / writing_rationale_matrix / evidence_pack 或 Zotero 映射`，不得另造平行流程。

| 子模式 | 触发场景 | 必须先确认 | 输出 |
|--------|----------|------------|------|
| `section-blueprint-first` | 用户要写指定章节，但章节功能、证据范围或论证顺序还不稳定 | 章节功能、目标读者、证据等级 | 章节蓝图 + evidence gap |
| `pre-review` | 写作前或初稿后要模拟审稿人视角找问题 | 草稿或 argument plan、目标体裁、证据来源 | 预审报告 + next move |
| `citation-audit` | 用户要求查引用、claim 支撑或虚构引用风险 | 草稿、引用标记、文献条目、证据层 | 引用审计报告 |
| `revision-roadmap` | 用户有审稿意见或导师意见，要求形成修稿方案 | 审稿意见、草稿、可用证据 | 修稿路线图 + 回应骨架 |

`pre-review` 的输出顺序固定为：

1. `Review setup`
2. `Major strengths`
3. `Major concerns`
4. `Technical failings`
5. `What blocks a stronger claim`
6. `Recommended next move`

`citation-audit` 的输出顺序固定为：

1. claim 原文或位置
2. 当前引用和证据来源
3. 支撑级别：`support / weak-support / not-supported / cannot-judge`
4. 风险说明
5. 回退建议：`stay_in_step7 / return_to_step4 / return_to_step5 / return_to_step6`

预审和引用审计可以阻止继续写强 claim，但不能替用户新增未核验文献、扩大论证范围或把候选证据升级为全文证据。

---

## 标准输出 (Standard Outputs)

| 输出 | 格式 | 说明 |
|------|------|------|
| 综述矩阵 | CSV/Markdown | 13 列证据矩阵 |
| research_dossier/ | 目录 | 样本状态 + `style_profile` + `writing_blueprints` + `writing_rationale_matrix`；Step 2 `section_blueprints.json` 保持不可变 |
| `retrieval_index_manifest.json` | .json | 🆕 内部索引清单：记录轻量索引 / PDF chunk 索引的来源与规模 |
| `retrieval_candidates.json` | .json | 🆕 章节级 claim 候选证据包：按章节→claim 组织候选片段；仅候选，不是最终证据 |
| `figure_index.json` | .json | 🆕 图号/表号索引：页码、图注、正文引用位置、来源层级 |
| `figure_evidence_report.md/json` | `.md` / `.json` | 🆕 图表证据确认结果：该图/表是否真的支撑某条 claim |
| `deep_read_cards.json/md` | `.json` / `.md` | 🆕 当前小节核心文献深读卡片：claim/method/experiment 摘要、机理提示、可用边界、读取深度和图文候选 |
| `mechanism_cards.json/md` | `.json` / `.md` | 🆕 机理分析卡片：现象、状态量、变量传导、模型/方程、边界条件、验证路径与反证边界 |
| `mechanism_argument_plan.json/md` | `.json` / `.md` | 🆕 机理章节论证计划：把机制 claim 绑定到全文、图表、实验/仿真和边界条件 |
| `step7_execution_card.md` | `.md` | 正文前硬门控状态卡：写作范围、证据入口、机理触发、图文模式、必需工件和 claim 强度 |
| `figure_asset_check.md` | `.md` | Zotero/PDF/evidence_pack 图文资产检查；写明 `auto_insert / post_write / skip` 依据 |
| `evidence_pack.json` | .json | 无 Zotero/MinerU 或混合证据入口下的最小证据映射 |
| 论文初稿 | .md，完成后可导出 .docx | 含完整结构和参考文献；默认先写 Markdown |
| 指定章节草稿 | .md，完成后可导出 .docx | chapter-only / continue-existing 模式产出；默认先写 Markdown |
| 图文联合草稿 | .md/.docx | 写文后或同步插图后的版本，保留正文引出句、图后解释句和图表证据链 |
| 修稿路线图 | .md | `revision_roadmap.md`，逐条审稿意见的优先级、章节绑定、证据动作 |
| 回应骨架 | .md | `response_letter_skeleton.md`，Point-by-Point 回应框架 |
| 证据缺口清单 | .md | `evidence_gap_list.md`，需回退 Step 4/6/7.2 的证据问题 |
| 中→英术语对照表 | .md | zh-to-en 模式额外产出 |
| 写作风险摘要 | .md | `draft_risk_summary.md`，记录反模式、证据空洞与需回退问题 |
| 公式登记与审计 | `.json` + `.md` | `equation_register` + `equation_audit`；绑定稿件哈希，阻断公式缺失、纯文本数学和 LaTeX/矩阵源码残留 |
| 评审报告 + rebuttal-预演 | .md → .pdf | 7.12 质量门产出 |
| 图表 | SVG/PDF/TIFF/JPG/PNG | 7.15 产出或从 MinerU ZIP/证据包复制，保存到 `figures/` |
| 引用审计报告 | .md → .pdf | 7.16 产出 |
| 状态卡 | .md block / 对话块 | 当前 Step、entry_mode、route_mode、输入依据、证据风险、下一步推荐 |

> 其中 `style_profile.json`、`writing_blueprints.json`、`writing_rationale_matrix.json` 是 Step 7 机器工件；对应 `.md` 是展示层与审阅层。旧项目的 `section_blueprints.json` 仅作兼容输入；若它来自 Step 2，则不得覆盖。
> `retrieval_index_manifest.json`、`retrieval_candidates.json` 是内部加速层工件，只用于“找哪里可能有证据”，不直接进入正文、综述矩阵或审计结论。第一版 `retrieval_candidates.json` 只覆盖文字证据，不并入图表证据子链。
> `figure_index.json`、`figure_evidence_report.md/json` 是图表证据子链工件，用于“图表定位、图注绑定、图表 claim 确认”，不替代文字证据主链。
> 图文联合模式下，正文和图表必须共用同一份 `argument_plan`；没有 MinerU ZIP 但本地 PDF 可读时，允许用 PyMuPDF 直接抽取 `pdf_direct` 候选图，但必须标记为低置信、无 caption、待人工确认；不得据此自动写“图中可见”“证明”等强视觉判断。若 PDF 也不可读，才只保留正文图位占位或降级为 `figure_mode=skip`。`post_write` 与 `auto_insert` 只是执行顺序不同，证据链要求相同。
> 对 Zotero 集合驱动的 full-document / chapter-only / continue-existing 写作，图文资产可用时必须在正文生成前或当前章节完成前产出 `figure_index.json` 与 `figure_evidence_report.md/json`；若没有产出，必须显式记录 `figure_mode=post_write` 或 `figure_mode=skip` 及理由。
> **有 MinerU ZIP 时的 post_write 限制：** `post_write` 只表示“正式图片插入可后置”，不表示可以交付纯文字稿。只要 `figure_asset_check.md/json` 显示存在 MinerU ZIP、`figure_index.json` 或本地图片候选，Step 7 完成前至少必须产出 `figure_index.json`，并在正文保留可解析图位标记，如 `[[FIGURE:wall_thinning_distribution|source=99QWSQ5K|status=post_write]]`。否则不得宣称 Step 7 完成。
> **图文并茂完成门：** 用户要求“撰写论文 / 期刊论文 / 完整论文 / 章节论文 / 重写论文”且输入来自 Zotero 集合、PDF 目录或 evidence_pack 时，默认交付不能只有纯文字。最小图文交付必须满足三者之一：`figures/` 相对路径图片已插入正文；正文保留可解析图位标记并生成 `figure_index.json` + `figure_evidence_report.md/json`；或 `draft_risk_summary.md` 明确记录 `figure_mode=skip`、已检查资产范围、不可插图原因和后续补图动作。没有这三者之一，不得宣称 Step 7 写作完成。
> 兼容旧表述：正文保留可解析图位标记并生成 `figure_evidence_report.md/json` 仍不够；当图文资产存在时，还必须同时生成 `figure_index.json`。
> **安装/使用 skill 的默认预期：** more-paper 写作入口默认是图文稿，而不是 text-only。只有用户明确说“纯文字稿 / 不要插图 / 先不插图”，或所有 PDF/附件/图文资产检查后确实不可用，才允许纯文字降级；降级必须可审计。

**正文引文格式完成门：**

Step 7 正文不得把 Zotero item key 当作最终引文。`99QWSQ5K（已读全文）`、`F98GDZSB（已读全文）` 这类写法只允许出现在证据矩阵、审计表或内部工件中，不允许作为 `论文初稿.md`、`journal_paper_draft.md`、指定章节草稿的正文引文。

正文必须采用下列一种格式，并在参考文献草表中保持可对应：

- 编号制：`[1]（已读全文）`、`[2]（已读摘要）`
- 作者-年份制：`Fang 等（2021）（已读全文）`、`易杰和董菲菲（2025）（已读全文）`

若仍残留裸 Zotero key、key + 阅读深度标签、或正文引用无法对应参考文献表，Step 7 不得宣称完成；应先转换引文格式，再运行 `scripts/validate_step7_output.py`。

**正文前硬门控：**

任何 `full-document / chapter-only / continue-existing` 写作，尤其是“撰写论文 / 写章节 / 基于 Zotero 集合写作 / 基于 PDF 证据包写作”，正文生成前必须先产出 `step7_execution_card.md`。模板见 `references/templates/step7_execution_card.md`。该卡不是展示性说明，而是 Step 7 的运行闸门，至少包含：

- `writing_scope`
- `target_genre`
- `writing_mode`
- `evidence_entry_mode`
- `zotero_collection` 或 `evidence_pack`
- `mechanism_trigger_decision`
- `figure_mode`
- `required_artifacts`
- `allowed_claim_strength`
- `blocked_until`

若 `step7_execution_card.md` 缺失，Agent 不得直接生成 `论文初稿.md`、`journal_paper_draft.md` 或指定章节正文；只能输出执行卡、证据映射、缺口清单或向用户确认必要边界。

以下情况命中任一项时，Step 7 不得宣称完成：

- 只有正文草稿，没有 `step7_execution_card.md`
- 没有证据矩阵、`deep_read_cards` 或等价 evidence mapping
- 没有 `citation_audit.md` / `引用审计报告.md` / `claim_evidence_audit.md`
- 正文仍残留 Zotero key 作为引文，或缺少 `[n]（已读全文）` / `作者（年份）（已读全文）` 这类可投稿草稿引文格式
- Zotero/PDF/evidence_pack 写作缺少 `figure_asset_check.md`，且 `draft_risk_summary.md` 未记录 `figure_mode`
- `figure_asset_check` 显示存在 MinerU ZIP / `figure_index` / 本地图候选，但缺少 `figure_index.json` 或正文缺少可解析图位标记
- 机理类任务缺少 `mechanism_trigger_decision`；若进入 `mechanism_analysis`，缺少 `mechanism_cards`、`mechanism_argument_plan` 或 `mechanism_claim_audit`

Agent 应在交付前运行或等价执行：

```bash
python3 scripts/validate_step7_output.py <step7-output-dir>
```

该脚本只校验工件链和关键字段，不评价文章质量；失败时应补齐缺失工件，而不是把失败解释为“用户未要求”。

**DOCX 导出时机：**

Step 7 默认先完成 Markdown 主稿和配套证据工件；当前写作范围完成后，才提示用户是否导出 DOCX。除非用户明确要求“边写边给 Word”或“每章给导师看”，否则不得在每个写作增量后自动导出 DOCX。导出时使用 `scripts/md_to_docx.py`，并确保正文图片引用的是项目内 `figures/` 的相对路径。若开启 `auto_insert_figures=true`，则导出前必须完成图文绑定和 `figure_evidence_report` 生成。

---

## 执行流程 (Execution Flow)

### 前置输入

写作开始前，确认以上所有前置输入文件可访问。Step 7 支持两种入口：

| 入口 | 适用场景 | 必要条件 | 处理方式 |
|------|----------|----------|----------|
| Step 6 产物入口 | 已按本工作流完成 Zotero 架构、对照和附件池 | `文献-Zotero架构对照.json`、Zotero 条目、PDF 附件 | 直接按 JSON 映射读取证据 |
| Zotero 直接入口 | 用户已有 Zotero 文库，未生成本工作流的附件池索引 | Zotero 集合/条目可读，核心条目有 PDF/笔记/标注 | 通过 Zotero MCP 动态读取条目、附件、笔记和全文，并生成最小映射 |

**缺少 `pdf-附件池索引.json` 时：**
1. 不阻塞写作。
2. 先用 Zotero MCP 读取目标集合或用户指定条目的 children/attachments。
3. 能获取本地路径时，动态写入或刷新 `pdf-附件池索引.json`。
4. 不能获取本地路径但能通过 `zotero_get_item_fulltext` 读到全文时，仍可生成综述矩阵和写作证据，但审计报告中标记 `pdf_path_unavailable`。
5. 如果条目既无附件、又无笔记/标注/全文，但有完整摘要和可靠元数据，则可作为“摘要级证据”；如果连摘要也缺失，则只能作为“元数据候选”。

**Step 7 的功能边界：**

Step 7 是写作生产层。它可以在正文生成过程中完成基础可读性整形，但不承担成稿级润色。用户不需要感知内部拆层；对用户仍然只表现为“写作、续写、写综述、审稿前自检”等任务。

| 子步骤 | 核心功能 | 主要输入 | 主要输出 |
|--------|----------|----------|----------|
| 7.1 | 入口判定 | 用户任务、已有材料、目标体裁 | `target_genre` + `writing_mode` + `writing_axes` |
| 7.2 | 生成文献证据矩阵 | Zotero 条目/笔记/标注、PDF 附件、对照 JSON | `综述矩阵.csv/.md` |
| 7.3 | 学习目标体裁/文档风格并生成统一写作工件 | 目标样本文献/学位论文规范/已有草稿、Step 2 大纲、综述矩阵 | `style_profile.md/json` + `writing_blueprints.md/json` + `writing_rationale_matrix.md/json` |
| 7.4 | 写作反模式闸门 | 已有草稿、写作蓝图、证据矩阵 | 反模式风险与回退要求 |
| 7.5 | 论文类型、目标体裁与语言识别 | 研究主题、大纲、投稿/毕业/课程目标 | paper_type + target_genre + language |
| 7.6 | 写作范围识别 | 写作范围、已有草稿、用户任务 | full-document / chapter-only / continue-existing / abstract-only / review-only / revision-only |
| 7.7 | 写作模式、语言规则与章节级论证计划 | `section_blueprints`、综述矩阵、已有草稿、章节范围 | `argument_plan.md/json` |
| 7.8 | 内部写作流水线 | `argument_plan`、章节蓝图、证据矩阵 | 可读性整形后的正文单元 |
| 7.9 | 章节级写作提示 | 大纲、矩阵、风格画像、已有草稿 | `论文初稿.md/.docx` 或指定章节草稿 |
| 7.10 | 实时引文支撑 | 已入库 Zotero 文献为主，新文献走回流闭环 | 段落引用匹配报告 |
| 7.11 | 防幻觉机制 | 引用、证据等级、JSON 追溯 | 引用安全规则 |
| 7.12 | 同行评审仿真与修稿闭环 | 初稿、矩阵、风格画像、审稿意见 | `评审报告.md` + `rebuttal-预演.md` + `revision_roadmap.md` |
| 7.13 | `revision-only` 修订执行 | 已有草稿、审稿意见、证据状态和写作蓝图 | 修订后正文 + 修订日志 |
| 7.14 | 复评 | `评审报告.md`、`revision_roadmap.md`、修订后正文、`引用审计报告.md` | `rereview_report.md` |
| 7.15 | 图表意图、生成与证据约束 | 初稿、数据/图文资产、图表意图、MinerU ZIP / `deep_read_cards` | `figures/` + `figure_index.json` + `figure_evidence_report.md/json` |
| 7.15.1 | 图文联合插图 | 初稿、图文资产、图表意图、MinerU ZIP / `deep_read_cards` | 带引出句的正文段落；执行 `scripts/resolve_figure_refs.py` 解析标记 |
| 7.16 | 写后引用审计 | 初稿、Zotero 条目、PDF/笔记/标注证据 | `引用审计报告.md` |
| 7.16.1 | 写作质量与审稿缺陷审计 | 初稿、argument_plan、图表/证据审计结果 | `scientific_writing_quality_audit.*`、`engineering_claim_audit.*`、`reviewer_defect_report.md` |

### 7.1. 入口判定：target_genre、writing_mode 与 writing_axes

Step 7 进入正文前，必须先明确三件事：

1. `target_genre` 是什么：
   - `thesis`
   - `journal`
   - `review`
   - `report`
   - `proposal`
   - `conference`
2. `writing_mode` 是什么：
   - `full-document`
   - `chapter-only`
   - `continue-existing`
   - `abstract-only`
   - `review-only`
   - `revision-only`
   - `pre-review`
3. `writing_axes` 是什么：
   - `paper_type`：`research / methods / hypothesis / algorithmic / review`
   - `section_role`：`context / gap / approach / result / comparison / mechanism / implication / limitation`
   - `language_mode`：`zh / en / zh-to-en / bilingual`
   - `style_target`：`thesis / journal / report / proposal / conference / generic`，也可记录明确目标期刊或范文风格

默认原则：

- `target_genre` 决定默认结构深度和语气，不由期刊 prestige 反向主导。
- `writing_mode` 决定本轮输出范围，不因“能写更多”而擅自扩写。
- `writing_axes` 只用于当前小节的写作路由和段落任务判定，不替代 `target_genre / writing_mode / evidence_entry_mode`，也不新增用户可见模式。
- `style_target` 可以借鉴 Nature / Nature Communications 等范文风格，但不得把 Nature 风格设为默认目标；没有明确投稿目标时，优先服从 `target_genre` 和用户已有文本风格。
- 未确认 `target_genre` 时，默认按用户当前任务选择最稳妥的通用体裁：
  - 学位任务 -> `thesis`
  - 投稿任务 -> `journal`
  - 综述任务 -> `review`
  - 工程交付 -> `report`
  - 开题/计划 -> `proposal`

`writing_axes` 的判定应尽量来自用户任务、Step 2 大纲、`section_blueprints`、已有草稿和证据矩阵；若无法判定，只记录 `unknown` 并继续按保守写作边界执行，不得为了补齐轴值而编造研究类型、目标期刊或章节功能。

#### 7.1.1. 默认输出顺序

Step 7 的默认输出顺序固定为：

1. 章节蓝图或小节写作计划
2. 证据矩阵或深读卡片
3. 正文草稿
4. 自检清单
5. claim / evidence 对照

如果用户只要求章节蓝图，就停止在第 1 步；如果用户只要求续写或改写正文，也必须在正文前给出最小蓝图或证据边界说明。

### 7.2. 生成文献证据矩阵（写作前证据组织）

**13 列矩阵：** 作者年份 | 标题 | 研究问题 | 理论/概念 | 数据/样本 | 方法 | 核心发现 | 贡献 | 局限 | 与我的主题关系 | 可引用摘录 | 我的笔记 | DOI/URL

**写作顺序要求：**

1. 先从 Step 2 不可变 `section_blueprints.json` 派生 `writing_blueprints.json/md`，再写正文；direct-entry 没有 Step 2 基线时直接生成带 `source_lineage` 的写作蓝图。
2. `writing_blueprints` 先定义每节的 `section_function / expected_length / key_claims / evidence_needed / do_not_write / transition_from / transition_to / risk_flags`，并保留上游 `rq_ids`。
3. 任何正文单元都必须先回到对应蓝图，不得跳过蓝图直接生成成段正文。
4. 证据矩阵的职责是锁定可写范围，不是把候选材料自动升级成强 claim。

**兼容性说明：** `full-document / review-only / abstract-only / chapter-only / continue-existing / revision-only` 仍然是本 Step 的公开模式名，不因新增蓝图约束而改变。

**图表证据可选扩展字段：**
- `figure_refs`
- `table_refs`
- `figure_evidence_level`

**输入优先级：**
```
0. 文献-Zotero架构对照.json / Zotero 动态映射     ← 机器主索引：tier/score/collection/zotero_item_key/pdf_path
1. retrieval_candidates.json（如存在）         ← retrieved_candidate 候选清单，必须二次确认
2. Zotero 笔记 (zotero_get_notes)              ← 最高质量人工证据
3. PDF 标注/高亮 (zotero_get_annotations)       ← 精读标注
4. Zotero 元数据 (zotero_get_item_metadata)     ← 标题/作者/DOI/摘要/URL/Extra/source_id
5. PDF 全文 (zotero_get_item_fulltext)          ← 完整原文
6. BibTeX/中文元数据 JSON/摘要                  ← 摘要级证据，只能支撑低风险概括
```

> 不要一上来就读 PDF 全文。优先用 `文献-Zotero架构对照.json` 确定 T1/T2/T3、集合归属、Zotero item key 和 PDF 状态；如存在 `retrieval_candidates.json`，只把它视为 `retrieved_candidate` 候选，不得直接写入正文或矩阵；必须再回到笔记、标注、元数据或 PDF 原文确认。`.md` 只用于人工审阅。

#### 7.2.1. 大纲-集合锁定取证

- Step 7 默认按“大纲片段 -> Zotero 子集合/条目映射”读取证据，不扫整个 Zotero 文库。
- 当本轮任务是 `chapter-only` 或用户明确指定 `1.1 / 1.1.1 / 2.3` 等节号时，只读取当前节号对应的集合、子集合、条目和附件。
- 若 `writing_blueprints.json`（或兼容的 `section_blueprints.json`）、`argument_plan.json`、`文献-Zotero架构对照.json` 同时存在，应先用它们确定当前小节的 `collection / item_key / pdf_path` 范围，再开始读笔记、标注或 PDF。
- 仅当当前小节证据不足以支撑必要论点时，才允许向同章相邻小节映射的集合作有限扩展，并在输出中标记扩展依据。
- 不得因为“文库里还有很多相关文献”就提前读取后续小节集合，更不得把后续节的论证提前写入当前节。
- 如果用户已经给出等价的章节-集合映射，直接使用该映射，不要求回跑 Step 6。

#### 7.2.2. deep_read_refine 章节级深读

`deep_read_refine` 是 Step 7 的内部证据整形子模式，不是新的公开 Step、独立 CLI 或最终稿生成器。它只用于当前章节/小节的 1-5 篇核心文献深读，服务后续章节写作、7.10 实时引文支撑和 7.16 引用审计。

> `1-5 篇核心文献` 是默认起点，不是硬上限。若核心 T1/T2 全文不足以支撑当前章节的必要 claim，Step 7 应触发“扩读”，继续读取同一章节证据范围内的更多全文，而不是把摘要级证据升级为强证据。

**分层全文深读链：**

Step 7 保留并鼓励对核心文献读全文，但全文 PDF/MinerU 不作为常驻写作上下文。核心文献必须先经过以下链路转化为可回查、可审计的证据结构：

1. `metadata-first`：读取题名、摘要、结论、目录、图表线索，用于筛选、章节定位和低风险背景判断。
2. `selective-fulltext`：对关键 claim、方法细节、实验/仿真参数、机制解释、图表/公式/页码做定点全文核验。
3. `deep_read_refine`：对当前小节 1-5 篇核心文献全文深读，产出 `deep_read_cards.json/md`。
4. `argument_plan`：把 `deep_read_cards` 中的 claim、方法、边界、图表证据绑定到章节论证。
5. 正文写作消费 `deep_read_cards + argument_plan + 必要原文回查`；不得直接依赖未压缩、未定位、未标注读取深度的全文堆料。

**触发条件：**
- 当前小节有明确 `section_id / section_title`，且已通过 `大纲-集合锁定取证` 锁定 Zotero 子集合或本地证据包范围。
- 当前小节存在关键 claim、方法细节、实验设置、图表解释或综述矩阵字段需要补强。
- 用户明确要求“深读核心文献”“先学习引用文献再写”，或 7.16 审计发现 `weak-support / not-supported`。

**扩读触发条件：**

当已读核心 T1/T2 文献仍不足时，满足任一条件必须扩读，而不是继续硬写正文：

- `argument_plan` 中存在 `required_evidence` 未满足，或 `rollback_if_missing` 指向 `supplement_pdf_or_fulltext`。
- 7.10 引文支撑或 7.16 引用审计出现 `weak-support / not-supported / cannot-judge`，且该 claim 是本节必要论点。
- 正文草稿中存在强 claim、机制判断、参数句、图表解释或数值比较，但当前支撑文献仍为 `abstract_only / metadata_only`。
- 当前 1-5 篇核心全文只覆盖单一工艺、单一材料或单一指标，无法覆盖本节必须讨论的对比维度，例如材料差异、工艺差异、反例、边界条件或工程适用范围。
- 章节目标升级为投稿稿、学位论文定稿、审稿回应、系统综述或用户明确要求“全文证据更扎实”。
- 读到的全文与 Zotero 摘要、Step 4 `paper_card` 或草稿表述发生冲突，需要更多全文判别。

**扩读顺序：**

1. 先扩读当前小节同一 Zotero 子集合或同一 `section_id` 下的 T1/T2 全文。
2. 若仍缺少必要证据，再读取同章相邻小节中 `content_fit=direct` 或 `evidence_role` 明确匹配当前 claim 的 T1/T2。
3. 若问题需要反例、方法参照、工程边界或参数对照，可扩读 T3；T3 进入正文时必须标明用途，不得默认升级为主证据。
4. 若集合内全文仍不足，输出 `evidence_gap_list.md`，并建议回退 Step 4/5/6 补检索、补下载或补 Zotero 附件。

**扩读边界：**

- 扩读只服务当前章节/小节的证据缺口，不得因为“相关文献很多”全库批读。
- 每次扩读后必须更新 `reading_depth`、`source_trace`、`usable_for / not_usable_for` 和扩读原因。
- 如果扩读后仍不能支撑强 claim，应降级措辞或保留 `[待补证据: claim]`，不得把更多摘要堆叠当作全文证据。

**文本读取优先级：**
`zotero_mineru > zotero_fulltext > zotero_note/annotation > PyMuPDF/pdfplumber > abstract_only`

**图片读取优先级：**
`MinerU ZIP / Zotero 图文资产 > 主抽图 > preview fallback`

**输出边界：**
- 只生成或更新 `deep_read_cards.json/md`、`evidence_gap_list.md` 和必要的 `figure_index.json` 候选项。
- 推荐执行入口：`python3 scripts/build_deep_read_cards.py --mapping-json 文献-Zotero架构对照.json --section-id <当前节号>`
- 每张卡片至少记录 `claim_summary`、`method_summary`、`experiment_summary`、`mechanism_hints`、`usable_for`、`not_usable_for`、`reading_depth`、`source_trace`。
- 图表只进入候选清单；是否可支撑正文 claim 仍由 `figure_evidence_report.md/json` 确认。
- `deep_read_refine` 结果不得直接越过 `reading_depth` 规则写入强 claim；`abstract_only` 只能做背景、候选或待补全文提示。

#### 7.2.3. mechanism_analysis 机理分析预处理

`mechanism_analysis` 是 Step 7 的内部写作准备层，不是新的公开 Step，也不是新的用户模式。每次进入正文写作、续写或图文联合写作前，都必须记录 `mechanism_trigger_decision`。

详细触发词、两段式确认规则、字段表、执行命令、Zotero 附件防误判规则、机制判别规则和领域增强规则以 `references/mechanism-analysis-writing-contract.md` 为唯一真相源。执行时按需读取该 reference；Step 7 主文件只保留运行边界：

- 命中机制增强条件时，正文生成前必须先产出或刷新 `mechanism_cards.json/md`、`mechanism_argument_plan.json/md` 和 `mechanism_claim_audit.json`（对应展示层 `mechanism_claim_audit.json/md`）。
- 若跳过机制分析，必须在 `mechanism_trigger_decision.reason` 中写明防误触发依据。
- 机理强 claim 必须有全文级证据和边界条件；摘要/元数据只能用于背景或待精读提示。
- 机制分析可读取图表候选和 MinerU/PDF 资产，但无锚点时不得写强视觉判断。
- 降级项必须写入 `evidence_gap_list.md` 或在正文中降强度后，才允许进入 Step 8。

#### 7.2.4. PDF 读取模式

Step 7 默认遵循 `references/pdf-processing-policy.md`，固定使用以下三档模式：

- `metadata-first`
  只读 `文献-Zotero架构对照.json`、Zotero notes、annotations、metadata、BibTeX/中文元数据/摘要。适用于章节规划、背景性综述、候选文献筛选和低风险概括。
- `selective-fulltext`
  当关键 claim、方法细节、参数、实验设置、页码、图注、表格或公式需要原文确认时，定点读取单篇 PDF、页段或小节；必要时可先提取为带锚点的 `clean.md/chunks.json`。
- `batch-fulltext`
  只用于综述批读、章节预研或用户明确要求的批量全文处理，不作为所有写作任务的默认起点。

#### 7.2.5. 从元数据层升级到全文层的触发条件

满足任一条件即可从 `metadata-first` 升级到 `selective-fulltext` 或 `batch-fulltext`：

- 需要支撑关键结论、强 claim、机制判断
- 需要核对实验参数、方法步骤、训练细节
- 需要核对页码、原句、图注、表格、公式
- 当前只有 metadata / abstract / notes，无法支撑判断
- 正在执行 7.16 引用审计
- 用户明确要求全文预读、批量综述或章节级证据整理
- 已读核心 T1/T2 全文仍不足以支撑当前章节必要 claim，需要按 `deep_read_refine` 的扩读触发条件补读更多全文

若只是主题归类、研究脉络说明、低风险综述句或候选定位，不应默认升级到全文层。

#### 7.2.6. 全文提取结果的使用约束

若使用 `scripts/prepare_pdf_for_llm.py` 或其他等价方式提取 PDF 文本，产物至少应保留：

- `paper_title`
- `citekey`
- `zotero_item_key`
- `source_pdf`
- `pages`
- `section`
- `chunk_id`
- `evidence_level`
- `must_check_pdf`

推荐 `evidence_level`：

- `metadata_only`
- `notes_or_abstract_supported`
- `pdf_fulltext_supported`

提取文本是模型工作输入，不替代原 PDF 的最终真值地位。

**纳入范围：**
- T1/T2/T3 均进入综述矩阵。T1/T2 是写作主证据，T3 作为背景、补充、反例或方法参照。
- T4 已在 Step 4 剔除，默认不进入 Step 7；如用户要求补充，只能作为“候选补查文献”，不得直接引用。
- 中文文献必须保留中文标题、作者、来源、年份、source/source_id、article_url；无真实 DOI 时不得用 `cnki.xxx` / `wanfang.xxx` 冒充 DOI。
- 写作优先使用 `VERIFIED` / `VERIFIED_LOCAL` 且 Tier 为 T1/T2 的文献；T3 主要作背景、补充、反例或方法参照。
- `WARN` 文献只能用于背景性描述、研究脉络或待补查线索，不能支撑关键结论、实验参数、性能提升、机制证明或强因果判断。
- `REJECT` 文献不得进入综述矩阵、正文引用或 Zotero 写入计划；若用户要求保留，只能放入“补查候选/异常清单”。
- `retrieved_candidate` 只是“可能相关”，不得直接升级为 `VERIFIED` / `VERIFIED_LOCAL`，也不得直接写入矩阵或正文。
- 若文献包含关键图表或表格，应把图号、页码、图注/表题先写入 `figure_index.json`，再决定是否进入图表证据子链。

**仅有元数据/完整摘要的条目用途：**

| 证据状态 | 可用于 | 不可用于 | 引用强度 |
|----------|--------|----------|----------|
| 完整元数据 + 完整摘要，无 PDF | 综述矩阵的研究问题/方法概述/主题归类/背景句/待精读优先级 | 具体数据、实验参数、模型细节、强结论、页码级原文摘录 | Weak/Background |
| 完整元数据，无摘要、无 PDF | 去重、集合归类、检索补全、参考文献候选 | 正文 claim 支撑 | Candidate only |
| 元数据 + Zotero 笔记/标注，无 PDF | 若笔记/标注明确记录原文依据，可支撑对应 claim；同时标记需补 PDF | 超出笔记/标注范围的细节 | Moderate，需补全文 |
| Step 4 `WARN` 文献 | 背景、研究脉络、待补查线索 | 关键结论、强 claim、实验数据、机制证明 | Weak/Background |

> 摘要可以派上用场，但不能被当作全文。它适合判断“这篇文献研究什么、用了什么大类方法、与主题是否相关”，不适合支撑“作者具体发现了多少、参数如何设置、机制如何证明”这类强断言。

#### 7.2.7. 高风险内容回 PDF 规则

以下内容不得仅凭提取文本直接进入最终引用或强结论，必须回到原 PDF 或可核验的 Zotero 原文层确认：

- 公式
- 复杂表格
- 图注
- 页码级直接引语
- appendix 细节
- 数值结果的精确比较

这类内容应显式标记：

- `must_check_pdf: true`
- `risk_flags`: `equation` / `table` / `figure_caption` / `direct_quote` / `appendix_detail`

**缺失值约定：** `未提及`（论文确实未讨论）/ `待补充`（计划后续补全）/ `推断：{内容}`（基于已有信息合理推断）

### 7.3. 目标体裁/文档风格学习与写作蓝图

**核心理念：** paper_type 轴告诉你"写什么类型的论文"，目标体裁/文档风格学习告诉你"这份文本应该按什么规范、结构深度和语言节奏来写"。目标可以是期刊，也可以是学位论文、会议论文、课程论文、开题报告，或用户已有草稿的既有风格。

> 从本版开始，Step 7 明确采用 `target_genre-driven`，而不是默认锁定某个高水平期刊风格。目标期刊仍可作为局部约束，但不应覆盖体裁本身。

> 若要借鉴外部 workflow 的写作质量做法，先按 `references/writing-quality-borrowing-plan.md` 抽取结构、语言和修订模式，再映射进 `style_profile` / `section_blueprints` / `writing_rationale_matrix`；不得把外部句子或默认体裁直接搬进正文。
style_profile / section_blueprints / writing_rationale_matrix 是当前落点。

**目标类型：**

| target_genre | 适用场景 | 风格/结构依据 |
|-------------|----------|---------------|
| `journal` | 目标期刊论文 | 目标期刊近期样文、author guidelines、投稿模板 |
| `thesis` | 硕士/博士学位论文 | 学校论文规范、学院模板、已有章节、大纲结构 |
| `conference` | 会议论文 | 会议模板、页数限制、领域样文 |
| `course-paper` | 课程论文/阶段报告 | 课程要求、教师给定格式、已有材料 |
| `existing-draft`（兼容入口标签） | 已有部分内容，只续写/改写一部分 | 规范化为 `mode=continue-existing|revision-only`，体裁仍从正式 `target_genre` 中选择 |

**写作范围：**
- `full-document`：从大纲开始撰写完整论文。
- `chapter-only`：只撰写一个或多个指定章节，如“绪论”“文献综述”“方法”“讨论”。
- `continue-existing`：在已有草稿基础上续写、补写或局部替换。
- `abstract-only`：只写中文摘要、英文摘要或双边摘要。
- `review-only`：只产出综述章节或综述主体，不扩展为完整论文。
- `revision-only`：不新增主体内容，只根据证据和风格规则修改已有章节，并生成修稿路线图与逐条回应骨架。

**工作流：**
```
Step 7.3.1: 样本盘点      → style_sample_status.md/json (样本来源、数量、缺口、回退策略；辅助元数据)
Step 7.3.2: 风格剖析      → style_profile.md/json         (统一风格画像 schema)
Step 7.3.3: 写作蓝图      → writing_blueprints.md/json    (从 Step 2 基线派生，保留 lineage 与章节功能矩阵字段)
Step 7.3.4: 写作逻辑矩阵  → writing_rationale_matrix.md/json (统一单元级理由 schema)
Step 7.3.5: LaTeX 校验    → latex_check.md（可选）
```

**`style_profile` 最小统一字段：**

| 字段 | 说明 |
|------|------|
| schema_version | schema 版本 |
| target_genre | 目标体裁 |
| target_name | 目标期刊/学位类型/报告名称 |
| sample_source | 样本来源 |
| sample_count | 样本数量 |
| confidence | 画像置信度 |
| structure_rules | 结构规则 |
| language_rules | 语言规则 |
| citation_rules | 引用规则 |
| figure_rules | 图表规则 |
| constraints | 约束 |
| warnings | 风险提醒 |

**`section_blueprints` 最小统一字段：**

| 字段 | 说明 |
|------|------|
| schema_version | schema 版本 |
| section_id | 章节编号 |
| section_title | 章节标题 |
| section_function | 本章功能 |
| key_claims | 核心论点列表 |
| evidence_needed | 证据类型 |
| evidence_basis | 当前可用证据 |
| do_not_write | 本章不该承载的内容 |
| expected_length | 预期长度 |
| figure_needs | 图表/表格需求 |
| transition_from | 承上关系 |
| transition_to | 启下关系 |
| style_notes | 风格约束 |
| risk_flags | 风险标签 |

**`writing_rationale_matrix` 最小统一字段：**

| 字段 | 说明 |
|------|------|
| schema_version | schema 版本 |
| unit_id | 单元编号 |
| parent_section_id | 上级章节编号 |
| unit_name | 单元名称 |
| what_it_does | 该单元做什么 |
| motivation_link | 如何服务总论证 |
| claim_binding | 绑定的 claim |
| evidence_used | 使用的证据 |
| quality_check | 通过条件 |
| risk_notes | 风险备注 |

> `style_sample_status` 是 `style_profile` 的辅助元数据，不再与主 profile 并列成另一套半独立风格工件。`章节功能矩阵` 从本版开始视为 `section_blueprints` 的视图/最小版，不再形成第四套 schema。

### 7.4. 写作反模式闸门

在开始 7.8 正文生成前，必须用 `references/writing-antipatterns.md` 做一次轻量检查。至少排查以下问题：

- 文献堆砌，不形成论证
- 章节功能漂移
- 强 claim，弱证据
- claim_strength 与 required_evidence 不匹配
- 图表 claim 缺 figure/table/panel 绑定
- 机理 claim 缺状态量、竞争机制或验证路径
- 风格目标不明
- 直写正文，不做蓝图

若命中以上问题：

- 轻度问题：继续写，但写入 `draft_risk_summary.md`
- 中度问题：先补 `writing_blueprints.md` 或 `章节功能矩阵`
- 重度问题：回退 Step 2、Step 4 或 Step 6 补结构/补证据

**两种分析深度：**

| 模式 | 范文数 | 时长 | 产出 | 适用场景 |
|------|:---:|------|------|------|
| **Flash** | 3 篇 | ~3 min | `style_profile.md/json` | 初次投稿该期刊 |
| **Pro** | 6 篇 | ~8 min | `style_profile.md/json` + `research_dossier.md` | 核心目标期刊/学位论文/既有草稿 |

```bash
python3 scripts/learn_journal_style.py --target-type journal --target-name "Applied Thermal Engineering" --sample-source zotero --collection "目标期刊样本" --mode flash
python3 scripts/learn_journal_style.py --target-type thesis --target-name "硕士学位论文" --sample-source draft --draft 论文已有草稿.md --mode flash
python3 scripts/generate_section_blueprints.py research_dossier/style_profile.md 大纲关键词.md --evidence 综述矩阵.csv --baseline section_blueprints.json --output research_dossier/
python3 scripts/generate_writing_rationale.py research_dossier/writing_blueprints.md --style-profile research_dossier/style_profile.md --output research_dossier/writing_rationale_matrix.md
```

> 目标样本是“风格学习语料”，不等同于 Step 4 的主题文献库。样本可来自目标期刊近期代表作、学位论文模板、学校格式规范、用户指定 PDF 目录、Zotero 样本集合或已有草稿；不得默认使用 `paper-temp/` 中的全部研究文献作为目标风格样本。

**样本集合命名约定：**

| target_genre | 推荐 Zotero 集合名 | 说明 |
|-------------|--------------------|------|
| `journal` | `目标风格样本 / 期刊-{target_name}` | 目标期刊近期样文、投稿模板、author guidelines |
| `thesis` | `目标风格样本 / 学位论文-{学校或层级}` | 学校模板、学院规范、优秀学位论文、已有章节 |
| `conference` | `目标风格样本 / 会议-{target_name}` | 会议模板、页数限制、领域样文 |
| `course-paper` | `目标风格样本 / 课程论文-{课程名}` | 课程要求、评分 rubrics、已有材料 |
| `existing-draft` | `目标风格样本 / 已有草稿-{项目名}` | 用户草稿、已定稿章节、导师修改稿 |

> 集合名只是推荐约定，不是硬性要求；如果用户直接提供目录、文件或草稿，也可以作为样本源。但 7.3 必须把实际使用的样本写入 `style_sample_status.md/json`。

**样本来源规则：**
1. 优先使用用户指定的样本 PDF、Zotero 集合、学校模板、投稿模板或已有草稿。
2. `journal` 未指定样本时，可从 Step 4/6 中筛选 `publication_title` 与目标期刊一致的近期 T1/T2 文献。
3. `thesis` 未指定样本时，使用学校/学院格式规范和已有章节；没有规范时先生成通用学位论文蓝图并标记待确认。
4. 样本不足时，先报告缺口，再建议补充目标样本；不要把非目标体裁文本混入风格画像。
5. 风格学习只学习结构、语气、引用密度、图表呈现和章节节奏；不得复制句子或段落。

**样本数量与回退策略：**

| 状态 | 样本条件 | 处理方式 | confidence |
|------|----------|----------|------------|
| 充足 | `journal/conference` ≥ 3 篇；`thesis` ≥ 1 个模板/规范 + 1 篇样文或已有章节；`existing-draft` ≥ 1500 字 | 正常生成风格画像和章节蓝图 | high |
| 偏少 | `journal/conference` 1-2 篇；`thesis` 只有模板/规范或只有已有章节；`existing-draft` 500-1500 字 | 生成低样本风格画像，标记缺口，不阻塞写作 | medium |
| 缺失 | 无可用样本，仅有 target_genre / target_name | 使用通用体裁规则 + Step 2 大纲，必须提示用户补样本 | low |

**`style_sample_status.md` 推荐格式：**

```text
标题：目标风格样本状态

target_genre: thesis
target_name: 硕士学位论文
sample_source: existing_draft + university_template
sample_count: 2
confidence: medium

已使用样本
1. 论文已有草稿.md
2. 学校硕士论文模板.docx

缺口
- 缺少优秀学位论文样本
- 缺少学院具体格式细则

回退策略
使用学校模板 + 已有草稿风格 + 通用硕士论文结构规则。
```

**`style_sample_status.json` 最低字段：**

```json
{
  "target_genre": "thesis",
  "target_name": "硕士学位论文",
  "sample_source": ["existing_draft", "university_template"],
  "sample_count": 2,
  "confidence": "medium",
  "samples": [
    {"title": "论文已有草稿.md", "source_type": "draft", "path_or_zotero_key": "论文已有草稿.md"},
    {"title": "学校硕士论文模板.docx", "source_type": "template", "path_or_zotero_key": "学校硕士论文模板.docx"}
  ],
  "gaps": ["缺少优秀学位论文样本", "缺少学院具体格式细则"],
  "fallback_strategy": "使用学校模板 + 已有草稿风格 + 通用硕士论文结构规则"
}
```

### 7.5. 论文类型、目标体裁与语言识别

**轴一：论文类型（paper_type）**

| paper_type | 特征 | 典型章节骨架 |
|------------|------|-------------|
| **research** | 有明确的实验/仿真研究 | intro → related-work → method → experiments → discussion → conclusion |
| **methods** | 侧重方法/工具创新 | intro → problem-statement → design → implementation → validation → comparison |
| **hypothesis** | 先提假设再做实验检验 | background → hypothesis → test-design → results → implications |
| **algorithmic** | 算法/模型为核心贡献 | intro → preliminaries → algorithm → analysis → experiments → related-work |
| **review** | 系统综述/调研 | 8 节文献综述骨架 |

**轴二：语言 / 投稿目标（language）**

| language | 场景 | 引用格式 |
|----------|------|---------|
| **en** | 直接用英文撰写 | IEEE / APA / Nature |
| **zh** | 用中文撰写 | GB/T 7714 |
| **zh-to-en** | 中文草稿→英文成稿 | 按目标体裁/投稿目标 |

**轴三：目标体裁（target_genre）**

| target_genre | 写作重点 |
|-------------|----------|
| **journal** | 问题集中、贡献明确、篇幅紧凑、结果导向 |
| **thesis** | 结构完整、背景充分、方法细节完整、论证链清楚 |
| **conference** | 篇幅受限、贡献和实验结果前置 |
| **course-paper** | 符合课程要求，重视概念解释和规范表达 |
| **existing-draft** | 保持已有章节风格、术语、编号、引用格式一致 |

### 7.6. 写作范围识别

Step 7 在生成正文前，必须先明确本轮输出范围。默认原则：**先锁定写作边界，再决定如何写；不因“能写更多”而擅自扩写。**

| 模式 | 触发场景 | 主输出 |
|------|----------|--------|
| `full-document` | 已有清晰大纲和文献，直接逐章完整撰写 | 全文初稿 |
| `review-only` | 只产出综述章节或综述主体 | 综述章节 |
| `abstract-only` | 只写摘要 | 摘要 |
| `chapter-only` | 只写一个或多个指定章节 | 指定章节草稿 |
| `continue-existing` | 在已有草稿基础上补写、续写、局部改写 | 修订章节草稿 |
| `revision-only` | 已有审稿意见，只做针对性修订 | 修订后正文 + 修稿记录 |

**已有草稿处理规则：**
- 先识别已有草稿的标题层级、术语、引用格式、语气和章节编号。
- 新写内容必须与已有内容保持结构和语言一致，除非用户明确要求重构。
- 只写部分章节时，不擅自改动其他章节；只在必要处提出“需前后文同步”的提示。
- 如果已有草稿中的引用缺证据，标记为 `needs_evidence_audit`，不要默认删除。

### 7.7. 写作模式、语言规则与章节级论证计划

Step 7 在正文生成前，必须先确定本轮写作模式，并为目标章节生成最小论证计划。核心原则：**先锁定 claim、证据、图表与风险边界，再进入正文写作。**

#### 7.7.1. `abstract-only` 子类型

| 子类型 | 适用场景 | 约束 |
|--------|----------|------|
| `journal-abstract` | 投稿前摘要 | 更紧凑，更结果导向，背景压缩 |
| `thesis-abstract` | 学位论文摘要 | 背景更完整，方法与贡献展开更充分 |
| `bilingual-abstract` | 中英双语摘要 | 中英独立撰写，不做机械直译 |

若用户只说“写摘要”，默认按当前 `target_genre` 推断：`journal` → `journal-abstract`，`thesis` → `thesis-abstract`；若明确要求中英双语，则使用 `bilingual-abstract`。

#### 7.7.2. 语言差异化规则

**zh-to-en 特殊规则（中国研究者最常用场景）：**
1. 术语锁定：写作开始前先列出"中→英关键术语对照表"
2. 中文笔记→英文翻译四步法（提取论点→按英文逻辑重排序→英文撰写→检查翻译腔）
3. 识别中文写作特有的"英文不该有"的模式
4. 中文数字和单位的英文转换

#### 7.7.3. 章节级论证计划

**目的：** 在 `7.3` 风格工件与 `7.8` 正文生成之间，先锁定每个目标章节的核心 claim、所需证据、图表约束和弱点边界，避免写到一半才发现证据不够。

**适用范围：**
- `chapter-only`
- `continue-existing`
- `revision-only`
- `full-document` 中证据风险高的章节

**标准输出：**
- `argument_plan.md`
- `argument_plan.json`

**`argument_plan` 最小字段：**

| 字段 | 说明 |
|------|------|
| `section_id` | 目标章节编号 |
| `writing_axes` | 当前小节的 `paper_type / section_role / language_mode / style_target` 判定结果 |
| `one_sentence_argument` | 一句话论证：围绕什么问题、用什么方法/证据、得到什么有限结论、边界在哪里 |
| `paragraph_job_map` | 段落任务图；每段只标一个主任务，如 `context / gap / approach / result / comparison / mechanism / implication / limitation` |
| `core_claim` | 本节主论点 |
| `required_evidence` | 本节必须具备的核心证据 |
| `allowed_evidence_level` | 允许使用的证据等级上限/下限 |
| `must_have_figure` | 是否必须包含图表 |
| `weak_points` | 当前最可能失守的论证点 |
| `rollback_if_missing` | 缺关键证据时回退到哪个 Step |
| `mechanism_path` | 机理章节的现象、变量链、模型/方程、边界条件和验证路径 |

**一句话论证模板：**

> 围绕 `[工程/科学问题]`，本节通过 `[方法/模型/实验/仿真/文献证据]` 说明 `[核心结论]`，其证据来自 `[已确认来源]`，适用边界为 `[对象/工况/材料/数据范围/证据等级]`。

若 `one_sentence_argument` 不能写清 `claim / evidence / boundary`，本节不得直接进入完整正文生成，只能输出论证草案、缺口和回退目标。

**论证对话与章节权重：**

- `三步对话公式`：核心文献不能只当引用装饰，必须尽量写清 `他说A -> 我说非A/A+ -> 所以C`；若当前证据只够重述文献，就降级为背景引用。
- `核心/支撑/补充` 分层：核心段落直接服务 `one_sentence_argument`，支撑段落提供机制、边界或对比，补充段落只作背景或脚注式说明。
- `章节权重` 必须进入 `paragraph_job_map`：不能让每个子主题获得相同篇幅，不能把不推进主论证的候选内容独立成节。
- `什么可以不写` 必须进入 `do_not_write` 或 `rollback_if_missing`，避免完备性偏执把候选池误写成正文。
- `最小对比` 用于写作前确认：至少说明一个 claim 为什么可写、一个相邻 claim 为什么必须降级或等待证据。
- 对话式论证不得越过证据边界；没有全文、笔记、标注或用户可核验证据时，只能保守表达或输出待补证据。

**`argument_plan` 证据确认区块（本版新增）：**

| 字段 | 说明 |
|------|------|
| `confirmed_evidence` | 已通过 note / annotation / 元数据 / PDF 原文确认的证据 |
| `unresolved_evidence` | 候选命中失败或原文确认失败的证据缺口 |
| `candidate_evidence_used` | 本轮候选定位曾触及的候选片段摘要 |
| `confirmation_status` | `confirmed / partially_confirmed / unconfirmed_requires_rollback` |
| `rollback_if_unconfirmed` | 仍未确认时的动作：`supplement_note_or_annotation / supplement_pdf_or_fulltext / downgrade_claim / rollback_to_step_4_or_6` |

**执行规则：**
1. `chapter-only` 和 `continue-existing` 默认先生成 `argument_plan`，再允许写正文。
2. 若关键证据缺失，不直接硬写正文；在 `argument_plan` 中输出 `rollback_if_missing`。
3. `revision-only` 需要把审稿意见中的问题映射到对应章节的 `argument_plan`，避免只改字面表达。
4. 若启用候选召回，必须把候选先写入 `retrieval_candidates.json`，再回到原文确认；不能把召回分数当作证据等级。
5. 对依赖图表支撑的章节，可新增：
   - `figure_role`
   - `figure_claim_binding`
   若缺少必要图/表，`rollback_if_missing` 可直接触发。
6. `argument_plan` 之后才能进入 7.8 正文流水线；没有 `argument_plan` 的直写正文视为未完成前置证据组织。
   argument_plan 之后才能进入 7.8 正文流水线。

**写作质量约束：**

- 每个章节/小节必须给出 `section_function`，只写这一节要完成的单一职责。
- 每个章节/小节必须给出 `key_claims` 和 `evidence_needed`，并显式写出证据等级上限。
- 每个章节/小节必须给出 `do_not_write`，列出本节不应混入的内容。
- 每个章节/小节必须给出 `transition_from / transition_to`，让正文能自然接上前后文。
- 每个章节/小节必须给出 `risk_flags`，把证据弱点先暴露出来。
- 证据不足时优先产出低风险结构稿或 `[待补证据: claim]`，不写强 claim。

**确认门（claim / evidence / boundary 不清时）：**

- 当 `core_claim`、`required_evidence` 或 `boundary` 任一项不清楚时，先输出 `one_sentence_argument`、`paragraph_job_map`、关键假设和 `unresolved_evidence`，停止完整正文生成。
- 只有当用户确认，或证据链足以把 `confirmation_status` 提升到 `confirmed / partially_confirmed` 且强 claim 已降级到可支撑范围，才允许继续写正文。
- 若用户要求继续但证据仍不足，只能写低风险结构稿、背景段或 `[待补证据: claim]`，不得把未确认内容写成确定性结论。
- 若只是短段落、摘要级低风险背景或用户已明确给出 claim、证据和边界，可跳过确认门，但必须在输出中保留一句话论证和证据等级。

#### 7.7.4. 小节粒度与展开边界

- 每次只写一个当前请求的小节；未被请求的小节只允许作为边界提示存在，不得提前展开正文。
- 不提前展开后续小节；未被请求的小节只允许作为边界提示存在。
- 例如用户要求写 `1.1.1`，则本轮只回答 `1.1.1` 的核心问题，不提前写 `1.1.2`、`1.1.3` 的问题全貌、结论或技术价值。
- 当前小节内部应保持问题推进式叙述：围绕本节问题逐段推进，不使用模板化“先总后分再综上”的机械骨架充数。
- `chapter-only` 若一次包含多个相邻小节，也必须按小节顺序逐个完成，并在每个小节结束处停住，不把下一小节内容并段合写。
- 如果用户没有明确写作粒度，优先追随最小已命名单元：有节号按节号，有标题按标题，没有则按本轮最小章节任务生成一个小节。

#### 7.7.5. 小节级证据完成门

每个章节/小节写作完成前，必须完成最小证据闭环：

- 每条强 claim 必须绑定 `reading_depth=full_text / pdf_verified / zotero_note`。
- 每条强 claim 必须有 `source_trace`，至少包含 PDF 路径或 Zotero item、页码/chunk/section、证据等级。
- 摘要级文献只能写背景、问题定义、研究趋势，不能支撑实验结果、参数、机制判断或效果比较。
- 若证据不足，输出 `[待补证据: claim]` 或写入 `evidence_gap_list.md`，不得硬写。
- PDF-only 入口下，`source_trace` 必须优先落到 `source_pdf + pages/chunk_id/section`；缺页码或 chunk 时只能进入 `must_check_pdf=true` 的候选状态。

#### 7.7.6. 学位论文深度下限

- `target_genre=thesis` 时，默认按博士论文深度组织当前小节，不得写成短综述、资料堆叠或提纲式背景。
- 每个背景/综述型小节通常应完成至少以下递进中的大部分：`工程场景 -> 需求来源 -> 机理约束 -> 制造约束 -> 研究必要性`。
- 若当前小节属于方法、实验或结果章节，则应替换为同等深度的论证链，而不是简单照搬背景型骨架。
- 篇幅由论证充分度决定，不追求机械字数；但只要用户要求的是博士论文章节，就不能用 1-2 段浅层概述草率收束。
- 若现有证据只够写“概况”，必须显式输出证据缺口，而不是用空泛套话把深度伪装出来。
- `target_genre=thesis` 时，默认采用“判定句优先、解释句收束”的章节语言风格：先给机制判断，再补证据与边界，不以口语化解释推进段落。
- 学位论文机理章节应减少“如果说……那么……”“换言之”“这个判断也说明了”等解释腔连接句，优先使用“据此可判定”“由此表明”“进一步可归结为”“需要指出的是”等书面学术连接句。
- 博士目标必须按 `references/doctoral-dissertation-writing-contract.md` 建立 `doctoral_thesis_map.json`，并对每章执行 `prepare -> write -> close -> incremental audit`：写前冻结中心问题、RQ、本章职责及后章预留内容，写后经抢写/重复/结果/RQ/贡献/过渡冲突检查再原子回写。direct-entry 可用 `provisional` 快照且不补跑 Step 1-6；只有 `evidence_closed / ready_for_step8` 才要求当前稿件通过 `doctoral_ready`。贡献、因果、方法、局限和实践含义必须记录作者确认，不得由 Agent 代填。

#### 7.7.7. 机理章节论证层

当 `section_title`、用户任务或 `section_blueprints` 命中机理类触发词时，正文生成前必须先完成 `mechanism_trigger_decision`。若决定进入 `mechanism_analysis`，必须把 `deep_read_cards` 中的 `mechanism_hints` 整理为 `mechanism_argument_plan`，并以 `mechanism_claim_audit` 约束正文 claim 强度。

**段落组织规则：**
- 每个机理段落按 `现象 -> 状态量/控制量 -> 作用路径 -> 证据锚点 -> 适用边界 -> 回扣本节问题` 推进。
- 不得用“已有研究表明”替代变量传导解释；引用只能支撑链条中的具体环节。
- 没有模型、方程或图表时，可以写定性机制，但必须说明证据边界。
- 没有实验、仿真或对比验证时，不得把相关性写成因果证明。
- 机理段落应优先使用“机制判别句 -> 图文/全文证据 -> 边界句 -> 收束句”的结构，避免整段停留在解释腔。
- 禁止把“图的价值不在于……而在于……”“这一点使……可以被明确区分”这类元评论式说明写得过密；此类句子每段至多 1 处，且必须服务于机制判别。
- 学位论文风格下，正文应减少“这说明”“这意味着”“也就是说”连续堆叠，避免口语化解释链主导段落节奏。

**回退规则：**
- 缺 `causal_chain`：回到 `deep_read_refine` 补全文或笔记。
- 缺 `boundary_conditions`：降级为候选解释，并输出需补工况/假设。
- 缺 `validation_path`：只写理论解释，不写“证明/验证”类措辞。
- 缺 `evidence_anchor`：不得写图表、方程、参数或数值级结论。

#### 7.7.8. 章节级候选证据层（弱 RAG，按章节确认）

本层放在 `argument_plan` 之后、正文生成之前；它不是独立 Step，而是 Step 7 的内部证据前移层。

**定位：**
- 只负责“找哪里可能有证据”
- 不负责确认是否构成正文证据
- 候选召回粒度按 claim 生成，确认粒度按章节推进

**固定流程：**
1. 从 `argument_plan` 读取章节 claim 与 `required_evidence`
2. 针对每个 claim 生成候选片段，写入 `retrieval_candidates.json`
3. 按章节统一回到 Zotero note / annotation / 元数据 / PDF 原文确认
4. 将确认结果直接回写 `argument_plan`
5. 只有 `confirmation_status` 满足要求的 claim，才允许进入正文生成或 `revision-only` 正文修改

**`retrieval_candidates.json` 第一版组织方式：**
- `chapter_id`
- `chapter_title`
- `claim_id`
- `claim_text`
- `evidence_question_id`
- `query_variant`
- `candidate_item_key`
- `candidate_chunk_id`
- `page`
- `source_page_hint`
- `source_type`
- `retrieval_score`
- `match_reason`
- `negative_or_conflicting_evidence`
- `requires_direct_verification`
- `post_verify_status`

**章节级确认规则：**
- 同一章节中，多个 claim 可以共享同一篇文献或相邻 chunk 的确认结果
- 但每条 claim 必须保留独立 `claim_id` 和独立确认状态
- 每个候选问题必须保留 `evidence_question_id`，便于同一 claim 下多轮候选、反证候选和页码线索追踪
- `query_variant` 只记录候选生成的不同提问方式，不代表多版本写作方案
- `negative_or_conflicting_evidence` 用于提示可能反驳或削弱 claim 的材料；它不能被静默忽略，也不能未经确认直接写成反方结论
- `source_page_hint` 只作为回到 note / annotation / PDF 的定位线索，不等同于页码级证据确认
- 候选命中失败或原文确认失败时，必须回写 `unresolved_evidence`，不得静默消失
- `retrieved_candidate` 只能表示“可能相关”，不得直接升级为正文证据

#### 7.7.9. thesis 机理章节风格收紧

当 `target_genre=thesis` 且当前章节进入 `mechanism_analysis` 时，蓝图与正文都应默认按博士论文章节深度组织，而不是按短综述节奏处理。

最低风格约束如下：

- 先给机制判断，再给证据和边界，不把解释腔放在段首
- 每段都要回到“现象 -> 状态量/控制量 -> 作用路径 -> 证据锚点 -> 适用边界 -> 回扣本节问题”
- 必须显式写出主导机制与竞争机制的区分
- 必须保留边界句，不把跨工况或跨材料外推写成默认成立
- 机理段落末尾要收束到本节论点，而不是停留在元评论式解释

这类收紧会同步体现在 `section_blueprints` 的 `section_function`、`evidence_needed`、`do_not_write`、`style_notes` 与 `risk_flags`，并由 `mechanism_analysis` 的后续工件链继续约束正文。

### 7.8. 内部写作流水线（用户不可见）

Step 7 的正文生产按以下内部顺序执行；这是 agent 执行纪律，不是用户可见模式，也不新增入口词。内部实现按六个子合同维护：`blueprint_style / drafting / citation_audit / figure_asset / pre_review / completion_validation`；它们共享同一份 `step7_execution_card.md`、稿件哈希和 run envelope，不得各自产生平行入口或互相覆盖状态；用户仍只看到一个 Step 7。

| 内部阶段 | 职责 | 允许修改 | 禁止越界 |
|----------|------|----------|----------|
| 生成 | 按 `argument_plan`、章节蓝图和证据矩阵写出正文单元 | 生成段落、句子、引用占位、章节过渡 | 不凭空补证据，不扩写未请求章节 |
| 整合 | 把多篇文献、图表、方法和 claim 合成为论证链 | 合并重复论点，调整段内信息顺序，补承上启下句 | 不把文献堆砌伪装成综述，不提高证据等级 |
| 审阅 | 对刚生成的段落做基础可读性整形 | 连贯性、术语统一、过渡句、重复句压缩、轻度机械句清理 | 不做全文终稿 polish，不重排整章结构 |
| 校验 | 检查 claim、引用、证据等级和风险边界 | 标记 `[待补引用]`、`needs_evidence_audit`、`rollback_if_missing` | 不把 WARN/摘要级证据升级为强证据 |

**段内写作质量底线：**

- 每节只承担一个主要功能，不把背景、方法、结果和讨论硬塞进同一节。
- 先写 `one_sentence_argument`，再写段落展开，最后才做语言收口。
- 每节都要显式写 `do_not_write`，防止把跨节内容或候选想法写进去。
- 每节都要保留 `transition_from / transition_to`，避免正文断裂。
- `risk_flags` 不是装饰字段，必须在正文前被处理。

执行要求：

- 每个正文单元完成后，先经过“审阅”和“校验”，再进入下一个单元。
- 内部阶段名不得作为用户选项、命令、按钮或对话模式暴露；对用户只汇报当前写作结果、证据风险和下一步建议。
- 如果校验发现关键证据缺失，优先输出风险和回退目标，而不是用润色语气掩盖证据问题。

#### 7.8.1. 轻量可读性整理

Step 7 可以在正文生成过程中做基础可读性整理，但这类整理只服务“让初稿可继续阅读与修订”，不应预设用户的写作策略、论证风格或表达审美。

允许的整理边界：

- 保持段落基本连贯
- 按 `.skill-state/term_aliases.md` 做最小术语统一
- 删除明显重复或空泛的句子
- 标记需要后续补证据、补引用或回退的问题

不应在本层写成硬规则的内容：

- 段落必须采用何种组织方式
- 某类章节必须遵循何种固定写法
- 具体句式、修辞、语气或“人味”策略

Step 7 的职责是维持 workflow 与证据边界，不替用户决定”正确写法”。成稿级精修、风格收口和终稿修订仍留给 Step 8。

#### 7.8.2. 参考文献图片标记语法（`[图: xxx]`）

写作中需要引用参考文献的图/表时，使用 `[图: 简短描述]` 声明图位，不中断正文去手动翻图库。完整标记规则、示例、解析命令和图片来源优先级见 `references/step7-figure-marker-syntax.md`。

Step 7 主文件只保留执行边界：图位描述必须具体，图前要有引出句，图后要有解释句；未匹配到图时保留占位符并生成警告，不得自动写强视觉判断。

### 7.9. 章节级写作提示

Step 7 可以根据 `section_blueprints`、`argument_plan`、`target_genre` 和现有草稿，为当前章节提供写作提示，但这些提示不构成硬性模板，也不应限制用户的创造性组织方式。

推荐保留的只有两类约束：

- **证据约束**：当前章节的 claim 需要哪些证据、哪些证据仍不足
- **边界约束**：当前章节不应擅自承载哪些未确认内容、未请求扩写内容或高风险强 claim

其余关于章节结构、段落组织、语气偏好、修辞策略的内容，只能作为可选提示，不应写成质量门或完成条件。

#### 7.9.1. 术语对齐检查

- 每章写作前，先从题目、大纲、少量核心 PDF、Zotero 题录和已有草稿中建立术语种子表；种子表只要求覆盖当前章节可写作所需的核心术语，不要求一开始就扫完全部 PDF
- 术语状态分三层：`seed`（初始可用但未完全收口）、`provisional`（暂定术语，后续证据到位再确认）、`locked`（证据足够后全篇统一使用）
- `seed` 和 `provisional` 术语可以先用于写作和证据组织，但必须显式保留状态；`locked` 术语才作为全篇标准（也就是 locked 术语才作为全篇标准）
- 若用户、学科或既有草稿已形成稳定写法，应优先尊重既有写法，再做最小统一
- 术语前移的目标是先建立可写作、可审计的标准，不是强行在第一轮就完备全库术语；后续在更多 PDF、note、annotation 或全文核验到位后再批量收口

> 具体的章节组织方式、常见写法、文体提示与反模式示例，不再留在主协议中，统一放到 `references/writing-modes.md`、`references/writing-antipatterns.md` 与相关参考文档中，按需查阅。

### 7.10. 实时引文支撑

本层只约束“引用必须可追溯到 Zotero / note / annotation / PDF 原文或允许的摘要级证据”，不规定用户必须采用哪种段落级写法、引用密度或叙述节奏。

**`paper_card` claim-source fit 预判：**
- 写作前按章节优先筛选 `evidence_role` 合适、`content_fit` 不为 `mismatch` 的文献；完整字段见 `references/paper-card-contract.md`。
- `paper_card` 只做文献级用途边界，不替代 PDF、Zotero note、annotation 或全文证据确认。
- `content_fit=direct` 可进入关键 claim 候选，但仍需原文/笔记/标注确认。
- `content_fit=adjacent` 只能支撑保守表述，若正文使用“证明/显著优于/最佳”等强动词，需降级为 `weak-support` 或补全文证据。
- `content_fit=background_only` 只能用于背景、领域现状或综述性句子，不得支撑方法细节、实验数值、强因果结论。
- `content_fit=mismatch` 不得作为正文 claim 支撑；只能进入排除说明、反例或待补查清单。
- 正文 claim 超出 `primary_claim` 或 `content_fit_note` 时，引用审计应标记为 `weak-support` 或 `not-supported`。
- 缺少 `paper_card` 不阻塞 Step 7；按现有 Zotero/PDF/证据包规则降级运行，并记录 `paper_card_missing` 风险。

**摘要级引用规则：**
- 只有完整摘要、无 PDF 的条目，可以用于背景性、领域概况性、研究主题归类性引用。
- 引用标记必须记录为 `evidence_level=abstract_only`，7.16 审计时单独列出。
- 不得用摘要级证据支撑具体实验数据、参数、机制解释、效果提升百分比或“证明/证实”类强动词。
- 写作主证据不足时，应回到 Step 5/6 补 PDF 或补全文，而不是提高摘要级证据的强度。

**已读深度标注规则：**
- Step 7 正文中，每个文献引用在作者-年份或编号标记后，必须显式追加已读深度标签：`（已读全文）` / `（已读摘要）` / `（仅元数据）`。
- 推荐写法：`……并通过轴向力和内压辅助弯曲研究其改善路径 [Wang and Agarwal, 2006, （已读全文）]。`
- 标签映射固定如下：
  - `reading_depth=full_text / pdf_verified / zotero_note` -> `（已读全文）`
  - `reading_depth=abstract_only` -> `（已读摘要）`
  - `reading_depth=metadata_only` -> `（仅元数据）`
- 若同一条引文同时依赖多篇文献，每篇文献都应各自标注已读深度，不得合并成一个笼统标签。
- 只允许对“本轮确实已读到的层级”打标，不得把摘要级或元数据级文献冒充为已读全文。
- `（仅元数据）` 文献只能承担题录定位、研究对象归类、候选线索或极弱背景提示，不得承载具体结论。
- `（已读摘要）` 文献只能承担背景概括、研究主题归类、方向性描述；不得承载具体实验结果、参数、机制、图表解释、效果百分比、强因果或“证明/证实/显著优于”等强结论。
- 具体结论、方法细节、实验设置、结果比较、机制判断和强 claim，只能引用 `（已读全文）` 文献；若当前只有摘要或元数据，必须改写为保守表述，或输出 `[待补证据: claim]`。

**新增引用回流规则：**
- 如果现有 Zotero 文库无法支撑某个 claim，不允许现场编造或只凭网页摘要引用。
- 新引用必须走 Step 4/6 小闭环：检索/评分 → 加入 `文献库.bib` 或增量 bib → 补充中文元数据 → PDF 下载/附件池匹配 → Zotero 入库 → 更新 `文献-Zotero架构对照.json` → 再进入 7.10。
- 紧急写作时可在段落中保留 `[待补引用: claim]`，但不得进入最终稿。
- 候选召回命中的片段只能标记为 `retrieved_candidate`；若原文确认失败，必须继续保持回退状态，不得因召回分数高而强行引用。
- `retrieval_candidates.json` 应按章节→claim 组织，便于章节级确认和 `argument_plan` 回写。

**当前试写阶段的引用格式：**
- Step 7 试写阶段默认保持作者-年份格式，并显式标注阅读深度。
- 在单条引文中，推荐形式为：`作者, 年份, （已读全文）`；若有多篇并列支撑，则逐篇并列标注，不合并阅读深度。
- 只有进入整章或全稿定稿阶段，才统一转换为 GB/T 7714 编号格式。

**英文文献与中文场景的联合支撑：**
- 关键论点优先采用“英文基础/国际研究 + 中文工程场景文献”共同支撑。
- 不得长期只依赖中文文献完成关键技术判断；也不得只靠英文通用研究而完全脱离具体航空/工程应用场景。
- 当中文场景文献缺失时，可以先用英文文献搭骨架，但必须把中文场景证据缺口显式写出。

**重要论点的并列支撑：**
- 重要判断默认不只挂 1 篇文献；优先用 2-3 篇文献并列支撑同一关键论点。
- 对承载章节核心判断或高强度结论的论点，若当前只找到单篇支撑文献，应标记为支撑不足或待补证据。
- 多文献并列时，应避免重复复述同一句结论，而是让各文献分别支撑需求、现象、约束或场景中的不同侧面。

两类 claim 仍区分为 `text_claim` 与 `figure_claim`，但具体评估细节和图表证据流程转交 `references/figure-writing-interface.md` 与图表证据子链文档。

### 7.11. 防幻觉机制（核心）

本层的硬边界只有三条：

- 引用必须可追溯
- 摘要级证据不能支撑强 claim
- 候选召回层不能直接进入正文或审计结论
- `paper_card` 的 `background_only`、`mismatch` 或 `abstract_only` 不能被提升为关键 claim 的强支撑

更细的写作与引用方法学说明，统一放到 `references/citation-audit-guide.md`、`references/evidence-tier-policy.md` 与相关参考文档。

### 7.12. 评审与修稿路线图

本层只定义修稿闭环的输入、输出、证据状态和回退边界；具体评审方法、review 话术、反驳思路和评分细则转交 `references/reviewer-protocol.md` 与相关参考文档。

#### 7.12.1. 修稿教练（审稿意见 → 路线图）

**适用场景：**
- 已收到真实审稿意见，需要先分解任务再执行修改
- 用户已有草稿，想知道哪些意见只改措辞、哪些必须回退补证据
- 需要先出 Point-by-Point 回应骨架，再进入 `revision-only`

**标准输出：**
- `revision_roadmap.md`
- `response_letter_skeleton.md`
- `evidence_gap_list.md`

**`revision_roadmap.md` 必备字段：**

| 字段 | 说明 |
|------|------|
| reviewer_comment_id | 审稿意见唯一编号 |
| comment_id | 稳定意见编号；编辑意见使用 `E.1 / E.2`，审稿人意见使用 `R1.1 / R1.2 / R2.1` |
| source_role | `editor / reviewer_1 / reviewer_2 / reviewer_3 / author_note` |
| original_comment | 原始审稿意见或编辑要求；不得改写到改变含义 |
| comment_type | `evidence_gap / method_question / citation_issue / structure_issue / language_issue / scope_request / other` |
| severity | `major / minor / editorial / blocking` |
| readiness_state | `ready_to_revise / needs_author_input / needs_evidence_repair / blocked` |
| missing_author_input | 需要作者补充的实验、数据、行号、图表、回应口径或决策 |
| priority | P0 / P1 / P2 |
| chapter_binding | 涉及章节、段落或图表 |
| claim_binding | 对应 claim / 论点 / 结果 |
| evidence_status | VERIFIED / VERIFIED_LOCAL / WARN / REJECT / abstract_only / candidate_only |
| action_type | 直接改写 / 补文献 / 补 PDF / 补 Zotero / 重做风格蓝图 / 回退上游 Step |
| rollback_target | Step 4 / Step 6 / Step 7.2 / 无需回退 |
| success_condition | 该条意见何时算处理完成 |
| assessment_boundary | 本轮修稿/评审只覆盖的范围：`abstract / section / chapter / full_document / partial` |

**审稿意见 tracker 规则：**

- 编辑意见先编号为 `E.1 / E.2`，审稿人意见按来源编号为 `R1.1 / R1.2 / R2.1`；若来源不清，先标 `reviewer_unknown`，不得编造 reviewer 身份。
- `original_comment` 必须忠实保留原始意见含义；中文摘要可以另列，但不能替代原文。
- 每条 `comment_id` 必须绑定至少一个 `chapter_binding`、`claim_binding`、`action_type` 或 `missing_author_input`；不能只写“已处理”。
- `response_letter_skeleton.md` 中声称完成的修改，必须能回到同一 `comment_id` 的正文位置、证据动作或明确占位符。
- `readiness_state=needs_author_input / blocked` 时，不得冒充已完成修改，也不得在回应信中伪造实验、行号、图表或补充材料。
- `assessment_boundary` 必须在路线图和回应骨架中显式保留；如果只看了摘要或局部章节，不能把该轮结论写成全文判断。

> 从本版开始，`revision_roadmap`、`claim_delta_report`、`evidence_gap_list` 与 Step 8 `revision_ledger` 共用同一套闭环语义：问题识别、修订动作、证据状态、验证结果、下一步动作。该语义只约束问题生命周期，不规定具体写作策略、修辞路径或段落组织方式。

**修订闭环最小字段族（Step 7 / Step 8 统一）：**

| 字段 | 说明 |
|------|------|
| `issue_id` | 问题唯一标识；跨 `revision_roadmap / claim_delta_report / revision_ledger` 复用 |
| `chapter_binding` | 涉及章节、段落或图表 |
| `claim_binding` | 对应 claim / 论点 / 结果 |
| `problem_summary` | 问题描述或修订目标 |
| `action_type` | 本轮修订动作 |
| `evidence_status` | 当前证据状态 |
| `verification_result` | 当前验证结果 |
| `next_action` | 下一步动作：继续保留 / 人工复核 / 回退补证据 / 回退上游 Step |
| `issue_state` | `identified / routed / in_revision / verification_pending / closed / blocked_author_decision / blocked_evidence / invalid_or_not_applied` |
| `state_reason` | 当前状态原因，说明为什么关闭、阻塞、回退或不采纳 |
| `assessment_boundary` | 本轮判断覆盖的输入边界：摘要、局部章节、单章、整稿或部分输入 |

约束：
- `revision_roadmap` 偏向“问题识别 + 动作分派”
- `claim_delta_report` 偏向“claim 变化 + 证据变化”
- `evidence_gap_list` 偏向“证据阻塞 + 回退目标”
- `revision_ledger` 偏向“最终修订验证 + 状态收口”
- 三者字段不要求完全同名同量，但必须能一一映射到上面这组最小闭环字段
- `closed` 只能表示问题已通过证据和验证条件关闭；不能因为文字被改顺就关闭
- `invalid_or_not_applied` 用于记录误读、无依据建议或用户决定不采纳的问题，不能从工件中删除
- `assessment_boundary` 是硬约束：bounded review 只能对已读/已核验范围给出结论，不得伪装为全文结论

**执行规则：**
1. 不允许只做“文字总结”；每条意见都必须绑定章节和 claim。
2. 发现证据不足时，优先输出回退动作，而不是建议“弱化语气”来掩盖问题。
3. `WARN`、摘要级证据或无 PDF 条目支撑关键 claim 时，必须写入 `evidence_gap_list.md`。
4. `response_letter_skeleton.md` 只提供标准回应骨架，不冒充已经完成修改。
5. 若使用候选召回，必须把召回片段视为待确认材料；只有原文确认成功后，才能计入 `evidence_added`。

### 7.13. `revision-only` 修订执行

**定位：** `revision-only` 不是“重新写论文”，而是基于已有草稿、审稿意见、证据状态和写作蓝图，对指定章节、指定 claim、指定引用进行可追踪修订。

**bounded review 声明：**

- `revision-only` 只能覆盖当前输入里已经给出的章节、段落或引用范围；若只给了局部材料，输出必须在 `assessment_boundary` 中明示
- 不能把局部修订、摘要级判断或单章修订写成全稿完成结论
- 如果当前边界不足以支撑完整修订，只能输出 `draft_with_placeholders` 或 `needs_author_input`，不得静默补全未读部分

**标准输出：**
- 修订后正文
- `revision_change_log.md`
- `claim_delta_report.md`
- 更新后的 `response_letter_skeleton.md`
- 更新后的 `evidence_gap_list.md`
- `revision_execution_status.md`

**`revision_change_log.md` 最小字段：**

| 字段 | 说明 |
|------|------|
| `comment_id` | 对应审稿意见；必须复用 `E.1 / R1.1` 等稳定编号 |
| `chapter_binding` | 所属章节 |
| `location_before` | 修订前位置 |
| `location_after` | 修订后位置 |
| `change_type` | 修改类型 |
| `summary_of_edit` | 修改摘要 |
| `evidence_touched` | 触及的证据 |
| `status` | `applied / partially_applied / blocked_requires_rollback` |

**`claim_delta_report.md` 最小字段：**

| 字段 | 说明 |
|------|------|
| `issue_id` | 对应修订问题编号 |
| `claim_id` | claim 编号 |
| `before_claim` | 修改前 claim |
| `after_claim` | 修改后 claim |
| `delta_type` | `unchanged / softened / strengthened_with_new_evidence / reframed / removed` |
| `evidence_status_before` | 修改前证据状态 |
| `evidence_status_after` | 修改后证据状态 |
| `risk_after_revision` | 修订后风险 |
| `verification_result` | `PASS / WARN / FAIL` 或等价结果 |
| `next_action` | 下一步动作：保留 / 人工复核 / 回退补证据 / 回退上游 Step |

**硬规则：**
1. 不得用“降级措辞”替代补证据。
2. 不得绕开 `section_blueprints` / `argument_plan` 重写章节功能。
3. 回应信、正文、证据三者必须同步。
4. 被阻塞的问题必须留在 `evidence_gap_list.md`，不得静默消失。
5. `retrieved_candidate` 命中不能直接记作 `evidence_added`；必须有 note / annotation / PDF 原文确认。
6. claim 问题只有在 `claim_delta_report` 与证据状态同时更新后，才可视为进入关闭判定。

### 7.14. 复评（验证修稿是否真的解决问题）

**输入：**
- `评审报告.md`
- `revision_roadmap.md`
- 修订后正文
- `引用审计报告.md`

**输出：**
- `rereview_report.md`

**固定判断维度：**
1. 上轮问题是否关闭
2. 是否引入新问题
3. 引用风险是否下降
4. 是否仍需回退到 Step 4 / Step 6 / Step 7.3 / Step 7.7 / Step 7.16

**执行规则：**
1. 复评不是新一轮大评审，不扩展 reviewer persona。
2. 每条上轮问题必须标记为：`closed` / `partially_closed` / `open`。
3. 若修稿引入新问题，必须单列为 `new_issue`，不得混进“旧问题未解决”。
4. 引用风险未下降时，优先建议回退到 Step 7.16 或 Step 4/6，而不是继续润色。

如需更细的反方挑战、review 话术或 rebuttal 提示，应查 `references/reviewer-protocol.md`，而不在主协议中强行预设用户的论证路线。

### 7.15. 图表意图与证据约束
本阶段记录 `figure_intent / evidence_basis / candidate_specs /
human_selected_candidate / figure_risk_note`，并把每张图绑定到 `figure_id /
caption / claim_binding / section_id`。详细接口统一读取
`references/figure-writing-interface.md`。需要新建论文流程图、系统/Agent 架构图、数据流图、时序图、状态图、时间线、对比矩阵、ER 图或用例图时，使用 `figure_backend=diagram` 并加载 `references/paper-diagram-contract.md`。先形成可审阅 Spec，再由 `scripts/generate_figures.py --backend diagram` 同时生成语义 SVG、PNG、布局检查和证据记录；不得手写未校验 SVG 冒充原生流程图。图内公式使用 math run 或 `$...$`，并服从 Step 7 公式合同。
若目标期刊要求黑白、无底纹，使用 `style=minimal`：图中只能出现纯黑和纯白，分组不填充，并在 `diagram-check.json.publication_profile` 中验证通栏 170–180 mm 下节点字号不低于 7 pt。单栏空间不足时先简化或拆图，不得直接缩小复杂图；`inspect.svg` 只用于审阅。
论文 PDF、MinerU ZIP 或本地已有原图默认使用
`figure_asset_action=insert_original`、`figure_backend=not_applicable` 和
`figure_transform_authorization=not_required`。只有用户明确要求重绘、数字化或
可编辑版本时，才记录 `explicit_user_request` 并进入 reproduction；参考图片、
曲线或 VisualSpec 的存在不构成授权。
原图插入完成后的交付说明必须提醒一次可选能力：

> 已按论文原图插入。本 skill 也支持图表重绘、曲线数字化、可编辑
> SVG/PDF 和严格 QA；如需启用，请明确指定要重绘的图及目标。

该提醒只说明能力，不是确认问题或重绘授权；不得因为已提醒而运行绘图代码。
#### 7.15.1. 图文联合插图
先运行 `scripts/build_figure_asset_check.py`。MinerU 候选按
`manifest.json → full.md 图片引用 → images/ 扫描 → PDF direct` 降级；
`resolve_figure_refs.py` 只物化正文选中的原图，并生成
`figure_resolution_report.json` 与原图 `figure_evidence_report.json`。

只有明确要求恢复数值时才按 `references/DIGITIZATION_WORKFLOW.md` 执行
`inspect → spec-review/用户确认 → candidates → 自动诊断 → review-decisions → observations → data → VisualSpec`。普通候选可由用户回复“继续/下一步”批量接受，异常候选逐项处理；候选或像素观测不能直接进入 VisualSpec。连续性只由用户确认的 `curve_topology` 写入正式 `data.csv`，渲染阶段禁止补线。
重绘、严格 QA 和 bundle 命令按
`references/scientific-figure-reproduction.md` 执行，并强制携带
`--transform-authorization explicit_user_request`。

### 7.16. 写后引用审计

> 核心目的：抓"LLM 把标题相关的论文当成支撑某个具体声明的论文"这种张冠李戴。

```
稿件 → 提取所有引用标记 [1][2]...[N] → 逐条：
① 通过 citekey / zotero_item_key 定位 Zotero 条目与对照 JSON 记录
  ② 读取 `paper_card`、Zotero child note、PDF 标注、元数据、PDF 全文证据
  ③ 定位稿件中引用该论文的具体声明（claim sentence）
  ④ 判断：`paper_card` + 原文/笔记/标注是否支撑这个 claim？
     ✅ 支撑 / 🟡 弱支撑 / ❌ 不支撑
  ⑤ 输出审计报告
```

```bash
python3 scripts/citation_audit.py 论文初稿.md \
  --mapping 文献-Zotero架构对照.json \
  --pdf-index pdf-附件池索引.json \
  --prepared-chunks paper.clean.chunks.json \
  --output 引用审计报告.md \
  --output-json claim_evidence_audit.json

# fallback: no prepared chunks, but citations can still map to Zotero items
python3 scripts/citation_audit.py 论文初稿.md \
  --mapping 文献-Zotero架构对照.json \
  --output 引用审计报告.md \
  --output-json claim_evidence_audit.json
```

**三层审计结构：**

| 审计层 | 核心问题 | 输出字段 |
|--------|----------|----------|
| 格式层 | GB/T 7714、作者、年份、条目字段是否合规 | `format_status` |
| 对应层 | 正文引用能否映射回 BibTeX / Zotero / 对照 JSON | `mapping_status` |
| 证据层 | claim 是否被 `VERIFIED` / `VERIFIED_LOCAL` / `WARN` / `REJECT` 或摘要级证据正确支撑 | `evidence_status` |

**引用对应表契约：**

写后引用审计和 7.10 实时引文支撑应生成同一类 claim-to-citation 映射，便于定位“哪一句 claim 被哪篇文献支撑”。每条记录至少包含：

| 字段 | 说明 |
|------|------|
| `claim_segment_id` | 稳定 claim 段号，如 `S001 / S002`；按正文顺序生成，长段落可拆成多个 claim |
| `claim_text` | 被引用支撑的原文 claim 或句子片段 |
| `claim_type` | `mechanism / association / method / background / definition / review_context / figure_claim` |
| `claim_strength` | `background / trend / parameter / numeric_comparison / mechanism / novelty` |
| `required_evidence` | 当前 claim 的最低证据要求，如 `abstract_ok / multi_source / full_text / page_or_table / figure_panel / search_coverage` |
| `insert_position` | 引用建议插入点，如句末、分句后、图表解释句后 |
| `citekey` | BibTeX citekey；无 citekey 时记录 Zotero key 或本地证据 ID |
| `zotero_item_key` | Zotero 条目 key，可缺省但必须说明映射状态 |
| `support_grade` | `strong / partial / background / contradictory_or_limiting / metadata_only_candidate / not_supported` |
| `reading_depth` | `full_text / abstract_only / metadata_only / zotero_note / pdf_verified` 等实际读取深度 |
| `evidence_anchor` | note / annotation / PDF 页码 / chunk / 图表 / 元数据来源 |
| `downgrade_required` | 证据低于 `required_evidence` 时必须为 `true` |
| `recommended_action` | `retain / downgrade_claim / supplement_pdf_or_fulltext / repair_mapping / replace_or_remove` |

`support_grade=metadata_only_candidate` 或 `not_supported` 不得进入最终稿的强 claim；`contradictory_or_limiting` 必须进入风险和缺口说明，不能静默忽略。若同一 claim 由多篇文献支撑，应保留同一个 `claim_segment_id` 下的多条记录，而不是合并成笼统“多文献支持”。

**句子强度分级：**

| claim_strength | 可接受证据 | 禁止升级 |
|---|---|---|
| `background` | 综述、摘要、元数据 | 不得写成具体实验结论 |
| `trend` | 多篇文献或系统性证据 | 单篇摘要不能写“普遍表明” |
| `parameter` | PDF 原文、方法表、用户数据或标准文件 | 无页码/表格锚点不得写强参数句 |
| `numeric_comparison` | 页码、图、表、数据文件或可核验计算 | 无锚点不得写百分比提升/降低 |
| `mechanism` | 全文级证据，优先图表、实验或仿真 | 无竞争机制判别不得写“证明/主导” |
| `novelty` | 检索覆盖和对比文献 | 无检索覆盖不得写“首次/创新” |
 
若 `claim_strength` 与 `required_evidence` 不匹配，必须输出 `downgrade_required=true`，并执行 `downgrade_claim`、保留 `[待补证据: claim]`，或回退 Step 4/5/6 补证据。

**动作化输出：**

在三层状态之外，每条引用必须追加 `recommended_action`，固定值域为：
- `retain`
- `downgrade_claim`
- `supplement_pdf_or_fulltext`
- `repair_mapping`
- `replace_or_remove`

四种误引模式：标题-摘要张冠李戴 / 综述当实证 / 贡献过度归因 / 数据编造

**`paper_card` 驱动的审计规则：**
- `content_fit=direct` 且 `reading_depth` 不低于 `full_text` / `pdf_verified` 时，才可进入关键 claim 的正常支撑候选。
- `content_fit=adjacent` 或 `reading_depth=abstract_only` 时，若正文使用强结论语气，优先给出 `downgrade_claim` 或 `supplement_pdf_or_fulltext`。
- `content_fit=background_only` 只能保留为背景支撑；不得用于验证具体实验结果、方法优势或因果结论。
- `content_fit=mismatch` 或 `paper_card` 缺失时，不得仅凭题目相关性保留为关键支撑，优先 `replace_or_remove` 或 `repair_mapping`。
- 若 Zotero child note 与 `paper_card` 不一致，以 `文献-Zotero架构对照.json` 为主；note 仅作辅助线索。

**审计结论分级：**
- `retain`：可保留
- `downgrade`：需降级表述
- `supplement`：需补证据
- `replace_or_remove`：必须删除或替换

**推荐动作映射：**
- 摘要级证据用于强 claim → `downgrade_claim` 或 `supplement_pdf_or_fulltext`
- BibTeX / Zotero / JSON 映射缺失 → `repair_mapping`
- `REJECT` 支撑关键 claim → `replace_or_remove`
- `retrieved_candidate` 本身不得决定 `recommended_action`；动作必须基于原文确认后结果。

**图表证据子路径：**

当某条 claim 主要依赖图/表时，除文字审计外，额外记录：
- `figure_id`
- `table_id`
- `panel_id`
- `figure_table_panel_binding`
- `caption_support`
- `text_support`
- `visual_support`
- `evidence_status`
- `recommended_action`

**图表证据状态值域：**
- `caption_only`
- `text_caption_aligned`
- `visual_confirmed`
- `figure_not_supported`

**图表误引风险：**
- `figure_overinterpretation`

**图表动作建议值域：**
- `retain`
- `downgrade_claim`
- `need_visual_check`
- `supplement_text_evidence`
- `replace_or_remove`

> Crossref / Semantic Scholar 摘要只能作为补充核验，不能替代 Zotero 条目和 PDF 原文。CNKI/万方中文文献尤其必须以本地元数据、详情页 URL、PDF 原文和 Zotero Extra/source_id 为审计依据。

**Step 7 分层完成状态：** `draft_ready / evidence_closed / ready_for_step8` 的稿件哈希、claim 审计、图表门和校验命令统一见 `references/claim-evidence-readiness.md`。分层状态只约束当前写作范围，不要求补跑 Step 1-6；自动摘要筛查不得关闭强 claim。写入统一 run envelope 时，上述值进入 `domain_state`；跨 Step readiness 映射为：`draft_ready -> partial`、`evidence_closed -> partial|complete`（取决于当前请求范围）、`ready_for_step8 -> complete`。图形复现状态与 claim evidence 状态继续分别记录，不得用其中一个替代另一个。

#### 7.16.1. 写作质量与审稿缺陷审计

本子路径用于把通用科学写作门、IMRaD 专项章节门和审稿人视角缺陷库转成可执行报告。它不是新的公开 Step，也不替代 7.16 引用审计。

**读取文件：**

- `references/scientific-writing-quality-rubric.md`
- `references/section-quality-gates.md`
- `references/reviewer-defect-taxonomy.md`
- 任务命中电力电子/充电/储能/EMS/V2G/快充/无线充电/超级电容时，同时读取 `references/domain-packs/power-electronics-ev-energy-writing.md`

**推荐执行入口：**

```bash
python3 scripts/audit_scientific_writing_quality.py 论文初稿.md \
  --section-type auto \
  --output-json scientific_writing_quality_audit.json \
  --output-md scientific_writing_quality_audit.md

python3 scripts/audit_engineering_claims.py 论文初稿.md \
  --output-json engineering_claim_audit.json \
  --output-md engineering_claim_audit.md
```

**审计范围：**

- `abstract_quality_gate / introduction_quality_gate / discussion_quality_gate / conclusion_quality_gate`
- `subject_action_audit / old_new_flow_audit / paragraph_function_audit / figure_first_argument_plan / phrasebank_guardrail`
- `novelty_and_positioning_defects / evidence_and_citation_defects / method_and_reproducibility_defects / result_and_figure_defects / discussion_and_claim_defects / power_energy_specific_defects`

**输出约束：**

- `scientific_writing_quality_audit.json/md` 只记录章节功能、段落任务、图表先行和 claim 强度边界问题。
- `engineering_claim_audit.json/md` 只记录工程 claim 的证据缺口，如 `stability_claim_without_stability_evidence`、`efficiency_without_test_conditions`、`only_simulation_no_hardware_for_hardware_claim`。
- `reviewer_defect_report.md` 可由上述报告和人工/Agent 预审合并生成，但不得冒充真实审稿意见。
- 所有 `rollback_target=step_7_citation_audit / step_7_argument_plan / step_4_or_6_evidence_repair` 的问题必须进入 `evidence_gap_list.md` 或 `revision_roadmap.md`，不得只靠润色关闭。

### 7.17. CHECKPOINT W — CP-CITATION-WARN

当 `WARN` 文献、弱引用、摘要级证据、无 PDF 条目或审计中的“不支撑/弱支撑”将被用于关键 claim 时，必须输出 checkpoint 块并等待用户明确确认。普通背景性描述、研究脉络说明、综述矩阵候选记录和待补查清单不触发 checkpoint。`REJECT` 仍禁止进入正文关键引用和 Zotero 写入计划。

```md
CHECKPOINT W — CP-CITATION-WARN

route_mode: normal_chain|direct_entry|resume|repair|partial_artifact
status: blocked
blocks_next: using risky evidence in key claims
must_confirm: true

summary:
- 列出异常文献/引用、风险类型和受影响 claim。

user_options:
1. 删除或替换异常引用
2. 保留但标注为背景/待补证据
3. 回退 Step 4/5/6 小闭环补证据
4. 逐条人工审查

does_not_block:
- WARN 文献用于背景性描述、研究脉络或待补查线索
- 摘要级证据用于领域概况、主题归类或精读优先级判断
- 综述矩阵中的候选记录、异常清单和低风险描述性整理

required_confirmation:
- “确认 CP-CITATION-WARN”
```

---

## 质量门槛 (Quality Gates)

- [ ] paper_type 和 language 已识别
- [ ] 7.2 文献证据矩阵：13 列完整，证据优先级规则已遵循
- [ ] 7.3 目标体裁/文档风格：`style_sample_status.md/json` 已生成，Flash 或 Pro 模式已完成，style_profile.md 已生成
- [ ] 7.7.3 章节级论证计划：`argument_plan.md/json` 已生成（适用时）
- [ ] 防幻觉机制：每处引用均来自 Zotero 条目和实际 PDF/笔记/标注证据
- [ ] 如输入含 Step 6 T1/T2/T3 映射：矩阵覆盖当前写作范围内相关条目，T3 用途已标明；direct-entry 不要求补跑 Step 6
- [ ] 如输入含 Step 4 可信度字段：关键 claim 遵守 `VERIFIED / VERIFIED_LOCAL / WARN / REJECT` 边界；direct-entry 使用当前证据入口自身的 reading_depth/evidence_level
- [ ] 7.8.1 段落自查：每段一个工作 / 从证据向外写 / 动词校准 / 无虚假新颖性 / 段落流；公式任务已通过 `equation-writing-contract` 与 `equation_guard.py`
- [ ] 🆕 术语对齐：核心术语与 `.skill-state/term_aliases.md` 一致
- [ ] 7.12 同行评审：`reviewer_scorecard.json` 已生成；`technical_soundness / evidence_adequacy >= 4`，其余三维 `>= 3`，`critical_issues=0`，且每项含 `evidence_locations / reason`
- [ ] 7.12.1 修稿教练：如存在外部审稿意见，`revision_roadmap.md`、`response_letter_skeleton.md`、`evidence_gap_list.md` 已生成
- [ ] 7.14 复评：如完成修稿，`rereview_report.md` 已生成，且旧问题关闭状态明确
- [ ] 7.16 引用审计：❌ 不支撑引用已移除或替换
- [ ] 博士目标：`doctoral_thesis_map.json` 已覆盖 RQ→结果→贡献、可复现性、反证边界与跨章综合；`draft_ready` 可为 provisional，`evidence_closed / ready_for_step8` 必须为当前稿件的 `doctoral_ready`

---

## 收尾检查 (Closing Checks)

### 产出完整性
- [ ] 当前模式的目标草稿已生成；`论文初稿.md/docx` 只对 `full-document` 必选；涉及公式时 `equation_audit.json/md` 与 `equation_register.json/md` 已生成并绑定当前稿件
- [ ] `综述矩阵.csv/md` 仅在本轮写作范围需要综述矩阵时必选；其他 direct-entry 模式使用最小证据映射
- [ ] 目标体裁/文档风格产出：`research_dossier/` 目录完整，含 `style_sample_status.md/json`
- [ ] `评审报告.md` + `rebuttal-预演.md` 已生成
- [ ] 如完成修稿复评：`rereview_report.md` 已生成
- [ ] `引用审计报告.md` 已生成
- [ ] 如走 `revision-only`：`revision_roadmap.md`、`response_letter_skeleton.md`、`evidence_gap_list.md` 已生成
- [ ] figures/ 目录图表完整

### 术语对齐检查 🆕
- [ ] 逐章扫描核心术语，确认与 `.skill-state/term_aliases.md` 一致
- [ ] 发现术语不一致 → 修正为 Main Term → 如 Main Term 不当 → 更新 term_aliases.md → 记录到 decision_log.md

### 错误日志更新 🆕
- [ ] 本轮是否出现新的 AI 操作错误？
  - 引用编造 → 追加到 `.skill-state/error_log.md`
  - 综述矩阵证据填充错误 → 追加到 `.skill-state/error_log.md`
  - 目标体裁/文档风格分析偏差 → 追加到 `.skill-state/error_log.md`
  - 术语混用 → 追加到 `.skill-state/error_log.md`
  - 7.16 审计发现系统性误引 → 追加到 `.skill-state/error_log.md`

### 决策日志更新 🆕
- [ ] 是否调整了章节结构？→ 记录到 `.skill-state/decision_log.md`
- [ ] 是否修改了 paper_type 判定？→ 记录到 `.skill-state/decision_log.md`

### 下一步提示
- [ ] 向用户明确说明下一步：论文润色（Step 8）
  > **下一步 → Step 8：** 同行评审通过 + rebuttal 预演无遗漏 + 引用审计无重大问题后，进入润色、保守修订与修订后验证。

### 成功判据
- [ ] 当前输出已说明证据基础来自 Zotero/PDF/笔记/摘要中的哪一层
- [ ] 当前输出已说明引用风险状态
- [ ] 用户能区分“正文已形成”和“证据仍弱但可继续修”

### 完成前必须确认
- [ ] 只有在 evidence basis 和 citation risk 都已说明时，才能声称“章节写完”
- [ ] 若关键 claim 仍为摘要级或候选级证据，只能表述为草稿可继续，不能表述为证据闭环已完成

### 失败分流
- 写不出来：先按 `references/failure-triage.md` 判定是证据层问题还是蓝图层问题
- 引用支撑弱：优先回 7.2/7.3 或 Step 4/6 小闭环，不让模型硬写
- 体裁不稳：先修 style profile / section blueprint，再改正文

---

## 故障排除 (Troubleshooting)

常见问题参见 `agents/known_pitfalls.md`。本 Step 特有的问题：

- **引用不足**：运行 7.10 扩展搜索补充引用；检查引用密度指南
- **现有 Zotero 文库不能支撑 claim**：回到 Step 4/6 小闭环补文献、补 PDF、补入库，再继续写作
- **表达明显机械或重复**：7.8.1 做轻量可读性整理；Step 8 Level 3 做表达风险清理
- **引用审计大量不支撑**：7.16 逐条处理，❌ 级别优先替换或移除
- **术语不一致**：回查 `.skill-state/term_aliases.md`，全篇统一为 Main Term
