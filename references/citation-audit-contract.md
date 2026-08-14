# 引用审计契约

## 目标

把 Step 7 的 citation audit 明确为一个独立子模式，而不是正文写作附带动作。

## 输入

- 草稿正文
- 引文标记
- 文献条目
- 摘要、笔记、标注或全文

## 输出

- 每条 claim 的支撑状态
- 风险级别
- 句子强度分级：`claim_strength`
- 证据最低要求：`required_evidence`
- 可回查锚点：`evidence_anchor`
- 是否必须降强度：`downgrade_required`
- 是否建议回退到 Step 4 补检索
- 是否建议回退到 Step 6 补证据映射

## Claim 强度分级

引用审计必须先判定 claim 属于哪一类，再决定能写多强。证据等级决定 claim 强度，不允许用顺滑表达掩盖证据不足。

| `claim_strength` | 典型句子 | `required_evidence` | 审计动作 |
|---|---|---|---|
| `background` | 背景、领域现状、研究对象归类 | 综述、摘要、元数据可作为低风险支撑 | 可保留，但不得升级成具体结论 |
| `trend` | 多数研究表明、总体呈现某趋势 | 多篇文献或系统性证据 | 单篇支撑时标记 `weak-support` |
| `parameter` | 温度、应变速率、样本数、实验/仿真设置 | PDF 原文、方法表、用户数据或标准文件 | 无全文/表格锚点时 `downgrade_required=true` |
| `numeric_comparison` | 提高 12%、降低 8.5°C、优于 baseline | 页码、图、表、数据文件或可核验计算 | 必须记录 `evidence_anchor` |
| `mechanism` | 证明某机制、导致、控制、主导、钉扎、载荷传递 | 全文级证据，优先图表/实验/仿真锚点 | 无竞争机制判别时降级 |
| `novelty` | 首次、创新、填补空白、目前尚无研究 | 检索覆盖、对比文献、目标范围说明 | 无检索覆盖不得写强创新 |

## Claim-to-citation 最小字段

每条审计记录至少包含：

- `claim_segment_id`
- `claim_occurrence_id`
- `claim_text`
- `claim_strength`
- `required_evidence`
- `current_evidence_level`
- `evidence_anchor`
- `support_status`
- `downgrade_required`
- `recommended_action`
- `risk_flags`

`evidence_anchor` 应尽量落到 PDF 页码、chunk、section、图/表/panel、Zotero note、annotation、用户数据文件或标准条款。若只能落到题录、摘要或搜索结果，应明确标为候选层。

## 支撑级别

- `support`
- `weak-support`
- `not-supported`
- `cannot-judge`

## 原则

- 不能因为题目相关就判定为支撑
- 没有足够依据时宁可保守
- 同一文献在多个 claim 位置出现时逐处审计，不按文献编号去重
- 中文或跨语言的低词面重叠只能进入 `cannot-judge`，不能由轻量关键词启发式直接判为 `not-supported`
