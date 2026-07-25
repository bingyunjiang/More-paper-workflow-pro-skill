# 目标体裁轴

Step 7 的默认写作目标应由 `target_genre` 决定，而不是默认假设“高水平期刊投稿”。

## 允许值

- `thesis`
- `journal`
- `review`
- `report`
- `proposal`
- `conference`
- `course-paper`

## 各体裁默认偏好

### thesis

- 背景更完整
- 理论基础更展开
- 章节层级更多

### journal

- 更紧凑
- 论点推进更快
- 证据密度更高

### review

- 分类框架优先
- 评价与 gap 识别优先

### report

- 场景、约束、方案、验证清晰

### proposal

- 可行性、计划、风险、技术路线更关键

### conference

- 服从页数、模板和现场交流约束
- 在有限篇幅中优先交付方法、关键结果和可复现信息

### course-paper

- 服从课程任务书、评分 rubric 和教师给定格式
- 重视概念解释、规范表达和学习目标，不默认提升为期刊投稿体裁

## 规则

- target_genre 决定默认结构和语言节奏
- target_journal 只是其下的局部约束，不应反客为主
- `existing-draft` 是入口状态，不是体裁；应映射到 `continue-existing / revision-only` 后继续识别真实 `target_genre`
