# Step 7 Figure Workflow

图表工作先判定动作授权，再选后端。

## 默认路径

- 论文 PDF、MinerU 或本地已有原图默认 `figure_backend=not_applicable`、`figure_asset_action=insert_original`。
- 原图插入前运行 `scripts/build_figure_asset_check.py`，生成 `figure_asset_check.json/md`。
- 没有 MinerU ZIP 但有本地 PDF 时，可生成 `pdf_direct` 低置信候选图；没有候选时只保留图位占位。

## 新图与复现

- 用户明确要求基于可信 CSV、实验数据或统计结果生成普通图，使用 `figure_backend=quick`、`figure_asset_action=generate_new`。
- 用户要求流程图、架构图、数据流图、时序图、状态图、时间线、ER、用例或对比矩阵，使用 `figure_backend=diagram`，并加载 `references/paper-diagram-contract.md`。
- 只有用户明确要求重绘、复现、恢复曲线数值、数字化或可编辑矢量时，使用 `figure_backend=reproduction`，并记录 `figure_transform_authorization=explicit_user_request`。
- 数字化链路必须完成 `inspect -> spec-review -> candidates.csv -> review-decisions.json -> observations.csv -> formal data.csv -> VisualSpec -> render/QA`。

图表的 `extraction_status`、`review_status`、`render_status` 和 `delivery_status` 必须独立记录。
