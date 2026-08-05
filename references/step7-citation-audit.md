# Step 7 Citation Audit

引用审计用于检查正文 claim、引用位置、证据等级和风险边界，不替代 Zotero 条目整理。

## 检查项

- 每个强 claim 是否有 confirmed evidence。
- 引文是否能追溯到 Zotero item、PDF 原文、页码/段落、笔记或标注。
- 摘要级、metadata-only、unlinked 或 inferred evidence 是否被错误写成确认结论。
- 图表、公式、方法和实验条件是否有独立证据锚点。

## 输出

- `claim_evidence_matrix`
- `citation_risk_summary`
- `evidence_gap_list`
- `rollback_if_missing`
- `needs_author_check`

Crossref / Semantic Scholar 摘要只能作为补充核验，不能替代 Zotero 条目和 PDF 原文。CNKI/万方中文文献必须保留本地元数据、详情页 URL、PDF 原文或 Zotero Extra/source_id。
