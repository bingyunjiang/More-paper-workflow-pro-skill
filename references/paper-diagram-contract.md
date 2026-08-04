# Step 7 原生论文流程图合同

## 目录

1. 适用范围
2. 路由与命令
3. Spec
4. 图型与风格
5. 黑白刊发模式
6. 公式
7. 产物与质量门

## 适用范围

`diagram` 用于新建语义流程图、系统架构图、Agent 架构图、数据流图、时序图、状态图、时间线、对比矩阵、ER 图和用例图。已有论文原图仍直接插入；定量 CSV 图仍走 `quick`；基于图片或 PDF 的重绘、数字化仍要求显式授权并走 `reproduction`。

## 路由与命令

```bash
python3 scripts/generate_figures.py \
  --backend diagram \
  --spec method-diagram.json \
  --output figures/ \
  --inspect
```

`auto` 遇到 `schema_version=morepaper.paper-diagram.v1` 时选择 `diagram`。执行卡使用 `figure_asset_action=generate_new`、`figure_backend=diagram`、`figure_transform_authorization=not_required`。显式 backend 不被自动判断覆盖。

## Spec

```json
{
  "schema_version": "morepaper.paper-diagram.v1",
  "figure_id": "fig-method-workflow",
  "diagram_type": "flowchart",
  "style": "clean",
  "title": "研究方法流程",
  "caption": "从证据输入到结果审阅",
  "canvas": {"width": 1600, "height": 1000},
  "nodes": [
    {"id": "input", "label": "证据输入", "order": 1},
    {"id": "model", "label_runs": [{"kind": "text", "value": "模型 "}, {"kind": "math", "value": "y=f(x)"}], "order": 2}
  ],
  "edges": [{"id": "e1", "source": "input", "target": "model"}],
  "groups": [],
  "annotations": []
}
```

顶层、节点、边、分组和文本 run 均拒绝未知字段。ID 必须稳定且唯一；边必须引用已有节点。坐标只在 `layout_locked=true` 时允许，用于已人工审阅的固定布局。

## 图型与风格

- 图型：`architecture`、`agent_architecture`、`flowchart`、`data_flow`、`sequence`、`state_machine`、`timeline`、`comparison_matrix`、`er_diagram`、`use_case`。
- 风格：`clean`、`terminal`、`blueprint`、`notebook`、`glass`、`editorial`、`minimal`、`dark`、`review-canvas`、`cloud`、`event-stream`、`operations`。

所有图型和风格共享统一 IR、布局、正交走线、语义 SVG 和组合质量门，不使用网络资源。

## 黑白刊发模式

期刊或会议要求黑白、无底纹时必须使用 `style=minimal`。该模式只允许纯黑 `#000000` 与纯白 `#ffffff`：画布和节点均为白色，分组不填充，不使用灰阶、彩色色块、网格、透明底纹或装饰性圆角。`inspect.svg` 仅供审阅，不能作为投稿插图。

刊发字号按画布宽度缩放：1200 px 画布基线为节点文字 18 px、标题 30 px；更宽画布按比例放大，避免高分辨率导出后文字相对缩小。`diagram-check.json.publication_profile` 必须记录推荐图宽 170–180 mm、180 mm 图宽下的节点字号和达到 7 pt 所需的最小图宽。

默认按双栏论文的通栏图设计，并保证在 170–180 mm 下节点文字不低于 7 pt。若目标是单栏图，应先减少节点、压缩标签或拆图，再重新生成；不得只把复杂通栏图整体缩小。

## 公式

节点、边和注释可以使用 `$...$` 行内数学或 `label_runs` 中的 `kind=math`。普通文字保留为可编辑 SVG `<text>`；数学 run 转为 SVG 矢量路径并保留 `data-math`。不支持的命令、矩阵源码、不配对定界符或含义不明表达式进入 `needs_author_check`，不得静默退化为普通文本。

## 产物与质量门

每张图固定生成：

- `figures/<figure_id>.svg`：规范语义产物。
- `figures/<figure_id>.png`：由同一布局场景生成的预览和兼容插图。
- `figures/<figure_id>.diagram-check.json`：Spec、SVG、PNG 哈希与布局检查。
- `figures/<figure_id>.inspect.svg`：仅在 `--inspect` 时生成的审阅覆盖层。
- `figure_evidence_report.json`：Step 7 图形证据记录。

节点重叠、越界、过密构图、悬空边、外部资源、脚本内容、无效 PNG、产物哈希不一致或检查状态非 `pass` 均阻断 Step 7 完成。
