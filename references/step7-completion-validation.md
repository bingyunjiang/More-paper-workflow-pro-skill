# Step 7 Completion Validation

Step 7 使用分层完成状态，避免把可继续版本误报为完整闭环。

## 状态

- `draft_ready`: 当前范围已有可读初稿，但引用、图表或公式可能仍有风险。
- `evidence_closed`: 当前范围的强 claim、引用、图表和公式均已完成必要审计。
- `ready_for_step8`: 当前范围可交给 Step 8 做成稿级保守精修。

## 验收

- 引用：运行 claim/evidence 审计，输出 `citation_risk_summary` 和 `evidence_gap_list`。
- 图表：原图插入需有资产检查；diagram/reproduction 需有对应 validation report、hash 和状态。
- 公式：运行 `scripts/equation_guard.py`，确认无 `missing_equation`、`plain_text_math_leak`、`unclosed_math_environment`。
- DOCX：需要交付 DOCX 时，验证公式已转为 OMML 或可接受的原生格式，不能只看 Markdown。
- 状态：写入 `morepaper.workflow-run.v1` run envelope，保持 `domain_state` 与全局 readiness 分离。
