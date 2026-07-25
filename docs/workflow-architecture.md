# more-paper-workflow 工作流架构契约

本文档记录当前 skill 的运行边界和标准产物链。它不是用户快速开始页；`README.md` 继续作为 GitHub 对外概览，运行时规则以 `SKILL.md` 与 `agents/step_*.md` 为准。

## 四层权威边界

| 层级 | 职责 | 不承担 |
| --- | --- | --- |
| `README.md` | 对外展示、能力概览、推荐入口 | 详细执行规则、checkpoint 细节、脚本参数真相 |
| `SKILL.md` | 运行时路由、checkpoint 协议、`.skill-state/` 初始化、脚本速查 | 单步执行细则 |
| `agents/step_*.md` | 每个 Step 的输入契约、执行顺序、质量门、交付物 | 底层下载/检索/转换实现 |
| `scripts/` | 可复用工具实现与 CLI 入口 | 定义工作流语义或替代 agent 决策 |
| `config/` | 可变 source/provider/template 元信息、展示标签、默认文件名、路由提示 | workflow 决策、评分公式、Zotero 写入边界、Step 7/8 写作逻辑 |

## 8 步产物链

| Step | 标准输入 | 标准产物 | 机器接口 |
| --- | --- | --- | --- |
| Step 1 主题 | 用户研究意图、约束、材料 | `研究主题.md` | 规范嵌套主题字段、范围、限制条件 |
| Step 2 大纲 | 主题或已有目录 | `大纲关键词.md`、`章节证据需求表`、不可变 `section_blueprints.json` | 章节、关键词、RQ 与证据需求 |
| Step 3 检索方案 | 大纲、关键词、证据需求 | `检索方案.md/json`、`retrieval_index_manifest.json` | `base_workflow + addons` 编译后的单一 `search_tasks` |
| Step 4 检索评分 | `search_tasks` 或等价查询 | 按 `core / review / release-systematic` 交付；核心交付为 `workflow_search_results.json` 和 `search_run_manifest.json`，条件交付为 review/release 展示与发布工件 | `workflow-contracts.v1` search results JSON + run envelope |
| Step 5 下载 | DOI、中文 article URL、publisher URL、workflow search results | PDF 池、下载日志、下载 manifest | `DownloadManifestItem` / `DownloadResult` |
| Step 6 Zotero | 文献库、PDF 池、中文元数据、Zotero 架构 | `zotero-架构.md/json`、`文献-Zotero架构对照.md/json`、`pdf-附件池索引.json`、`capability_index.json/md` | plan-only Zotero plan JSON、资产能力索引 |
| Step 7 写作 | Zotero/证据矩阵、PDF 附件池、Step 2 结构基线 | `writing_blueprints.json/md`、`论文初稿.md`、指定章节、引用审计报告、`retrieval_candidates.json` | 带 source lineage 的写作派生蓝图、证据矩阵、章节级候选证据层、图表意图链 |
| Step 8 润色与保守修订 | 初稿、术语表、审计结果 | `论文润色稿.md/.docx`、`revision_ledger.json/md` | 风险标记、术语终验结果、问题闭环、轻量含义审计 |

Step 7/8 的边界：Step 7 是写作生产层，负责主体写作与主论证展开，可以在生成过程中做基础可读性整形，并在 `argument_plan` 之后插入章节级候选证据层（弱 RAG，仅定位候选、按章节确认、结果回写 `argument_plan`）；图表链只记录图表意图、证据依据、候选规格、人工选择和风险，不预设固定图表风格。Step 8 是成稿级精修与保守修订层，不接管主体写作，不补外部证据，不替代完整引用审计，但承担受约束补写、局部修订、轻量含义审计与修订后验证。Step 8 必要时可读取候选层做提醒，但不得把候选层当作证据。

## 正式脚本入口

| 阶段 | 正式入口 | 说明 |
| --- | --- | --- |
| 检索 | `scripts/search_by_topic.py` | 唯一顶层检索入口；新增来源应进入 source adapter，而不是新增平行顶层脚本 |
| 下载 | `scripts/unified_download_router.py` | 统一 DOI、中文 article URL、publisher URL、workflow JSON 到 provider/strategy |
| Zotero plan | `scripts/build_zotero_plan.py` | 只生成计划和索引，不写 Zotero |
| 检索报告 | `scripts/generate_search_report.py`、`scripts/generate_retrieval_report.py` | 消费检索表或标准 workflow JSON |
| Workflow run state | `scripts/workflow_run_envelope.py` | 原子生成/校验 Step 1-8 统一运行状态；可输出 `search_run_manifest.json` 等 Step 特定文件名 |

下载 provider 脚本如 `generic_publisher_downloader.py`、`sd_download.py`、`download_via_scihub.py`、`download_via_ieee.py` 保留为 strategy/provider 能力，不应重新成为工作流主入口。

## 薄配置层

`config/` 只承载低风险、可变的策略元信息：

- `config/sources.toml`：检索源的 display name、报告标签、默认语言、中文源标记和 CDP 需求。
- `config/publishers.toml`：下载 provider 的 DOI prefix、strategy、auth 说明、domain、selector 和 manual/skip 提示。
- `config/output_templates.toml`：报告标题、默认文件名、章节顺序和用户可见 label。

配置层不得承载评分公式、引用审计规则、Zotero 写入边界、Step 7/8 写作逻辑或 checkpoint 语义。脚本读取配置失败时必须回退到现有默认行为。

## 不得破坏的运行规则

- 任意 Step 都可以直接进入。checkpoint 记录当前输入依据和风险，不作为线性流程锁。
- `.skill-state/artifact_passport.json` 是材料索引和路由说明，不是上游产物替代品，也不是新的流程锁。
- `schemas/workflow-contract-registry.json` 是八步轴、档位、稳定工件和领域状态的统一注册表；manifest 和 Step 文档不得各自维护冲突枚举。
- 每个 Step 的机器交接使用 `morepaper.workflow-run.v1` envelope。`domain_state` 保留领域语义，跨步只通过 `readiness / can_continue / blocking / warnings / recommended_next_step` 判断。
- 全局 `route_mode` 只描述当前进入方式；Step 7 `mode`、Step 8 `revision_scope / target_genre` 等 Step 内部轴保持独立。
- Step 4 的核心交付物必须保持兼容；`workflow_search_results.json` 是机器主输出，Markdown/Excel/PDF/BibTeX 是审阅、报告和交接层。
- CNKI/Wanfang 保留 `--language zh`、长 CDP 会话和串行可靠性优先的运行策略。
- Step 5 下载来源、优先级和阶段顺序保持既有合同；所有 English/Chinese/CDP 阶段串行，不并发复用浏览器会话。
- `build_zotero_plan.py` 必须保持 plan-only，不调用 Zotero MCP，不修改外部文库。
- 所有 Zotero 写入动作必须经过 `CP-ZOTERO-WRITE`，只读、规划、dry-run 不应被该 checkpoint 阻塞。
- `.skill-state/` 属于项目运行态；不要把运行日志或 checkpoint 写入 `references/templates/`。

## 标准契约模块

`scripts/workflow_contracts.py` 提供轻量数据结构和 JSON 读写：

- `SearchTask`
- `SearchResultRecord`
- `DownloadManifestItem`
- `DownloadResult`
- `RetrievalIndexManifest`
- `CapabilityIndex`
- `CapabilityRecord`
- `ZoteroPlanRecord`
- `ReportInputs`
- `ArtifactRecord`
- `StepReadiness`
- `ArtifactPassport`

当前 schema version 为 `workflow-contracts.v1`。它的目标是固定字段语义和阶段边界，不要求一次性迁移所有旧脚本。

## Artifact Passport

`Artifact Passport` 是 `workflow-contracts.v1` 之上的轻量索引层，schema 为 `artifact-passport.v1`。它放在项目运行态目录 `$CWD/.skill-state/artifact_passport.json`，用于把 direct-entry 输入契约连起来：

- 记录当前已有材料：如 `文献库.bib`、workflow JSON、PDF 池、Zotero 对照、PDF 索引、初稿、引用审计报告。
- 记录材料来源：用户提供、workflow 生成、agent 重建。
- 给出可直接进入的 Step、允许的 route mode、缺失项、风险和推荐下一步。
- 不保存正文内容，不替代 `文献库.bib`、`pdf-附件池索引.json`、`文献-Zotero架构对照.json` 等正式产物。
- 不新增重型 orchestrator；agent 读取 Passport 后仍按对应 `agents/step_*.md` 的执行契约工作。

生成命令：

```bash
python3 scripts/artifact_passport.py --project-root "$CWD" --scan --output "$CWD/.skill-state/artifact_passport.json"
```
