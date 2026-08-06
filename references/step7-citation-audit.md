# Step 7 Citation Audit

引用审计检查 claim、引用位置、证据等级和风险边界，不替代 Zotero 条目整理。

## 三层审计

- 格式层：`format_status`
- 对应层：`mapping_status`
- 证据层：`evidence_status`

每条记录给出 `recommended_action=retain|downgrade_claim|supplement_pdf_or_fulltext|repair_mapping|replace_or_remove`。

## Claim-to-citation 映射

记录字段至少包括：`claim_segment_id / claim_text / claim_type / claim_strength / required_evidence / insert_position / citekey / zotero_item_key / support_grade / reading_depth / evidence_anchor / downgrade_required / recommended_action`。

`support_grade` 值域为 `strong / partial / background / contradictory_or_limiting / metadata_only_candidate / not_supported`。同一 claim 的多条证据保留相同 `claim_segment_id`，不得合并成笼统的“多文献支持”。

## Claim 强度

- `background`: 摘要或元数据只能支撑低风险背景。
- `trend`: 需要多篇文献或系统性证据。
- `parameter`: 无页码/表格锚点不得写强参数句。
- `numeric_comparison`: 必须有图、表、数据或可核验计算。
- `mechanism`: 需要全文、图表/实验/仿真和竞争机制判别。
- `novelty`: 无检索覆盖不得写“首次/创新”。

证据等级决定 claim 强度。蓝图中 `downgrade_required=true` 的 claim 不能以强结论进入正文。

## 图表证据

图表 claim 额外记录 `figure_id / table_id / panel_id / figure_table_panel_binding / caption_support / text_support / visual_support`。只有 caption 的状态不能自动升级为 visual confirmed；`figure_overinterpretation` 必须进入风险清单。

## 章节级完成门

每节结束时检查：关键 claim 已映射、弱支撑已降级、冲突证据已保留、引用位置可追溯、图表/公式锚点独立、`evidence_gap_list` 已更新。未通过时回退 `step_7_argument_plan` 或补证据，不得靠润色关闭。

Crossref / Semantic Scholar 摘要只能补充核验。CNKI/万方文献必须保留本地元数据、详情页、PDF 原文或 Zotero source id。
