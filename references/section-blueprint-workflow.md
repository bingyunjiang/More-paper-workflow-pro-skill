# 章节蓝图工作流

## 目标

让 Step 7 写作先得到“写作蓝图”，再生成正文。

## 每个章节建议定义

- 本章功能
- 核心 claim
- 证据来源
- 关键文献
- 需要的图表或表格
- 不该写什么

## 使用顺序

1. 读取 Step 2 大纲和证据需求
2. 映射 Step 4/6 的证据状态
3. 给每章做 claim-evidence blueprint
4. 再开始正文生成

## 工件血缘

- Step 2 的 `section_blueprints.json` 是结构基线，不由 Step 7 覆盖。
- Step 7 生成 `writing_blueprints.json/md`，并记录基线、大纲、风格样本和证据矩阵的 SHA-256。
- 有基线时必须保留 `rq_ids / core_research_question_ids / evidence_calibration / keyword_audit`；direct-entry 无基线时显式记录 `outline_state=not_provided`。
- Step 8 优先读取 `writing_blueprints.json`；旧项目可降级读取 `section_blueprints.json`，并标记兼容路径。
