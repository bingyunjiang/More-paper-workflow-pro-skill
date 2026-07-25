# Step Handoff Contract

> 跨步骤统一交接契约。用于回答三个问题：**我现在有什么？缺什么？下一步能不能直接做？**

---

## 1. 最小 handoff block

每个关键 Step 收尾时，建议输出以下结构：

```md
## HANDOFF

current_step:
- 当前 Step 编号和名称

confirmed_inputs:
- 已确认输入 1
- 已确认输入 2

primary_outputs:
- 本步主产物 1
- 本步主产物 2

open_risks:
- 尚未解决的风险或缺口

recommended_next_step:
- 推荐下一步
```

机器交接同时写入 `morepaper.workflow-run.v1` envelope；Markdown handoff 只做人类可读摘要，不另造状态事实源。生成和验证入口为 `scripts/workflow_run_envelope.py`，字段定义见 `static/core/workflow-run-envelope.md`。

---

## 2. 字段解释

### `current_step`
- 记录当前处于哪个 Step
- direct-entry / repair / plan-only 时也要如实写

### `confirmed_inputs`
- 只写已经被确认可用的输入
- 不把推测中的材料写进去

### `primary_outputs`
- 只写这一步真正生成或确认可用的产物
- 若是 plan-only，则标明 `plan-only output`

### `open_risks`
- 写会影响下一步质量的缺口
- 不写无关小问题

### `recommended_next_step`
- 给出最推荐的下一步
- 若不建议继续，写明“需先回补哪一层”

---

## 3. 使用原则

- handoff 是**交接块**，不是完整报告。
- handoff 的作用是让代理或用户跨会话恢复时，不必重新猜当前状态。
- handoff 应与 Artifact Passport 互补：
  - Passport 偏 Step 4-8 的机读材料索引与 readiness 路由
  - handoff 偏当前阶段的人类可读结论
  - workflow run envelope 提供 Step 1-8 统一的 `domain_state + readiness` 机器状态

---

## 4. 关键限制

- 不把候选结论写成 confirmed input
- 不把待人工确认项写成 primary output 已完成
- 不因 handoff 存在，就跳过本 Step 的 Completion Gate
