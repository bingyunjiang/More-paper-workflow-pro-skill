# Step 7 Router: 写作与写作前证据组织入口

本文件是 Step 7 的路由层，不替代 [step_7_writing.md](./step_7_writing.md)。

## 作用

- 将 Step 7 从单一超长协议拆成多个子模式
- 默认使用 `target_genre` 驱动，而不是期刊 prestige 驱动
- 让 style learning、citation audit、pre-review 等能力按需加载
- Step 7 内部可完成基础可读性整形，但用户不需要感知内部写作流水线；外部入口仍只有写作、续写、综述、审稿前自检等任务。
- Step 7 同时支持写文后补图和写作中同步插图；图文必须共享同一条证据链，不允许正文和图表分开漂移。

## mode 轴

- `full-document`
- `chapter-only`
- `continue-existing`
- `abstract-only`
- `review-only`
- `revision-only`

## operation 轴

| operation | 作用 |
|---|---|
| `write` | 按当前 `mode` 执行写作、续写、综述或定向修订 |
| `citation-audit` | 只做 claim 与引文证据审计 |
| `figure` | 只做图表生成、复现、数字化或图文接口 |
| `pre-review` | 只做审稿人视角预审 |

`operation` 不替代 `mode`。进入 `citation-audit / figure / pre-review` 时，
仍保留当前文本范围的 `mode` 作为边界；默认 `operation=write`。

## figure_mode 轴

- `auto_insert`
- `post_write`
- `skip`

## figure_backend 轴

- `auto`：先判断是否需要生成新图，再按输入和交付要求选择后端
- `quick`：从可信结构化数据生成普通论文图表
- `reproduction`：重绘、数字化、视觉对齐、语义审计或可复现交付
- `not_applicable`：只筛选并插入已有图，不运行绘图代码

## target_genre 轴

- `thesis`
- `journal`
- `review`
- `report`
- `proposal`
- `conference`
- `course-paper`

`existing-draft` 是现有文本的入口状态，由 `mode=continue-existing|revision-only` 表达，不属于 `target_genre`。

## 路由规则

- 用户说“开始写/基于文献写全文” -> `full-document`
- 用户说“只写某章/只补某节/按章节写” -> `chapter-only`
- 用户说“续写已有草稿/基于现有正文继续写” -> `continue-existing`
- 用户说“只写摘要/中英摘要” -> `abstract-only`
- 用户说“写文献综述” -> `review-only`
- 用户说“按审稿意见修改/修稿/逐条回应后改正文” -> `revision-only`
- 用户说“自动插图/同步插图/写完顺手补图” -> 进入 Step 7 图文联合链路，默认 `figure_mode=auto_insert`
- 只插入 MinerU/PDF/本地已有论文原图 -> `figure_backend=not_applicable`；这是图文联合的默认路径，不重绘、不数字化
- 用户明确要求基于 CSV、实验数据或统计结果生成普通新图 -> `figure_backend=quick`
- 只有用户明确要求“重绘/复现/恢复曲线数值/转成可编辑矢量/严格图形 QA”时 -> `figure_backend=reproduction`
- `reproduction` 中如果需要从图片/PDF恢复数值，必须完成 `inspect → spec-review/用户确认 → candidates → 自动诊断 → review-decisions → observations → data → VisualSpec`；只有 `extraction_status=formal_data_ready`、`review_status=complete` 后才交给 reproduction。只做视觉重绘、不恢复数值时不需要该前置链。
- 发现参考图、截图、裁剪图或 VisualSpec 本身不构成重绘授权；必须记录 `figure_transform_authorization=explicit_user_request`
- 用户显式指定 `quick/reproduction` 时覆盖默认插图路径；严格后端缺依赖时中止并提示安装，不得静默降级

## Artifact Passport 读取规则

Step 7 启动时先检查 `$CWD/.skill-state/artifact_passport.json`：

- 有 `draft` 时，可直接进入 `continue-existing` 或 `chapter-only`，不要求回跑 Step 6。
- 有 `zotero_mapping / pdf_index / bibliography / workflow_search_results` 时，可进入 `full-document / review-only / chapter-only`。
- 有 `citation_audit` 时，可进入基于审计结果的 `revision-only`，或作为 `continue-existing / chapter-only` 的风险输入。
- 缺 `pdf-附件池索引.json` 或证据矩阵时，生成最小映射和风险标记；不得声明引用安全通过。
- Passport 的全局 `route_mode` 只决定 direct-entry/plan-only/repair，不覆盖本文件的 Step 7 `mode` 和 `target_genre`。

Artifact graph 只负责登记当前可用材料和可确认关系，不强制线性 Step 4→5→6→7：

- `zotero_item / evidence_item / claim / draft_section` 可以从 Zotero、evidence pack、MinerU ZIP、已有初稿或章节大纲独立登记。
- 每个正文 claim 或引用映射必须带 `reading_depth` 与 `trace_status`；`trace_status=inferred/unlinked` 只能支撑候选、背景或待确认表达。
- `metadata_only`、`abstract_only` 或 `unlinked` 证据必须显式进入 `citation_risk_summary` / `evidence_gap_list`，不得被写成全文已读或 confirmed evidence。
- 只有 `evidence_item -> claim` 或 `claim -> draft_section` 关系有明确 evidence id、citation key、页码/段落/注释来源时，才可标为 confirmed。
- direct-entry 下允许先产出“当前入口可继续版本”；如果用户要求“全链路可追溯”，则必须把缺失的 Step 4/5/6 关系列为待补任务。

## 图文联合规则

- Step 7 开始图文处理前运行 `scripts/build_figure_asset_check.py`，将已发现的 MinerU ZIP、`figure_index.json`、本地图片目录和 PDF 写入 `figure_asset_check.json/md`；不得仅靠口头判断资产状态。
- `auto_insert_figures=true` 时，条目必须具备 `LLM-for-Zotero-MinerU-cache-*.zip` 或等价图文资产包。
- 没有 MinerU ZIP 但本地 PDF 可读时，允许先进入 `post_write`，用 PyMuPDF 生成 `pdf_direct` 低置信候选图；没有可读 PDF 或无候选图时，才只能放图位占位，不自动选图。
- `post_write` 用于正文先完成、后按章补图；`auto_insert` 用于写作中同步扫图位。
- `skip` 允许用户显式跳过插图，只保留正文和图位说明。
- `figure_mode` 决定是否及何时插图，`figure_backend` 决定需要生成新图时使用哪条代码路径；二者不得混用。
- 原图插入完成后，在本次任务的图表交付说明中提醒一次：“已按论文原图插入。本 skill 也支持图表重绘、曲线数字化、可编辑 SVG/PDF 和严格 QA；如需启用，请明确指定要重绘的图及目标。”提醒不构成授权，不得因此自动启动 quick/reproduction。
- 选择 `reproduction` 时按需加载 `references/scientific-figure-reproduction.md`。

## 加载顺序

1. `manifest.step7.yaml`
2. `static/core/output-contract.md`
3. `references/genre-style-axis.md`
4. `references/writing-modes.md`
5. mode 与 operation 对应 reference
6. `agents/step_7_writing.md`

## 输出要求

Step 7 的正式输出应显式说明：

- `mode`
- `operation`
- `target_genre`
- `figure_mode`
- `figure_backend`
- `figure_asset_action`
- `evidence_basis`
- `citation_risk_summary`
- `recommended_next_step`

## existing-draft 三类入口边界

### `continue-existing`

- 适用：已有草稿，需要继续写主体内容
- 最小输入：已有草稿 + 续写范围或续写目标
- 最小输出：更新后的正文 + 当前章节/段落的证据状态说明
- 边界：允许继续展开主体内容，但仍不得跳过候选定位和原文确认

### `chapter-only`

- 适用：只处理指定章节或小节
- 最小输入：章节范围 + 最小证据基础（Zotero / PDF / BibTeX / workflow JSON / 已有草稿之一）
- 最小输出：章节草稿 + `argument_plan` + 候选/确认状态
- 边界：章节内部可走候选证据层，但不擅自扩写到未指定章节

### `revision-only`

- 适用：已有草稿 + 审稿意见或明确修订目标，只做定向修订
- 最小输入：已有草稿 + 审稿意见/修订目标 + 至少可追溯的证据状态
- 最小输出：修订正文 + `revision_roadmap.md` + `claim_delta_report.md` + `evidence_gap_list.md`
- 边界：只做定向修订，不接管主体重写；证据不足时优先回退或补证据，不得仅靠降级措辞掩盖问题
