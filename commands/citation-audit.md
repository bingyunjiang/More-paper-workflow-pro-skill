# Citation Audit

## 何时使用
- 初稿完成后，需要检查正文引用是否真实、对应、可追溯
- 担心摘要级证据、`WARN` 文献或错配条目支撑了强 claim
- 想在 Step 8 前先排掉高风险引用

## 最小输入
- `论文初稿.md`
- `文献-Zotero架构对照.json` 或 Zotero 集合
- 可选：`pdf-附件池索引.json`

## 主要产出
- `引用审计报告.md`
- `claim_evidence_audit.json`（每个引用位置有稳定 `claim_occurrence_id`）
- 三层状态：
  - `format_status`
  - `mapping_status`
  - `evidence_status`

## 常见阻塞点
- 格式正确不等于证据安全
- 只有摘要无 PDF 的条目必须降权
- `REJECT` 不得被误判为可保留引用
- 同一文献编号在多个 claim 中出现时必须逐处审计，不能按编号去重
- 中文/跨语言低词面重叠只能标记 `cannot-judge / needs-review`，不能由轻量启发式直接判“不支撑”
