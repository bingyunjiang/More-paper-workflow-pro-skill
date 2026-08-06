# Step 7 Figure Workflow

图表工作先检查资产和动作授权，再选择后端。项目统一使用 `figures/`，不把缓存目录或外部绝对路径写入交付稿。

## 资产检查与降级

先运行 `scripts/build_figure_asset_check.py`，生成 `figure_asset_check.json/md`。候选按 `manifest.json -> full.md -> images/ -> PDF direct` 降级。

没有 MinerU ZIP 但本地 PDF 可读时，允许用 PyMuPDF 直接抽取 `pdf_direct` 候选图，状态为 `figure_evidence_status=pdf_direct_candidate_pending_manual_check`。没有可读 PDF 或候选时，保留可解析图位，不静默删除图表需求。

`figure_index.json/md` 记录候选、选中图、来源、图号和 panel；`figure_evidence_report.md/json` 记录 claim 支撑、授权、后端、验证和哈希。

## 图文并茂完成门

默认交付不能只有纯文字。以下三者至少满足一个：

1. `figures/` 相对路径图片已插入正文；
2. 正文保留可解析图位标记，并生成 `figure_index` 与 `figure_evidence_report.md/json`；
3. `draft_risk_summary.md` 明确记录 `figure_mode=skip`、原因、已检查范围和后续补图动作。

Markdown-first 不等于 text-only。已插入的项目内 `figures/` 相对路径图片，或可解析图位标记 + `figure_evidence_report.md/json`，或带 `figure_mode=skip` 原因的 `draft_risk_summary.md`，是最小图文交付。

## 后端与授权

- 原图：`figure_backend=not_applicable`、`figure_asset_action=insert_original`。
- 可信结构化数据新图：`figure_backend=quick`、`figure_asset_action=generate_new`。
- 流程图/架构图/数据流/时序/状态/时间线/ER/用例/对比矩阵：`figure_backend=diagram`。
- 重绘、数值恢复、数字化、可编辑矢量或严格 QA：`figure_backend=reproduction`。

发现论文原图不等于获得重绘授权。只有用户明确要求重绘或数字化，才能记录 `figure_transform_authorization=explicit_user_request` 并进入 reproduction。

原图插入完成后提醒一次：“已按论文原图插入。本 skill 也支持图表重绘、曲线数字化、可编辑 SVG/PDF 和严格 QA；如需启用，请明确指定要重绘的图及目标。”提醒不构成授权。

## 完成状态

`quick / diagram / reproduction` 分别遵守自己的验证报告；`extraction_status / review_status / render_status / delivery_status` 独立记录。render 成功不能替代 extraction/review，图形复现成功也不能证明正文 claim 正确。

数字化固定经过 `inspect -> spec-review/用户确认 -> candidates.csv -> 自动诊断 -> review-decisions.json -> observations.csv -> formal data.csv -> VisualSpec -> render/QA`。候选或 observations 不得直接进入 VisualSpec。
