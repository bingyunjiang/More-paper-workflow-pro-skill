# Step 8: 润色与保守修订

> 对既有成稿进行成稿级风险收口：全文一致性、术语终验、表达清理，以及**受约束补写 + 直接修改 + 修订后验证**。
> Step 8 不负责主体写作，不补外部证据，不替代完整引用审计或修稿路线图；但它可以在现有正文、Step 7 三工件和评审/审计输入支撑下，对正文做修订性补写与局部增强。

---

## 启动前读取 (Pre-read Checklist)

执行本步骤前，必须确认以下文件已加载：

- [ ] `agents/step_7_writing.md` — 论文初稿 + 评审报告 + 引用审计报告
- [ ] `.skill-state/term_aliases.md` — 🆕 术语标准化映射（以本表为基准校验术语一致性）
- [ ] `.skill-state/error_log.md` — 已知表达风险、术语风险与重复错误
- [ ] `.skill-state/decision_log.md` — 影响润色策略的决策
- [ ] `references/polish-modes.md` — 🆕 revision scope 约束
- [ ] `references/step8-rewrite-scope.md` — 🆕 Writing Read、rewrite_scope / rewrite_level 与保真/残留味回读
- [ ] `references/protected-spans.md` — 🆕 引用、图表、公式、术语、参数和证据边界保护区
- [ ] `references/equation-writing-contract.md` — 公式签名保真、源码残留与 DOCX 原生公式终验
- [ ] `references/academic-ai-trace-index.md` — 🆕 学术 AI 痕迹轻量索引；只定位 Top 5-10 个最影响读感和可核验性的模式
- [ ] `references/ai-trace-taxonomy.md` — 🆕 机械化表达风险参考
- [ ] `references/deterministic-writing-diagnostics.md` — 🆕 AI 味确定性检查规则族与映射边界
- [ ] `references/authorial-revision-and-ai-use.md` — 作者声音、智识决定、AI 使用披露与检测器边界
- [ ] `references/genre-style-axis.md` — 🆕 target_genre 默认规则
- [ ] `references/scientific-writing-quality-rubric.md` — 通用科学写作质量 rubric；仅用于可读性、段落功能和图表先行诊断，不改变 claim 强度
- [ ] `references/section-quality-gates.md` — 摘要/引言/讨论/结论专项写作门；仅用于章节功能诊断和保守分流
- [ ] `references/reviewer-defect-taxonomy.md` — 审稿人视角缺陷库；仅用于 review-style-polish 的问题分类，不冒充真实审稿意见
- [ ] `references/writing-antipatterns.md` — 🆕 写作反模式回退条件

---

## 润色前先答 (Before You Polish)

先把下面六个问题答清楚，再开始改正文：

1. 这次是 `quick-polish` 还是 `audited-polish`？
2. 这段文字的问题主要是语言、结构、术语，还是 claim / evidence / citation 风险？
3. 当前可用的约束源是什么：Step 7 三工件、评审报告、引用审计报告，还是只有初稿？
4. 这一轮允许做到哪一层：直接修改、局部补写，还是必须回退 Step 7？
5. 本轮 `Writing Read` 是什么：文本范围、target_genre、language、reader、evidence_state、`rewrite_scope + rewrite_level`？
6. 哪些片段已经划入 `protected spans`：引用、图表/公式、术语、参数、证据边界、责任主体、命令/路径？

如果问题已经落到证据缺口、章节功能错误或引用不匹配，不要继续硬修句子，先回退对应 Step。

---

## 适用任务 (Applicable Tasks)

- 逐句精修学术论文
- 检查明显机械化、重复化或空泛表达
- 修复影响读者理解的局部衔接问题
- 术语一致性检查（以 term_aliases.md 为基准）
- 成稿级全文一致性检查与保守修订
- 基于现有上下文的局部补写：桥接句、限定句、解释句、引证配套句、局部支撑句

---

## 不适用任务 (Non-applicable Tasks)

- 论文写作 → 路由到 `agents/step_7_writing.md`
- 引用审计 → 路由到 `agents/step_7_writing.md`（7.16）
- 图表生成 → 路由到 `agents/step_7_writing.md`（7.14）
- 正文生成、文献整合、证据补强、修稿路线图 → 路由到 `agents/step_7_writing.md`

## When to use this Step

- 用户已有草稿、章节或全文，需要保守润色、表达收口、术语一致性检查、机械化表达清理或修订后验证。
- 用户要把 Step 7 的预审、引用审计或导师意见转成可执行的局部修订，但不需要新增文献或重写主论证。
- 用户需要投稿/送审前的审稿式诊断摘要、严重性分级、修订账本和质量报告。

## When NOT to use this Step

- 用户还没有正文，需要写作、续写、综述整合或章节蓝图，去 Step 7。
- 发现关键 claim 缺证据、引用不匹配、图表证据断裂或需要补文献，回 Step 7/4/6，而不是在 Step 8 硬修。
- 用户要求重构研究问题、重写大纲、改贡献点或新增实验解释，回 Step 2/7。

---

## 输入要求 (Input Requirements)

| 输入 | 来源 | 格式 | 必选 |
|------|------|------|:--:|
| 论文初稿 | Step 7 | .md | ✅ |
| 评审报告 | Step 7.11 | .md | 推荐 |
| 引用审计报告 | Step 7.16 | .md | 推荐 |

### 输入契约

执行润色前，必须先明确以下上下文：

| 字段 | 说明 | 缺省处理 |
|------|------|----------|
| 初稿路径 | 待润色的 `.md` 初稿文件 | 用户未指定时，使用 Step 7 最新论文初稿 |
| 目标语言 | 中文、英文或中英双语 | 继承 Step 7 初稿语言 |
| 目标体裁 | 期刊论文、学位论文、课程论文、会议论文等 | 继承 Step 7 的 target_genre（旧文档若写 `target_type`，按兼容字段处理） |
| 保留原章节编号 | 是否保持标题层级、章节编号、图表编号不变 | 默认保留 |
| 允许大幅改写 | 是否允许重排段落、改写论证顺序 | 默认不允许，只做局部结构润色 |
| 改写范围轴 | `rewrite_scope=in-place / bounded / structural` | 默认 `bounded`；引用/公式/数据密集段落默认 `in-place` |
| 改写力度轴 | `rewrite_level=minimal / standard / aggressive` | 默认 `standard`；`aggressive` 只在用户明确允许且不新增证据时使用 |
| 修订范围 | `local-polish / section-revision / full-manuscript-pass` | 默认 `local-polish` |
| 输出模式 | `quick-polish / audited-polish` | 默认按任务风险选择；局部低风险段落可用 `quick-polish` |

**Direct-entry input contract：**

| 可接受输入 | 最小处理 | 降级规则 |
|------------|----------|----------|
| 用户直接提供初稿 `.md/.docx/文本` | 直接进入输入接收阶段 | 不要求补跑 Step 7 |
| 初稿 + 评审意见 | 按评审意见标记修改任务 | 缺引用审计时不声明引用安全 |
| 初稿 + 引用审计报告 | 保留引用风险和修复建议 | 不重新做完整审计 |
| 初稿 + `scientific_writing_quality_audit.json/md` | 将章节功能、段落任务和图表先行问题并入诊断摘要与 `revision_ledger` | 不把质量审计当作证据审计 |
| 初稿 + `engineering_claim_audit.json/md` | 将工程 claim 缺口并入 `evidence_gap / contribution_overclaim / structure_drift` 分流 | 不新增实验、仿真、标准或引用 |
| 只有局部章节/段落 | 只润色指定范围 | 不改全篇结构和未提供章节 |

Step 8 的直接入口只要求有可润色文本。评审报告、引用审计报告、Step 7 完整上下文都是质量增强输入，不是入口门。缺失时按降级规则标记风险，不能要求用户回跑 Step 7。
Step 8 可以补局部内容，但仅限可由现有正文、Step 7 三工件、评审/审计输入支撑的修订性补写，不允许把本层升级为开放式重写器。

**输出模式边界：**

| 模式 | 适用场景 | 必须输出 | 不允许 |
|------|----------|----------|--------|
| `quick-polish` | 单段、局部章节、低风险语言润色，且不触及 claim、引用落点或章节功能 | 润色稿 + 3-5 条修改说明；必要时附“引用安全未审计”提醒 | 不生成新证据、不声称完成全文审计、不重排章节主论证 |
| `audited-polish` | 全文章节、投稿/送审前终稿、触及 claim 强度/引用/结构的问题 | `diagnostic_summary.md`、`revision_ledger.json/md`、修改对照表、术语一致性报告、润色质量报告 | 不替代 Step 7 引用审计，不新增外部证据 |

完成门按输出模式判定：`quick-polish` 只要求实际润色文本、3-5 条修改说明、protected spans 边界和必要的风险提醒；不得因为缺少 audited 工件判定失败。`audited-polish` 才要求完整 ledger、对照表、术语报告、质量报告和请求范围内的导出文件。
| `review-style-polish` | 用户要求审稿式修订、投稿前 final pass、导师意见收口，或 Step 7 预审后进入修订 | 严重性分级摘要、top fixes、`revision_ledger.json/md`、润色质量报告 | 不做编辑决定预测、不新增外部证据、不把预审意见伪装成真实审稿意见 |

若 `quick-polish` 过程中发现 `evidence_gap / structure_drift / citation_misalignment / contribution_overclaim`，必须升级为 `audited-polish` 或回退 Step 7，不能继续把结构或证据问题包装成句子润色。

**审稿式严重性分级：**

Step 8 的严重性用于安排修订优先级，不用于预测录用结果。

| 级别 | 含义 | 默认动作 |
|------|------|----------|
| `CRITICAL` | 阻塞当前成稿质量，Step 8 通常不能独立解决，例如核心 claim 无证据、章节功能错误、贡献点与正文不一致 | 回退 Step 7/4/6 或转人工决策 |
| `MAJOR` | 明显影响审稿阅读或导师判断，例如多处术语漂移、关键段落衔接断裂、引用落点风险、机械化表达密集 | 进入 `revision_ledger`，优先修订或降强度 |
| `MINOR` | 局部表达、格式、冗余和轻微机械化问题 | Step 8 可直接修改或记录为低风险建议 |

`diagnostic_summary.md` 在 `review-style-polish` 中必须先列 `CRITICAL / MAJOR / MINOR` 计数，再列前三个最值得先修的问题。若存在 `CRITICAL`，不得继续宣称“终稿已完成”，只能输出可修项和回退目标。

#### 默认输出顺序

Step 8 的默认输出顺序固定为：

1. 诊断摘要
2. 修订任务清单
3. 润色正文草案
4. `revision_ledger`
5. 修改对照表
6. 术语一致性报告
7. 润色质量报告

如果只是局部 low-risk 润色，可以压缩输出，但诊断摘要和风险标记仍然必须保留。

> **AI 味确定性检查边界：** Step 8 内部包含一个“AI 味确定性检查”子层，输入为待润色正文、`.skill-state/term_aliases.md` 与 Step 7 三工件（如可用）。它只检查表达层确定性风险，用于识别机械化表达、空泛套话、悬垂洞见、节奏过匀和载体脏污等问题；它不判断学术观点真假，不判断引用是否真实存在，也不把“像 AI 写的”直接等同于“不能发表”或“必须回退”。

> **作者声音与检测器边界：** 同时读取 `references/authorial-revision-and-ai-use.md`。本 Step 通过删除模板套话、恢复作者稳定术语与真实判断、强化具体对象/证据/边界来降低机械感，但不以规避 AIGC 检测为目标，不承诺检测结果，也不通过随机扰动、故意错误或隐藏真实 AI 使用记录来“过检”。检测结果仅可作为人工复核的弱信号。

> **Writing Read / Protected Spans 边界：** Step 8 修改正文前必须先声明 `Writing Read`，并按 `references/protected-spans.md` 划定引用、图表、公式、术语、参数、证据边界和责任主体等保护区。保护区内只允许低风险格式、标点、术语一致性和语法修复；任何可能改变事实、引用落点、claim 强度或责任主体的改动，都必须进入 `revision_ledger` 并触发保真回读。

> **RAG 边界：** Step 8 默认消费 `argument_plan` 中已确认的证据状态。必要时可读取 `retrieval_candidates.json` 做缺口提醒或修订风险说明，但不得把候选层内容直接当作正文证据、引用修复依据或 claim 支撑结论，不允许跳过原文确认层。

> **PDF 边界：** Step 8 默认消费 Step 7 已确认的证据层与 PDF 处理结果。必要时可以读取带锚点的 `clean.md/chunks.json` 作为修订参考，但不得把未经确认的提取文本当成新增外部证据，也不得绕过原 PDF 的最终核验地位。统一口径见 `references/pdf-processing-policy.md`。

**写作工件读取优先级：**

若同时存在 Step 7 的统一工件：

1. `style_profile.json`
2. `writing_blueprints.json`（旧项目兼容读取 `section_blueprints.json`）
3. `writing_rationale_matrix.json`

则 Step 8 在判断 `target_genre`、章节功能、风险来源时应默认以这些 JSON 为**约束源**，不是仅作参考；对应 `.md` 只作为人工解释和展示层。  
JSON 缺失时，可降级读取 `.md`，但需在质量报告中标记“基于展示层工件解析”，不得伪装为完整风格对齐。

**三工件默认约束关系：**
- `style_profile.json`：约束句长、语域、引用密度、标题层级
- `writing_blueprints.json`：约束章节功能、信息顺序、图表位置，并通过 `source_lineage` 回查 Step 2 不可变结构基线
- `writing_rationale_matrix.json`：约束保留的论证顺序、不可删改的证据链、保守改写边界

### PDF 提取结果的使用限制

Step 8 只允许把 PDF 提取结果用于以下用途：

- 解释已有正文的语言与结构问题
- 标记可能需要回 PDF 核验的高风险位置
- 辅助定位 claim 所在 section / pages / chunk
- 帮助保持术语、句意和章节逻辑与 Step 7 一致

Step 8 不允许：

- 把新提取的 PDF 文本直接升级为新增引用依据
- 把候选提取文本当作 claim 修复结论
- 用全文提取替代 Step 7 的完整引用审计

若提取结果缺少 `pages / source_pdf / chunk_id / evidence_level / must_check_pdf` 等锚点，应在质量报告中标记“PDF 提取结果不可完全回查”，不得伪装为完整证据层。

### 缺失输入降级规则

- 缺少评审报告：可以继续润色，但必须在输出报告中标记“评审依据不足”，并只做语言、结构和 AI 痕迹层面的修订。
- 缺少引用审计报告：可以继续润色，但不得声称引用安全已通过；发现疑似虚构引用、证据不足或数据异常时，只能标记为“引用安全提醒”，不替代 Step 7 的完整引用审计。

---

## 标准输出 (Standard Outputs)

| 输出 | 格式 | 说明 |
|------|------|------|
| `diagnostic_summary.md` | .md | 标准诊断摘要：问题类型、严重度、是否可在 Step 8 修复、回退目标 |
| `revision_ledger.json` | .json | Step 8 问题闭环主工件：问题分类、允许动作、修订建议、验证结果、最终状态 |
| `revision_ledger.md` | .md | `revision_ledger.json` 的人工审阅层，供快速浏览与人工复核 |
| 论文润色稿 | .md → .docx | 精修后的终稿 |
| 修改对照表 | .md/.csv | 位置 / 原文 / 修改后 / 修改类型 / 修改原因 / 涉及规则 |
| 术语一致性报告 | .md | 术语修改数、新增术语数、Main Term 变更数 |
| 润色质量报告 | .md | 最终风险、降级说明、验证结果、人工复核项 |
| 公式审计与登记 | `.json` + `.md` | 公式相关稿件必须刷新 `equation_audit` / `equation_register`，并记录润色前后公式签名与 DOCX 原生公式状态 |

**AI 味检查结果并入规则：**

- `diagnostic_summary.md` 必须包含 `AI 味确定性检查摘要` 区块：规则族命中数量、高密度章节/段落、可直接修复项数量、需人工复核项数量。
- `revision_ledger.json/md` 中所有进入实际处理队列的 AI 味命中项，复用现有 issue 字段，并可追加 `rule_family / rule_id / rule_examples / density_signal`。
- `润色质量报告.md` 必须包含 `AI 味检查结果` 区块：已处理的高频机械表达、保留未改的风格性项、建议作者人工复核的章节。
- 若需要机器层中间结果，优先使用 `scripts/deterministic_writing_diagnostics.py` 生成结构化 issue，再并入 `revision_ledger.json`。
- 若需要一个可直接运行的 Step 8 局部入口，优先使用 `scripts/run_step8_ai_trace.py`，默认文件名为：`论文初稿.md` 输入，`.skill-state/ai_trace_diagnostics.json`、`diagnostic_summary.md`、`revision_ledger.json`、`revision_ledger.md` 输出。
- 自动化/CI 可增加 `--strict`；全局 readiness 为 blocked 时返回非零。默认诊断模式仍允许写出阻塞报告并返回 0，便于 direct-entry 读取结果。
- Step 8 JSON/Markdown 状态工件必须使用同目录临时文件、flush/fsync 和原子替换；中断时不得暴露半截 ledger 或 diagnostics。

---

## 执行流程 (Execution Flow)

### 执行阶段与润色层级的关系

- **Stage** 表示完整执行顺序，从输入接收到日志回写。
- **Level** 表示 8.2 内部的四层润色深度，不单独代表完整流程。

| Stage | 阶段 | 输入 | 动作 | 输出 |
|------:|------|------|------|------|
| 0 | 输入接收 | 初稿、评审报告、引用审计报告、共享记忆 | 确认输入契约，输出 `Writing Read`，记录缺失项和降级状态，划定 protected spans | 输入检查摘要 |
| 1 | 初稿诊断 | 初稿 + Step 7 评审/审计信息 | 按章节识别语言、结构、机械化表达、术语和引用风险，并做中文三分法分类；内部运行 AI 味确定性检查 | `diagnostic_summary.md` + 润色任务清单 |
| 2 | 分层润色 | 初稿 + 任务清单 | Level 1 默认执行；Level 2-3 按诊断命中执行；Level 4 仅在用户要求或已有 `style_profile` 时执行 | 润色正文草案 |
| 3 | 问题闭环账本 | 原文 + 润色正文草案 + 诊断任务清单 | 记录每个问题的允许动作、修订建议、验证结果与最终状态 | `revision_ledger.json` + `revision_ledger.md` |
| 4 | 对照表生成 | 原文 + 润色正文草案 | 抽取代表性修改，按固定字段记录原因 | 修改对照表 |
| 5 | 术语与公式终验 | 润色正文草案 + `.skill-state/term_aliases.md` + 公式登记 | 校验 Main Term，并运行公式签名/缺失/源码残留审计 | 术语一致性报告 + `equation_audit/register` |
| 6 | DOCX 导出 | 已通过公式预检的 `论文润色稿.md` | 转换为 `.docx`，沿用 Step 7/项目既有样式，并回读 OMML 原生公式 | `论文润色稿.docx` |
| 7 | 日志回写 | 质量报告、术语报告、修改对照表 | 仅回写可复用错误和结构性决策 | `.skill-state/` 更新摘要 |

### 职责边界

- Step 8 是成稿级精修与保守修订层，不接管 Step 7 的主体写作、整合、审阅、校验流水线。
- Step 7 负责主体写作与主论证展开；Step 8 负责局部增强、风险收敛、终稿修订闭环。
- Step 8 可以指出引用风险，但不重新做完整引用审计；完整引用审计仍路由到 Step 7。
- Step 8 可以做局部结构润色与局部补写，但不重写论文大纲或章节主体；如需重构章节，应回到 Step 2/Step 7。
- Step 8 可以更新术语表；涉及 Main Term 的重大变更时，必须同步记录到 `.skill-state/decision_log.md`。
- Step 8 可以修复写法、补桥接句/限定句/解释句/引证配套句/局部支撑句，但不替 Step 7 重新发明 `target_genre`、章节功能或主论证结构；这些若不清晰，应回退到 Step 7 蓝图层。
- Step 8 不得绕开 `style_profile / section_blueprints / writing_rationale_matrix` 自行重设风格目标；若三工件缺失，只能按降级模式运行并显式记录。
- Step 8 的允许动作分为两类：
  - `直接修改`：术语统一、语言清理、论断降强度、局部衔接修复、已有引用落点调整、格式风格统一。
  - `局部补写`：桥接句、限定句、解释句、引证配套句、局部支撑句。
- Step 8 的禁止动作：新增外部证据或引用来源、重写章节主体、重定义贡献点/研究问题、修复需要作者私有知识或新增实验的信息缺口。
- Step 8 不得替换 Step 7 的引用审计结论，不得新增未经确认的证据，不得把“去 AI 味”变成重新立论。
- Step 8 只负责保守修订：改善衔接、压缩或扩展局部表达；凡涉及新增论据、补全文献、扩大章节范围，必须回退 Step 7。
- Step 8 不能解决的问题：新增引用或补证据、修复 claim 与证据不匹配、重构章节功能、修复图表缺失造成的论证断裂、补 systematic-review 筛选协议；以上一律导向回退，不允许“润色硬修”。
- Step 7 已经完成的基础可读性整形不应在 Step 8 中重复展开；Step 8 只处理全局一致性、终验和成稿级表达质量。
- Step 8 会自动执行 AI 味确定性检查；其结果只是润色诊断的一部分，不构成新的完成门，也不会因为“像 AI”就单独要求用户回跑主写作。
- 每项修改必须归为 `editorial_only / author_confirmed / requires_author_input`。语言级修改可继续；贡献、因果、方法、局限或含义变化若未获作者确认，只能写入 `authorial_revision_record.json` 的待确认项，不得擅自进入终稿。
- 单纯词表或模式命中不得直接升格为 `evidence_gap / structure_drift / contribution_overclaim`；若没有独立证据支持，默认只能落入 `language_mechanical` 或术语一致性相关问题。

### 8.1. 标准诊断层

进入四层润色前，必须先输出 `diagnostic_summary.md`，至少逐项记录：

| 字段 | 说明 |
|------|------|
| `issue_type` | 问题类型 |
| `category` | `可直接修订 / 需作者决定 / 当前依据不足` |
| `severity` | `low / medium / high` |
| `location` | 章节/段落/句子位置 |
| `can_fix_in_step8` | `true / false` |
| `rollback_target` | `none / step_7_revision_only / step_7_citation_audit / step_7_argument_plan / step_4_or_6_evidence_repair` |
| `recommended_action` | 推荐动作 |

**`issue_type` 固定值域：**
- `evidence_gap`
- `structure_drift`
- `language_mechanical`
- `term_consistency`
- `contribution_overclaim`
- `citation_misalignment`
- `mechanism_bluff`

**固定诊断动作表：**

| `issue_type` | Step 8 默认动作 | 禁止动作 / 回退目标 |
|--------------|-----------------|---------------------|
| `language_mechanical` | 可在 Step 8 直接修，执行语言清理、机械表达修复、局部衔接补写 | 不得扩大为新论证 |
| `term_consistency` | 可在 Step 8 直接修，并记录术语一致性报告 | 涉及 Main Term 重大变更时写入 `.skill-state/decision_log.md` |
| `structure_drift` | 默认回退 Step 7 `argument_plan`，必要时只给诊断和建议 | 不靠润色硬修章节功能 |
| `evidence_gap` | 默认回退 Step 7 `citation_audit` 或证据补强 | Step 8 不新增外部证据 |
| `citation_misalignment` | 只记录引用安全提醒，保留风险位置 | 完整处理回 Step 7 引用审计 |
| `contribution_overclaim` | 允许降强度或补边界句 | 若仍需新证据，回 Step 7，不在 Step 8 新增文献 |
| `mechanism_bluff` | 只做科学空话诊断、降强度、补边界句或提示回退 | 不新增机理证据，不补图号，不替代 Step 7 机理审计 |

**诊断原则：**
- 诊断优先级固定为：`章节功能 -> 段落逻辑 -> claim/evidence/boundary -> 句子润色`。
- 先判断当前段落是否服务正确章节功能，再判断段落内信息顺序和主任务，随后判断 claim、证据和边界是否匹配，最后才做词句层面的润色。
- 若章节功能错误或段落承担多个互相冲突的任务，优先标记 `structure_drift` 并回退 `step_7_argument_plan`，不得直接做句子润色。
- 若 claim 缺证据、证据无法支撑结论或边界缺失，优先标记 `evidence_gap / citation_misalignment / contribution_overclaim` 并回退 Step 7 的 citation audit 或 argument plan。
- `language_mechanical` 通常可在 Step 8 修复。
- `evidence_gap`、`structure_drift`、`citation_misalignment` 默认优先考虑回退，而不是本层强行修顺。
- `contribution_overclaim` 需结合 Step 7 的 claim 与证据状态判断，不能只靠降级措辞判定为已解决。
- AI 味确定性检查的大多数命中项默认映射到 `language_mechanical`。
- 若命中同时涉及术语混乱，仍保持 `issue_type=language_mechanical`，并在 `problem` 或 `evidence_basis` 中标注 `term_consistency_related`。
- 若命中同时暴露“空泛归因贴着关键结论”，主类型仍为 `language_mechanical`，但 `next_action` 可指向 `return_to_step_7_citation_audit`。
- 若命中机理空话、因果跳跃、图像幻觉或证明动词无证据，主类型应为 `mechanism_bluff`；Step 8 只能降强度、加边界句或回退 Step 7，不得补写新证据。
- 若输入包含 `scientific_writing_quality_audit` 或 `engineering_claim_audit`，Step 8 只消费其中的 `severity / recommended_action / rollback_target` 做修订分流；`rollback_target` 非 `none` 的问题不得在 Step 8 内直接关闭。

**双向校准规则：**
- 防止润色不足：明显机械化表达、术语混乱、局部衔接断裂和低风险重复必须处理或说明保留原因。
- 防止润色过头：不得为了“更自然”重写章节主论证、重定义贡献点、移动关键引用或删除边界条件。
- `过头和不足都要防` 是 Step 8 的固定判断标准；若两者冲突，优先保护证据边界和章节功能。
- 风格校准只能作为 Level 4 的有限收口，不得升级为全文重写或新的写作目标。
- `术语终验的分层收口` 只统一、修正和风险提示；对 `provisional` 术语不硬删，对 `locked` 术语才执行全篇强一致。

### 8.1.1. 中文三分法

- `可直接修订`：当前问题可以通过直接修改或局部补写处理，且能在本层完成最小验证。
- `需作者决定`：看得出问题，但修到哪一步需要作者拍板，或可能影响章节主论证。
- `当前依据不足`：当前正文、三工件、评审/审计输入不足以安全修订，不能贸然补写。

### 8.2. 润色分层架构（由浅入深）

```
Level 1: 表面清理  → 拼写、语法、标点、缩写统一
Level 2: 结构优化  → 章节逻辑、段落衔接、论证递进
Level 3: 表达风险清理  → 识别机械化、重复化和空泛表达
Level 4: 可选风格校准  → 在不越界的前提下做有限风格收口
```

Step 8 只在以下边界内执行这些层级：

- 可以修：语言清理、结构性读者障碍、机械化表达、可选风格收口
- 不可越界：补外部证据、发明新论证、强行统一用户风格、把某种审美当作硬标准
- 用户仍保留自己的写作策略和表达风格

更细的润色示例、AI 痕迹分类与可选风格提示，统一查阅：

- `references/step8-rewrite-scope.md`
- `references/protected-spans.md`
- `references/academic-ai-trace-index.md`
- `references/ai-trace-taxonomy.md`
- `references/deterministic-writing-diagnostics.md`
- `references/scientific-writing-quality-rubric.md`
- `references/polish-modes.md`
- `references/writing-antipatterns.md`

其中 `scientific-writing-quality-rubric.md` 只用于 `subject_action_audit`、`old_new_flow_audit`、`paragraph_function_audit`、`figure_first_argument_plan` 和 `phrasebank_guardrail`。Step 8 可据此修复读者障碍、段落衔接和图文顺序说明，但不得改变 claim 强度，不替代证据审计，也不得把候选证据写成强结论。

`section-quality-gates.md` 与 `reviewer-defect-taxonomy.md` 只服务于诊断和分流。若命中 `abstract_quality_gate / introduction_quality_gate / discussion_quality_gate / conclusion_quality_gate` 的缺失 move，Step 8 可修局部顺序和边界句；若缺失的是结果、证据、图表、基准、稳定性验证或工程约束，必须回退 Step 7/4/6。

### 8.2.1. AI 味确定性检查

Step 8 在 Level 3 表达风险清理前，默认运行“AI 味确定性检查”。该子层不是独立命令，也不是新的完成门，而是 `language_mechanical` 的高置信诊断器。

运行确定性检查前，先按 `references/academic-ai-trace-index.md` 做轻量分流：只定位最影响本轮修订的 Top 5-10 个学术 AI 痕迹问题族，并排除已划入 protected spans 且不应改写的片段。该轻量索引只决定诊断优先级，不改变 issue_type 的固定值域。

**规则族固定为 6 组：**

- `套话短语规则`：高频空泛短语和模板化句式，如 `plays a crucial role`、`it is worth noting that`、`值得注意的是`、`综上所述`。
- `机械连接词堆积规则`：段首或句首连接词使用过密，如 `Moreover / Furthermore / Additionally / Notably`、`此外 / 另外 / 首先 / 其次 / 更重要的是`。
- `伪洞见与悬垂表达规则`：如 `..., highlighting the importance of ...`、`..., underscoring ...` 或结尾挂抽象洞见却未增加实质信息的从句。
- `空泛归因规则`：如 `Studies have shown`、`Experts believe`、`研究表明`、`学者认为`。
- `句长节奏过匀规则`：只做段落/章节级节奏诊断，不对每句单独报错。
- `冗余破折号与插入语规则`：识别过度插入、句内人工拉伸和冗余解释性补充。

**科学空话诊断补充规则族：**

- `mechanism_without_state_variables`：只有“促进/抑制/改善/增强”，没有状态量、控制量或作用路径。
- `causal_jump_without_validation`：从性能变化直接跳到微观机制，没有实验、仿真、消融、图表或全文锚点。
- `visual_claim_without_panel`：写“图中可见/如图所示/由图证明”，但缺 figure/table/panel 绑定。
- `proof_verb_without_evidence`：使用“证明/验证/揭示/表明主导”等强动词，但缺全文级证据锚点。
- `generic_strengthening_list`：堆叠晶粒细化、位错强化、第二相强化、载荷传递等通用机制，却没有当前体系证据。

这些规则只服务于 `mechanism_bluff` 诊断。Step 8 可以把“证明”降为“可能说明/提示/可解释为”，可以补适用边界句，但不能新增文献、补图号、补实验解释或替代 Step 7 引用审计。

**动作矩阵固定为：**

- 可在 Step 8 直接修订：套话短语、机械连接词堆积、悬垂 `-ing` / 伪洞见尾句、冗余破折号/插入语、明显重复表达、句子表面机械化但不改变 claim 的措辞。
  - 默认 `allowed_action=直接修改` 或 `局部补写`
  - 默认 `next_action=保留修改`
- 可修但需轻量含义审计：涉及限定词、比较词、因果词的 AI 味表达；会影响句子强度的模板化短语；与引用落点相邻的空泛归因。
  - 默认 `meaning_audit_required=true`
  - 审计通过才可关闭 issue；否则 `next_action=转人工复核` 或 `return_to_step_7_citation_audit`
- 只提醒，不在 Step 8 内硬修：统计层面的句长均匀、轻度被动语态偏高、少量风格化重复但作者可能有意保留的节奏。
  - 写入 `润色质量报告.md`
  - 可不进入逐条修改
  - 不影响 Step 8 总完成结论

**实现边界：**

- 风格类命中默认不触发 rollback。
- 单纯词表命中不得直接升格为证据问题。
- Step 8 不因“AI 味”要求用户回跑主写作。
- `full_manuscript` 或 audited polish 必须生成 `authorial_revision_record.json`；direct-entry 局部低风险润色只需最小记录，不要求补跑 Step 7。
- 不以 detector score、perplexity 或 burstiness 为优化目标；不得承诺“通过 AIGC 检测”。

---

### 8.3. 最小验证规程

Step 8 不要求证明文本“更高级”，但必须验证低风险修订没有把正文改坏。每个进入 `revision_ledger` 的问题，至少执行以下 4 项验证：

#### 8.3.1. 术语一致性验证

- 检查同一概念是否仍出现多种叫法混用
- 检查缩写首次定义、后文一致性、中英文术语/符号是否统一
- 结果值：`PASS / WARN / FAIL`

#### 8.3.2. 核心含义漂移验证

- 检查修订后主语、对象、关系、结论方向是否改变
- 检查是否新增原文没有的因果、范围或结论
- **硬门槛**：出现明显含义漂移，直接 `FAIL`

#### 8.3.3. 论断强度验证

- 检查 claim 是否被意外增强
- 允许降强度，不允许升强度
- 检查限定词、边界条件是否被删掉
- **硬门槛**：出现论断意外增强，直接 `FAIL`

#### 8.3.4. 引用/指代/衔接验证

- 检查 citation 是否仍支撑对应句子
- 检查指代对象是否明确
- 检查句间逻辑连接是否被改断
- 结果值：`PASS / WARN / FAIL`

#### 8.3.5. 总判定规则

- 任一硬失败项 -> `FAIL`
- 无失败但存在风险 -> `WARN`
- 全部通过 -> `PASS`

推荐运行 before/after 保真审计：

```bash
python3 scripts/audit_polish_fidelity.py 论文初稿.md 论文润色稿.md \
  --output-json polish_fidelity_audit.json \
  --output-md polish_fidelity_audit.md
```

`run_step8_ai_trace.py` 在检测到 `论文润色稿.md` 时会自动运行同一保真审计。纯诊断只能输出 `ready_to_polish`；只有润色稿存在、保真审计为 `pass` 且机械化表达问题没有回归时，才能输出 `ready_for_finalize`。

保真审计除数字、单位、引用、限定语和否定词外，还必须检查：标题层级、待补证据/TODO 标记、段落论证单元、因果/转折标记、claim 动词及全文修改幅度。段落大规模合并、删除待补证据标记或改变章节标题属于硬失败，不得以“语言更简洁”为由放行。

若 direct-entry Step 8 未提供 `claim_evidence_audit.json`，允许继续保守润色，但必须保留“未提供结构化引用审计”的边界；若该文件已提供，则必须继承其风险，稿件哈希过期或 `unresolved_count>0` 时不得输出 `ready_for_finalize`。

#### 8.3.6. 保真回读与残留味回读

Step 8 完成正文修改前，必须按固定顺序回读：

1. **保真回读**：事实、术语、引用、图表、公式、责任主体、claim 强度和证据边界没有漂移；若失败，先回滚该修改或转人工复核。
2. **残留味回读**：确认高密度路标词、空泛价值拔高、无源归因、伪洞见尾句和机械对称结构已经处理或说明保留原因。

保真回读优先级高于残留味回读。不能为了“更自然”删掉限定条件、移动关键引用、改写 protected spans 或提升 claim 强度。

---

### 8.4. revision_ledger 双层工件契约

Step 8 的问题闭环主工件为：

- `revision_ledger.json`：机器执行源
- `revision_ledger.md`：人工审阅层

`revision_ledger.json` 最小字段固定为：

| 字段 | 说明 |
|------|------|
| `issue_id` | 问题唯一标识 |
| `category` | `可直接修订 / 需作者决定 / 当前依据不足` |
| `issue_type` | 问题类型 |
| `severity` | 严重度 |
| `location` | 章节/段落/句子位置 |
| `before` | 修订前文本或问题片段 |
| `after` | 修订后文本；未修订时记录为空并说明原因 |
| `problem` | 问题描述 |
| `rollback_target` | `none / step_7_revision_only / step_7_citation_audit / step_7_argument_plan / step_4_or_6_evidence_repair` |
| `evidence_basis` | 当前修订依据：正文、三工件、评审或审计输入 |
| `evidence_status` | 当前证据状态：已确认、候选、缺失、需回 PDF、需回 Step 7 |
| `allowed_action` | `直接修改 / 局部补写 / 回退 / 人工决定` |
| `proposed_revision` | 拟采用的修订动作或补写方案 |
| `meaning_audit_required` | `true / false`，当改动触及 claim、引用、限定词、比较词或因果关系时为 `true` |
| `meaning_audit_reason` | 触发轻量含义审计的原因 |
| `verification` | 4 项最小验证结果 |
| `verification_result` | `PASS / WARN / FAIL`，从 `verification` 汇总得到 |
| `final_status` | `PASS / WARN / FAIL` |
| `next_action` | `保留修改 / 转人工复核 / 回退修改 / 回到 Step 7/4/6` |
| `issue_state` | `identified / routed / in_revision / verification_pending / closed / blocked_author_decision / blocked_evidence / invalid_or_not_applied` |
| `state_reason` | 当前状态原因 |

> 与 Step 7 的 `revision_roadmap`、`claim_delta_report`、`evidence_gap_list` 对齐时，至少应能映射到同一组闭环最小字段：`issue_id / chapter_binding / claim_binding / problem_summary / action_type / evidence_status / verification_result / next_action / issue_state / state_reason`。`revision_ledger` 是这组字段的终态收口层。

#### 8.4.1. 轻量含义审计触发

`meaning_audit_required` 只用于风险触发，不把普通润色升级成重审稿。以下改动必须触发：

- 改动 claim 主语、对象、范围或结论方向
- 移动、删除或新增引用落点
- 删除限定词、边界条件、置信表达或适用范围
- 改动比较词、因果词、程度词或强弱动词
- 修改与图表、数据、实验结果直接绑定的句子

触发后只做最小含义审计：检查核心含义是否漂移、claim 是否被增强、引用是否仍支撑对应句子。若无法判断，`final_status` 至少为 `WARN`，并写入 `next_action=转人工复核` 或回退到 Step 7。

---

### 8.5. 修改对照表生成

修改对照表固定使用以下字段：

| 字段 | 说明 |
|------|------|
| 位置 | 章节、段落或句子位置 |
| 原文 | 修改前文本，可截取关键句 |
| 修改后 | 修改后文本 |
| 修改类型 | 语言清理 / 结构优化 / AI 痕迹修复 / 风格校准（可选） / 术语统一 / 引用安全提醒 |
| 修改原因 | 为什么必须改，避免只写“润色” |
| 涉及规则 | Level 编号、术语规则或引用安全提醒 |

记录原则：

- 每章至少保留代表性修改。
- 标点、空格、简单错字不必逐条记录，除非属于系统性错误。
- 引用风险只记录为“引用安全提醒”，不得替代 Step 7 引用审计结论。

### 8.6. 轻量一致性检查（可选增强）

若输入中存在 `response_letter_skeleton.md` 或 `rereview_report.md`，Step 8 只做轻量一致性提醒：

- 润色后正文是否可能与回应信失配
- 是否把原本保守的回应改成了过强 claim

此检查只做告警，不替代 Step 7 的修稿闭环或复评。

---

### 8.7. 终验：术语一致性检查（增强）

**以 `.skill-state/term_aliases.md` 为基准：**

1. 加载 `.skill-state/term_aliases.md` 获取标准术语映射表
2. 逐章扫描正文，提取所有核心术语
3. 对比映射表：
   - 术语是否与 Main Term 一致？
   - 是否存在同义词轮换（Level 2 中的"同义替换综合征"）？
   - 是否在错误章节使用了不该出现的术语变体？
   - `seed` / `provisional` / `locked` 是否与当前证据状态一致
4. 不一致处理：
   - 修正为 Main Term → 记录到 before/after 表
   - 如果 Main Term 选择不当 → 更新 `.skill-state/term_aliases.md` → 记录到 `.skill-state/decision_log.md`
   - 如果属于新术语 → 追加到 `.skill-state/term_aliases.md`
   - `provisional` 术语只做风险提示和统一建议，不得因为尚未收口就硬删；只有证据足够时才提升为 `locked`，而不是把 `seed / provisional / locked` 当作一次性静态名单
5. 输出：术语一致性报告（含修改数、新增术语数、映射表更新说明）

---

### 8.8. DOCX 导出

1. 将终验后的正文保存为 `论文润色稿.md`
2. 先运行 `scripts/equation_guard.py 论文润色稿.md --output-dir .`；公式缺失、纯文本数学或裸 LaTeX/矩阵源码未关闭时禁止导出
3. 使用 `scripts/md_to_docx.py` 生成 `论文润色稿.docx`，保持 Step 7 既有样式、标题层级、图表/公式编号和引用格式
4. 导出后回读 DOCX：源稿有公式时必须存在对应 OMML/Word 原生公式对象，且不得出现 `T(omega)`、`F_{i+1}`、`X_in` 或 `\\begin{bmatrix}` 等纯文本残留
5. 如果 DOCX 生成或公式回读失败，保留 `.md` 终稿，并在润色质量报告中记录失败原因和可复现命令

---

### 8.9. 日志回写

日志回写只写运行态 `.skill-state/` 文件，不修改 `references/templates/`：

| 文件 | 写入条件 | 不写入内容 |
|------|----------|------------|
| `.skill-state/error_log.md` | 新发现的可复用表达风险、系统性术语混用、反复出现的引用风险模式 | 一次性措辞偏好、单句审美判断 |
| `.skill-state/decision_log.md` | Main Term 重大变更、revision scope 变化、影响后续 Step 的结构性决策 | 普通语法修正、局部句式偏好 |
| `.skill-state/term_aliases.md` | 新术语追加、Main Term/Aliases 修正 | 润色说明、修改理由长文 |

---

## CHECKPOINT 8 — CP-POLISH-SCOPE

进入最终润色或交付前，必须确认本轮修改仍停留在 Step 8 范围内：

1. 不新增外部证据、不补写未经 Step 7 确认的引用。
2. 不扩大原有 claim 强度，不把候选证据写成已验证结论。
3. 对 `meaning_audit_required=true` 的改动完成轻量含义审计，无法判断时转人工复核。
4. 若发现证据缺口、章节功能错误或引用不匹配，输出回退目标，而不是继续用润色硬修。

---

## 质量门槛 (Quality Gates)

- [ ] Level 1 已完成；Level 2-4 均记录为 `applied` 或 `not_applicable + reason`，其中 Level 4 仅在用户要求或已有 `style_profile` 时执行
- [ ] `diagnostic_summary.md` 已生成，且问题已按固定 `issue_type` 分类
- [ ] 表达风险检查已输出发现项、已修复项、保留项和保留原因
- [ ] `meaning_audit_required=true` 的改动已完成轻量含义审计或转人工复核
- [ ] `polish_fidelity_audit.json/md` 已生成；硬失败为 0，warning 已人工确认或保留为未关闭项
- [ ] 公式相关稿件的 `equation_audit.json/md` 与 `equation_register.json/md` 已刷新；润色前后公式签名一致，DOCX 公式对象回读通过
- [ ] 标题、段落论证单元、claim 边界、待补证据标记和全文修改幅度已通过 argument fidelity 检查
- [ ] 如提供 `claim_evidence_audit.json`：稿件哈希一致且未关闭风险为 0；未提供时已明确 direct-entry 审计边界
- [ ] `authorial_revision_record.json` 已区分语言编辑、作者确认与待作者输入；高风险智识修改未确认时不输出 `ready_for_finalize`
- [ ] AI 使用披露状态已按学校/期刊/机构规则保留；未作检测规避承诺
- [ ] 🆕 术语一致性检查完成——以 `.skill-state/term_aliases.md` 为基准，全文术语一致
- [ ] 修改对照表已按“位置 / 原文 / 修改后 / 修改类型 / 修改原因 / 涉及规则”产出
- [ ] 缺少评审报告或引用审计报告时，润色质量报告已标记“审计依据不足”
- [ ] 所有 `.skill-state/` 回写均符合日志边界，不误写 `references/templates/`

---

## 收尾检查 (Closing Checks)

### 产出完整性
- [ ] `diagnostic_summary.md` 已生成
- [ ] `论文润色稿.md` 已生成
- [ ] `论文润色稿.docx` 已自动生成
- [ ] DOCX 中矩阵、分式、上下标、希腊字母和编号已作为原生公式显示，无 LaTeX 源码或纯文本数学残留
- [ ] 修改对照表（位置 / 原文 / 修改后 / 修改类型 / 修改原因 / 涉及规则）已产出
- [ ] 润色质量报告已产出（最终风险、降级说明、验证结果、人工复核项）

### 润色质量报告固定区块
- [ ] 诊断阶段 `Overall Status` 已输出：`ready_to_polish / ready_with_warnings / not_ready_requires_rollback`
- [ ] 只有润色稿存在且 before/after 保真验证通过后，终验阶段才可输出 `ready_for_finalize`
- [ ] `Issues Fixed In Step 8` 已输出
- [ ] `Issues Deferred / Rollback Required` 已输出
- [ ] `Next Action` 已输出：`apply_polish_and_verify / finalize_polished_draft / return_to_step_7_revision_only / return_to_step_7_citation_audit / return_to_step_7_argument_plan / return_to_step_4_or_6`

### 术语一致性报告 🆕
- [ ] 全文核心术语已与 `.skill-state/term_aliases.md` 对齐
- [ ] 术语修改数：X 处
- [ ] 新增术语数：X 个（已追加到 term_aliases.md）
- [ ] Main Term 变更数：X 个（已记录到 decision_log.md）

### 错误日志更新 🆕
- [ ] 本轮是否发现了新的可复用表达风险？
  - 如有 → 追加到 `.skill-state/error_log.md`，更新 Level 3 参考清单
- [ ] 术语不一致是否为系统性错误？
  - 如有 → 追加到 `.skill-state/error_log.md`，更新 Step 2/3/7 的术语规则
- [ ] 是否仅记录了可复用的系统性错误？
  - 一次性措辞偏好不得写入 `.skill-state/error_log.md`

### 决策日志更新 🆕
- [ ] 是否调整了 revision scope 或影响后续 Step 的修订边界？→ 记录到 `.skill-state/decision_log.md`
- [ ] 是否修改了术语 Main Term 选择？→ 记录到 `.skill-state/decision_log.md`
- [ ] 是否只记录了影响后续 Step 的结构性决策？

---

## 故障排除 (Troubleshooting)

- **表达风险反复出现**：回查 `.skill-state/error_log.md` 中的可复用表达风险；Level 3 分类逐类排查
- **术语不一致**：以 `.skill-state/term_aliases.md` 为唯一基准，不依赖直觉判断
- **含义审计无法通过**：不要继续润色硬修；转人工复核，或回退到 Step 7 的 claim / citation / argument_plan 层
