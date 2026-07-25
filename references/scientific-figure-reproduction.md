# 科学图形生成与可复现验证

## 目录

- 自动后端选择
- 严格复现工作流
- 重建模式
- 工具路由
- 状态与证据边界
- 完成门

## 自动后端选择

先判断是否需要绘图，再选择后端：

- `not_applicable`：已有 MinerU、PDF 或本地图片，只需筛选和插入，不运行绘图代码。
- `quick`：用户明确要求从可信 CSV、实验数据或统计结果生成普通新图，且没有严格复现要求。
- `reproduction`：用户明确要求对论文原图、截图、裁剪图或光栅图执行重绘、数字化、视觉优化、语义审计、矢量验证或可移植复现；或者明确要求 manifest、checksums、严格 QA、可编辑 SVG/PDF。

原图存在、图片中含曲线或识别到 VisualSpec 都不构成用户重绘授权。Step 7
默认插入原图；只有记录
`figure_transform_authorization=explicit_user_request` 后才允许进入
reproduction。进入后依赖不完整必须中止并提示安装
`requirements-figures.txt`，不得静默改走 quick。

## 严格复现工作流

1. 识别每张图和 panel 的来源、用途、数据基础、坐标轴、单位、图例和注释。
2. 如果输入是栅格/PDF 且需要恢复数值，先通过 `figure_evidence_pipeline.py` 建立源文件合同并完成数字化授权；未授权的候选值不得进入 VisualSpec。
3. 创建或更新 `scientificfigure.visualspec.v2`；v1 只作为兼容输入。
4. 对复杂示意图、相图、EBSD、异常填充或领域图像处理使用项目级自定义 renderer，但仍进入统一 QA 闭环。
5. 使用统一入口：

```bash
python scripts/generate_figures.py \
  --backend reproduction \
  --spec visualspec.json \
  --source source.png \
  --output bundle \
  --qa-profile semantic \
  --require-strict \
  --transform-authorization explicit_user_request
```

6. 交付 PNG、SVG、PDF、`render_semantics.json`、视觉与 panel 评分、语义审计、矢量检查、环境记录、manifest、bundle lock、run attestation 和 checksums。
7. 在最终响应前运行 bundle 内 `verify.py`，并检查 `run_report.json` 和 `reproduction_manifest.json`。

## 重建模式

| 来源 | source_strategy | representation | 处理 |
|---|---|---|---|
| 原始或可信表格数据 | `raw_data` | `semantic_vector` | 从数据重新绘制并保留单位、刻度和图例 |
| 只有光栅曲线 | `digitized_raster` | `semantic_vector` | 标定绘图区和坐标映射，导出数字化数据 |
| 设备、机理或参数示意图 | `vector_redraw` | `semantic_vector` | 使用可编辑矢量对象重建 |
| 热图、等高线、相图或图像图层 | `color_region_extraction` 或 `raw_data` | `semantic_raster` 或 `mixed` | 优先使用源数组，否则记录区域提取方法 |
| 用户明确要求像素描摹 | `pixel_trace` | `pixel_primitives` | 只能声明视觉 trace，不得声明科学语义重建 |

多 panel 图允许分别选择模式，不要强迫所有 panel 共用一种来源策略。

## 工具路由

- `scripts/figure_evidence_pipeline.py`：原图/PDF 指纹、图型路由、源身份复核、候选折线提取、覆盖/残差证据和 VisualSpec 桥接。
- `scripts/scaffold_figurespec.py`：生成 VisualSpec 骨架。
- `scripts/validate_visualspec.py`：渲染前校验协议。
- `scripts/run_reproduction.py`：构建自包含复现包并执行完整闭环。
- `scripts/render_visualspec_matplotlib.py`：渲染标准曲线、散点、误差棒、柱状图、区域图、热图、等高线和注释。
- `scripts/data_resolver.py`：读取 CSV、TSV、JSON、NPY、NPZ 和可选 Excel 数据。
- `scripts/score_visual.py`：比较整图与指定 QA 区域，不拉伸参考图掩盖画布误差。
- `scripts/audit_semantics.py`：比较实际 Matplotlib artist 语义与 VisualSpec。
- `scripts/check_vector_output.py`：拒绝伪矢量或整页光栅 SVG/PDF。
- `scripts/trace_image_primitives.py`：仅用于明确接受的 pixel trace。
- `scripts/run_visual_optimization_loop.py`：执行有界布局和画布优化。
- `scripts/check_environment.py`：排查依赖、字体和环境漂移。
- `scripts/validate_portability.py`、`scripts/verify_checksums.py`：验证路径可移植性和交付完整性。
- `scripts/render_visualspec_r.R`：实验性 R 后端，必须进入相同 QA 路径。

字段细节按需读取 `VISUALSPEC_V2_PROTOCOL.md`、`QA_PROFILES.md`、`DIGITIZATION_WORKFLOW.md`、`EXPORT_REQUIREMENTS.md` 和 `FREEZE_POLICY.md`。

## 状态与证据边界

- `semantic_strict_pass`：语义、视觉、矢量和所有要求的 panel QA 均通过。
- `semantic_validated_pass`：没有参考图，但原始数据渲染的语义与矢量检查通过；这不是视觉严格声明。
- `semantic_near_pass`：语义对象已重建，但仍有视觉偏差，必须记录 deviation。
- `visual_trace_pass`：像素 trace 视觉通过，但没有恢复科学数据语义。
- `render_only`：只证明导出文件存在。
- `not_strict` 或 `failed`：不得声明复现完成。

复现状态只说明图形产物与输入/规范的关系，不能自动证明论文 claim 正确。正文 claim 仍需绑定原文、图注、panel 和可核验证据，并由 `figure_evidence_report` 给出 `support_status`。

每个 reproduction 记录还必须包含
`figure_asset_action=redraw|digitize` 与
`figure_transform_authorization=explicit_user_request`。原图直接插入必须使用
`figure_asset_action=insert_original` 和 `generation_backend=not_applicable`。

数字化还必须单独保留 `extraction_status` 和
`value_delivery_authorized`。`semantic_strict_pass` 不能反向授权未通过
源身份、坐标校准、覆盖审计或人工 overlay 复核的提取数据。

自定义 command renderer 不能自我声明 semantic strict；其上限为 `semantic_near_pass`，除非语义由内置提取与审计路径独立验证。

## 完成门

每个目标图至少具备：

- 输入来源和 VisualSpec；
- 独立可运行脚本或明确的 batch 函数；
- PNG、SVG、PDF 或声明的替代格式；
- 整图及必要 panel 的视觉评分；
- 语义审计和矢量验证；
- `reproduction_manifest.json`、`run_report.json`、`bundle.lock.json` 和 `checksums.json`；
- bundle `verify.py` 通过；
- 仍存在的偏差、数据标定假设和证据边界。

机器工件必须使用 bundle 相对 POSIX 路径，不得包含宿主机绝对路径。导出成功不等于 QA 通过。
