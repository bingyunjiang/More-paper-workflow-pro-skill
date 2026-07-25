# Step 3: 生成文献检索方案

> 基于大纲和关键词，生成结构化检索方案。L1→L2→L3 分层路由架构 + 概念块布尔模型 + 反模式检查。

---

## 启动前读取 (Pre-read Checklist)

执行本步骤前，优先确认以下输入或其等价替代物是否可用；若缺失，则在当前 Step 内做最小重建，而不是强制要求补齐前序步骤：

- [ ] `大纲关键词.md` — Step 2 产出（章节大纲 + 关键词清单 + 章节证据需求表）
- [ ] `研究主题.md` — Step 1 产出（tier/search_tier + 聚焦主题 + 预审结论）
- [ ] `references/search-query-frameworks.md` — 检索查询框架参考（概念块布尔模型 + PICO + 反模式清单）
- [ ] `references/search-source-capability-evidence.md` — 各来源官方语法证据、endpoint 边界和降级规则
- [ ] `config/search_source_capabilities.json` — 来源能力机器真相；未经查证的能力不得编译为 exact
- [ ] `manifest.step3.yaml` — Step 3 `base_workflow + addons` 可组合入口定义
- [ ] `references/workflows/search-plan-standard.md` — 🆕 常规检索方案
- [ ] `references/workflows/search-plan-citation-expansion.md` — 🆕 引文扩展方案
- [ ] `references/workflows/search-plan-prisma-s.md` — 🆕 PRISMA-S 透明度方案
- [ ] `references/evidence-tier-policy.md` — 🆕 保守证据分级策略
- [ ] `references/claim-evidence-readiness.md` — 🆕 章节 claim 的可写 readiness
- [ ] `.skill-state/term_aliases.md` — 🆕 术语标准化映射（确保查询用词与大纲一致）
- [ ] `.skill-state/error_log.md` — 已知错误及修复规则
- [ ] `.skill-state/decision_log.md` — 影响本 Step 的结构性决策

---

## 适用任务 (Applicable Tasks)

- 将论文大纲拆解为子课题检索方案
- 构建概念块布尔查询（Concept Block / PICO / Methods-focused）
- 反模式检查（8 项）
- 分配 L1→L2→L3 分层路由
- 生成多策略检索计划（relevance / cited / recent）
- 生成或复用轻量 `retrieval_index_manifest.json`，记录检索索引和结果缓存的可复用状态

---

## 不适用任务 (Non-applicable Tasks)

以下任务不属于本 Step 范围：

- 大纲生成 → 路由到 `agents/step_2_outline.md`
- 执行检索 → 路由到 `agents/step_4_search_score.md`
- 文献评分 → 路由到 `agents/step_4_search_score.md`

---

## 输入要求 (Input Requirements)

| 输入 | 来源 | 格式 | 必选 |
|------|------|------|:--:|
| 章节大纲 | Step 2 `大纲关键词.md` / 用户目录 | .md / 文本 | ✅ |
| 关键词清单 | Step 2 `大纲关键词.md` / 当前 Step 补提取 | .md / 文本 | ✅ |
| 章节证据需求表 | Step 2 `大纲关键词.md` / 当前 Step 补提取 | .md / 结构化摘要 | ✅ |
| 术语映射表 | Step 2 → .skill-state/term_aliases.md | .md | 推荐 |

**独立入口规则：**

如果用户已有大纲、章节列表、开题报告、论文草稿或导师给定目录，可直接从 Step 3 开始，不要求回跑 Step 1/2。Agent 应在当前 Step 内完成：

1. 从用户材料中抽取最小可用的章节结构、关键词和证据需求。
2. 输出 soft `CHECKPOINT 2 — CP-OUTLINE`，设置 `route_mode: direct_entry`，`status: satisfied_by_user_artifact` 或 `satisfied_by_agent_reconstruction`，记录“当前检索将基于哪份大纲/目录”。
3. 大纲可用时直接生成 `search_tasks`；只有章节结构、主题对象或关键词缺失到无法安全生成检索方案时，才设为 `status: blocked` 并请用户补充。

**Direct-entry input contract：**

| 可接受输入 | 最小处理 | 输出 |
|------------|----------|------|
| 已有目录/章节列表 | 抽取 chapter_id、chapter_title、关键词候选 | `search_tasks` 草案 |
| 开题报告/研究计划/论文草稿 | 反推研究主题、章节证据需求、术语表候选 | `search_tasks` + 术语补充建议 |
| 用户给定关键词/数据库偏好 | 直接生成概念块和 route | `检索方案.md` |
| 已有检索式 | 转换为 search_tasks，不要求回到 Step 2 | 可执行检索方案 |

Step 3 的成功标准是生成当前任务可用的 `search_tasks`，不是补齐完整 Step 1/2 产物。缺少正式 `研究主题.md` 或 `大纲关键词.md` 时，必须在 `CP-OUTLINE` 中记录输入依据和缺失项，但不得阻止检索方案生成，除非用户材料不足以判断研究对象或章节范围。

**流程设计补充：**

- `消费方分析`：生成检索方案前先确认谁会消费结果：Step 4 评分、Step 5 下载、Step 6 Zotero 集合、Step 7 写作或系统综述筛选协议。
- `依赖分析`：每个 `search_task` 必须绑定章节、证据类型、查询块、语言路由和排除词；缺任一关键依赖时标为风险，而不是凭空补强。
- `风险标注`：查询过宽、AND 块过多、中文源未加语言边界、系统综述缺纳排标准，都必须写入检索方案风险区。
- `快速通道边界`：用户已有检索式时可以直接标准化为 `search_tasks`，但快速通道不跳质量门，仍要做反模式检查、语言路由和后续消费方说明。
- `契约变更 vs 实现变更`：改变 `search_tasks` 字段、route、tier、纳排标准属于契约变更；只替换具体数据库命令属于实现变更。

**系统综述 / 综述型分支：**

若 Step 1 的 `research_intent_type` 为 `综述型` 或 `系统综述型`，或用户显式要求 PRISMA / systematic review，则 Step 3 必须在常规 `search_tasks` 之外补入：

- `review_protocol`
- `inclusion_criteria`
- `exclusion_criteria`
- `screening_priority`

此分支不改变 `Step 1-8` 主结构，只增强检索方案的筛选透明度与可解释性。

**Step 2 字段读取规则：**

| 字段 | 用途 |
|------|------|
| 章节大纲 | 决定检索子课题编号、章节归属和检索顺序 |
| 关键词清单 | 提供核心词、同义词/缩写、上位词、下位词、方法词、场景词、指标词、排除词 |
| 章节证据需求表 | 决定每个子课题需要找综述、方法、实验、数据、标准、案例中的哪类证据 |
| 检索语言 | 决定中文/英文/中英文混合路由 |
| search_tier 或 tier | 决定 limit、策略数量和补充源 |

**Tier 读取优先级：**

1. 优先读取 `研究主题.md` 顶层 `tier`
2. 若无顶层字段，读取 `研究主题.md` 的 `search_tier.tier`
3. 若仍缺失，读取 `大纲关键词.md` 的 `search_tier`
4. 全部缺失时默认 `standard`

---

## 标准输出 (Standard Outputs)

| 输出 | 格式 | 说明 |
|------|------|------|
| 检索方案.md | .md | v3.1：含 search_tasks + 分层路由 + 概念块拆解 + 反模式检查 |
| 检索方案.json | .json | 🆕 Step 3 机器执行源，稳定承载 `search_tasks`、route、tier、query_blocks |
| `retrieval_index_manifest.json` | .json | 🆕 轻量检索索引清单：记录 search_tasks、workflow results、metadata cache 的复用状态 |
| 检索方案.pdf | .pdf | 自动由 md_to_pdf.py 生成 |

> 从本版开始，`检索方案.json` 是 Step 3 交给 Step 4 的机器执行源；`检索方案.md` 是人工审阅版。若两者同时存在，以 JSON 为准。
> `retrieval_index_manifest.json` 只记录检索索引和缓存是否可复用，不包含正文证据裁决，不替代 Step 4 评分表，也不触发全文 RAG。

---

## 执行流程 (Execution Flow)

### 执行流程总览

```
Step 2 产出（大纲关键词.md）
  → ① 领域识别：判断工科子领域（机械/电气/土木/材料/控制/信号/AI...）
  → ② 读取章节证据需求表：按章节ID + 证据类型生成 search_tasks
  → ③ 框架选择：Concept Block（工科默认）/ PICO / Methods-focused
  → ④ 概念块拆解：每块通常 ≥2 个变体；唯一规范术语可保留单词并记录理由
  → ⑤ 组装布尔查询：(syn1 OR syn2) AND (syn3 OR syn4) NOT (excl)
  → ⑥ 反模式检查（8 项）
  → ⑦ 读 Step 2 产出中的「检索语言」字段 → 中文→L1 CNKI→L2 Wanfang；英文→L1 OpenAlex→L2 Crossref→L2 Semantic Scholar→L3 PubMed
  → 产出：检索方案.md → 检索方案.pdf
```

### 3.1. Search Tasks 结构化模板

`检索方案.json` 必须包含机器可读的 `search_tasks`，供 Step 4 执行；`检索方案.md` 负责展示同一内容的可读视图：

```yaml
plan_mode: standard|deep|systematic
plan_state: compiled|pilot_verified|offline_unverified
base_workflow: standard|systematic
addons: [citation-expansion, prisma-s, chinese-sources]
execution_context: step3_planning|step4_direct_entry
retrieval_language: zh|en|mixed
source_scope: [openalex, crossref, semantic_scholar_bulk]
publication_year_range: {from: 2000, to: null}
document_types: [journal_article, conference_paper]
known_relevant_records: []
inclusion_criteria: []
exclusion_criteria: []
deduplication_plan: {keys: [doi, normalized_title], software: "", version: ""}
query_versions: [{version: v1, date: YYYY-MM-DD, reason: initial}]
search_update_policy: {rerun_before_submission: true, last_search_max_age_days: 90}
core_research_question_ids: [RQ1]
search_tasks:
  - id: S1
    rq_id: RQ1
    chapter_id: ch1
    chapter_title: "绪论"
    evidence_type: "review|method|experiment|data|standard|case"
    question_to_answer: ""
    framework: "concept_block|pico|methods_focused"
    required: true
    query_blocks:
      - name: "研究对象"
        terms: ["term1", "term2"]
        required: true
        single_canonical_term_reason: ""
      - name: "方法"
        terms: ["term3", "term4"]
    exclusion_terms: []
    route:
      language: "zh|en|mixed"
      l1: ["cnki|openalex"]
      l2: ["wanfang|crossref|semantic_scholar|arxiv"]
      l3: ["pubmed"]
    recommended_commands: []
    source_compilation: {}
    minimum_t1_t2: 2
    known_relevant_records: []
    pilot_acceptance_criteria:
      min_title_abstract_precision_proxy: 0.5
      require_all_concept_blocks: true
      min_seed_recall: 1.0
    anti_patterns_checked: true
review_protocol:
  databases: []
  platforms: []
  search_dates: []
  full_strategies: []
  controlled_vocabulary: []
  supplementary_sources: []
  press_review: {status: pending, reviewer: "", date: null, findings: []}
retrieval_index_manifest:
  schema_version: "retrieval-index.v1"
  index_scope: "search_plan"
  source_artifacts: ["检索方案.json"]
  reusable_for: ["step4_search_execution", "step4_dedup_scoring"]
  authority: "non_evidence"
  rebuild_triggers: ["search_tasks_changed", "route_changed", "tier_changed"]
```

**生成规则：**

- 每个 `search_task` 必须绑定 `chapter_id` 和 `evidence_type`
- 一个章节可生成多个任务，例如 `ch2-method`、`ch2-experiment`
- `question_to_answer` 必须来自章节证据需求表，不得凭空新增
- `query_blocks` 优先使用关键词清单中的核心词、同义词/缩写、方法词、场景词、指标词
- `exclusion_terms` 优先来自关键词清单的排除词
- `review_protocol` 在 `plan_mode=systematic` 时强制填写；普通与 deep 模式可省略
- `search_tier` 只决定 limit、策略数量和补充源；`plan_mode` 决定普通、深度或系统综述方法合同。
- `base_workflow` 只能有一个；`addons` 可组合，最后仍编译为一份 `search_tasks`。
- 计划生成后先标记 `plan_state=compiled`；试检索通过后提升为 `pilot_verified`；离线或来源不可用时使用 `offline_unverified`，不阻塞计划交付。
- 每个来源必须保存 `compile_status=exact|degraded|manual_required|invalid`；`degraded` 必须带 `post_filter_required=true` 和丢失语义，`manual_required` 不得声称官方 API 精确编译
- 关键词分层只用于检索表达层，不等于 Zotero 分类层；它服务于检索式构造、召回控制和路由，不负责文献归档。
- `query_blocks` 默认保留核心词、同义词/缩写、方法词、场景词、指标词和排除词；上位词/下位词只在检索过窄、过散或需要扩召回时补入。

### 3.2. retrieval_index_manifest 复用规则

Step 3 可生成或更新 `retrieval_index_manifest.json`，用于告诉 Step 4 当前检索计划、历史检索结果、metadata cache 是否可复用。

最小字段：

| 字段 | 说明 |
|------|------|
| `schema_version` | 固定为 `retrieval-index.v1` |
| `index_scope` | `search_plan / search_results / metadata_cache / candidate_locator` |
| `source_artifacts` | 该索引来自哪些文件，如 `检索方案.json`、`workflow_search_results.json` |
| `search_task_ids` | 覆盖的 search_tasks |
| `source_count` | 涉及检索源数量 |
| `record_count` | 已有记录数量；Step 3 仅规划时可为 0 |
| `reusable_for` | 可复用场景，如 `step4_search_execution`、`step4_dedup_scoring` |
| `authority` | 固定为 `non_evidence` 或 `candidate_only` |
| `rebuild_triggers` | 何时必须重建索引 |
| `warnings` | 复用风险 |

边界：

- 该 manifest 只服务检索复用和后续候选定位，不直接进入正文、综述矩阵或引用审计结论。
- 当 `search_tasks`、route、tier、语言或纳入/排除条件变化时，必须重建或标记为 stale。
- Step 3 不基于 manifest 判断某条文献是否真的支撑 claim。

### 3.3. 查询构建框架

#### 框架选择

| 框架 | 适用场景 | 概念块结构 |
|------|---------|-----------|
| **Concept Block**（工科默认） | 探索性检索、大多数工科问题 | 2-4 个核心概念块，每个含 2-5 个同义词 |
| **PICO** | 有明确干预/对比的工科问题 | Population + Intervention + Comparator + Outcome |
| **Methods-focused** | 方法学论文 | Method + Application + Validation |

#### 概念块模型

> 概念块是检索语义分层，不是文献管理分类。Step 3 只负责把关键词组织成可执行检索式，真正的 Zotero 分类与集合组织留到 Step 6。

```
✅ 正确 — 概念块模型：
  C1 — 冷却对象: ("cold plate" OR "liquid cooling" OR "microchannel")
  C2 — 方法: ("topology optimization" OR "shape optimization" OR "generative design")
  C3 — 验证: ("experimental" OR "test rig" OR "measurement")
  排除: NOT ("PCM" OR "phase change" OR "spray cooling")
  组合: C1 AND C2 AND C3 NOT 排除
```

#### 🆕 术语一致性规则

- 概念块中的**核心词**必须与 `.skill-state/term_aliases.md` 中的 Main Term 一致
- 同义词展开时，将 Aliases 列的内容作为 OR 候选项
- 若发现大纲关键词使用了与众不同的术语变体，在此处统一为 Main Term

#### AND 块数限制

| AND 块数 | 预期结果 | 建议 |
|:--------:|---------|------|
| 2 | 100-500 条 | ✅ 推荐 |
| 3 | 20-200 条 | ✅ 常见 |
| 4 | 5-50 条 | ⚠️ 边界 |
| 5+ | 0-10 条 | ❌ 禁止，拆分为 2 个独立查询 |

### 3.4. 反模式检查清单

| # | 反模式 | 说明 |
|---|--------|------|
| 1 | `language=english` 过滤 | ❌ 过严，丢弃中日韩研究 |
| 2 | 🔴 CNKI/万方检索不带 `--language zh` | ❌ 中文库中混有英文论文，必须加 `--language zh` |
| 3 | 无意义限定词 | ❌ `AND "human"` 等 |
| 4 | AND 块数 > 4 | ❌ 召回率断崖下跌 |
| 5 | 单概念无变体且无理由 | ⚠️ 通常至少 2 个变体；唯一规范术语须写 `single_canonical_term_reason` |
| 6 | 跨来源硬套字段语法 | ⚠️ 字段限制必须由 source capability 决定；不得把 OpenAlex 旧 `title.search`、PubMed `[tiab]` 或网页字段语法互相套用 |
| 7 | 排除词用方法学术语 | ⚠️ 如 `NOT "simulation"` 会误杀 |

### 3.5. 工科检索分层架构

路由由 Step 2 产出中的 **「检索语言」** 字段决定。如果直接进入 Step 3（无 Step 2 产出），则从关键词/查询词中自动检测：含中文字符 → 中文路由；否则 → 英文路由。

```
检索语言: 中文
  → CNKI + Wanfang     ← 双源并行检索（--parallel），结果在 Step 4.2 以 DOI 去重合并。
                         同一论文出现在两个源 → Step 4.3 评分「主题匹配度」+1。
                         两库高度重叠，并行再合并是最高效策略。
  → 🔴 必须加 --language zh   ← CNKI 和万方数据库中包含中文学术期刊发表的英文论文。
                                  本 workflow 将中文源定位为中文学术记录补充，英文文献由 OpenAlex 等英文源覆盖。
                                  --language zh 会：(1) CNKI 端设置 isinEn=0 停用中英文扩展；
                                  (2) 万方端设置 lang=chi URL 参数；(3) 结果级标题语言检测安全网。

检索语言: 英文
  → L1  OpenAlex         ← 全学科覆盖最广（2.5 亿+），默认首选
     L2  Crossref         ← DOI/出版社元数据补充（必选源，不可跳过）
     L2  Semantic Scholar ← CS 交叉子领域并行，传统工科回退；用于影响力/引文富集
     L2  arXiv (条件触发)  ← 🆕 仅 CS/AI 跨域信号时启用（T-0~T-4 新鲜度窗口）
     L3  PubMed           ← 仅医工交叉启用

> **🔴 Deep tier 下 Crossref 强制规则：** 当检索深度为 deep 时，Crossref 必须作为英文文献补充检索源执行，
> 不得仅用 OpenAlex 完成英文检索。Standard tier 下，若 Semantic Scholar 返回 429 或中文源不可用，
> Crossref 同样必须启用作为补充源。

检索语言: 中英文混合 → 按子课题拆分，分别走中文/英文路由
```

> **中英文路由边界：** CNKI + 万方默认只承担中文学术记录；英文文献交由 OpenAlex、Crossref、Semantic Scholar、arXiv 和条件性 PubMed。这是来源分工与质量边界，不是下载阶段的限制。

#### 3.5.1. CNKI 触发条件 🆕

| 信号 | 触发 CNKI? | 说明 |
|------|:---------:|------|
| 查询含中文字符 | ✅ YES | 中文查询以 CNKI 为 L1（主检索），万方为 L2（补充） |
| 用户明确要求"知网"/"CNKI"/"硕博论文" | ✅ YES | 显式要求 |
| 仅英文查询且无中文语境 | ⚠️ 推荐 | Agent 判断是否遗漏国内团队英文发表 |
| 用户明确要求"仅英文" | ❌ NO | 尊重用户意愿 |

> **CNKI 访问方式**：通过 CDP Chrome 浏览器实现。校园网下浏览器自动 IP 认证，无需额外操作；
> 校外 → CARSI/RVPN 登录（需在 CDP Chrome 中完成一次机构登录，登录态持久化）。
> CNKI 没有可用的纯 HTTP 搜索 API，所有检索均通过 CDP 浏览器完成。
> **CNKI 优势**：支持硕博论文检索、支持多排序策略（相关度/时间/被引/下载）、支持调用 Export API 获取 GB/T 7714 引用格式。

#### 3.5.2. Wanfang 触发条件

| 信号 | 触发 Wanfang? | 说明 |
|------|:------------:|------|
| 查询含中文字符 | ✅ YES | 中文查询以 Wanfang 为 L2（补充检索），补全 CNKI 可能遗漏的医药/自然科学文献 |
| 用户明确要求"中文文献"/"万方"/"Wanfang" | ✅ YES | 显式要求 |
| 仅英文查询且无中文语境 | ⚠️ 推荐 | Agent 判断是否可能遗漏国内团队工作 |
| 用户明确要求"仅英文" | ❌ NO | 尊重用户意愿 |

> **Wanfang 访问方式**：自动检测。校内IP直连（零配置），校外CARSI SSO需在CDP Chrome中完成一次机构登录。
> **Wanfang 限制**：万方 Web 搜索仅支持默认排序，不支持多策略（relevance/cited/recent）切换。在 L2 阶段统一使用 `--source wanfang` 或通过 T2 级联调用。

**🆕 arXiv 触发条件：**

| 信号 | 触发 arXiv? | 说明 |
|------|:----------:|------|
| 查询含 "machine learning" / "deep learning" / "neural network" / "transformer" | ✅ YES | CS/AI 核心术语 |
| 查询含 "computer vision" / "NLP" / "reinforcement learning" / "large language model" | ✅ YES | CS 子领域 |
| 查询含 "AI" / "artificial intelligence" / "LLM" / "GPT" / "graph neural" | ✅ YES | AI 通用术语 |
| 用户明确要求"最新预印本" / "arXiv" / "preprint" | ✅ YES | 显式要求 |
| 传统工科（机械/电气/土木/材料/化工）且无上述信号 | ❌ NO | 默认跳过 |
| 医工交叉 | ❌ NO | PubMed 覆盖 |

**触发时**：在检索方案中写入 `arxiv_enabled: true` + arXiv 查询命令。**未触发时**：写入 `arxiv_enabled: false`。

### 3.6. 多策略检索

每个子课题的 L1 OpenAlex 检索同时跑 3 条策略线：

| 策略线 | 排序方式 | 产出 |
|--------|---------|------|
| **By relevance** | `sort=relevance_score:desc` | 最佳主题匹配 |
| **By citations** | `sort=cited_by_count:desc` | 高引经典 |
| **By recency** | `sort=publication_date:desc` | 最新发表 |

> 同一篇论文出现在 ≥2 条策略线中 → 提升最终评分的「主题匹配度」维度。

### 3.7. Tier-driven 检索参数配置 🆕

> 按“顶层 tier → search_tier.tier → 大纲 search_tier → standard 默认值”的顺序读取检索深度，自动配置检索参数。

| Tier | limit/策略 | strategies | 补充策略 | 适用场景 |
|------|:--------:|-----------|---------|---------|
| Quick | 30 | relevance only | 无 | 快速摸底、博三冲刺 |
| Standard（默认） | 50 | relevance + cited + recent | 无 | 一般文献检索、开题 |
| Deep | 100 | relevance + cited + recent | + seminal cutoff + review type | 综述写作、深度研究 |

**配置写入**：在检索方案顶层和每个 `search_task` 中标注 `tier: quick|standard|deep`，Step 4 根据 tier 选择 `--limit` 值。

### 3.8. Pre-flight 检查

```bash
python3 scripts/search_by_topic.py --preflight
```

在真实全量检索前，先执行结构验证、查询编译和 pilot search（standard 默认 10 条，deep/systematic 可用 20 条）：

```bash
python3 scripts/validate_early_step_output.py step3 检索方案.json
python3 scripts/lint_search_plan.py 检索方案.json \
  --run-pilot --pilot-limit 10 \
  --pilot-output pilot_search_results.json \
  --output compiled_queries.json
```

pilot 必须为每个 `search_task_id` 记录 `hit_count / title_abstract_precision_proxy / required_block_coverage / seed_recall / status`。`zero-result / concept_block_dropout / seed_miss / low_precision` 必须先在当前 Step 3 修查询式；仅当执行上下文明确为 `step4_direct_entry` 时在 Step 4 就地修复，均不强制回跑前序 Step。

`compiled_queries.json` 还必须保留 `source_compilation`：

- OpenAlex 使用当前官方 `search=` 布尔语法；长 URL 超过约 4 KB 时拆分 OR 列表并按 work ID 求并集。
- Semantic Scholar `/paper/search` 只能使用 plain text，不得传入 `AND/OR/NOT`；需要布尔语义时显式选择 `/paper/search/bulk`。
- Crossref `query.title/query.bibliographic` 只作为相关性候选召回；概念块 AND/OR/NOT 由 Step 4 客户端复核。
- PubMed 和 arXiv 使用各自官方字段与布尔语法。
- CNKI/万方使用 CDP 网页 adapter，状态为 `manual_required`；UI 变化时重新 probe。

---

## 质量门槛 (Quality Gates)

- [ ] 领域识别和框架选择正确
- [ ] `search_tasks` 已生成，且每个任务绑定章节ID、证据类型和检索问题
- [ ] 每个概念块有 ≥ 2 个有效变体，或已记录唯一规范术语理由
- [ ] AND 块数 ≤ 4
- [ ] 反模式检查 8 项全部通过（含 🔴 `--language zh` 检查）
- [ ] L1→L2→L3 分层路由分配合理
- [ ] 🆕 arXiv 触发条件已检测（arxiv_enabled: true/false）
- [ ] 🆕 Tier 检索参数已配置（顶层 tier + 每个 search_task 的 tier）
- [ ] 🆕 核心术语与 `.skill-state/term_aliases.md` 中 Main Term 一致
- [ ] 🆕 CNKI 触发条件已检测（cnki_enabled: true/false + 访问模式：IP/CDP）
- [ ] 🆕 Wanfang 触发条件已检测（wanfang_enabled: true/false + 凭证存在性）
- [ ] Pre-flight 检查已通过
- [ ] Step 3 结构验证通过，`compiled_queries.json` 无 lint error
- [ ] 每个来源的 `source_compilation` 已生成；没有 `invalid`，所有 `degraded/manual_required` 均有降级或人工探针说明
- [ ] 每个 search task 已完成 pilot，所有必需概念块在标题+摘要中均有覆盖，种子文献召回和精度代理达标
- [ ] `plan_mode=systematic` 时，PRISMA-S 可复现字段和 PRESS 审核记录已齐全

---

## 收尾检查 (Closing Checks)

### 产出完整性
- [ ] `检索方案.md` 已生成（含 search_tasks + 完整概念块拆解 + 分层路由 + 反模式检查）
- [ ] `检索方案.pdf` 已自动生成

### 术语一致性检查 🆕
- [ ] 检索方案中的核心词是否与 `.skill-state/term_aliases.md` 中的 Main Term 一致？
- [ ] 是否发现了新的术语变体？→ 追加到 Aliases 列

### 错误日志更新 🆕
- [ ] 本轮是否出现新的 AI 操作错误？
  - 框架选择不当 → 追加到 `.skill-state/error_log.md`
  - 同义词展开遗漏 → 追加到 `.skill-state/error_log.md`

### 下一步提示
- [ ] 向用户明确说明下一步：执行多渠道检索（Step 4）
  > **下一步 → Step 4：** 按检索方案的 L1→L2→L3 分层路由执行多渠道检索，对结果进行 5 维度评分和 Tier 分级筛选。

### CHECKPOINT 3 — CP-SEARCH

执行 Step 4 多源检索命令前，必须输出 checkpoint 块并等待用户明确确认。
生成或修改 `检索方案.md`、search_tasks、关键词扩展和 dry-run 摘要不触发本 checkpoint。

```md
## CHECKPOINT 3 — CP-SEARCH

route_mode: normal_chain|direct_entry|resume|repair|partial_artifact
status: confirmed_by_workflow|satisfied_by_user_artifact|satisfied_by_agent_reconstruction
blocks_next: Step 4 multi-source search execution
must_confirm: true

summary:
- `检索方案.md` 已包含 search_tasks、L1/L2/L3 路由、tier、中文源策略和概念块布尔查询。
- 用户可确认执行真实检索命令、要求轻量修改检索式，或暂停补充数据库/关键词偏好。

required_confirmation:
- “确认 CP-SEARCH”
```

---

## 故障排除 (Troubleshooting)

- **Pre-flight 检查失败**：检查网络连接，确认各 API 端点可达
- **检索结果预期过少**：减少 AND 块数（4→3→2），放宽同义词范围
- **术语不一致**：回查 `.skill-state/term_aliases.md`，确保概念块核心词与 Main Term 对齐
- **search_tasks 与大纲脱节**：回查 Step 2 的章节证据需求表，确保每个任务都有章节ID和 evidence_type
