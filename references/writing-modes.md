# Step 7 写作模式

## 模式列表

### `full-document`

从证据组织到完整起草。

### `chapter-only`

只写一个或多个指定章节。

### `continue-existing`

在已有草稿上续写、补写、替换局部内容。

### `abstract-only`

只写中文摘要、英文摘要或双语摘要，不扩展论文主体。

### `review-only`

只输出综述主体，不扩展为完整论文。

### `revision-only`

根据审稿意见或明确修订目标进行定向修订；证据不足时先生成修订路线和缺口清单。

## 专项操作

专项操作使用独立的 `operation` 轴，不占用写作范围 `mode`：

- `write`：按当前 `mode` 执行写作。
- `citation-audit`：不扩写正文，只检查 claim 与引文是否匹配。
- `figure`：只处理图表设计、生成、复现与图文接口。
- `pre-review`：从审稿人视角预审当前稿件或核心摘要。

## 图文与资产轴

- `figure_mode=auto_insert|post_write|skip`：决定是否以及何时插图。
- `figure_backend=auto|quick|reproduction|not_applicable`：决定需要生成新图时的执行后端。
- `figure_asset_action=insert_original|generate_new|redraw|digitize`：决定对已有或待生成图形采取的动作。

三个轴互相独立：插入论文原图通常为 `post_write/auto_insert + not_applicable + insert_original`；只有明确授权生成、重绘或数字化时才进入对应动作。

## 默认原则

- 模式先于 prose 风格
- 先确认 `mode + operation`，再加载深 reference
- `operation` 不是新的公开 Step；四类操作都保留在 Step 7 内
