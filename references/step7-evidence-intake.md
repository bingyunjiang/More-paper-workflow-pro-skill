# Step 7 Evidence Intake

Step 7 可以从 Zotero、PDF、BibTeX、CSL JSON、MinerU ZIP、prepared PDF artifacts、evidence pack、已有草稿或用户粘贴材料直接进入。

## 证据等级

- `confirmed`: 有 Zotero 条目、PDF 原文、页码/段落、标注、笔记或用户提供的可核验证据。
- `candidate`: 检索命中、RAG 候选、摘要片段、metadata-only 或 unlinked PDF，只能用于定位和风险提示。
- `missing`: 当前 claim 缺少可核验来源，必须进入 `evidence_gap_list`。

## Intake 要求

- 读取 `.skill-state/artifact_passport.json` 时只把它当材料图谱和 readiness 路由，不覆盖 Step 7 的 `mode`、`operation` 或 `target_genre`。
- 没有 `pdf-附件池索引.json` 时，可从 Zotero MCP、BibTeX、CSL JSON 或本地 PDF 生成最小映射，但不得声明引用安全通过。
- `retrieval_candidates.json` 和 `source_page_hint` 只用于回查，不等同于页码级证据确认。
- `negative_or_conflicting_evidence` 必须保留为风险输入，不得静默删除。

## 最小输出

- `evidence_basis`
- `citation_risk_summary`
- `evidence_gap_list`
- 可继续状态：`blocked / partial / complete`
