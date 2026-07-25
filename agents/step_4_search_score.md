# Step 4: 多渠道检索与相关性筛选

> 按 Step 3 方案的 L1→L2→L3 分层路由逐子课题检索，对结果进行 5 维度评分和 Tier 分级筛选。

---

## 启动前读取 (Pre-read Checklist)

执行本步骤前，优先确认以下工件是否可用；若同时存在 JSON 和 Markdown，优先读取 JSON 机器源：

- [ ] `检索方案.json` / `检索方案.md` — Step 3 产出（`检索方案.json` 为机器执行源，`检索方案.md` 为人工审阅版）
- [ ] `retrieval_index_manifest.json` — 🆕 检索索引复用清单（如存在，先判断是否 still reusable）
- [ ] `研究主题.md` — Step 1 产出（tier/search_tier + 聚焦主题 + 预审结论）
- [ ] `references/search-query-frameworks.md` — 检索查询框架参考
- [ ] `references/rcs-rubric.md` — 🆕 主题匹配度评鉴启发指南
- [ ] `references/paper-card-contract.md` — `paper_card` 字段、证据角色、Zotero note 同步与 Step 7 消费契约
- [ ] `.skill-state/error_log.md` — 已知错误及修复规则
- [ ] `.skill-state/decision_log.md` — 影响本 Step 的结构性决策

---

## 适用任务 (Applicable Tasks)

- 按检索方案的 L1→L2→L3 分层路由逐子课题执行文献检索
- 对检索结果进行引文验证（DOI 有效性 + 元数据完整性）
- 多源检索结果 DOI 去重合并
- 五维度相关性评分（主题匹配度/方法学严谨性/来源质量/时效性/影响力）
- Tier 分级筛选（T1/T2/T3/T4）
- 统一 .bib 导出（含评分标签和子课题归属）
- 生成或更新 `retrieval_index_manifest.json`，记录本轮 `workflow_search_results.json`、metadata cache 和检索结果索引的复用状态
- 为 `workflow_search_results.json` 中每条 T1-T3 候选生成或保留 `paper_card`，记录文献级证据角色、读取深度和内容贴合边界

---

## 不适用任务 (Non-applicable Tasks)

以下任务不属于本 Step 范围：

- 检索方案设计 → 路由到 `agents/step_3_search_plan.md`
- PDF 下载 → 路由到 `agents/step_5_download.md`
- 文献综述矩阵 → 路由到 `agents/step_7_writing.md`

---

## 输入要求 (Input Requirements)

| 输入 | 来源 | 格式 | 必选 |
|------|------|------|:--:|
| 检索方案 | Step 3 | .md | ✅ |
| search_tasks | Step 3 `检索方案.md` | YAML/Markdown | ✅ |
| 检索执行参数 | search_tasks 中的 tier + L1/L2/L3 路由配置 | 文本 | ✅ |

**独立入口规则：**

如果用户已有检索方案、检索式、关键词组合、数据库清单、文献表或 BibTeX，可直接从 Step 4 开始，不要求回跑 Step 3。Agent 应在当前 Step 内完成：

1. 将用户材料整理为最小 `search_tasks` 或 direct scoring/import plan。
2. 输出 `CHECKPOINT 3 — CP-SEARCH`，设置 `route_mode: direct_entry` 或 `partial_artifact`，`status: satisfied_by_user_artifact` 或 `satisfied_by_agent_reconstruction`。
3. 用户明确“确认 CP-SEARCH”后，才执行真实多源检索命令；生成 dry-run 摘要、评分用户已有文献表、格式转换或报告生成不需要补跑完整 Step 3。

**Direct-entry input contract：**

| 可接受输入 | 最小处理 | 是否触发 CP-SEARCH |
|------------|----------|--------------------|
| `search_tasks` / `检索方案.md` | 直接执行或 dry-run 检索计划 | 真实检索前触发 |
| 用户给定检索式/数据库清单 | 包装为最小 `search_tasks` | 真实检索前触发 |
| 已有 `检索文献表.md` / `.xlsx` | 只做评分、报告、格式补齐 | 不触发，除非继续联网检索 |
| 已有 `文献库.bib` / workflow search results JSON | 导入为标准结果集，补报告或交给 Step 5/6 | 不触发，除非继续联网检索 |

Step 4 的直接入口不强制生成完整标准交付物。只有用户要求“完成标准 Step 4 交付”时，才按核心交付质量门执行；如果用户只要求评分已有文献、生成报告或转入下载/Zotero，应输出当前可用产物和缺失项清单，不要求回跑 Step 3。

**Direct-entry 局部修复合同：**

Step 4 direct-entry 发现 `zero-result / suspected_query_drift / too-broad / 关键证据类型未覆盖` 时，默认在 Step 4 内完成最小闭环，不要求用户回到 Step 1/2/3：

1. 从用户当前题目、问题描述、检索式、文献表或目标交付中重建 `topic_basis / rq_basis / chapter_or_scope_basis`。
2. 只修正受影响的 `search_task`、概念块、同义词、排除词、数据库路由、时间窗或筛选阈值。
3. 对修正后的查询重新执行 pilot，并保存变更前后查询、偏差样本、修正理由和影响范围。
4. 在结果中写入 `basis_origin=step4_reconstructed`、`repair_scope` 和 `unresolved_assumptions`；不得伪装成已完成 Step 1/2/3。
5. 只有用户明确要求重新定题、重做大纲或制定完整检索方案时，才建议切换到 Step 1/2/3；这属于用户选择的新任务，不是 Step 4 的完成前置条件。

局部修复不得静默改变研究对象、核心研究问题或纳入边界。若修正会实质改变这些高影响定义，应在 Step 4 内给出“保持原范围 / 采用修订范围”的对比并等待用户确认；确认后仍可继续 Step 4。

**执行前流程判定：**

- `消费方分析`：先判断本轮结果主要交给 Step 5 下载、Step 6 Zotero、Step 7 写作、导师/审稿人报告，还是仅做已有文献表清洗；消费方不同，交付物可以不同，但机器主工件完整性不降级。
- `依赖分析`：真实联网检索依赖 `search_tasks / route / tier / language / source`；已有文献评分依赖题录、摘要、DOI/source_id 和来源页；缺失依赖必须写入 gaps。
- `风险标注`：中文源登录、Semantic Scholar 429、metadata 缺摘要、T4 排除、WARN/REJECT 文献都要进入报告或 manifest，不能用“无结果”笼统覆盖。
- `快速通道不跳质量门`：评分已有文献表可以不触发 CP-SEARCH，但仍要保留 verification_status、Tier 依据、排除理由和下游 handoff。
- `有效结果驱动回退`：T1/T2/T3 是否继续不得只看 API 原始返回数；必须看去重后、具备 DOI/source_id/article_url 且题名/摘要与当前任务相关的有效记录数，标准完成还要看 VERIFIED T1/T2 的逐任务覆盖。
- `最小对比`：必要时用一条 T1 和一条 T4 展示筛选边界，说明为什么一条进入主表，另一条只进排除或异常清单。

**Step 3 字段读取规则：**

| 字段 | 用途 |
|------|------|
| search_tasks[].id | 输出表中的子课题归属和文件名前缀 |
| search_tasks[].chapter_id / chapter_title | 关联 Step 2 章节，供 Step 6/7 回溯 |
| search_tasks[].evidence_type | 影响评分解释和后续证据类型归类 |
| search_tasks[].question_to_answer | 判断主题匹配度和检索覆盖 |
| search_tasks[].query_blocks | 生成布尔查询与执行命令 |
| search_tasks[].route | 决定中文/英文源执行顺序 |
| search_tasks[].tier | 决定 limit、策略和补充源 |

---

## 标准输出 (Standard Outputs)

> Step 4 完成时，必须生成所选 execution profile 的核心交付物；更高档位的派生交付物按触发条件生成或明确标注跳过原因。所有最终导出的文献表和 BibTeX 仅含 **T1-T3 论文**（T4 已在 4.6 剔除或单独进入排除说明）。

**执行档位：**

| execution_profile | 必需交付 | 使用场景 |
|---|---|---|
| `core` | `workflow_search_results.json`、`retrieval_index_manifest.json`、`research_traceability_matrix.json`、`stratified_search_audit.json`、`search_run_manifest.json` | direct-entry、增量检索、下游机器消费 |
| `review` | `core` + Markdown/XLSX/Dashboard/BibTeX | 导师审阅、下载准备、Zotero 整理 |
| `release-systematic` | `review` + PDF 报告、PRISMA-S、饱和度及完整对账材料 | 系统综述、送审或发布验收 |

档位只控制派生交付物，不降低筛选、证据分级、机器字段完整性和完成门。没有生成的条件性展示工件必须记录跳过原因，不得列入 `outputs`。

**核心交付物与派生交付物目录（按 execution_profile 选择）：**

| # | 输出 | 格式 | 生成工具 | 说明 |
|---|------|------|---------|------|
| 1 | workflow search results JSON | .json | `search_by_topic.py --export_workflow_json` 或 Agent 标准化写入 | Step 4 机器主输出，供 Step 5/6/7 继续消费 |
| 2 | 检索文献表 | .md | Agent 直接写入 | 人工审阅版，顶部含筛选依据、饱和度摘要，底部含 PRISMA-S 摘要 |
| 3 | 检索文献表 | .xlsx | `generate_retrieval_report.py` | openpyxl 生成，冻结表头+自动筛选+Tier 色标 |
| 4 | 检索报告 | .md | `generate_search_report.py` | 完整检索方法论报告：检索范围→流水线→评分→分布→饱和度→行动建议 |
| 5 | 检索报告 | .pdf | `generate_search_report.py` → `md_to_pdf.py` | 面向审稿人/导师的 PDF 报告 |
| 6 | 文献库 | .bib | `generate_retrieval_report.py` | 全量 T1-T3，含 Tier/Score/influential_citations/子课题归属 |
| 7 | retrieval index manifest | .json | Agent 直接写入或由检索脚本补写 | 记录检索结果和元数据索引复用状态；不是证据裁决 |
| 8 | 文献-大纲对照 | .md/.json | Agent 导出或脚本生成 | 文献与 `chapter_id / chapter_title / search_task_id / evidence_type` 的初始对照，供用户感知 Step 4 已完成章节挂接，也供 Step 6/7 回查 |
| 9 | Step 4 可视化 Dashboard | 静态 HTML | `export_step4_dashboard.py` | 从 `workflow_search_results.json` 生成本地审阅页，用于检索后筛选、下载准备和 Zotero 入库前检查；展示层，不替代机器主工件 |
| 10 | 研究追溯覆盖矩阵 | .json/.md | `build_research_coverage_matrix.py` | RQ→章节→证据类型→search task→文献覆盖，逐任务显示 verified/T1-T2/反例与缺口 |
| 11 | 分层检索审计 | .json/.md | `audit_search_coverage.py` | 按任务、证据类型、来源、语言、年份和期刊检查饱和度与检索偏差 |
| 12 | Step 2 检索对账报告 | .json/.md | `reconcile_step2_after_search.py` | 有 Step 2 结构基线且完成标准检索时，输出关键词动作、章节覆盖、证据缺口和需用户确认的高影响修改 |
| 13 | Step 4 run manifest | .json | `workflow_run_envelope.py` | 记录档位、输入哈希、实际输出、来源警告、checkpoint 与下一步；推荐文件名 `search_run_manifest.json` |

**条件性交付物：**

| # | 输出 | 格式 | 触发条件 | 说明 |
|---|------|------|----------|------|
| 14 | 饱和度曲线快照 | .json | T1-T3 文献数 ≥ 30 | 文献覆盖率估算，含置信区间；不足 30 篇时标注跳过 |
| 15 | 中文论文元数据 JSON | .json | 存在 source=cnki/wanfang 的行 | 供 Step 5 下载与 Step 6 Zotero 中文条目入库使用 |

**统一文件命名规范：**

| 产出 | 推荐文件名 |
|------|------------|
| 检索文献表 Markdown | `检索文献表.md` |
| 检索文献表 Excel | `检索文献表.xlsx` |
| 检索报告 Markdown | `检索报告.md` |
| 检索报告 PDF | `检索报告.pdf` |
| 文献库 BibTeX | `文献库.bib` |
| 文献-大纲对照 Markdown | `文献-大纲对照.md` |
| 文献-大纲对照 JSON | `文献-大纲对照.json` |
| 饱和度快照 | `saturation_snapshot.json` |
| 中文论文元数据 | `中文论文元数据.json` |
| workflow search results JSON | `workflow_search_results.json` |
| retrieval index manifest | `retrieval_index_manifest.json` |
| Step 4 run manifest | `search_run_manifest.json` |
| Step 4 可视化 Dashboard | `step4-dashboard/` |
| 研究追溯覆盖矩阵 | `research_traceability_matrix.json/.md` |
| 分层检索审计 | `stratified_search_audit.json/.md` |

`workflow_search_results.json` 是 `paper_card` 的第一主存储。展示层可以只显示 `evidence_role + content_fit + reading_depth` 摘要列，但不得从截断展示层反向恢复 `paper_card`。

`文献-大纲对照.md/.json` 是 Step 4 对用户显式交付的“章节挂接层”，用于说明检索文献已和大纲/章节需求建立初始映射。它不替代 `workflow_search_results.json`，但应从该 JSON 稳定导出。

`step4-dashboard/` 是围绕 `workflow_search_results.json` 生成的本地静态审阅页，默认显示 T1-T3，并保留 T4 排除项复核视图。它必须显示 `record_id`、`doi/source_id`、`article_url`、`search_task_id`、`chapter_id`、`paper_tier` 和 `reading_depth`，用于检索后审阅、Step 5 下载优先级判断和 Step 6 Zotero 入库前检查；不得作为 Step 5/6/7 的机器主输入。

---

## 执行流程 (Execution Flow)

### 4.1. 检索执行总览

按 Step 3 的 `search_tasks` 逐任务执行。每个任务都必须保留 `id`、`chapter_id`、`evidence_type`、`tier`、`source`，并写入后续检索文献表。

> 从本版开始，Step 4 的机器主输出是 `workflow_search_results.json`。`检索文献表.md/.xlsx`、`检索报告.md/.pdf` 是围绕该 JSON 生成的展示层和审阅层；`文献库.bib`、`中文论文元数据.json`、`retrieval_index_manifest.json` 是下游交接层和索引层。`retrieval_index_manifest.json` 记录这些检索资产是否可复用，但不替代评分表和人工审阅。

### 4.1.1. 阶段输入输出表

| 阶段 | 输入 | 动作 | 输出 |
|------|------|------|------|
| 4.2 文献可信度验证 | 原始检索结果 | DOI/元数据校验；中文 source id 保护 | 验证后候选表 |
| 4.3 去重合并 | 多源候选表 | 英文按 DOI 去重；中文按作者+题目联合判断 | 去重文献表 |
| 4.4 筛选依据确认 | 去重文献表 + search_tasks | 向用户展示评分维度、权重、阈值和排除规则 | 用户确认或调整后的 screening basis |
| 4.5 五维评分 | 去重文献表 + screening basis | 主题/方法/来源/时效/影响力评分 | 带 score 的文献表 |
| 4.6 Tier 分级 | 带 score 的文献表 | T1/T2/T3/T4 判定；T4 剔除 | T1-T3 文献表 |
| 4.7 引文扩展 | T1 种子 | 单轮 1-hop 扩展 + 闭环评分 | 扩展后 T1-T3 文献表 |
| 4.8 饱和度估算 | 全量 T1-T3 | 覆盖率估算 | `saturation_snapshot.json` 或跳过说明 |
| 4.9 报告生成与完成检查 | 最终 T1-T3 + 标准输出 | 生成交付物 + 字段完整性检查 + 索引复用状态 | Step 5/6 handoff |

> **中文查询路由：** 查询含中文字符时，CNKI（L1 主检索）+ Wanfang Data（L2 补充）双路检索。

### 4.1.2. 防截断与机器工件完整性

Step 4 允许为了人工阅读压缩展示层，但机器主工件禁止截断。任何被 Step 5/6/7 继续消费的字段，都必须保留完整文本和稳定回查 ID。

**机器主工件禁止截断：**

| 工件 | 完整性要求 |
|------|------------|
| `workflow_search_results.json` | 标题、作者、摘要、关键词、DOI、URL、source_id、评分理由、排除理由、来源元数据完整保留 |
| `文献库.bib` | 必须从完整机器记录生成，不得从已截断的 Markdown/XLSX/PDF 展示行反向生成 |
| `中文论文元数据.json` | 中文标题、作者、摘要、来源、source_id、article_url 完整保留 |
| `retrieval_index_manifest.json` | `source_artifacts`、`search_task_ids`、record count、索引层级和复用边界完整保留 |

**展示层可截断但必须可回查：**

- `检索文献表.md/.xlsx`、`检索报告.md/.pdf` 可以为排版截断长标题、长摘要、长 URL 或长评分理由。
- 展示层一旦截断，必须保留至少一个稳定回查字段：`record_id`、`citekey`、`source_id`、`DOI`、`article_url` 或 `source_url`。
- 展示层截断不得污染 `workflow_search_results.json`、`文献库.bib`、`中文论文元数据.json` 或后续 Step 6/7 的 evidence mapping。
- 若只有截断展示层可用，必须标注 `source_integrity=display_truncated`，并在继续写作或入库前回查完整 JSON/BibTeX/PDF/数据库详情页。

### 4.1.3. 英文源执行规则（公开 API，无需认证，直接跑）

> 英文源全部是公开 API，与机构账号无关。执行时按 tier 选择启用的源，遇错处理即可，无需等待用户。

| 数据源 | Deep tier | Standard tier | Quick tier | 遇错行为 |
|--------|-----------|---------------|-----------|---------|
| **OpenAlex** | ✅ 首选 | ✅ 首选 | ✅ 首选 | FAIL → 切换独立来源并标记降级，不因单一供应方中止 |
| **Crossref** | ✅ **必跑** | ⚠️ OpenAlex < 30 或 SemSch 429 → 必跑 | ⬜ 跳过 | FAIL → 报告标注缺失 |
| **Semantic Scholar** | ✅ 跑 | ✅ 跑 | ⬜ 跳过 | 429 → ⬜ 跳过不阻塞 |
| **arXiv** | ✅ 仅 CS/AI 信号 | 同左 | ⬜ 跳过 | FAIL → 跳过 |
| **PubMed** | ✅ 仅医工交叉 | 同左 | ⬜ 跳过 | FAIL → 跳过 |

> **来源能力仲裁：** 不把任何单一供应方设为全局入口锁。Quick 至少需要 1 个可验证来源或用户提供语料；Standard/Deep 至少需要 2 个独立来源，或 1 个可靠来源加用户提供的可追溯语料。Systematic 还必须记录所有计划来源的成功、失败和替代原因。能力不足时使用 `degraded_source_coverage` 并降低 readiness，不得静默冒充完整覆盖。Crossref deep tier 仍为默认必跑来源；Semantic Scholar 429 不阻塞。

---

### 4.1.4. 中文源 preflight + 认证（仅中文查询触发）

> 中文源（CNKI/万方）在校园网外可能需要 CARSI 机构登录。**中文源的问题不阻塞英文源——英文源先行，中文源默认先直跑，只有直跑失败时才触发登录门控。**

> **中文库语言边界（强约束）：**
> - `CNKI` 与 `Wanfang` 在本 workflow 中默认且必须只检索中文文献。
> - Agent 调用中文源命令时，默认必须显式带 `--language zh`。
> - 即使中文库返回英文题名或双语条目，也应在结果层做中文题名过滤；英文国际论文应回到 OpenAlex / Crossref / Semantic Scholar 等英文源获取。
> - 只有当用户明确要求“检索中文库中的英文文献”或“保留双语条目”时，Agent 才能放宽此规则，并且必须在当轮输出中明确标注偏离默认语言边界。

```
执行顺序：
  1. 🏃 英文源命令先行（上表），不等待中文源
  2. 🔍 同时确保中文源执行条件：可选 preflight + 可复用 CDP 浏览器
  3. 🚀 中文源默认先直跑 CNKI/万方命令
  4. 📊 仅当直跑返回 login/captcha/连续 0 结果且页面异常时 → 进入下方认证流程
```

**中文源路由决策：**

| 数据源 | Preflight 结果 | 行为 |
|--------|:------------:|------|
| **CNKI** | IP 直连 OK | ✅ 直接跑，无需用户操作 |
| **CNKI** | CDP/CARSI 但直跑可检索 | ✅ 直接跑，无需先门控 |
| **CNKI** | 直跑失败且需登录/验证 | 🔐 再问用户是否有机构账号（见下方流程） |
| **CNKI** | 用户无机构账号 | 📝 确认后跳过，报告标注「中文源: 用户无机构账号」 |
| **CNKI** | 用户选择跳过 | 📝 报告标注「中文源: 用户跳过」 |
| **Wanfang** | IP 直连 OK | ✅ 直接跑，无需用户操作 |
| **Wanfang** | CDP/CARSI 但直跑可检索 | ✅ 直接跑，无需先门控 |
| **Wanfang** | 直跑失败且需登录/验证 | 🔐 再问用户是否有机构账号（见下方流程） |
| **Wanfang** | 用户无机构账号 | 📝 确认后跳过，报告标注「中文源: 用户无机构账号」 |
| **Wanfang** | 用户选择跳过 | 📝 报告标注「中文源: 用户跳过」 |

**中文源默认命令约束：**

```bash
python3 scripts/search_by_topic.py "<中文检索词>" --source cnki --language zh ...
python3 scripts/search_by_topic.py "<中文检索词>" --source wanfang --language zh ...
```

若缺少 `--language zh`，视为未满足中文源默认执行规范。

**中文源认证流程（CDP/CARSI 时——CHECKPOINT W — CP-SOURCE-AUTH）：**

`CP-SOURCE-AUTH` 只约束 Step 4 中文检索认证。旧宿主若仍传入 `CP-DOWNLOAD-LOGIN`，作为兼容别名读取并在状态记录中规范化为 `CP-SOURCE-AUTH`；Step 5 的下载登录门仍保持原名和既定语义。

> **交互兼容性规则：**
> - 若当前智能体/宿主环境支持弹窗、表单、结构化选项卡片或 `request_user_input`，优先使用结构化交互。
> - 若当前智能体不支持弹窗或结构化 UI，必须退化为固定文案 + 明确编号选项的纯文本 checkpoint。
> - 无论使用弹窗还是纯文本，选项语义、状态迁移和最终产物记录必须一致，不能因为宿主能力不同而改变流程分支。
> - 纯文本模式下，Agent 不得只说“请去登录后告诉我”，必须同时给出可选分支（继续登录 / 局部跳过 / 全部跳过 / 停止本次 Step 4）。

```
🔐 CNKI/万方直跑失败，检测到需要 CARSI 机构登录或人工确认。

   第一步：先进入固定 checkpoint：
   标题：中文数据库需要登录
   说明：CNKI / 万方已先尝试直接检索，但本轮返回登录/验证/异常 0 结果。你可以先完成登录后重试，也可以先跳过中文源，仅继续英文数据库。

   标准选项：
   > 选项 A: 去登录并继续
   >   说明：启动 CDP Chrome，用户完成 CARSI / 机构登录，随后继续跑 CNKI 和万方。
   >
   > 选项 B: 仅跳过 CNKI
   >   说明：CNKI 当前不可用或暂不处理，只继续万方和英文源。
   >
   > 选项 C: 仅跳过万方
   >   说明：只继续 CNKI 和英文源。
   >
   > 选项 D: 跳过全部中文源
   >   说明：只保留英文源结果，并在 `检索报告.md` / `retrieval_index_manifest.json` 里记录「中文源: 用户跳过」或更具体原因。
   >
   > 选项 E: 停止本次 Step 4
   >   说明：不继续检索，等待用户稍后处理登录。

   若是纯文本模式，Agent 必须输出上述标题、说明和 A-E 选项，不得自行压缩成自由叙述。

   第二步（用户选 A — 去登录并继续）：
   🚀 Agent 执行交互式批量检索（一条命令内完成全部操作，防止 CDP 断连）：

   a) Agent 基于 Step 3 检索方案，汇总所有 CNKI/Wanfang 查询 → 写入临时 JSON 文件
      （文件格式见下方 queries.json 模板）

   b) Agent 启动一条长驻 exec_command（yield_time_ms=30000）：
        python scripts/batch_chinese_search.py <queries.json> --output-dir <output/>

   c) 脚本自动处理 CDP Chrome：
      ├─ 端口 9223 已有 CDP → 复用（打印 CDP_ALIVE）
      └─ 无 CDP → 自动启动 Chrome → 导航到 CNKI/万方 → 等待就绪（打印 CDP_READY）

   d) 脚本先直接跑全部查询；只有存在失败项时，才打印 `=== LOGIN_REQUIRED ===` 并阻塞等待 stdin

   e) Agent 检测到 `=== LOGIN_REQUIRED ===`，告知用户：
      「CNKI/万方本轮有失败查询。Chrome 已打开，请完成 CARSI 机构登录后回复「已登录」」

   e.1) 若宿主支持第二个结构化 checkpoint，则进入：
      标题：登录完成了吗？
      选项：
      > A. 已完成登录，继续检索
      > B. 还没完成，稍后再试
      > C. 放弃中文源，继续英文源

      若宿主不支持结构化交互，Agent 必须以纯文本输出同样三个选项，不得只问“登录好了吗？”。

   f) 用户完成 CARSI 登录后回复「已登录」

   g) Agent 调用 write_stdin("go\n")，脚本只重试失败的中文查询

   h) 逐条执行查询（打印 `SEARCH_START:Sx / SEARCH_DONE:Sx:N`）；首轮默认直跑，登录后只重跑失败项
      每条命令自动加 --no-cache（避免空结果毒化缓存）和 --language zh

   i) 脚本打印 === ALL_DONE === 汇总结果数 + .bib 文件列表

   第二步（用户选 B/C/D — 局部或全部跳过中文源）：
   > Agent 必须明确回显跳过范围：
   > - B → `skip_cnki`
   > - C → `skip_wanfang`
   > - D → `skip_all_chinese_sources`
   >
   > 检索报告与 manifest 中需记录对应原因，例如：
   > - `中文源: 用户跳过 CNKI`
   > - `中文源: 用户跳过万方`
   > - `中文源: 用户跳过全部中文源`
   >
   > 可以建议备用方案：联系学校图书馆获取 VPN、或使用 iData 等第三方镜像。
   ⚠️ 确认后继续剩余可执行数据源，不阻塞英文公开 API 检索。

   第二步（用户选 E — 停止本次 Step 4）：
   > Agent 应输出 `status=paused_by_login_checkpoint`，并停止后续真实检索命令。
```

> 该认证 checkpoint 的 `route_mode` 可为 `normal_chain` 或 `direct_entry`。用户明确完成登录并确认 `CP-SOURCE-AUTH`（或旧兼容别名 `CP-DOWNLOAD-LOGIN`）后，Agent 才能继续中文源检索；英文公开 API 检索不受该 checkpoint 阻塞。

**queries.json 模板（Agent 动态生成）：**
```json
[
  {"id":"S1","query":"冷板拓扑优化","source":"cnki","limit":50,"strategy":"relevance"},
  {"id":"S1","query":"冷板拓扑优化","source":"wanfang","limit":50},
  {"id":"S2","query":"液冷板 结构优化 传热","source":"cnki","limit":50}
]
```

**Agent 执行参考命令：**
```bash
# 1. Agent 动态生成查询 JSON 文件
cat > .skill-state/chinese_queries.json << 'JSONEOF'
[
  {"id":"S1","query":"子课题1","source":"cnki","limit":50,"strategy":"relevance"},
  {"id":"S1","query":"子课题1","source":"wanfang","limit":50}
]
JSONEOF

# 2. 启动交互式批量检索（一条命令，CDP 不会断连）
python scripts/batch_chinese_search.py .skill-state/chinese_queries.json \
  --output-dir .skill-state/

# 3. 检测到 === LOGIN_REQUIRED === 后告知用户登录，等回复后用 write_stdin("go\n")
# 4. 检测到 === ALL_DONE === 后取结果
```

**CDP Chrome 手动启动（备用）：**
```bash
# 仅当 batch_chinese_search.py 自动启动失败时手动兜底
python scripts/start_cdp_browser.py --port 9223 --url https://kns.cnki.net/kns8s/

# macOS/Linux wrapper: bash scripts/start_cdp_chrome.sh --port 9223 --url https://kns.cnki.net/kns8s/
```

# L1 OpenAlex：每子课题跑 3 策略（relevance + cited + recent），每策略 50 条
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source openalex --strategy relevance --limit 50 --export-bib s1_l1_rel.bib
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source openalex --strategy cited --limit 50 --export-bib s1_l1_cited.bib
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source openalex --strategy recent --limit 50 --export-bib s1_l1_recent.bib

# L2 Semantic Scholar：CS 交叉子领域并行，传统工科在 L1<30 时回退
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source semantic_scholar --limit 50 --export-bib s1_l2.bib

# 传统用法（向后兼容，不使用概念块）：
python3 scripts/search_by_topic.py "cold plate liquid cooling optimization" \
  --t1 openalex --t2 semantic_scholar --limit 50 --export-bib s1_results.bib

### 4.1.5. L2 Crossref（DOI/出版社元数据补充，Deep tier 必跑）

> 🆕 按 Step 3 路由规则，Deep tier 下 **必须执行**，不得仅用 OpenAlex 完成英文检索。
> Standard tier 在 OpenAlex 结果不足或 Semantic Scholar 429 时也必须启用。
> Crossref 提供 DOI 归一化 + 出版社元数据（期刊名、页码、卷期号），
> OpenAlex 和 Semantic Scholar 经常缺这些字段。

```bash
# L2 Crossref：逐子课题补检，结果与 OpenAlex DOI 去重
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source crossref --limit 50 --export-bib s1_l2_crossref.bib

# 多子课题可合并在一条命令中
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source crossref --limit 50 --export-bib all_l2_crossref.bib
```

### 4.1.6. L1 CNKI

> 🆕 中文文献主检索。支持两种访问模式：
> 1. **IP 直连**（校园网/VPN）：自动 POST/GET HTTP 检索，零配置，支持多策略排序
> 2. **CDP 浏览器**（校外 CARSI/RVPN）：通过 CDP Chrome 使用新 SPA 界面检索
> CNKI 支持多策略切换（相关度/时间/被引），可使用 `--strategy` 参数。

```bash
# CNKI 中文文献检索（🔴 必须带 --language zh，排除英文论文）
python3 scripts/search_by_topic.py "冷板拓扑优化" \
  --source cnki --language zh --limit 50 --export-bib s1_cnki.bib

# CNKI 多策略检索（被引排序）
python3 scripts/search_by_topic.py "冷板拓扑优化" \
  --source cnki --language zh --strategy cited --limit 50 --export-bib s1_cnki_cited.bib

# 概念块布尔查询模式
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source cnki --language zh --limit 50 --export-bib s1_cnki.bib

# T1 CNKI + T2 Wanfang 级联
python3 scripts/search_by_topic.py "冷板拓扑优化" \
  --t1 cnki --t2 wanfang --language zh --limit 50
```

### 4.1.7. L2 Wanfang Data

> 中文文献补充检索。支持两种访问模式：
> 1. **机构 IP 直连**（校园网/VPN）：自动检测，无需额外配置
> 2. **CARSI SSO 登录**（校外）：需在 CDP Chrome 中完成一次机构登录
> 万方无多策略（relevance/cited/recent）支持，搜索请求为单次网页查询。

```bash
# L2 Wanfang Data：中文文献检索（🔴 必须带 --language zh）
python3 scripts/search_by_topic.py "冷板拓扑优化" \
  --source wanfang --language zh --limit 50 --export-bib s1_l2_wanfang.bib

# 概念块布尔查询模式（PQ 语法自动转换）
python3 scripts/search_by_topic.py --bool query_plan.json \
  --source wanfang --language zh --limit 50 --export-bib s1_l2_wanfang.bib

# 通过 T2 补充：CNKI T1 → 不足时万方补充
python3 scripts/search_by_topic.py "冷板拓扑优化" \
  --t1 cnki --t2 wanfang --language zh --limit 50
```

### 4.1.8. Tier-driven 检索参数

> 优先读取 `search_tasks[].tier`；若缺失，则按 Step 3 顶层 `tier`、Step 1 顶层 `tier`、Step 1 `search_tier.tier`、默认 `standard` 的顺序回退。

| Tier | limit/策略 | strategies | 补充策略 |
|------|:--------:|-----------|---------|
| Quick | 30 | relevance only | 无 |
| Standard（默认） | 50 | relevance + cited + recent | 无 |
| Deep | 100 | relevance + cited + recent | + seminal cutoff + review type |

### 4.1.9. L2 arXiv 条件触发

> 仅当 Step 3 检索方案标记了 `arxiv_enabled: true` 时执行。

```bash
# L2 arXiv：仅 CS/AI 跨域信号时触发（T-0~T-4 新鲜度窗口）
python3 scripts/arxiv_helper.py "query string" \
  --days 4 --limit 20 --output s1_l2_arxiv.json
```

### 4.2. 文献可信度三态机制

> 4.2 的目标是判断“文献条目本身是否可追溯、可入库、可引用候选”，不是判断它是否支撑某个 claim；claim 支撑关系留到 Step 7.9/7.15。

**三态定义：**

| 状态 | 判定 | 后续处理 |
|------|------|----------|
| `VERIFIED` | 可信公开源返回稳定 DOI/ID，且 title/year/authors 基本匹配 | 可进入 4.3-4.6，按评分与 Tier 参与筛选 |
| `VERIFIED_LOCAL` | CNKI/万方等中文源有 `source_id` 或 `article_url`，且 title/authors/year/publication_title 可追溯 | 可进入 4.3-4.6；不得因无 DOI 降级或剔除 |
| `WARN` | 存在真实不确定性：标题/年份/作者冲突、摘要缺失、来源弱、无稳定详情页、疑似重复、元数据残缺 | 保留进入人工审查队列；可评分，但写作时只能作背景/待补查线索 |
| `REJECT` | DOI 指向另一篇论文、关键元数据明显冲突、0 可追溯来源、明确撤稿或假条目 | 不进入最终 T1-T3 主表和 `文献库.bib`；只在检索报告异常清单中保留痕迹 |

**关键规则：**
1. `VERIFIED` 不要求至少 2 个来源一致。Crossref / OpenAlex / Semantic Scholar / PubMed / arXiv 任一可信源即可确认，只要稳定标识与核心元数据闭环。
2. 多源一致只提高 `verification_confidence=high`，不是进入 `VERIFIED` 的硬门槛。
3. 中文无 DOI 文献默认不是 `REJECT`。CNKI/万方条目只要有稳定详情页或 source_id，并能追溯标题、作者、年份、来源，即标为 `VERIFIED_LOCAL`。
4. WARN 是“需要人审或补证据”，不是“低质量文献”。中文核心、会议论文、新预印本和数据库覆盖弱领域不得因单源而自动降为 WARN。
5. 撤稿或表达关注应优先标记 `REJECT`；如只是 corrigendum/erratum，按具体影响写入 `warn_class`。

**4.2 必写字段：**

| 字段 | 值域/示例 | 说明 |
|------|-----------|------|
| `verification_status` | `VERIFIED` / `VERIFIED_LOCAL` / `WARN` / `REJECT` | 文献条目可信度三态 |
| `verification_confidence` | `high` / `medium` / `low` | 多源一致或强来源为 high；单可信源通常 medium；弱来源/残缺为 low |
| `warn_class` | `metadata-mismatch`, `missing-abstract`, `weak-source`, `no-stable-url`, `legacy-unverified`, `retracted` | 仅 WARN/REJECT 必填；VERIFIED 可空 |
| `verified_sources` | `crossref`, `openalex`, `semantic_scholar`, `cnki`, `wanfang` | 实际确认过的来源，多个用逗号分隔 |

`检索文献表.md` 主表必须包含上述 4 列；`generate_retrieval_report.py` 会将其写入 Excel 和 BibTeX note，供 Step 6/7 继续读取。

标准正式检索导出 workflow JSON 前必须执行元数据验证，例如：

```bash
python3 scripts/search_by_topic.py "query" \
  --t1 openalex --t2 crossref --limit 50 \
  --score --verify-metadata \
  --export-workflow-json workflow_search_results.json
```

Crossref/API 暂时不可用时标为 `WARN + doi_verification_unavailable`，不得直接当作 DOI 无效或 `REJECT`。只有 DOI 已解析到另一篇论文、核心元数据明确冲突或确认撤稿时才进入 `REJECT`。

**CP-CITATION-WARN**

当 4.2 产生的异常会改变最终 T1-T3 纳入策略、下游关键引用策略，或涉及 `REJECT` 条目的保留/剔除处置时，才输出 warning checkpoint。仅把 `WARN` 条目列入背景性候选、综述矩阵候选、待补查清单或异常清单，不触发 checkpoint。

```md
## CHECKPOINT W — CP-CITATION-WARN

route_mode: normal_chain|direct_entry|repair|partial_artifact
status: blocked
blocks_next: final T1-T3 library and downstream citation use
must_confirm: true

summary:
- 列出会影响主表纳入、关键引用或 REJECT 处置的 WARN/REJECT 条目数量、warn_class 分布和风险范围。

user_options:
1. 删除 REJECT，WARN 保留但标注
2. 逐条审查 WARN/REJECT
3. 回退补元数据或补检索来源

does_not_block:
- 将 WARN 作为背景候选或待补查线索
- 在综述矩阵中保留候选记录并显式标注 warn_class
- 低风险主题归类、去重、来源统计和异常清单整理

required_confirmation:
- “确认 CP-CITATION-WARN”
```

### 4.2.1. 引文验证执行细则

在评分之前先验证——剔除 DOI 无效、元数据残缺的条目，避免后续下载白费功夫。

```
检索结果 → 逐条验证：
  ① DOI 格式合法性（正则 + Crossref API 校验）
  ② 元数据完整性：title / authors / year / journal 是否在结果中存在
  ③ 标记问题条目：
     ⚠️ DOI 无效 → 跳过（无法下载）
     ⚠️ 缺作者/年份 → 尝试从 Crossref 补全
     ✅ 完整 → 进入评分
```

> **CNKI + 万方备注** 🆕：无真实 DOI 的论文使用 `cnki.{title_hash}` 或 `wanfang.{title_hash}` 作为标识符。
> 这些条目不进入 Crossref 验证（跳过步骤①），直接进入评分阶段。
> 若有真实 DOI（`10.xxxx/...` 格式），则正常验证。
> `cnki.xxx` / `wanfang.xxx` 是内部 source id，不是真实 DOI；后续导入 Zotero 时不得写入 DOI 字段，只能写入 `Extra` 或等价元数据字段。
>
> **中文论文文章 URL 保留** 🆕：中文论文（source=cnki/wanfang）在检索结果中必须保留**文章详情页 URL**，
> 写入检索文献表的 `文章链接` 列。此 URL 是 Step 5 Chinese CDP Round 下载的入口。
> CNKI 检索结果中的 `briefDl_D` 链接和 Wanfang 结果中的详情页链接均需保留。
> 若无可用 URL，标注 `⚠️ 缺文章页URL`，该论文将无法在 Step 5 自动下载。

### 4.3. DOI 去重

多源检索会产生重复（同一篇论文从 Semantic Scholar 和 Crossref 各返回一次）：

```
去重策略：
  - 主键：DOI（大小写 + 前缀统一后比对）
  - 无 DOI 时：title + first_author + year 组合键
  - 冲突时保留元数据最完整的条目
```

### 4.4. 筛选依据确认（用户可见）

在 4.2 文献可信度验证和 4.2 去重完成后，正式评分和剔除前，必须把本轮筛选依据以对话框或 checkpoint 形式展示给用户。目标是让用户知道“检索后根据什么筛选”，并允许用户调整权重、阈值或排除规则。

**筛选依据来源：**

| 依据 | 来源 | 作用 |
|------|------|------|
| 研究问题 / 子课题 | `search_tasks[].question_to_answer`、用户当前描述 | 决定主题匹配度 |
| 章节或任务归属 | `search_tasks[].chapter_id`、`chapter_title` | 决定后续 Step 6/7 可追溯性 |
| 证据类型 | `search_tasks[].evidence_type` | 决定方法学严谨性的解释重点 |
| 检索层级 | `tier` / `search_tier` | 决定源、limit、扩展策略 |
| 文献可信度 | 4.2 的 `VERIFIED / VERIFIED_LOCAL / WARN / REJECT` | 决定能否进入主表或异常清单 |
| 用户偏好 | 用户指定期刊、年份、语言、研究对象、方法边界 | 覆盖默认阈值或排除项 |

**默认评分维度：**

| 维度 | 权重 | 说明 |
|------|:----:|------|
| 主题匹配度 | 35% | 标题+摘要与研究主题、子课题、问题目标的相关程度 |
| 方法学严谨性 | 20% | 方法/实验/数据是否能支撑当前任务；实验、对照、数据质量按任务解释 |
| 来源质量 | 15% | 期刊/会议/机构来源、索引情况、出版稳定性 |
| 时效性 | 15% | 近 3 年优先；经典文献可因 foundational role 保留 |
| 影响力 | 15% | 引用量、influentialCitationCount、领域内代表性 |

**默认 Tier 阈值：**

| 等级 | 分数范围 | 默认处理 |
|------|----------|----------|
| Tier 1 | ≥20 | 核心文献，必须下载 |
| Tier 2 | 15-19 | 重要文献，尽量下载 |
| Tier 3 | 10-14 | 参考文献，有选择下载 |
| Tier 4 | <10 | 不进入最终导出；进入排除说明或异常清单 |

**CHECKPOINT 4.4 - CP-SCREENING-BASIS：**

```md
## CHECKPOINT 4.4 - CP-SCREENING-BASIS

route_mode: normal_chain|direct_entry|partial_artifact
status: waiting_user_confirmation
must_confirm: true
blocks_next: scoring, Tier grading, final T1-T3 export

screening_basis:
- research_question_basis: <本轮用于判断相关性的研究问题/子课题>
- inclusion_rules: <纳入规则，如主题、方法、年份、语言、来源>
- exclusion_rules: <排除规则，如无关主题、元数据不可追溯、撤稿、重复>
- scoring_dimensions: 主题匹配度35 / 方法学20 / 来源质量15 / 时效性15 / 影响力15
- tier_thresholds: T1>=20, T2=15-19, T3=10-14, T4<10
- trust_boundary: VERIFIED/VERIFIED_LOCAL 可进入主表；WARN 标注风险；REJECT 不进入主表

user_options:
1. 确认使用默认筛选依据
2. 调整权重、阈值、年份范围、语言范围或排除规则
3. 暂不剔除，只生成候选清单和风险说明

does_not_block:
- 元数据验证
- 去重
- 来源统计
- dry-run 报告
- direct-entry 下的已有文献表格式补齐

required_confirmation:
- "确认 CP-SCREENING-BASIS"
```

用户确认或调整后的筛选依据必须写入 `检索文献表.md` 顶部、`检索报告.md` 的评分方法章节，以及 `.skill-state/decision_log.md`。如用户选择“暂不剔除”，Step 4 可以输出候选清单和风险说明，但不得声称已经完成最终 T1-T3 文献库。

### 4.5. 相关性评分（v3.0 五维度）

按 4.4 用户确认后的 `screening_basis` 对去重文献表打分。每项仍按 0-5 评分，满分 25；评分解释可参考 `references/rcs-rubric.md`，但不得把 RCS 启发当成唯一筛选依据。

**评分回溯规则：**

- 主题匹配度必须参考 `search_tasks[].question_to_answer` 或用户在 4.4 确认的研究问题。
- 方法学严谨性必须参考 `search_tasks[].evidence_type`，例如 `experiment` 任务更重视实验/对照证据。
- 同一论文服务多个 `search_task` 时，保留多重归属，不覆盖原归属。
- 每条 T1/T2 评分理由至少写明一个匹配词、摘要依据、方法依据或来源依据，避免黑箱分数。
- 实现必须保存 `_score_dimensions / _score_weights / _score_reasons / _score_confidence / _uncertainty_flags / _weighted_score`；不能只保存总分。
- 五维权重固定为主题匹配 35%、方法严谨性 20%、来源质量 15%、时效性 15%、影响力 15%，除非用户在 4.4 明确调整。
- 影响力按论文年龄归一化；新论文无引用不得自动降为低相关。缺摘要、缺年份或 venue 未解析必须进入 uncertainty flags。

**证据层级提示（解释层增强，不改核心状态机）：**

- `VERIFIED / VERIFIED_LOCAL / WARN / REJECT` 仍是 Step 4 的核心信任状态，不替换。
- 高相关不等于高证据等级。
- 高证据等级不等于与当前 research question 高匹配。
- 系统综述 / 方法学敏感任务下，检索报告应说明哪些条目适合作背景综述、方法依据或低风险补充。

**`paper_card` 文献用途卡片（写入 `workflow_search_results.json`）：**

Step 4 在五维评分之后为每条 T1-T3 记录生成或保留 `paper_card`；具体字段、枚举值和 Zotero 同步模板见 `references/paper-card-contract.md`。

最小字段：

```json
{
  "paper_card": {
    "evidence_role": "method|background|theory|review|experiment|data|benchmark|counterpoint|standard_policy|case_specific|unknown",
    "primary_claim": "",
    "main_methods_or_baselines": [],
    "reading_depth": "metadata_only|abstract_only|full_text|zotero_note|pdf_verified",
    "content_fit": "direct|adjacent|background_only|mismatch|unknown",
    "content_fit_note": "",
    "usable_for": [],
    "not_usable_for": []
  }
}
```

生成规则：

- `content_relevance` 仍由五维评分承担，`evidence_role` 不替代主题匹配度。
- `evidence_role` 回答“这篇文献适合做什么证据”；`content_fit` 回答“它与当前研究问题/章节的内容贴合度”。
- 高相关文献仍可能只是 `background_only`；综述文献优先标为 `review/background/theory`。
- 实验或方法论文可标为 `method/experiment/benchmark`；数据、标准、案例类材料按实际证据角色标注。
- 标题相关但摘要无法支持当前方向时，`content_fit=mismatch` 或 `background_only`。
- `reading_depth=abstract_only` 的条目只可作为低风险背景候选，不得在 Step 7 直接支撑关键 claim。
- Step 4 不做句子级引用裁决；具体 claim-source fit 留到 Step 7.10/7.16。

### 4.6. 筛选标准（Tier 分级）

按 4.4 确认后的阈值执行 Tier 分级。若用户未修改阈值，使用默认 T1-T4；若用户修改阈值，必须把修改理由写入 `decision_log` 和检索报告。

| 等级 | 分数范围 | 处理 |
|------|---------|------|
| Tier 1 | ≥20，且主题匹配≥4、方法严谨性≥3、评分置信度非 low | 核心文献，必须下载 |
| Tier 2 | 15-19 | 重要文献，尽量下载 |
| Tier 3 | 10-14 | 参考文献，有选择下载 |
| Tier 4 | <10 | 不进入后续导出（`.bib` / `.md` / `.xlsx` 均不含 T4）；进入排除说明或异常清单 |

### 4.7. 引文网络扩展（单轮 1-hop）

> 设计约束：单轮，不做第二跳；仅 T1 种子论文，最多 10 篇；新增论文在 4.7 内复用 4.4/4.5 完成评分和分级闭环。

**触发条件：** T1 论文数 > 0，且 4.4 未选择“暂不剔除，只生成候选清单”。

```bash
# 对每篇 T1 论文：
python3 scripts/search_by_topic.py --citation-network <DOI> \
  --refs-limit 30 --cited-by-limit 50 \
  --existing-dois existing_dois.txt \
  --output expanded_<seq>.json
```

**评分闭环：**

1. 收集所有 `expanded_*.json` 并合并去重。
2. 与现有文献库做 DOI 去重，排除已有。
3. 对新增论文复用 4.5 五维度评分。
4. 对新增论文复用 4.6 Tier 分级。
5. T4 剔除，T1-T3 追加到检索文献表，标注 `source: openalex_citation_network`。
6. 记录到 `decision_log`：新增 X 篇（T1: a, T2: b, T3: c），种子 Y 篇。

**防爆炸规则：**

- 最多 10 篇种子论文。
- refs-limit 30 + cited-by-limit 50 = 每篇最多 80 条原始结果。
- 不做第二跳。

### 4.8. 饱和度曲线估算

> 基于全量 T1-T3 文献（原始 + 扩展）计算最终覆盖率。它只用于解释检索覆盖，不强制停止工作流。

**条件门：** T1-T3 文献数 ≥ 30 时执行；少于 30 篇时跳过，并标注 `insufficient_data`。

```bash
python3 scripts/discovery_curve.py \
  --results 检索文献表.md \
  --output saturation_snapshot.json
```

**解读输出：**

| coverage_estimate | CI 宽度 | Agent 判断 |
|:-----------------:|:-------:|-----------|
| ≥ 0.85 | < 0.15 | 覆盖良好 |
| ≥ 0.85 | > 0.15 | 信心不足 |
| 0.6-0.85 | - | 中等覆盖 |
| < 0.6 | - | 覆盖不足 |
| fit_failed | - | 无法拟合 |

### 4.9. 报告生成、索引清单与完成检查

4.9 统一处理最终交付物生成、`retrieval_index_manifest.json` 更新、文件存在性验证和 Step 5/6 转交。标准 Step 4 只有通过 4.9，才可声明完成。

**4.9.1 生成 `检索文献表.md`**

Agent 生成最终版 `.md` 文件，仅含 T1-T3（T4 进入排除说明）。顶部必须展示筛选依据，让用户回看“根据什么筛选”。

**必须保留的回溯字段：**

| 字段 | 说明 |
|------|------|
| `record_id` | Step 4 稳定记录 ID；展示层截断时必须保留 |
| `citekey` | BibTeX citation key；用于回查 `文献库.bib` |
| `search_task_id` | 来自 Step 3 `search_tasks[].id` |
| `chapter_id` | 来自 Step 3 `search_tasks[].chapter_id` |
| `chapter_title` | 来自 Step 3 `search_tasks[].chapter_title` |
| `evidence_type` | review/method/experiment/data/standard/case |
| `source` | openalex/crossref/semantic_scholar/arxiv/pubmed/cnki/wanfang |
| `tier` | quick/standard/deep |
| `score` | 0-25 |
| `paper_tier` | T1/T2/T3 |
| `article_url` | 中文论文详情页 URL；英文可为空 |
| `paper_card` | JSON 机器源完整保留；展示层只显示 `evidence_role / content_fit / reading_depth` 摘要 |

`检索文献表.md` 是展示层，允许对标题、摘要、URL 和评分理由做排版截断；但截断行必须保留 `record_id` 和至少一个可回查字段（`citekey` / `source_id` / `DOI` / `article_url` / `source_url`）。

**顶部必须包含：**

```md
## 检索概况
- 检索日期：YYYY-MM-DD
- Tier：quick / standard / deep
- 数据库：OpenAlex, Semantic Scholar, Crossref[, arXiv][, CNKI][, Wanfang Data][, PubMed]
- 原始检索：X 篇 -> 去重后 Y 篇 -> 评分后 Z 篇 (T1: a, T2: b, T3: c, T4: d 剔除)
- 引文扩展：+X 篇 (T1: a, T2: b, T3: c)，种子 Y 篇 [若触发]
- 最终文献：Z 篇 (T1-T3)
- 饱和度：coverage% (CI: ci_l%-ci_u%) [若执行]

## 筛选依据
- 研究问题依据：...
- 纳入规则：...
- 排除规则：...
- 评分维度与权重：...
- Tier 阈值：...
- 用户确认：CP-SCREENING-BASIS confirmed / adjusted / candidate-only
```

**4.9.2 生成 `中文论文元数据.json`（条件性）**

触发条件：检索文献表中存在 `source=cnki` 或 `source=wanfang` 的行。无中文论文时跳过并记录原因。

字段约束：

| 字段 | 必填 | 说明 |
|------|:--:|------|
| `title` | 是 | 论文标题原文 |
| `source` | 是 | `cnki` 或 `wanfang` |
| `source_id` | 是 | 内部稳定标识符，不得当作真实 DOI |
| `article_url` | 是 | 文章详情页 URL；无 URL 的行不写入 JSON |
| `doi` | 可选 | 仅填写真实 DOI |
| `authors` | 建议 | 中文作者数组 |
| `year` | 建议 | 发表年份 |
| `publication_title` | 建议 | 期刊/会议/学位授予单位等来源名称 |
| `abstract` | 可选 | 中文摘要 |
| `language` | 建议 | 固定为 `zh-CN` |

`中文论文元数据.json` 是机器交接层，禁止截断中文标题、摘要、作者、来源名称、source_id 和 article_url。后续 `文献库.bib`、Step 6 中文 Zotero 入库和 Step 7 引用审计不得从已截断的中文 Markdown 行恢复这些字段。

**4.9.3 生成 `.xlsx`、`.bib`、`检索报告.md/.pdf`**

```bash
python3 scripts/generate_retrieval_report.py 检索文献表.md

python3 scripts/generate_search_report.py \
  --results 检索文献表.md \
  --saturation saturation_snapshot.json \
  --output 检索报告.md
```

检索报告必须包含 4.4 的筛选依据、五维评分说明、Tier 分级、排除原因、引文扩展摘要、饱和度解释和下一步行动。综述或系统综述场景下，还必须显式写出 `screening rationale`（为什么保留当前文献）和 `exclusion buckets`（剔除条目的主要原因分类）。

**4.9.3.a 英文摘要补全（可选后处理，不阻塞 Step 4 主流程）**

适用范围：

- 仅针对英文源（如 OpenAlex / Crossref / Semantic Scholar / arXiv / PubMed）
- 优先针对 `T1/T2` 论文
- 仅在英文 `T1/T2` 文献存在缺摘要条目时考虑执行
- 默认使用公开元数据/API 补全，不要求机构登录

默认规则：

- Step 4 完成真实检索后，Agent 应先汇报英文 `T1/T2` 摘要覆盖率，例如 `12/22`。
- 英文摘要补全属于 `optional post-processing`，不得默认静默执行，不得阻塞 Step 5/6/7 转交。
- 当英文 `T1/T2` 缺摘要比例较高（建议阈值：`> 30%`），或用户后续意图明显是综述写作、证据矩阵、Step 7 写作时，Agent 应主动建议执行该后处理。

**摘要补全确认 checkpoint（CHECKPOINT E — CP-EN-ABSTRACT-ENRICH）：**

> **交互兼容性规则：**
> - 若当前智能体/宿主环境支持弹窗、结构化选项卡片或 `request_user_input`，优先使用结构化交互。
> - 若当前智能体不支持弹窗或结构化 UI，必须退化为固定文案 + 明确编号选项的纯文本 checkpoint。
> - 无论使用弹窗还是纯文本，选项语义、执行范围和产物记录必须一致。

推荐弹窗/结构化文案：

```text
标题：补全英文摘要？
说明：当前英文 T1/T2 文献摘要覆盖率为 X/Y。可以执行一次公开源摘要补全，不需要机构登录；能补就补，补不到会保留缺失标记。

选项：
A. 立即补全
B. 跳过
C. 稍后再说
D. 仅补 T1
```

纯文本降级版必须输出同等信息，不得简化成“要不要补摘要？”。

选项语义：

- `A. 立即补全`
  - 立即执行英文摘要补全脚本
  - 默认范围为英文 `T1/T2`
- `B. 跳过`
  - 保持当前结果
  - 在本轮 Step 4 结束说明中标记 `english_abstract_enrichment=skipped_by_user`
- `C. 稍后再说`
  - 不在当前 Step 4 执行
  - 允许用户后续在 Step 7 前再次触发
- `D. 仅补 T1`
  - 只对英文 `T1` 条目尝试公开源摘要补全，减少请求量

执行约束：

- 只能补全缺失摘要，不能覆盖已有摘要，除非用户明确要求刷新。
- 公开源补全失败时，必须保留缺失状态，例如 `abstract_missing_after_enrichment` 或等价字段。
- 若未来扩展到 publisher 页面补抓或 PDF 级补全，应另设更高风险 checkpoint，不得沿用本轻量 checkpoint 默许执行。
- 若执行了英文摘要补全并更新了 `workflow_search_results.json`，Agent 必须在当前 Step 4 内重新导出下游交接层：
  - 英文侧：重新生成 `文献库.bib`
  - 中文侧（如存在中文源）：重新生成 `中文论文元数据.json`
  - 展示层如需保持一致，也应同步刷新 `检索文献表.md/.xlsx` 与 `检索报告.md/.pdf`

生成顺序要求：

1. 先生成或确认完整的 `workflow_search_results.json`。
2. `文献库.bib`、`中文论文元数据.json` 必须从完整机器记录生成。
3. `检索文献表.md/.xlsx`、`检索报告.md/.pdf` 才是展示层，可按版面截断。
4. 禁止从已截断的 `检索文献表.md/.xlsx` 或 `检索报告.md/.pdf` 反向生成 `文献库.bib`、`中文论文元数据.json` 或 Step 6 对照 JSON。

**4.9.3a OA 下载线索字段**

Step 4 可在 `workflow_search_results.json` / workflow JSON 中为英文论文写入 OA 候选线索，供 Step 5 的 OA fast 轮次优先使用。该标记只是候选，不代表 PDF 已经下载或验证通过。

| 字段 | 说明 |
|------|------|
| `oa_status` | `unknown / candidate / closed / no_oa` 等候选状态 |
| `oa_source` | OA 线索来源，如 `openalex / semantic_scholar / unpaywall / arxiv` |
| `oa_pdf_url` | 候选公开 PDF URL；不得写 landing page 冒充 PDF |
| `oa_landing_url` | OA 论文落地页，可用于人工核验或二次解析 |
| `oa_license` | 公开许可，如 `cc-by`；未知则留空 |
| `oa_checked_at` | 线索查询时间 |

边界：

- Step 4 只负责标记候选线索，不声明 `oa_pdf_url` 已通过 PDF verifier。
- Step 5 下载后必须重新验证 `%PDF`、最小大小、非 HTML、可读页数；通过后才可记录为 `public_pdf_verified`。
- 缺少这些字段的旧 workflow JSON 仍然有效；Step 5 视为 `oa_status=unknown`。

**4.9.4 更新 `retrieval_index_manifest.json`**

Step 4 执行真实检索、导入已有文献表或更新 `workflow_search_results.json` 后，必须生成或更新 `retrieval_index_manifest.json`。

最小字段：

| 字段 | 说明 |
|------|------|
| `schema_version` | 固定为 `retrieval-index.v1` |
| `index_scope` | `search_results / metadata_cache / candidate_locator` |
| `source_artifacts` | `workflow_search_results.json`、`检索文献表.xlsx`、`文献库.bib` 等来源 |
| `search_task_ids` | 覆盖的 search task |
| `source_count` | 覆盖的检索源数量 |
| `record_count` | 结果记录数量 |
| `index_levels` | 如 `metadata_only / abstract_only / pdf_chunk_pending` |
| `sources` | OpenAlex / Crossref / Semantic Scholar / CNKI / Wanfang 等 |
| `reusable_for` | `step5_download_routing / step6_capability_index / step7_candidate_locator` |
| `authority` | `non_evidence / candidate_only` |
| `staleness` | `fresh / stale / unknown` |
| `rebuild_triggers` | search_tasks、筛选条件、route 或源结果变化时的重建条件 |
| `warnings` | 复用风险 |

边界：

- `retrieval_index_manifest.json` 可以帮助 Step 5 下载、Step 6 capability index 和 Step 7 候选证据定位。
- 它不能把检索命中、摘要、metadata cache 或候选 chunk 直接升级为正文证据。
- 它不直接进入正文、综述矩阵，也不能驱动引用审计结论。
- 评分、纳入/排除、Tier 分级仍以 Step 4 文献表和 `workflow_search_results.json` 为准。

**4.9.4a 默认生成 `step4-dashboard/`**

标准 Step 4 完成链路必须默认生成本地可视化看板，除非用户明确要求极简输出或只导出机器工件。Agent 不应等待用户知道“可视化/看板”这个功能名。

默认命令：

```bash
python3 scripts/export_step4_table.py \
  --workflow-inputs workflow_search_results.json \
  --output-md 检索文献表.md \
  --output-manifest retrieval_index_manifest.json
```

该命令会同步生成 `step4-dashboard/`。如需单独重建看板，可运行：

```bash
python3 scripts/export_step4_dashboard.py \
  --workflow-inputs workflow_search_results.json \
  --output-dir step4-dashboard
```

跳过规则：

- 用户明确说“不要生成看板 / 只要 JSON / 只要表格和 manifest”时，可传 `--skip-dashboard`。
- 仅做 dry-run、评分口径讨论或不产生 `workflow_search_results.json` 时，不生成看板。
- 看板生成失败不得污染 `workflow_search_results.json`；应报告失败并保留已生成的机器主工件。

**4.9.4b Step 2 大纲与关键词证据对账**

当存在 `section_blueprints.json` 或等价 Step 2 结构基线，且本轮完成标准 Step 4 正式检索时，运行：

```bash
python3 scripts/reconcile_step2_after_search.py \
  --outline section_blueprints.json \
  --results workflow_search_results.json \
  --output-json Step2-检索对账报告.json \
  --output-md 大纲关键词-证据校准版.md
```

对账规则：

- 可自动处理：关键词保留/扩展/限定/排除建议、章节覆盖状态、证据需求和 evidence gap。
- 必须用户确认：核心 RQ、研究对象、scope、主要方法路线、章节合并/拆分、创新目标降级。
- 不静默覆盖 `大纲关键词-结构基线.md`；通过源文件哈希保留可追溯差异。
- 对账结果只有所有核心章节达到覆盖要求时才能标为 `evidence_validated`；否则标为 `requires_revision` 并说明受影响章节。
- Step 4 direct-entry 没有 Step 2 基线时，生成“检索后建议大纲与关键词”或记录 `not_applicable=no_step2_baseline`，不要求回跑 Step 2。
- 用户只要求检索、评分、格式转换或已有文献导入时，可记录 `not_applicable=search_or_scoring_only`；对账不阻塞当前局部任务。

`Step2-检索对账报告.json` 必须内嵌 `calibrated_outline`，保留 Step 2 原章节、RQ、章节功能和核心论点，并逐章追加正式检索覆盖、T1/T2 数量、语料候选词和 evidence gap。`大纲关键词-证据校准版.md` 是该机器工件的用户审阅版，不得只输出差异摘要。

**4.9.5 完成检查与转交**

> **Step 4 checkpoint 组织原则：**
> - 中途 checkpoint（如中文库登录、筛选依据确认、英文摘要补全）应放在各自阶段触发，不必强行集中到收尾。
> - 但 **Step 4 收尾类确认** 应尽量聚合展示，避免用户在末尾被零散的多个确认连续打断。
> - 收尾阶段至少应统一展示三类信息：
>   1. 主交付物完成状态；
>   2. 中间检索文件处理选项（保留 / 清理 / 归档）；
>   3. 文献与大纲初始对照状态 + 下一步推荐入口。
> - 若宿主支持结构化交互，优先把这些收尾信息组织为一个连续的 finish summary + cleanup checkpoint，而不是零散散落在多条短消息中。

所有 execution profile 的机器核心必须存在：

| # | 文件 | 若缺失 |
|---|------|--------|
| 1 | `workflow_search_results.json` | 回到检索结果标准化 |
| 2 | `retrieval_index_manifest.json` | 回到 4.9.4 |
| 3 | `research_traceability_matrix.json` | 回到覆盖矩阵生成；不得用总量替代逐任务覆盖 |
| 4 | `stratified_search_audit.json` | 回到分层饱和度与偏差审计 |
| 5 | `search_run_manifest.json` | 运行 `workflow_run_envelope.py create` 并登记当前实际输出 |

`review` 档还必须存在：`检索文献表.md/.xlsx`、`检索报告.md`、`文献库.bib`、`step4-dashboard/index.html`、`research_traceability_matrix.md`、`stratified_search_audit.md`。`release-systematic` 档在 review 基础上还必须存在 `检索报告.pdf` 及系统综述/发布所需工件。`core` 不因缺少这些展示层失败。

条件性交付物必须存在或有跳过说明：

| 文件 | 触发条件 | 若缺失 |
|------|----------|--------|
| `saturation_snapshot.json` | T1-T3 文献数 ≥ 30 | 回到 4.8 |
| `中文论文元数据.json` | 存在 CNKI/Wanfang 论文 | 回到 4.9.2 |
| `Step2-检索对账报告.json` + `大纲关键词-证据校准版.md` | 存在 Step 2 基线且执行标准 Step 4 | 回到 4.9.4b；direct-entry/局部任务必须记录不适用原因 |

4.9 汇报时必须向用户展示：execution profile、实际交付物路径、T1/T2/T3 数量、T4 排除数量、WARN/REJECT 数量、筛选依据确认状态、饱和度状态、下一步推荐入口。

生成统一 run manifest 的示例：

```bash
python3 scripts/workflow_run_envelope.py create \
  --project-root . --output search_run_manifest.json --step 4 \
  --entry-mode direct-query --route-mode direct_entry --execution-profile core \
  --input 检索方案.json --artifact workflow_search_results.json \
  --artifact retrieval_index_manifest.json \
  --artifact research_traceability_matrix.json \
  --artifact stratified_search_audit.json \
  --domain-state search_complete --readiness partial --can-continue \
  --recommended-next-step "Step 5"
```

**用户提示要求（Step 4 完成时必须显式说明）：**

- Agent 必须明确告诉用户：`文献与大纲初始对照已生成`；若存在 Step 2 基线，还要说明 `大纲与关键词证据校准版已生成` 及其状态。
- `review / release-systematic` 档必须明确告诉用户：`Step 4 可视化看板已生成`，并给出 `step4-dashboard/index.html` 路径；`core` 档只说明本轮未生成展示层，不冒充看板已完成。
- 若本轮已导出 `文献-大纲对照.md/.json`，应显式点名该交付物；若当前只在 `workflow_search_results.json` 中内嵌保存，也必须说明“初始对照已写入 workflow JSON，可供 Step 6/7 回查”。
- Agent 不得只说“检索完成”或“可进入下一步”，必须同时说明：
  1. 文献与大纲章节/检索任务的初始挂接状态；
  2. 可视化看板路径和它用于审阅/下载优先级判断；
  3. 下一步可进入 `Step 5` 还是 `Step 6`；
  4. 用户可以直接回复的推荐动作。

推荐提示模板：

```text
Step 4 完成：
- 文献检索已完成
- 文献与大纲初始对照已生成
- 大纲与关键词证据校准版已生成：大纲关键词-证据校准版.md
- 对账状态：evidence_validated / requires_revision / not_applicable
- Step 4 可视化看板已生成：step4-dashboard/index.html
- 可回查字段：search_task_id / chapter_id / chapter_title / evidence_type

下一步可选：
A. 继续 Step 5 下载 PDF
B. 继续 Step 6 生成 Zotero 对照与入库计划

推荐回复词：
- 继续 Step 5
- 继续 Step 6
```

若某一方向当前不满足进入条件，也必须给出降级提示，例如：

- `Step 5 所需下载字段不足，推荐先继续 Step 6 做 Zotero 对照`
- `若暂不下载 PDF，可直接回复“继续 Step 6”`

**中间检索文件清理 checkpoint（CHECKPOINT F — CP-SEARCH-ARTIFACT-CLEANUP）：**

> **交互兼容性规则：**
> - 若当前智能体/宿主环境支持弹窗、结构化选项卡片或 `request_user_input`，优先使用结构化交互。
> - 若当前智能体不支持弹窗或结构化 UI，必须退化为固定文案 + 明确编号选项的纯文本 checkpoint。
> - 无论使用弹窗还是纯文本，选项语义、清理范围和最终文件状态记录必须一致。

默认策略：

- Step 4 完成后，默认**不自动删除**中间检索文件。
- 在用户确认主交付物可用之前，应优先保留补检、调试和增量合并中间文件，方便回滚与复盘。
- 只有当用户明确选择 `清理` 或 `归档`，Agent 才能处理这些中间文件。

推荐弹窗/结构化文案：

```text
标题：清理中间检索文件？
说明：主交付物已生成。中间检索结果可保留用于回滚和复盘，也可以清理或归档。

选项：
A. 保留
B. 清理
C. 归档
```

选项语义：

- `A. 保留`
  - 保留中间检索文件
  - 推荐默认选项
- `B. 清理`
  - 删除非主交付物的中间检索结果
  - 不得删除 `workflow_search_results.json`、`检索文献表.*`、`检索报告.*`、`文献库.bib`、`中文论文元数据.json`、`文献-大纲对照.*`、`retrieval_index_manifest.json`
- `C. 归档`
  - 将中间检索文件移动到 `intermediate/` 或 `archive/`
  - 主交付物保持原位

中间文件判定范围：

- 可清理/归档的典型文件：
  - `workflow_search_results.cnki_*.json`
  - `workflow_search_results.wanfang_*.json`
  - `workflow_search_results.*_v2.json`
  - `workflow_search_results.*_zhcheck.json`
  - 配套的测试/补检 `*.bib`
- 主交付物永远不在该 checkpoint 的清理范围内。

推荐回复词：

- `保留中间文件`
- `清理中间文件`
- `归档中间文件`

---

## 质量门槛 (Quality Gates)

> 以下检查项**全部通过**才能进入 4.9 完成。任一未通过 → 回到对应子步骤修复。

- [ ] 4.2 文献可信度验证已完成——每条保留文献均有 `verification_status` / `verification_confidence` / `verified_sources`；WARN/REJECT 均有 `warn_class`
- [ ] Step 3 提供或 Step 4 direct-entry 重建的最小 `search_tasks` 已展开；每条结果保留 search_task_id/chapter_id/evidence_type/tier/source，并记录 `basis_origin`
- [ ] direct-entry 局部修复已记录 `repair_scope / before_query / after_query / reason / unresolved_assumptions`；修复未静默改变研究对象、核心 RQ 或纳入边界
- [ ] 4.3 DOI 去重已完成——无重复条目
- [ ] 4.4 筛选依据已向用户展示，且 `CP-SCREENING-BASIS` 已确认、调整或标注 candidate-only
- [ ] 4.5 五维度评分已完成——参考用户确认后的 `screening_basis`，并保留评分理由
- [ ] 4.6 Tier 分级已完成——T4 已剔除或进入排除说明
- [ ] 4.7 引文网络扩展已完成（若有 T1 触发）——新论文已评分+分级
- [ ] 4.8 饱和度曲线已生成（若 ≥ 30 篇）或已标注跳过原因
- [ ] 4.9 所选档位核心交付物已生成；所有档位均含 `workflow_search_results.json`、`retrieval_index_manifest.json`、两项 JSON 审计和 `search_run_manifest.json`
- [ ] `review / release-systematic` 档的 `检索文献表.md` 和 `检索报告.md` 均包含筛选依据、纳入规则、排除规则和 Tier 阈值；`core` 不因缺展示层失败
- [ ] `workflow_search_results.json`、`文献库.bib`、`中文论文元数据.json`、`retrieval_index_manifest.json` 作为机器主工件或交接层均禁止截断
- [ ] 展示层若截断长字段，必须保留 `record_id` 和 `citekey/source_id/DOI/article_url/source_url` 中至少一个回查字段
- [ ] `文献库.bib` 不得从已截断的 Markdown/XLSX/PDF 展示层生成
- [ ] `research_traceability_matrix.json/md` 已生成；所有必需 search task 不为 `uncovered/weak`
- [ ] `stratified_search_audit.json/md` 已生成；未饱和任务已补检或明确阻塞，偏差 flags 已解释
- [ ] 有 Step 2 基线的标准检索已生成 `Step2-检索对账报告.json` 和 `大纲关键词-证据校准版.md`；无基线或局部任务已记录 `not_applicable` 原因

---

## 收尾检查 (Closing Checks)

> 文件存在性和字段完整性由 4.9.5 统一处理。此处只保留运行记录、成功判据和失败分流，避免再次维护一套交付物清单。

### 错误日志更新 🆕
- [ ] 本轮是否出现新的 AI 操作错误？
  - 评分偏差 → `.skill-state/error_log.md`
  - DOI 验证失败新模式 → `.skill-state/error_log.md`
  - 饱和度曲线拟合失败 → `.skill-state/error_log.md`
  - 引文扩展查询失败 → `.skill-state/error_log.md`
  - `generate_retrieval_report.py` 执行失败 → `.skill-state/error_log.md`

### 决策日志更新 🆕
- [ ] 评分权重调整？→ `.skill-state/decision_log.md`
- [ ] 筛选阈值修改？→ `.skill-state/decision_log.md`
- [ ] 🆕 引文扩展统计（新增 X 篇/种子 Y 篇）→ `.skill-state/decision_log.md`
- [ ] 🆕 最终交付物生成结果 → `.skill-state/decision_log.md`

### 成功判据
- [ ] 去重、评分、分级和缺口说明都已形成
- [ ] 可把当前结果安全交给 Step 5，而不是只给一个模糊“检索结束”结论

### 完成前必须确认
- [ ] 只有在去重结果、评分分级、缺口说明都齐全时，才能声称“检索完成”
- [ ] WARN/REJECT/待补查条目必须显式分流，不能混进“已完成文献库”

### 失败分流
- 结果太少/太偏：先按 `references/failure-triage.md` 判定是关键词层、数据源层还是筛选阈值层
- 中文元数据不足：先补 article_url/source_id，再决定是否进入下载
- 交付物缺失：回对应子步骤补产物，不直接转 Step 5

---

## 故障排除 (Troubleshooting)

常见问题参见 `agents/known_pitfalls.md`。本 Step 特有的问题：

- **Pre-flight 检查失败**：运行 `python3 scripts/search_by_topic.py --preflight` 验证各 API 端点可达性
- **检索结果过少**：检查 AND 块数是否超过 4；回退到 L2/L3
- **评分偏差**：回顾 error_log 中的评分偏差记录
