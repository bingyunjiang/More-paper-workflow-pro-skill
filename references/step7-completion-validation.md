# Step 7 Completion Validation

Step 7 使用分层状态，避免把可继续版本误报为完整闭环。

## 正文前硬门控

`step7_execution_card.md` 至少记录 `writing_scope / target_genre / evidence_entry_mode / mechanism_trigger_decision / figure_mode / figure_backend / allowed_claim_strength / blocked_until`。

正文前还要有当前范围的 argument plan 和证据确认区块。只有正文草稿而没有执行卡、citation audit、figure gate 或机理决定，不能声明 evidence closed。

## 状态

- `draft_ready`: 当前范围已有可读初稿，引用、图表或公式仍可有警告。
- `evidence_closed`: 当前范围的强 claim、引用、机理、图表和公式已完成必要审计。
- `ready_for_step8`: 当前范围可交给 Step 8 做成稿级保守精修。

状态绑定当前稿件 SHA-256；稿件变化后，旧审计不得继续作为通过依据。

## 验收

- 运行 `scripts/validate_step7_output.py`。该脚本只校验工件链和关键字段，不评价文章质量。
- 正文引文格式完成门禁止残留原始 Zotero key；引用必须映射为投稿格式并保留 reading depth。
- 有 MinerU ZIP 时的 post_write 限制要求非空 `figure_index.json` 和正文图片或 `[[FIGURE:...]]`。
- 机理类任务缺少 `mechanism_trigger_decision`，或进入后缺少三件机理工件，必须失败。
- quick/diagram/reproduction 分别要求有效报告、hash、授权和后端状态。
- 公式运行 `scripts/equation_guard.py`，阻断 `missing_equation / plain_text_math_leak / unclosed_math_environment`。
- DOCX 交付时回读 OMML/原生公式对象，不能只检查 Markdown。

## 章节证据完成门

当前章节的关键 claim、引用锚点、冲突证据、图表 panel、公式状态和风险清单必须闭合。未闭合时输出 `rollback_if_missing`，回到 argument plan、citation audit 或最小补证据路径。

## Run envelope

将 Step 7 状态写入 `morepaper.workflow-run.v1` 的 `domain_state`，再映射到 `readiness / can_continue / blocking / warnings / recommended_next_step`。`can_continue=true` 不等于当前 Step 完成。
