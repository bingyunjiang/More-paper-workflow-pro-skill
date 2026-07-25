# 总入口路由规则

本文件定义 `more-paper` 在不改变现有 Step 1-8 主协议的前提下，如何从任意用户输入判断入口。

## 1. 设计目标

- 保留现有 `agents/step_X*.md` 的完整执行协议。
- 新增一层轻量 router，只负责入口判断、最小加载、交接说明。
- 默认支持 direct-entry，不要求用户回到 Step 1。

## 2. 顶层路由优先级

按下列顺序匹配，一旦命中则优先进入对应 Step：

1. 用户提供初稿、段落、已有章节、修订稿：
   - 默认进入 Step 8
   - 若明确要求“开始撰写/扩写”而非润色，则进入 Step 7
2. 用户提供 Zotero 集合、文库结构、`文献-Zotero架构对照.json`、`文献库.bib + PDF 池`：
   - 默认进入 Step 6
3. 用户要求下载 DOI、标题、BibTeX 列表、补附件：
   - 进入 Step 5
4. 用户要求执行检索、评分、筛选、PRISMA-S、引文扩展：
   - 进入 Step 4
5. 用户要求制定检索式、数据库策略、搜索框架：
   - 进入 Step 3
6. 用户提供大纲、目录、章节结构并要求优化或据此检索：
   - 进入 Step 2
7. 用户只给研究方向、想法、问题域、选题困惑：
   - 进入 Step 1

## 3. 入口模式

`entry_mode` 只服务路由，不替代 Step 内部模式：

- `conversational`：普通对话式进入
- `direct-topic`：用户直接给研究方向
- `direct-outline`：用户直接给大纲/目录
- `direct-query`：用户直接给检索式、数据库任务或待执行查询
- `direct-bib`：用户直接给 BibTeX / 文献库
- `direct-zotero`：用户已有 Zotero 文库
- `direct-draft`：用户直接给初稿
- `direct-review-comments`：用户直接给审稿意见/修改要求

## 4. 路由输出

每次路由至少向下游 Step 交付：

- `selected_step`
- `entry_mode`
- `input_basis`
- `missing_but_nonblocking`
- `hard_blockers`
- `recommended_next_step`

这些字段的具体写法见 `static/core/output-contract.md`。
