# Step 6: Zotero 文库管理

> Step 6 负责把 Step 4 的 BibTeX 条目、Step 2 的论文大纲、Step 5/其他来源的 PDF 附件池整理成一个可审阅、可恢复、可追溯的 Zotero 文库整理计划，并尽可能完成低风险 Zotero 写入。

---

## 启动前读取 (Pre-read Checklist)

执行本步骤前，优先确认当前任务需要哪些输入；若缺少标准链路产物，则在本 Step 内生成 plan-only 映射、只读扫描结果或缺口报告，而不是要求用户回跑前序步骤：

- [ ] `agents/step_2_outline.md` — 大纲关键词（章节结构 + 术语映射表；可缺失，缺失时允许从现有集合名/用户目录反推最小结构）
- [ ] `agents/step_4_search_score.md` — 检索筛选结果与 `文献库.bib` 生成规则（可缺失，缺失时允许从 BibTeX/JSON/现有 Zotero 反推 plan-only）
- [ ] `agents/step_5_download.md` — Step 5 下载 PDF（paper-temp/）及后续补下载入口（可缺失，只影响附件来源说明）
- [ ] `references/zotero-structure-template.md` — Zotero 架构示例
- [ ] `references/zotero-outline-mapping.md` — 文献与集合对齐思路
- [ ] `references/zotero-output-contract.md` — 🆕 JSON + Markdown 双工件输出契约
- [ ] `references/zotero-entry-modes.md` — 🆕 Step 6 direct-entry 模式
- [ ] `references/paper-card-contract.md` — `paper_card`、Zotero child note 与短 tag 索引同步契约
- [ ] `capability_index.json/md` — 🆕 文献资产能力索引（如已存在，先读；如缺失，本 Step 生成）
- [ ] `.skill-state/error_log.md` — 已知错误及修复规则
- [ ] `.skill-state/decision_log.md` — 影响本 Step 的结构性决策

---

## 适用任务 (Applicable Tasks)

- 依据 Step 2 论文大纲生成 Zotero 集合架构（6.1）
- 依据 Step 4 `文献库.bib` 和 6.1 架构生成文献-集合对照表（6.2）
- 保留 Step 4 `paper_card`，并在真实 Zotero 导入时同步为每篇 T1-T3 文献的 `More-Paper Evidence Card` child note
- 通过 Zotero MCP 创建 Zotero 集合并检查架构一致性（6.3）
- 将 PDF 附件池中的文件纳入附件状态判断，生成安全的附件处理策略（6.4）
- 生成 `capability_index.json/md`，让用户和后续 Step 清楚知道当前可用的 Zotero、PDF、BibTeX、workflow JSON、附件池能力与推荐入口

---

## 不适用任务 (Non-applicable Tasks)

- 论文写作 → 路由到 `agents/step_7_writing.md`
- 文献综述矩阵 → 路由到 `agents/step_7_writing.md`
- 目标期刊风格学习 → 路由到 `agents/step_7_writing.md`
- PDF 下载 → 路由到 `agents/step_5_download.md`

---

## 输入要求 (Input Requirements)

| 输入 | 来源 | 格式 | 必选 |
|------|------|------|:--:|
| 大纲关键词 / 章节结构 | Step 2 / 用户已有目录 / 当前 Step 反推 | `大纲关键词.md`、目录、草稿、集合层级 | 规划集合时推荐其一 |
| 筛选后文献库 | Step 4 / 用户已有文献库 | `文献库.bib`、workflow JSON、CSL JSON | 计划导入时推荐其一 |
| PDF 附件池 | Step 5 / 原有文件 / 后续补下载 | `paper-temp/`、用户指定目录、补下载目录 | 附件规划时推荐 |
| MinerU ZIP 缓存 | Zotero 附件 / 用户提供 | `LLM-for-Zotero-MinerU-cache-*.zip` | 图文写作增强时可选 |
| Zotero 模式选择 | 用户确认 | `local` / `cloud` / `skip` | ✅ |
| Zotero MCP 可写连接 | 环境配置 | MCP 工具 | 仅真实写入时必选 |

> 标准链路下推荐使用 Step 4 生成的 `文献库.bib`。但 Step 6 不把它当成唯一合法入口：若用户已有 Zotero 文库、已有 BibTeX/CSL JSON、已有 workflow search results JSON、已有 PDF 目录或只想整理现有集合，也可直接进入本步骤。
> Zotero 是 Step 7 的推荐资产管理层，不是唯一写作入口。若用户没有 Zotero 或选择 `skip`，Step 7 可改走本地 `evidence_pack`；Step 6 只需把可用 PDF、MinerU ZIP、文献库和缺口记录清楚。

**大纲对齐分类边界：**

- Step 6 才是文献与大纲二级标题对齐的 Zotero 集合组织入口，不做脱离大纲的自由分类。
- Step 3 的关键词分层只用于检索式构造，不作为 Zotero 分类规则。
- 标准链路下，Zotero 根集合为论文标题，一级集合只作为一级章节容器；文献默认直接归入对应的大纲二级章节集合，方便 Step 7 按小节集合限定证据链范围。
- 新建集合和子集合优先依据 Step 2 大纲二级章节；关键词、证据类型和文件名匹配只做标签或降级匹配。
- 有前序文献-大纲映射时，入库集合路径应直接复用该映射，不重新按关键词猜章节。

**Artifact Passport / Direct-entry Graph：**

- Step 6 可从 Zotero 集合、BibTeX、workflow JSON、PDF 附件池、PDF 索引或既有 `文献-Zotero架构对照.*` 直接进入；不要求 Step 5 已跑过。
- `artifact_passport.json` 中 Zotero 相关材料登记为 `zotero_item`，PDF/附件池登记为 `pdf_attachment`，BibTeX/workflow JSON 登记为 `search_record`。
- Zotero 对账必须区分 `matched_attachment`、`missing_attachment`、`unlinked_pdf`、`duplicate_candidate`；其中 `unlinked_pdf` 只能表示待匹配 PDF，不能表述为已挂载附件。
- 只有 Zotero item key、集合路径、附件路径或对照 JSON 明确一致时，`imported_to_zotero` / 附件关系才能视为 confirmed；标题相似、同目录共存或文件名相似只能视为 inferred。
- direct-entry 下缺 Step 4/5 不是阻塞项；只需在 gaps/risks 中说明来源链缺口和后续补齐动作。

**资产整理执行纪律：**

- `交付定义`：本步交付的是 Zotero 架构、文献-集合对照、附件池索引、capability index 和写入计划；不是下载 PDF，也不是写作证据裁决。
- `输入依赖`：Zotero 写入依赖用户选择 `local / cloud / skip` 和 `CP-ZOTERO-WRITE`；plan-only 只依赖可读取的 BibTeX、workflow JSON、Zotero 集合或 PDF 目录。
- `可委派边界`：Agent 可以自动扫描、匹配、生成计划和低风险元数据补全；用户必须决定真实 Zotero 写入、冲突合并、权限受限附件和高风险覆盖。
- `最小实验优先`：新文库、来源混杂或匹配质量未知时，先生成 plan-only 双工件或小批量 smoke plan，再做真实写入。
- `快速通道不跳质量门`：已有 Zotero 文库可直入 Step 6，但仍要区分 `matched_attachment / missing_attachment / unlinked_pdf / duplicate_candidate`，不得把 inferred 关系写成 confirmed。

**工件读取优先级：**

从本版开始，Step 6 对上游输入的优先顺序为：

1. `workflow_search_results.json`
2. `文献库.bib`
3. `文献-Zotero架构对照.json`
4. 对应 Markdown 审阅版

如果 JSON 和 Markdown 同时存在，以 JSON 为准；Markdown 仅作为人工审阅和解释层。

---

## 标准输出 (Standard Outputs)

**执行档位：**

| execution_profile | 允许动作 | 完成状态 |
|---|---|---|
| `plan-only` | 只读扫描、查重、生成集合/条目/附件计划，不修改 Zotero | `plan_ready` 或 `blocked` |
| `write` | 在 `CP-ZOTERO-WRITE` 确认后执行计划并逐条回读验证 | `write_partial / write_complete / blocked` |
| `repair` | 只处理既有计划中的失败、冲突、缺附件和可重试操作 | `write_partial / write_complete / blocked` |

每个档位使用同一份 `文献-Zotero架构对照.json`、`plan_fingerprint` 和 operation journal。`plan-only` 是有效交付，不要求存在真实 Zotero 集合；`write_complete` 则必须有当前 fingerprint 下的逐记录成功证据。

`execution_profile` 表达任务阶段（plan-only/write/repair）；既有 `execution_mode=local|cloud|skip|plan-only` 只表达 Zotero 连接/写入后端。两者正交：write/repair 必须选择 local 或 cloud，plan-only/skip 不得冒充 write。

统一 run envelope 中，`plan_ready / write_partial / write_complete / blocked` 写入 `domain_state`；全局 readiness 分别映射为 `partial / partial / complete / blocked`。`plan_ready` 可以 `can_continue=true`，但不得改写成真实 Zotero 已完成。

| 输出 | 格式 | 说明 |
|------|------|------|
| `zotero-架构.md` | Markdown | 基于论文大纲生成的 Zotero 集合结构 |
| `zotero-架构.json` | JSON | 供 MCP 递归创建集合使用的树结构 |
| `文献-Zotero架构对照.md` | Markdown | 人类审阅版映射表，可截断长字段 |
| `文献-Zotero架构对照.json` | JSON | 机器执行源，所有字段完整，禁止截断 |
| `pdf-附件池索引.json` | JSON | 多来源 PDF / MinerU ZIP / supplement 附件的完整路径、来源、匹配状态 |
| `prepared_pdf_artifacts.json` | JSON | 可选的 PDF 提取产物索引：raw/clean/chunks/report 路径、证据层级、风险标记 |
| `capability_index.json` | JSON | Step 6 资产能力索引：记录可用文献资产、证据入口、缺口、建议 Step 和降级说明 |
| `capability_index.md` | Markdown | `capability_index.json` 的人工审阅层，帮助用户判断“现在能从哪一步继续” |
| Zotero 集合 | Zotero | 与 `zotero-架构.json` 一致的集合树 |
| Zotero 条目 + PDF/MinerU ZIP 附件状态 | Zotero / JSON | 元数据可低风险导入；PDF/MinerU ZIP 附件默认只判断状态，不直接挂载 |

---

## 执行流程 (Execution Flow)

### 6.1. Zotero MCP 写入能力检查

执行任何 Zotero 写操作前，先确认 MCP 工具可用且具备写入能力：

```bash
python3 scripts/setup_zotero.py --install --target auto
python3 scripts/setup_zotero.py --smoke-test
```

**必须确认：**
1. Zotero 桌面端已运行，且本地文库可访问。
2. `zotero_create_collection`、`zotero_add_by_bibtex`、`zotero_add_from_file`、`zotero_manage_collections` 等写入工具可用。
3. 如果当前本地 API 配置只读，必须切换到可写 MCP 配置（Web API / hybrid / 上游支持的本地写入模式），否则不能执行 6.3/6.4。
4. 若上游已升级到 `zotero-mcp-server 0.5.0`，可额外使用 `zotero_read_pdf_pages` 做按页取证，优先替代“整篇全文读取”作为局部核验手段。

**如果用户选择跳过 Zotero 写入，或当前 MCP 不可写：**
1. 只执行 6.1 和 6.2。
2. 在 `文献-Zotero架构对照.md/json` 中把集合创建、条目导入、PDF 附件标记为「后续手动处理」。
3. 缺文件不是致命错误；应在 JSON 顶层写入 readiness、blocking_missing、nonblocking_missing、warnings 和 recommended_next_step。

**独立入口规则：**
如果用户已有 Zotero 文库、已有 PDF 目录、已有 BibTeX/CSL JSON 或只想整理某个集合，可直接从 Step 6 开始，不要求补跑 Step 1-5。Agent 可先读取 Zotero、生成对照表、检查重复、扫描 PDF、生成写入计划；只有即将实际修改 Zotero 这个外部持久状态时，才触发 `CP-ZOTERO-WRITE`。

**Step 6 入口第一问：**

进入 Step 6 后，必须先确认 Zotero 模式：`local` / `cloud` / `skip`。该选择决定后续读写能力和附件策略；**默认推荐并优先使用 `local` 模式**；不得静默默认 cloud。

> **写入原则（强约束）：**
> - Step 6 默认使用 **Zotero MCP 的 `local` 模式** 完成条目入库与集合管理。
> - **不得使用 SQLite 直写** 作为默认入库路径；SQLite 只可作为诊断/只读上下文，不作为常规写入方案。
> - 导入优先级应为：先把条目批量写入 Zotero，再做 DOI/API 二次补元数据；不要把“单条 DOI 在线解析”放在批量入库之前，避免拖慢主流程。

**Step 6 对话入口约定（默认按任务意图触发，不让用户手动挑文件）：**

- 用户在对话中默认只需要表达目标，例如：
  - `把当前 Step 4 结果导入 Zotero`
  - `开始 Step 6，导入 Zotero`
  - `把英文和中文文献都入库到 Zotero`
- Agent 默认不得先要求用户手动指定 `文献库.bib`、`中文论文元数据.json` 或 workflow JSON 路径。
- Agent 应先读取当前工作目录/已知工件，按下方分流规则自动决定使用哪个文件。
- 只有在以下情况，Agent 才应追问具体文件来源：
  1. 默认工件缺失或彼此不一致；
  2. 用户明确说要覆盖默认来源（例如“不要用 Step 4 的 bib，改用我自己的 bib”）；
  3. 用户同时提供多份同类工件，且无法安全判断哪份是主版本。

**用户触发 PDF 绑定 / 重建 Zotero 对照的标准口令：**

- 用户默认不需要提脚本名（如 `build_zotero_plan.py`）。
- 只需要表达任务意图，Agent 应自动理解为“扫描 PDF 目录 + 更新 `pdf-附件池索引.json` + 重建 `文献-Zotero架构对照.json/md`”。

推荐用户口令：

- `重新扫描 PDF 并更新 Zotero 对照`
- `把下载好的 PDF 绑定到当前文献`
- `更新 PDF 附件池索引`
- `继续 Step 6，并重新扫描 PDF 目录`
- `按当前文献结果和 PDF 目录更新 Zotero 对照`

Agent 收到上述口令后，应默认执行：
1. 确认或读取当前 PDF 目录；
2. 更新 `pdf-附件池索引.json`；
3. 重建 `文献-Zotero架构对照.json` 和 `文献-Zotero架构对照.md`；
4. 回显哪些文献已绑定 PDF、哪些仍缺失。

若 PDF 目录不明确，Agent 才应追问：
- `请给我 PDF 目录路径`
- 或在支持结构化交互时，给出目录来源选项。

**默认回显格式（进入写入前）：**

- Agent 应先回显本轮导入分流计划，例如：
  - 英文条目：将从 `文献库.bib` 导入
  - 中文条目：将从 `中文论文元数据.json` 导入
  - 若某一侧缺失：明确说明将重建、跳过或等待用户确认
- 然后再进入 `CP-ZOTERO-WRITE`，而不是让用户先手动挑文件。

**默认自动后处理（无需用户额外交待）：**

- 一旦用户已经触发 Step 6 并确认实际写入 Zotero，以下动作默认视为**顺序执行的一部分**，不需要用户再单独发口令：
  1. 主条目入库；
  2. 高确定性次 collection 自动挂接；
  3. 生成 `Zotero 次挂执行报告.md`；
  4. 对英文已入库条目执行 DOI/API 二次补元数据；
  5. 回写更新后的 `文献-Zotero架构对照.json/md`。
- Agent 不应在上述动作之间反复要求用户回复“继续下一步”“继续次挂”“开始 DOI 补元数据”。
- 只有在以下情况才应中断自动顺序并请求用户判断：
  - 批量命中不唯一；
  - 目标 collection 冲突；
  - DOI/API 返回元数据冲突或覆盖风险较高；
  - 大规模失败需要用户决定是重试、跳过还是回滚。

**下一步动作提示要求（必须给用户可执行下一步，而不只是状态说明）：**

- Agent 在每个关键节点都应告诉用户“接下来你可以怎么做”，至少包含一个推荐动作。
- 不能只说“已检测到缺失”“计划如下”“等待确认”，必须补一句面向用户的可执行提示。
- 若宿主支持结构化交互，可把下一步动作做成按钮/选项；若不支持，则必须用纯文本明确写出推荐回复或推荐命令。

推荐模板：

- 模式确认后：
  - `下一步：请回复 local / cloud / skip 之一，我将按该模式继续生成 Zotero 入库计划。`
- 已识别到默认工件并完成分流计划后：
  - `下一步：若按默认规则继续，请回复“继续 Step 6”；若要覆盖默认来源，请直接说明要改用哪份 bib/json。`
- 检测到缺失工件后：
  - `下一步：你可以选择让我先重建缺失工件，或提供你自己的文件。推荐先回复“重建缺失工件”。`
- 即将写入 Zotero 前：
  - `下一步：若确认执行 Zotero 写入，请回复“确认 CP-ZOTERO-WRITE”；若只想先看计划，请回复“仅生成 plan”。`
- 写入受阻或附件能力受限时：
  - `下一步：你可以先继续做元数据入库，附件稍后手动处理；若接受该降级，请回复“按降级方案继续”。`

**用户可直接复用的标准回复词：**

- `继续 Step 6`
- `重建缺失工件`
- `仅生成 plan`
- `确认 CP-ZOTERO-WRITE`
- `按降级方案继续`

| 模式 | 允许动作 | 禁止/限制 |
|------|----------|-----------|
| `local` | 读取本地 Zotero、生成计划、在确认后写入集合/条目、尽可能处理附件；默认首选模式 | 写入前仍需 `CP-ZOTERO-WRITE` |
| `cloud` | 元数据规划、Web API 可用范围内的条目/集合操作 | 通常不能自动挂载本地 PDF，必须提示附件限制 |
| `skip` | 只生成 `文献-Zotero架构对照.md/json` 和 `pdf-附件池索引.json` | 不调用 Zotero 写入工具 |

**Direct-entry input contract：**

| 可接受输入 | 最小处理 | 输出 |
|------------|----------|------|
| `文献库.bib` + PDF 目录 | 生成 plan-only 对照与附件索引 | `文献-Zotero架构对照.*`、`pdf-附件池索引.json` |
| workflow search results JSON | 转为 Zotero plan 候选，中文保留 source_id/article_url | plan-only JSON |
| 已有 Zotero 集合 key/路径 | 只读扫描集合、条目、附件状态 | 最小映射和缺口报告 |
| CSL JSON / 中文论文元数据 | 中文条目 plan，Extra 写 source_id，不伪造 DOI | 中文入库计划 |
| 只有 PDF 文件夹 | 扫描附件池，按文件名/元数据尝试匹配 | PDF index + 未匹配清单 |
| MinerU ZIP 文件 / 目录 | 识别 `LLM-for-Zotero-MinerU-cache-*.zip`，读取 `_llm_source.json` 最小元数据 | 附件池索引 + Step 7 图文增强候选 |

`scripts/build_zotero_plan.py` 是 plan-only 入口：可在缺少部分输入时继续生成 readiness、blocking_missing、nonblocking_missing、warnings、recommended_next_step。它不调用 Zotero MCP，不修改 Zotero 文库。

计划转为真实写入时，Agent 必须按统一编排执行：读取并校验当前 `plan_fingerprint` → 输出 `CP-ZOTERO-WRITE` 范围 → 用户确认 → 按计划执行低风险 MCP 写操作 → 每个 operation 写入 `zotero_operation_journal.py` → 回读集合/条目/附件 → 运行 `validate_step6_output.py`。不得跳过 journal 直接把 state 文件改为 `write_complete`。

```bash
# JSON / Zotero 只读扫描 direct-entry
python3 scripts/build_zotero_plan.py --records-json zotero_readonly_scan.json

# PDF-only direct-entry，不依赖 Step 5
python3 scripts/build_zotero_plan.py --pdf-dir ./user-pdfs

# 真实 Zotero 写入后追加幂等操作事件
python3 scripts/zotero_operation_journal.py --output-dir . \
  --operation-type create_item --target-id zrec-0123456789abcdef \
  --plan-fingerprint zplan-0123456789abcdef0123 \
  --status success --zotero-key ABCD1234 --checkpoint-confirmed
```

`record_id` 由 DOI/source_id/标题-作者-年份和 citekey 的稳定身份生成，不使用输入序号；同一输入重排后 ID 不变。`plan_fingerprint` 绑定集合路径、导入方式和附件动作；新计划不得复用旧计划的 success operation。

**可选增强提示：**

如果用户已安装 Zotero，并计划写带图综述、图文版 Word 文档或需要批量复用图表候选，建议在 Zotero 中安装 `llm-for-zotero` 插件，并尽量对核心 PDF 执行 MinerU 解析。解析结果通常会以 `LLM-for-Zotero-MinerU-cache-*.zip` 附件回挂到同一 Zotero 条目，供 Step 7 复用。该提示不构成入口门槛；没有插件或 ZIP 时，Step 7 仍可走 Zotero fulltext、PDF 原文或本地 `evidence_pack`。

**附件角色约定：**

`pdf-附件池索引.json` 中附件应尽量标注 `attachment_role`：

| attachment_role | 含义 | Step 7 用途 |
|-----------------|------|-------------|
| `pdf` | 论文 PDF 原文 | 最终真值源，支撑全文、页码、图注、表格、公式核验 |
| `mineru_zip` | MinerU 回挂到 Zotero 的 ZIP 缓存 | 图文增强层，读取 `manifest.json`、`full.md`、`images/` |
| `supplement` | 试验报告、数据、补充图片、标准文件等 | 用户证据包或补充材料，需标注证据等级 |

MinerU ZIP 通常与论文 PDF 挂在同一 Zotero item 下。`_llm_source.json` 中的 `parentItemKey`、`attachmentKey`、`sourceFilename` 是回挂依据；若 ZIP 与 PDF 无法匹配，只能作为本地证据包候选，不得自动升级为某篇文献的图表证据。

**双工件契约：**

无论从哪种入口进入，只要 Step 6 生成了正式整理结果，默认应同时产出：

- 一个可机读 JSON
- 一个可人工审阅 Markdown

缺输入时也应优先产出 plan-only 双工件，而不是只给口头建议。

**CHECKPOINT W — CP-ZOTERO-WRITE（Zotero 外部状态写入确认）**

`CP-ZOTERO-WRITE` 不是 Step 6/7 的入口门，也不是读取 Zotero 前的许可门。它只表示：执行任何会改变 Zotero 文库的写操作前，必须输出 checkpoint 块并等待用户明确确认写入范围。只读操作、计划生成、查重和 dry-run 不触发本 checkpoint。

```md
## CHECKPOINT W — CP-ZOTERO-WRITE

route_mode: normal_chain|direct_entry|resume|repair|partial_artifact
status: confirmed_by_workflow|satisfied_by_user_artifact|satisfied_by_agent_reconstruction
blocks_next: actual Zotero write operations only
must_confirm: true

summary:
- 即将创建/复用的集合数量
- 即将导入、移动或更新的条目数量
- WARN 待审项、REJECT 排除项和附件动作风险

does_not_block:
- 读取 Zotero 集合/条目/笔记/附件
- 生成 `文献-Zotero架构对照.md/json`
- 扫描 PDF 附件池
- 查重报告和写入 dry-run

required_confirmation:
- “确认 CP-ZOTERO-WRITE”
```

---

### 6.2. 根据 Step 2 大纲生成 Zotero 架构

输入：`大纲关键词.md`

```bash
python3 scripts/organize_zotero.py 大纲关键词.md --output zotero-架构.md --json zotero-架构.json

# 可选：显式覆盖根集合名
python3 scripts/organize_zotero.py 大纲关键词.md \
  --root-name "自定义根集合名" \
  --output zotero-架构.md --json zotero-架构.json
```

输出：
- `zotero-架构.md`：给用户审阅的集合结构和标签方案
- `zotero-架构.json`：给 6.3 MCP 自动创建集合使用的树结构

**质量要求：**
- 根集合应尽量明确；标准链路下优先从 `大纲关键词.md` 中解析论文标题，direct-entry 时也允许从用户目录、现有 Zotero 根集合、项目名或用户指定名称中反推。
- 根集合解析优先级：
  1. `## 论文标题` 下方第一段非空文本。
  2. `论文题目：xxx`、`题目：xxx`、`标题：xxx`、`研究主题：xxx`。
  3. YAML/frontmatter 中的 `title`。
  4. 一级标题，但必须排除 `论文大纲与关键词`、`论文大纲`、`大纲关键词` 等模板标题。
  5. 全部失败时回退为 `论文文献库`。
- 用户显式传入 `--root-name` 时，以用户指定为准。
- 标准链路中，集合树应优先复用 Step 2 大纲层级：根集合为论文题目，一级集合只作为一级章节容器，文献默认直接归入对应的大纲二级章节集合。
- 三级及更深集合只有在大纲真实存在对应层级时才创建；不得用关键词、证据类型或单篇文献临时替代大纲层级。
- 关键词、证据类型、方法路线和研究对象默认进入标签、note 或 `paper_card` 字段，不作为主集合层级。
- 不为单篇论文创建集合；单篇论文归属通过条目、标签和附件体现。
- 架构生成后先向用户展示概要，确认后再进入 6.2。

---

### 6.3. 生成文献-Zotero架构对照

输入：
- `文献库.bib`（Step 4 筛选后的 BibTeX 文献库）
- `中文论文元数据.json`（如存在中文文献；兼容旧名 `chinese_papers.json` / `chinese_metadata.json`）
- `workflow_search_results.json` 或 `文献-大纲对照.json`（如存在；用于复用前序文献-大纲映射）
- `zotero-架构.md`
- `zotero-架构.json`
- PDF 附件池目录：Step 5 下载目录（通常为 `paper-temp/`）、项目原有 PDF 目录、用户后续补下载目录

推荐命令：

```bash
python3 scripts/build_zotero_plan.py \
  --bib 文献库.bib \
  --structure zotero-架构.json \
  --workflow-results workflow_search_results.json \
  --pdf-dir paper-temp/ \
  --chinese 中文论文元数据.json \
  --output 文献-Zotero架构对照.json \
  --review 文献-Zotero架构对照.md \
  --pdf-index pdf-附件池索引.json
```

如果某篇 PDF 已进入全文层，推荐改用这条串联 workflow：

```bash
# A. 先把单篇 PDF 准备成全文工作层
python3 scripts/prepare_pdf_for_llm.py \
  --pdf paper-temp/example.pdf \
  --paper-title "Example Paper" \
  --citekey wang2024example \
  --out-dir pdf-prepared/

# B. 再把 prepared artifacts 回挂到 Step 6 主 JSON
python3 scripts/build_zotero_plan.py \
  --bib 文献库.bib \
  --structure zotero-架构.json \
  --workflow-results workflow_search_results.json \
  --pdf-dir paper-temp/ \
  --prepared-pdf-artifacts pdf-prepared/prepared_pdf_artifacts.json \
  --chinese 中文论文元数据.json \
  --output 文献-Zotero架构对照.json \
  --review 文献-Zotero架构对照.md \
  --pdf-index pdf-附件池索引.json

# C. Step 7 / 7.16 审计时读取 prepared chunks
python3 scripts/citation_audit.py 论文初稿.md \
  --mapping 文献-Zotero架构对照.json \
  --pdf-index pdf-附件池索引.json \
  --prepared-chunks pdf-prepared/example.chunks.json \
  --output 引用审计报告.md
```

输出：
- `文献-Zotero架构对照.md`：人类审阅版，可为排版截断标题/摘要/URL/PDF 文件名等长字段，但必须保留 `record_id`、`citekey`、`source_id`、`DOI`、`article_url`、`zotero_item_key` 等回查字段
- `文献-Zotero架构对照.json`：机器执行源，所有字段必须完整保留，禁止截断
- `pdf-附件池索引.json`：记录所有候选 PDF 的完整路径、来源、匹配结果
- `prepared_pdf_artifacts.json`：PDF 全文工作层索引，供 Step 6/7/7.16/8 共享

**核心任务：**
优先复用 `workflow_search_results.json` / `文献-大纲对照.json` 中已有的 `chapter_id / chapter_title / secondary_chapter_ids / secondary_chapter_titles`，再与 `zotero-架构` 中按大纲二级章节生成的集合路径匹配，生成每篇文献应该进入哪个 Zotero 集合的对照表。

如果前序文献-大纲映射存在，Step 6 不应重新用关键词猜章节归属；关键词匹配只作为映射缺失时的降级手段。

**PDF 附件池规则：**
- 不假设 PDF 只来自 Step 5。
- 附件池可包含：Step 5 下载的 PDF、用户项目中原已有 PDF、后续补下载 PDF、手动整理目录中的 PDF。
- 执行 6.2 前先扫描附件池，生成 `pdf-附件池索引.json`。
- 每个 PDF 记录完整路径、文件名、来源目录、文件大小、可提取标题/DOI/source_id（如能提取）、匹配状态。
- 同名或疑似重复 PDF 不删除，标记为 duplicate_candidate，等待人工确认或按匹配置信度选择。

**Markdown 审阅表推荐字段：**

| 字段 | 说明 |
|------|------|
| 序号 | 稳定编号 |
| record_id | JSON 中的稳定记录 ID；Markdown 截断时仍必须保留 |
| citekey | BibTeX citation key |
| 标题 | BibTeX title |
| source/source_id | `openalex` / `crossref` / `cnki` / `wanfang`；中文条目必须有 `cnki.xxx` / `wanfang.xxx` |
| DOI/URL | 真实 DOI 或详情页 URL；中文合成 ID 不得放入 DOI |
| Tier/Score | 来自 BibTeX note 字段 |
| 可信度状态 | 来自 Step 4 的 `verification_status` / `verification_confidence` / `warn_class` / `verified_sources` |
| 推荐集合路径 | 如 `论文文献库 / 2-方法 / P1-D1 数值模拟` |
| 推荐标签 | 来自 6.1 标签方案，可多值 |
| 条目导入方式 | 英文 DOI / 英文 BibTeX / 中文 CSL JSON / 手动补全 |
| 匹配理由 | 关键词、摘要、子课题、note 字段依据 |
| PDF 文件 | Step 5 下载到的本地 PDF 文件名或「未找到」 |
| 导入状态 | 待导入 / 已导入 / 待人工确认 |
| 附件状态 | 待关联 / 已关联 / 缺 PDF |

**JSON 执行源最低字段：**
```json
{
  "schema_version": "1.2",
  "plan_fingerprint": "zplan-0123456789abcdef0123",
  "root_collection": "从大纲解析出的论文标题",
  "readiness": "complete|partial|blocked",
  "can_continue": true,
  "blocking_missing": [],
  "nonblocking_missing": [],
  "warnings": [],
  "recommended_next_step": "",
  "records": [
    {
      "record_id": "zrec-0123456789abcdef",
      "citekey": "zhang2024_example",
      "source": "cnki",
      "source_id": "cnki.a1b2c3d4",
      "language": "zh-CN",
      "title": "完整标题，不截断",
      "authors": ["张三", "李四"],
      "year": "2024",
      "publication_title": "完整期刊名/会议名/学位授予单位",
      "doi": "",
      "article_url": "https://完整详情页URL",
      "abstract": "完整摘要，不截断",
      "tier": "T1",
      "score": "22",
      "subtopic": "S1: 子课题名称",
      "verification_status": "VERIFIED_LOCAL",
      "verification_confidence": "medium",
      "warn_class": "",
      "verified_sources": "cnki",
      "paper_card": {
        "evidence_role": "method",
        "primary_claim": "文献的核心主张",
        "main_methods_or_baselines": ["POD", "POD-Galerkin"],
        "reading_depth": "abstract_only",
        "content_fit": "adjacent",
        "content_fit_note": "方法相近但工况不同，只适合作为方法参照",
        "usable_for": ["方法背景", "方法对比"],
        "not_usable_for": ["强结论", "具体数值"]
      },
      "collection_path": ["论文文献库", "2-方法", "P1-D1 数值模拟"],
      "collection_key": "",
      "tags": ["P1-D1", "数值模拟"],
      "import_method": "csl_json",
      "pdf_path": "/完整/path/to/file.pdf",
      "pdf_source": "existing|step5|supplemental|manual",
      "pdf_match_confidence": "high|medium|low|none",
      "matched_pdf_candidates": [],
      "prepared_pdf_artifacts": {
        "raw_md": "",
        "clean_md": "",
        "chunks_json": "",
        "extraction_report_json": "",
        "evidence_level": ""
      },
      "zotero_item_key": "",
      "import_status": "pending|ready|metadata_incomplete|manual_required",
      "item_state": "planned|existing_confirmed|imported|duplicate_candidate|metadata_conflict|import_failed|rejected_do_not_import|manual_confirmation_required",
      "attachment_status": "missing|found|already_attached|duplicate_candidate|conflict|unknown|rejected",
      "attachment_state": "matched_attachment|missing_attachment|unlinked_pdf|duplicate_attachment|invalid_attachment|attachment_conflict|manual_attach_required|rejected",
      "attachment_action": "skip|manual_drag|add_from_file_then_merge|wait_for_attach_tool|none",
      "existing_attachment_keys": [],
      "notes": ""
    }
  ]
}
```

> `文献-Zotero架构对照.md` 只供人工审阅；6.3/6.4 的集合创建、条目导入、PDF 附件关联、状态回写必须以 `文献-Zotero架构对照.json` 为准。

**匹配规则：**
1. 若存在 `workflow_search_results.json` 或 `文献-大纲对照.json`，优先使用其中的 `chapter_id / chapter_title` 匹配主集合路径。
2. 若存在 `secondary_chapter_ids / secondary_chapter_titles`，写入 `secondary_collection_paths`，供 6.5 自动次挂。
3. 英文/国际文献：优先使用真实 DOI 精确匹配 PDF 文件名、下载日志或文献表。
4. CNKI/万方中文文献：不得依赖 DOI；优先使用 `source + source_id`、`article_url`、标题规范化匹配 PDF 和 Zotero 条目。
5. DOI 缺失时，使用标题规范化匹配；标题仍不可靠时标记为「待人工确认」。
6. 前序映射缺失时，才依据 BibTeX `note` 中的 `subtopic`、`Tier`、`Score` 字段匹配集合。
7. 再次降级时，才依据 title / abstract / keywords 与 `zotero-架构.md` 的集合名、标签说明匹配。
8. 不确定归属时不要硬分配，放入 `待确认` 集合或在对照表中标注「待人工确认」。
9. 同一个 PDF 若被两个不同 record 高置信命中，所有相关记录统一标为 `attachment_conflict + manual_review_shared_pdf`；不得按处理顺序把文件静默分给最后一个条目。

**中文文献元数据规则：**
- `cnki.xxx` / `wanfang.xxx` 是内部 source id，不是真实 DOI。
- Zotero 的 DOI 字段只能填写真实 `10.xxxx/...` DOI。
- 无真实 DOI 的中文条目必须把 `source_id`、`source`、`article_url`、Tier、Score、subtopic 写入 Zotero `Extra` 或等价字段。
- 中文条目必须优先从 `中文论文元数据.json` 读取 authors、year、publication_title、abstract、language，不能只依赖 `文献库.bib`；旧名 `chinese_papers.json` / `chinese_metadata.json` 仅作为兼容输入。
- `paper_card` 必须在 `文献-Zotero架构对照.json` 中完整保留，并在真实导入 Zotero 时同步到 `More-Paper Evidence Card` child note。Zotero note 是人类可读副本，不替代 JSON 机器主源。

**质量要求：**
- 每个 BibTeX 条目必须出现在对照表中。
- 每个 T1/T2/T3 条目必须有推荐集合路径。
- 标准链路下，推荐集合路径应直接落到大纲二级章节；只有大纲没有二级章节或文献确属章级背景时，才允许停留在一级章节容器集合。
- 每个条目必须保留 Step 4 的可信度字段；旧 BibTeX 缺失时标记 `verification_status=WARN`、`warn_class=legacy-unverified`，但不中断。
- `verification_status=REJECT` 的记录不得进入 Zotero 写入队列；只保留在异常清单或补查候选中。
- `verification_status=WARN` 的记录可进入计划表，但必须保留 `warn_class`，写入前作为待审项向用户展示。
- 中文条目必须有 `source_id` 和 `article_url`；缺作者/年份/来源名称时必须列入「中文元数据待补全」清单。
- 缺真实 DOI、缺 PDF、重复条目、无法判定集合的文献必须单独列出。
- `文献-Zotero架构对照.json` 中所有用于机器执行的字段禁止截断；Markdown 中的截断不得反向污染 JSON。
- `文献-Zotero架构对照.md` 如截断标题、摘要、URL 或 PDF 文件名，必须保留 `record_id`，并尽量保留 `citekey`、`source_id`、`DOI`、`article_url`、`zotero_item_key`，保证可回查到完整 JSON、BibTeX、Zotero 条目或 PDF。
- 6.3/6.4 所有 Zotero 写入操作都以 `文献-Zotero架构对照.json` 为准。
- `scripts/build_zotero_plan.py` 只生成中间产物，不调用 Zotero MCP、不修改 Zotero 文库。
- 缺 `文献库.bib` 时输出 `readiness=blocked`；缺 `zotero-架构.json` 时允许进入 `待确认集合`；缺 PDF 目录时写 warning，不中断。
- 若已存在 `prepare_pdf_for_llm.py` 生成的产物，应把其路径回挂到 `prepared_pdf_artifacts`，供 Step 7/7.16/8 重用；没有时不阻塞 Step 6。

---

### 6.4. 通过 Zotero MCP 创建集合并检查架构一致性

输入：`zotero-架构.json`

**创建流程（递归，每个子集合的 `parent_collection` 传直接父级 key）：**

```
# Step 1 — 幂等性检查
zotero_search_collections(query="{zotero-架构.json 中的根集合名}")
  → 如果已存在，询问用户：跳过 / 补充缺失 / 新建带日期后缀的根集合

# Step 2 — 创建或复用根集合
zotero_create_collection(name="{zotero-架构.json 中的根集合名}")
  → root_key

# Step 3 — 按 zotero-架构.json 递归创建子集合
zotero_create_collection(name="1-基础", parent_collection=root_key)
  → l1_key

zotero_create_collection(name="P0-A1 基础理论", parent_collection=l1_key)
  → l2_key

# Step 4 — 验证
zotero_get_collections()
  → 与 zotero-架构.json 逐级对照
```

**关键规则：**
- 创建集合时只以 `zotero-架构.json` 中的根集合名为准，不再硬编码 `论文文献库`。
- 标准链路中，递归创建的集合树应保持 Step 2 大纲层级：一级章节为容器集合，二级章节为文献默认归属集合。
- 只有 `zotero-架构.json` 中真实存在三级及更深节点时，才继续创建更深子集合。
- `parent_collection` 始终传直接父级的 8 位 key，不能偷懒传根 key。
- 每创建或复用一个集合，立即记录 `collection_path → collection_key` 映射。
- 集合已存在时复用 key；不得创建同名重复集合。
- 中途中断后，下次执行必须能通过幂等性检查续跑。

**一致性检查：**
- 根集合名称一致。
- 每一级子集合数量一致。
- 每个集合的父子关系一致。
- `文献-Zotero架构对照.json` 中出现的所有推荐集合路径都能找到对应 Zotero collection key。
- 如发现缺失、多余、错层集合，先报告并征求用户确认，再补建或调整。

**完成后报告：**
- 新建集合数、复用集合数、失败集合数。
- 根集合 key。
- `collection_path → collection_key` 映射摘要。
- 架构一致性结论：通过 / 有差异但已修复 / 仍需人工处理。

---

### 6.5. 导入条目并生成/执行附件处理策略

输入：
- `文献库.bib`
- `中文论文元数据.json`（如存在中文文献；兼容旧名 `chinese_papers.json` / `chinese_metadata.json`）
- `文献-Zotero架构对照.json`
- `pdf-附件池索引.json`
- `collection_path → collection_key` 映射
- PDF 附件池目录（Step 5 / 原有 / 后续补下载 / 手动整理）

**目标：**
将 Step 4 的英文 BibTeX 条目和中文增强元数据低风险导入 Zotero，并把条目放入 6.2 推荐的集合；PDF 附件默认只判断状态和处理策略，不自动挂载到已有条目。

**多章节 / 多 collection 原则：**

- 一篇文献可以对应多个章节，也可以对应多个 Zotero collection。
- 这**不等于多次入库**。
- 对用户而言，默认只需要一次“入库”口令，例如：
  - `继续 Step 6`
  - `开始 Zotero 入库`
  - `把当前结果导入 Zotero`
- Agent 在内部应执行：
  1. **条目只创建一次**；
  2. 先写入 `primary_collection_path`；
  3. 再把同一个 Zotero item 挂入 `secondary_collection_paths`；
  4. 不得因为存在多个 collection 就重复创建 Zotero 条目。

实现边界：

- `primary_collection_path` 表示该文献的主归属集合。
- `secondary_collection_paths` 表示同一文献的次归属集合，可为多个。
- 若某 collection 挂接失败，应回写为集合层失败，不得退化为再创建一个重复条目。

**折中加速方案（通用，不限当前项目）：**

- 当需要把同一批文献挂入多个 collection，而逐条搜索 `item_key` 成本过高时，优先采用“折中加速方案”，而不是改成“重复入库后再合并”。
- 核心思路：
  1. **第一阶段：主条目入库**  
     - 每篇文献只创建一个 Zotero 条目；  
     - 先落到 `primary_collection_path`。
  2. **第二阶段：批量次 collection 挂接**  
     - 基于 `文献-Zotero架构对照.json` 中的 `secondary_collection_paths` 生成挂接清单；  
     - 先做 `title / source / primary_collection` 级别的批量匹配；  
     - 再按目标 collection 批量调用 `zotero_manage_collections`；  
     - 对高确定性条目先执行，低确定性条目留给人工确认。

默认原则：

- 优先优化“批量匹配 item_key -> 批量挂接 collection”的路径。
- 不把“重复入库 -> 后续查重合并”当作默认加速策略。
- 只有在当前 MCP 工具能力明显不足、且用户显式接受库内重复条目风险时，才允许进入重复入库回退方案。
- **次 collection 挂接默认不单独触发用户对话确认。**
  - 它应作为“主条目入库完成后”的顺序执行步骤自动继续；
  - 不应要求用户再额外发送一次“继续挂接次 collection”的口令；
  - 只有当匹配不唯一、命中冲突、或存在明显误挂风险时，才把该条目标记为 `待人工确认`，并在阶段总结中统一回显。

高确定性条目判定建议：

- 标题唯一或近似唯一；
- `source` 明确且与计划记录一致；
- 已在 `primary_collection_path` 中可定位；
- 中文条目同时具有 `source_id` / `article_url` / 标题三者中的至少两项；
- 英文条目具有真实 DOI，且标题匹配稳定。

低确定性条目处理建议：

- 搜索结果返回多条同题记录；
- 同题不同版本/同题不同源且无法稳定区分；
- 多个可能 keeper 同时存在；
- 这类条目应进入 `待人工确认` 清单，而不是盲挂。

**次 collection 挂接判据优先级（后续执行默认快速路径）：**

- 次挂的前提不是“标题看起来像”，而是：`secondary_collection_paths` 已经在 Step 4/Step 6 规划层中被明确给出。
- 在执行层，Agent 应优先使用以下顺序快速定位已入库条目，再调用 `zotero_manage_collections` 追加次集合。

英文条目优先级：

1. `DOI + primary_collection`
2. `citekey + primary_collection`
3. `title + primary_collection`

中文条目优先级：

1. `source_id + primary_collection`
2. `article_url + primary_collection`
3. `title + primary_collection`

执行规则：

- 一旦上位判据命中且唯一，直接进入批量次挂，不必继续走下位判据。
- 若 `title` 匹配返回多条同题候选，且上位判据缺失或冲突，则该条目标记为 `待人工确认`。
- 不得因为追求速度而跳过 `primary_collection` 这一限制条件；同题跨 collection 误挂的风险高于单条逐步补挂的收益。
- 推荐先按目标 `secondary_collection_key` 分组，再批量调用 `zotero_manage_collections`，减少逐条操作开销。
- Agent 对用户的回显方式应是：
  - 主条目入库完成后，直接继续执行高确定性次挂；
  - 执行完成后统一报告“已自动补挂 X 条次 collection，另有 Y 条待人工确认”；
  - 而不是在每一批次挂接前逐次向用户询问。

**推荐执行顺序：**
1. 分流条目：先排除 `verification_status=REJECT`，再按 `source` / `source_id` / 标题语言把英文国际文献与 CNKI/万方中文文献分开；`WARN` 条目作为待审项展示。
2. **英文 dispatch 规则：** 有真实 DOI 的英文国际文献，默认使用 `文献库.bib` 批量写入本地 Zotero；主路径优先 `zotero_add_by_bibtex`，而不是逐条先跑 `zotero_add_by_doi`。在批量条目落库后，如仍需补齐更丰富元数据，再对缺口条目做 DOI 二次解析/更新。除非用户明确覆盖默认来源，否则 Agent 不应要求用户手动指定英文导入文件。
3. **中文 dispatch 规则：** `cnki/wanfang` 中文文献，默认使用 `中文论文元数据.json` 构造 CSL JSON，并优先批量 `zotero_add_by_csl_json` 写入本地 Zotero；必要时再用 `zotero_update_item` 补全作者、年份、刊名、摘要、URL、language、Extra。旧名 `chinese_papers.json` / `chinese_metadata.json` 仅作为兼容输入。除非默认 JSON 缺失或用户明确覆盖来源，Agent 不应让用户手动挑中文导入文件。
4. **二次元数据补全规则：** 条目入库成功后，英文可对高价值条目执行 DOI/API 二次补元数据；中文可对 metadata_incomplete 条目执行定向补全。该阶段是增强层，但在用户已确认真实写入后，默认应作为顺序自动后处理执行；不得再把它变成新的用户口令门槛，也不得阻塞“先把条目全部写入库”这一主目标。
5. 查重：英文用 DOI/title；中文用 `source_id` / `article_url` / title+first_author+year，不用合成 ID 当 DOI 查重。
6. 移入集合：按 `文献-Zotero架构对照.json` 的推荐集合路径调用 `zotero_manage_collections`。
6.a. 对存在 `secondary_collection_paths` 的条目，主条目入库完成后默认自动继续高确定性次挂；不得要求用户单独下达“继续次挂”的口令。
7. 附件状态判断：从 `pdf-附件池索引.json` 选择候选文件；英文按 DOI 优先；中文按 `source_id` / `article_url` / 标题优先；先判断 `missing` / `found` / `already_attached` / `duplicate_candidate` / `conflict`。
8. 附件验证：用 `zotero_get_item_children` / `zotero_get_items_children` 检查每个条目是否有 PDF 附件。
9. 附件动作建议：默认写入 `attachment_action`，不直接执行高风险动作。
10. 回写状态：更新 `文献-Zotero架构对照.json` 和 `pdf-附件池索引.json` 中的导入状态、附件状态、匹配置信度，并同步生成/刷新 `文献-Zotero架构对照.md` 审阅版。
10.a. 次挂阶段结束后，默认生成 `Zotero 次挂执行报告.md`，列出自动补挂成功条目和待人工确认条目。
11. child note 同步：对每篇 T1-T3 条目写入或更新 `More-Paper Evidence Card` child note；同时写入短 tag 索引（`mp-role:*` / `mp-fit:*` / `mp-depth:*` / `mp-tier:*`），但不把长文本 claim 或 note 作为 tag。

**当前 Zotero MCP 附件限制：**
- 当前 MCP 没有直接“向已有 item 添加本地 PDF 附件”的工具。
- `zotero_add_from_file` 是“从本地 PDF/EPUB 创建 Zotero 条目并附带文件”的入口，不是 attach-to-existing 工具。
- 少量附件推荐在 Zotero 桌面端手动拖拽到对应条目。
- 批量回退可以先用 `zotero_add_from_file` 创建临时/重复条目，再用 `zotero_merge_duplicates` 将该条目合并到 keeper；执行前必须 dry-run 并确认。

**中文条目 CSL JSON 最低字段：**
```json
{
  "type": "article-journal",
  "title": "中文论文标题",
  "author": [{"family": "张三"}, {"family": "李四"}],
  "issued": {"date-parts": [[2024]]},
  "container-title": "中文期刊名",
  "abstract": "中文摘要",
  "URL": "https://kns.cnki.net/...",
  "language": "zh-CN",
  "note": "Source: cnki | Source ID: cnki.xxxxx | Tier: T1 | Score: 22 | Subtopic: S1"
}
```

> 只有存在真实 DOI 时才写 `DOI` 字段；不要把 `cnki.xxx` / `wanfang.xxx` 写入 `DOI`。

**一致性检查：**
- `文献库.bib` 中每个条目：Zotero 中都有唯一条目或明确标记为重复/失败。
- CNKI/万方中文条目：Zotero 中的 title、author、year、publicationTitle/来源、URL、language、Extra/source_id 必须完整。
- T1/T2/T3 条目：必须有集合归属；缺 PDF 时必须列入「缺附件清单」。
- 每个 T1-T3 条目：如果条目导入成功且存在 `paper_card`，则必须至少有一个 `More-Paper Evidence Card` child note；该 note 只是同步副本，不替代 `文献-Zotero架构对照.json`。
- PDF 文件：不得静默忽略；每个候选 PDF 必须能追溯到匹配状态和建议动作。
- 附件池中未匹配 PDF 必须列入「未关联 PDF 清单」，不得静默忽略。
- Zotero 条目：不得只导入元数据却未移动到推荐集合，除非 JSON 记录标记为「待人工确认」。
- 已有同 DOI / 同 hash / 同名同大小附件时，必须标记 `already_attached` 或 `duplicate_candidate`，不得重复挂载。
- `write_complete` 时，每个非 REJECT、非 existing 的 record_id 必须存在当前 `plan_fingerprint` 下的 success operation；只存在 state 文件或旧计划 success 不算完成。

**附件动作规则：**
| 情况 | attachment_status | attachment_action |
|------|-------------------|-------------------|
| 已有同 DOI / 同 hash 附件 | `already_attached` | `skip` |
| 同名同大小候选 | `duplicate_candidate` | `skip` |
| 多个候选 PDF | `conflict` | `none` |
| 无附件且唯一高置信 PDF | `found` | `manual_drag` 或 `add_from_file_then_merge` |
| 当前 MCP 无直接挂载工具 | `found` | 不生成直接挂载动作 |

**失败与回退：**
| 情况 | 处理 |
|------|------|
| DOI 匹配失败 | 标题规范化匹配；仍失败则标记「待人工确认」 |
| 中文文献无 DOI | 正常情况；使用 `source_id` / `article_url` / 标题匹配，不报错 |
| 中文元数据缺作者/年份/来源 | 回到 Step 4/5 从 CNKI/万方详情页补抽，或标记「中文元数据待补全」 |
| PDF 缺失 | 记录到缺附件清单，路由回 Step 5 补下载 |
| PDF 来自原有目录或后续补下载 | 纳入附件池索引，按同一匹配规则关联，不要求来自 Step 5 |
| 一个条目匹配多个 PDF | 标记 duplicate_candidate，优先选 DOI/source_id 命中的文件，低置信度需人工确认 |
| 一个 PDF 匹配多个条目 | 不自动关联，标记 conflict，等待人工确认 |
| 条目重复 | 保留最完整条目，必要时提示用户合并 |
| 附件工具不可写 / 无 attach-to-existing | 保留元数据导入结果，提示手动拖拽或 `add_from_file_then_merge` 回退 |
| 集合 key 丢失 | 回到 6.3 重新生成 `collection_path → collection_key` 映射 |

---

### 6.6. 能力索引（capability_index）

`capability_index.json/md` 是 Step 6 的资产状态入口，不是新的流程锁，也不替代 `文献-Zotero架构对照.json`、`pdf-附件池索引.json` 或 Zotero 实际条目。它只回答三件事：

1. 当前有哪些文献资产可用。
2. 每类资产可以支持哪些 Step 和哪些能力。
3. 哪些缺口会影响写作、引用审计、下载或 Zotero 写入。

`capability_index.json` 最小字段：

| 字段 | 说明 |
|------|------|
| `schema_version` | 固定为 `capability-index.v1` |
| `generated_at` | 生成时间 |
| `project_root` | 当前项目根目录或运行目录 |
| `asset_summary` | Zotero、BibTeX、workflow JSON、PDF、附件池、中文元数据等资产数量摘要 |
| `capabilities` | 能力条目数组，逐项说明可用能力 |
| `recommended_entry_points` | 推荐后续 Step：如 Step 5 / Step 6 / Step 7 / Step 8 |
| `blocking_gaps` | 真正阻塞下一关键动作的缺口 |
| `warnings` | 非阻塞风险与降级说明 |
| `next_action` | 推荐下一步 |

`capabilities[]` 最小字段：

| 字段 | 说明 |
|------|------|
| `capability_id` | 稳定编号，如 `bibtex_available`、`pdf_pool_ready`、`zotero_mapping_ready` |
| `source_artifact` | 能力依据，如 `文献库.bib`、`workflow_search_results.json`、Zotero collection、PDF 目录 |
| `status` | `available / partial / missing / blocked` |
| `supports_steps` | 可支持的 Step 列表 |
| `supports_actions` | 可支持动作，如下载、入库、写作、引用审计、润色风险提示 |
| `evidence_boundary` | 该能力能否作为证据、候选、元数据或附件线索 |
| `risk_note` | 风险说明 |

执行规则：

- `capability_index.json` 应优先读取 `workflow_search_results.json`、`文献库.bib`、`文献-Zotero架构对照.json`、`pdf-附件池索引.json`、Zotero 只读扫描结果和用户指定 PDF 目录。
- `capability_index.md` 只用于人工判断，不作为机器执行源。
- 缺 Zotero 写入能力不阻塞生成 capability index；只能把写入能力标为 `partial` 或 `blocked`。
- 有 `capability_index.json` 时，Step 7 direct-entry 可先读它判断是否已有可用 Zotero 映射、PDF 附件、候选证据入口和引用审计风险。
- capability index 不允许把摘要、候选召回或 PDF 文件名匹配直接升级为正文证据。
- 当只需核对某一页、某一图表所在页、某一节局部内容时，优先用 `zotero_read_pdf_pages`，而不是 `zotero_get_item_fulltext` 整篇拉取。


---

## 质量门槛 (Quality Gates)

- [ ] 已识别本轮 direct-entry 输入；Zotero 只读扫描、BibTeX、CSL/workflow JSON、既有对照或 PDF-only 均可独立进入，不要求 Step 5。
- [ ] 有大纲时，`zotero-架构.md` 与大纲章节一一对应；无大纲 direct-entry 时明确使用待确认/现有集合结构。
- [ ] `文献-Zotero架构对照.md/json` 覆盖本轮所有可读取文献记录；PDF-only 模式允许仅生成未链接附件清单。
- [ ] `文献-Zotero架构对照.json` 所有机器字段完整无截断。
- [ ] `pdf-附件池索引.json` 已扫描所有 PDF 来源目录。
- [ ] Zotero 集合树与 `zotero-架构.json` 一致。
- [ ] T1/T2/T3 条目已导入 Zotero 并进入对应集合。
- [ ] T1/T2/T3 条目 PDF 附件状态已判断；缺失、重复、冲突、已存在项已分别列入清单。
- [ ] 重复条目、缺 DOI、缺 PDF、待人工确认项已单独报告。
- [ ] `item_state / attachment_state / completion_state` 已写入，`python3 scripts/validate_step6_output.py <output-dir>` 已通过。
- [ ] 如执行真实写入，`zotero_write_operations.jsonl` 与 `zotero_execution_state.json` 已生成，成功 operation 可幂等恢复。
- [ ] `record_id` 为内容稳定 ID，`plan_fingerprint` 已写入计划和每条操作；操作 payload 变化不会被旧幂等记录静默跳过。
- [ ] 同一 PDF 被多个条目争用时已统一标为 attachment conflict，没有发生最后写入覆盖。
- [ ] `write_complete` 已逐 record 验证当前计划 success operation，operation log 行合法且 event_id 唯一。

---

## 收尾检查 (Closing Checks)

### 产出完整性
- [ ] `zotero-架构.md` 已生成
- [ ] `zotero-架构.json` 已生成
- [ ] `文献-Zotero架构对照.md` 已生成
- [ ] `文献-Zotero架构对照.json` 已生成并更新状态
- [ ] `pdf-附件池索引.json` 已生成并更新匹配状态
- [ ] 如果 `skip` 或 plan-only：readiness、blocking_missing、nonblocking_missing、recommended_next_step 已写入
- [ ] 如果执行 Zotero 写入：`CP-ZOTERO-WRITE` 已确认，集合创建完成并通过一致性检查
- [ ] 中断恢复只重放当前 `plan_fingerprint` 下未 success 的 operation；`zotero_execution_state.json` 通过临时文件原子替换更新
- [ ] PDF 附件状态与建议动作已写回；高风险挂载动作已等待人工确认

### 错误日志更新
- [ ] 文献无法匹配集合 → 追加到 `.skill-state/error_log.md`
- [ ] PDF 无法匹配条目 → 追加到 `.skill-state/error_log.md`
- [ ] Zotero MCP 写入失败 → 追加到 `.skill-state/error_log.md`

### 决策日志更新
- [ ] 是否调整了文库架构策略？→ 记录到 `.skill-state/decision_log.md`
- [ ] 是否人工改判文献集合归属？→ 记录到 `.skill-state/decision_log.md`
- [ ] 是否采用手动附件导入回退？→ 记录到 `.skill-state/decision_log.md`

### 下一步提示
- [ ] 向用户明确说明下一步：开始写作前证据组织与论文写作（Step 7）
  > **下一步 → Step 7：** Zotero 文库、集合归属和 PDF 附件已准备好，接下来生成综述矩阵、学习目标期刊风格，并开始撰写论文。

### 成功判据
- [ ] 集合结构、条目导入状态、PDF 附件状态三者都已核对
- [ ] 重复、缺附件、待人工确认项已单独列出

### 完成前必须确认
- [ ] 只有在集合、条目、附件状态都明确后，才能声称“Zotero 已整理完成”
- [ ] plan-only / skip 模式下必须明确说明“已生成整理计划”，不能冒充真实写入完成

### 失败分流
- 集合不一致：归类为映射层问题，回 6.2/6.3
- PDF 对不上：归类为附件路径层问题，回 6.2 或 Step 5
- MCP 写入失败：归类为 Zotero 写入层问题，不直接否定前面的整理计划

---

## 故障排除 (Troubleshooting)

常见问题参见 `agents/known_pitfalls.md`。本 Step 特有的问题：

- **Zotero MCP 连接失败**：运行 `python3 scripts/setup_zotero.py --smoke-test` 诊断。
- **MCP 本地模式只读**：切换到可写 MCP 配置后再执行创建集合、导入条目、关联附件。
- **文献无法归类**：回到 6.2，依据 title / abstract / note 重新标注，必要时设为「待人工确认」。
- **PDF 附件缺失**：回到 Step 5 补下载，或在 Zotero 桌面端手动添加附件。
- **集合结构不一致**：回到 6.3，以 `zotero-架构.json` 为准补建缺失集合并重跑一致性检查。
