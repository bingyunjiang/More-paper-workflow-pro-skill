# 统一输出契约

从本次重构开始，所有 Step 的正式产物都应尽量显式声明以下状态字段。

## 1. 必备状态字段

- `readiness`
  - `blocked`：存在硬阻塞，不能继续执行下一关键步
  - `partial`：可继续，但存在缺口或风险
  - `complete`：本步核心产物已齐备
- `can_continue`
  - `true` / `false`
- `blocking`
  - 真正阻塞下一步的缺失项列表
- `warnings`
  - 非阻塞但重要的风险、降级、证据边界
- `recommended_next_step`
  - 推荐进入的下一 Step 或回退点

## 2. 建议补充字段

- `entry_mode`
- `route_mode`
- `input_basis`
- `evidence_risk`
- `output_artifacts`
- `assumptions`
- `issue_state`
- `state_reason`

`issue_state` 用于跨 `revision_roadmap / claim_delta_report / evidence_gap_list / revision_ledger` 追踪同一问题生命周期，固定值域为：

- `identified`
- `routed`
- `in_revision`
- `verification_pending`
- `closed`
- `blocked_author_decision`
- `blocked_evidence`
- `invalid_or_not_applied`

该状态只约束问题、证据、动作、验证和回退，不约束作者的写作策略、表达风格或创造性组织方式。

## 3. 写法原则

- `blocked` 只用于真实阻塞，不要把“最好补齐”写成阻塞。
- `warnings` 必须可行动，避免空泛风险描述。
- `recommended_next_step` 必须明确到 Step，不要只写“继续后续工作”。

## 4. 示例

```yaml
readiness: partial
can_continue: true
blocking: []
warnings:
  - 缺少中文数据库复核，当前只完成英文源计划
  - 目标期刊尚未确认，写作体裁先按 thesis 处理
recommended_next_step: Step 4
entry_mode: direct-outline
route_mode: direct_entry
input_basis:
  - 用户提供目录草稿
  - 已存在章节关键词清单
```

## 5. Step 间交接要求

- Step 3 -> Step 4：至少交付结构化 search plan、evidence tier 预期；如存在复用索引，同时交付 `retrieval_index_manifest.json`
- Step 6 -> Step 7：至少交付 JSON 映射、集合路径、附件状态、证据风险；如生成资产能力索引，同时交付 `capability_index.json/md`
- Step 7 -> Step 8：至少交付 draft scope、style target、citation risk summary、issue lifecycle summary；Step 8 产出 `diagnostic_summary` + `revision_ledger` + 终稿风险摘要
