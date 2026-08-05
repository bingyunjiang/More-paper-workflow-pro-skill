# Step 7: 论文写作轻量总合同

> Step 7 负责把 Zotero、PDF、BibTeX、证据包、草稿和图表资产转成可审计的学术正文。它可以 direct-entry，但不能跳过证据边界、引用审计、公式门、图表授权和完成状态。

## 启动判断

执行前先确认本轮任务的四个轴：

- `mode`: `full-document` / `chapter-only` / `continue-existing` / `abstract-only` / `review-only` / `revision-only`
- `operation`: `write` / `citation-audit` / `figure` / `pre-review`
- `target_genre`: `thesis` / `journal` / `review` / `report` / `proposal` / `conference` / `course-paper`
- 图表轴：`figure_mode=auto_insert|post_write|skip`，`figure_backend=auto|quick|diagram|reproduction|not_applicable`，`figure_asset_action=insert_original|generate_new|redraw|digitize`

若用户只给出自然语言请求，按 `agents/step_7_entry.md` 和 `manifest.step7.yaml` 选择最小可继续路线。

## 最小 always-load

Step 7 默认只加载：

- `static/core/output-contract.md`
- `static/core/workflow-run-envelope.md`
- `references/genre-style-axis.md`
- `references/writing-modes.md`

其他材料按任务触发加载，不再把完整写作、图表、审计和预审合同一次塞入上下文。

## 按需 reference

- 写作证据 intake：`references/step7-evidence-intake.md`
- 正文生成与章节蓝图：`references/step7-drafting-contract.md`
- 引用和 claim 审计：`references/step7-citation-audit.md`
- 图文联合和图表后端：`references/step7-figure-workflow.md`
- 审稿前预审：`references/step7-pre-review.md`
- 完成状态与验收：`references/step7-completion-validation.md`
- 公式登记、渲染和 DOCX/OMML 门：`references/equation-writing-contract.md`

## 执行顺序

1. 明确写作范围、体裁、证据基础和输出契约。
2. 读取 Artifact Passport 或最小证据包，给出 `evidence_basis` 和风险摘要。
3. 生成或读取章节蓝图，先确定每节的 `one_sentence_argument`、证据需求和 `do_not_write`。
4. 写作时逐段绑定 claim、引用、图表和公式状态；证据不足时输出风险或占位，不提高证据等级。
5. 按 operation 触发引用审计、图表工作或预审。
6. 用 `draft_ready / evidence_closed / ready_for_step8` 声明分层完成状态，并写入统一 run envelope。

## 禁止事项

- 不凭摘要、候选检索命中或模型常识写成 confirmed evidence。
- 不把原图插入提醒当作重绘、数字化或可编辑矢量授权。
- 不在 Step 7 做 Step 8 的成稿级全文润色，除非用户明确要求 revision-only 且范围受控。
- 不把 `can_continue=true` 写成当前 Step 已完整完成。

## 输出要求

正式输出至少说明：`mode`、`operation`、`target_genre`、`figure_mode`、`figure_backend`、`figure_asset_action`、`evidence_basis`、`citation_risk_summary`、`equation_audit_status`、`unresolved_equation_count`、`needs_author_check`、`recommended_next_step`。
