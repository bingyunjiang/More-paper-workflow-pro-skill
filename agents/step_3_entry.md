# Step 3 Router: 检索方案入口

本文件是 Step 3 的轻量路由层，不替代 [step_3_search_plan.md](./step_3_search_plan.md)。

## 作用

- 判断用户要的是“检索计划”，不是“直接执行检索”
- 根据请求选择一个基础 workflow，并叠加所需 addons
- 避免在 Step 3 装载 Step 5/6/7 的重内容

## base_workflow 与 addons

- `base_workflow=standard`：常规或 deep 检索计划的基础结构
- `base_workflow=systematic`：系统综述基础结构，强制 review protocol
- `addons=citation-expansion`：叠加向前/向后引用扩展方案
- `addons=prisma-s`：叠加检索透明度与日志要求
- `addons=chinese-sources`：叠加中文源和中英文术语映射方案

## 路由规则

- 明确要求“设计检索式/数据库方案/关键词框架” -> `base_workflow=standard`
- 明确要求“系统综述/系统评价” -> `base_workflow=systematic`，并增加 `prisma-s`
- 明确要求“引文网络/向前向后引用/参考文献扩展” -> 增加 `citation-expansion`
- 明确要求“PRISMA/PRISMA-S/检索合规/透明度” -> 增加 `prisma-s`
- 明确要求“知网/万方/中文文献路线” -> 增加 `chinese-sources`

混合请求允许一个基础方案叠加多个 addon，但主输出仍是单一搜索计划。`search_tier=quick|standard|deep` 只控制资源投入；`plan_mode=standard|deep|systematic` 控制方法规范，两者不得互相覆盖。

正式输出还应记录 `plan_state=compiled|pilot_verified|offline_unverified`。无法联网时可以交付 compiled/offline 计划，但不得声称 pilot 已验证。

## 加载顺序

1. `manifest.step3.yaml`
2. `static/core/output-contract.md`
3. `references/evidence-tier-policy.md`
4. workflow 对应 reference
5. `agents/step_3_search_plan.md`

## 输出要求

Step 3 产物至少应交付：

- 关键词组
- 数据库与优先级
- inclusion / exclusion 边界
- 预期 evidence tier
- 进入 Step 4 的执行建议
