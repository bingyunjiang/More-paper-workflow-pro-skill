# Step 7 Pre-Review

预审是审稿人视角的写作前或写作后缺陷扫描，不替代引用审计。

## 读取条件

当 `operation=pre-review`，或用户要求“审稿人视角”“预审”“投稿前自查”“rebuttal 预演”时加载本文件。

## 检查项

- 研究问题、方法、结果、贡献是否在当前范围内闭环。
- claim 强度是否超过证据强度。
- 章节功能是否混杂。
- 图表是否被过度解释或缺少正文回扣。
- 机理解释是否缺少变量、路径、边界或反例处理。
- 审稿意见回应是否区分“已改正文”“需补实验/数据”“需作者确认”。

## 输出

- `reviewer_defect_list`
- `revision_roadmap`
- `claim_delta_report`
- `recommended_next_step`
