# Step 1 -> Step 2/3 交接字段

Step 1 的正式机器产物采用 `研究主题.md` front matter 中的嵌套结构。下游不得再维护另一套扁平事实源；旧扁平字段只作为读取兼容别名。

## 规范字段路径

| 交接语义 | 规范字段路径 | 旧扁平别名 |
|---|---|---|
| 研究主题 | `topic.focused_topic` | `topic_statement` |
| 用户阶段 | `user_profile.stage` | `user_stage` |
| 目标类型 | `user_profile.target` | `goal_type` |
| 应用场景 | `topic.application_scenario` | `application_context` |
| 核心研究问题 | `topic.primary_rq` | `core_research_question` |
| 方法路线 | `topic.method_route` | `method_route` |
| 评价指标 | `topic.evaluation_metrics` | `evaluation_metrics` |
| 创新候选 | `innovation` | `innovation_candidates` |
| 检索深度 | `search_tier.tier` | `search_depth` |
| 证据风险 | `pre_review.fatal_risks` | `evidence_risk` |

建议字段继续保存在规范结构中：`topic.scope_boundaries`、`topic.minimum_viable_study`、`topic.topic_kill_criteria`、`evidence_calibration`、`interaction_record` 和中英文种子关键词。

## 决策优先级

1. `pre_review.feasibility.signal=red`、`pre_review.method_readiness.signal=red` 或 `fatal_risks` 非空时，结论必须为 `red`；致命轴优先于总分。
2. 没有致命条件时，按五轴总分判定：`>=21 green`、`15-20 yellow`、`<15 red`。
3. `literature_support=red` 可以表示新颖但证据稀薄的方向，不单独构成致命否决；必须进入风险和检索建议。

## 交接用途

- Step 2 使用规范字段生成章节蓝图、关键词和证据需求表。
- Step 3 使用规范字段生成数据库策略、关键词框架和检索深度。
- 兼容读取器可以接受旧扁平别名，但新写入只产生规范嵌套字段。
- 机器可读映射以 `schemas/workflow-contract-registry.json` 为准。
