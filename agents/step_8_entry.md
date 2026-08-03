# Step 8 Router: 润色与保守修订入口

本文件是 Step 8 的路由层，不替代 [step_8_polishing.md](./step_8_polishing.md)。

## 作用

- 把润色任务先做 revision scope 判定
- 默认保守改写，不将 Step 8 变成开放式重写器
- 按 `paper_type / language / target_genre / revision_scope` 最小加载
- 启动正文修改前先输出 `Writing Read`，并划定 protected spans
- Step 8 不负责主体写作；它在既有成稿基础上执行受约束补写、直接修改与修订后验证，不接管 Step 7 的完整写作、引用审计或修稿路线图。

## revision_scope

- `local-polish`：局部润色
- `section-revision`：章节级修订
- `full-manuscript-pass`：全稿一轮保守精修

## output_mode / language / target_genre

- `output_mode=quick-polish|audited-polish`：局部低风险任务默认 quick；章节/全文、投稿前或触及 claim/结构时使用 audited。
- `language=zh|en|bilingual`：只决定语言诊断和交付语言，不改变证据边界。
- `target_genre=thesis|journal|review|report|proposal|conference|course-paper`：继承 Step 7 或由当前文稿/用户目标确认；不由 prestige 推断。

## rewrite_scope / rewrite_level

- `rewrite_scope` 控制能不能动结构：`in-place / bounded / structural`，默认 `bounded`。
- `rewrite_level` 控制修多重：`minimal / standard / aggressive`，默认 `standard`。
- 引用、公式、数据、图表和术语密集段落默认降到 `in-place`。
- `aggressive` 只在用户明确允许且不新增证据时使用；触及 claim、引用、章节功能或证据边界时回 Step 7。

## 路由规则

- 用户只给一段或一节 -> `local-polish`
- 用户给一章并要求优化结构 -> `section-revision`
- 用户给完整稿件并要求最终精修 -> `full-manuscript-pass`

## Artifact Passport 读取规则

Step 8 启动时先检查 `$CWD/.skill-state/artifact_passport.json`：

- 有 `draft` 时，可直接进入 `local-polish / section-revision / full-manuscript-pass`，具体由文本范围和用户目标决定。
- 有 `polishing` 时，按 `resume` 或局部修订处理。
- 只有 `citation_audit`、没有正文时，只能做风险解释或回到 Step 7 审计/修稿计划，不能假装已进入润色。
- 缺引用审计时，Step 8 只做润色与术语终验风险标记，不替代 Step 7 的引用审计结论。
- Passport 的全局 `route_mode` 不覆盖 Step 8 的 `revision_scope / target_genre`。
- 如果 artifact graph 中存在 `metadata_only`、`abstract_only`、`trace_status=unlinked` 或 `confidence=inferred` 的证据关系，Step 8 只能保守降级表达、标注风险或建议回到 Step 7；不得把弱证据升级为 confirmed，也不得新增外部证据补洞。
- Step 8 direct-entry 只要求有待修订正文；不要求完整 Step 4-7 链路，但必须在输出中说明证据链缺口是否影响本轮修订结论。

Step 8 不找图、不换图源、不新增图表证据；若正文含图文联合草稿，只能做图注和图文表达收口。

Step 8 若存在 `$CWD/.skill-state/ai_trace_diagnostics.json`，应把它视为运行态状态源之一：

- 其中的 `step8_decision` 记录本地分诊结论
- 其中的 `status_contract` 记录 `readiness / can_continue / blocking / warnings / recommended_next_step`
- `artifact_passport.json` 可消费该状态块，进而影响 Step 8 readiness 与推荐下一步
- 它不是上游证据产物替代品，也不替代 `diagnostic_summary.md` / `revision_ledger.json` / `润色质量报告.md` 的正式交付地位

## 加载顺序

1. `manifest.step8.yaml`
2. `static/core/output-contract.md`
3. `static/core/workflow-run-envelope.md`
4. `references/polish-modes.md`
5. `references/step8-rewrite-scope.md`
6. `references/protected-spans.md`
7. `references/equation-writing-contract.md`
8. `references/academic-ai-trace-index.md`
9. `references/ai-trace-taxonomy.md`
10. `agents/step_8_polishing.md`

## 输出要求

Step 8 默认必须明确：

- `Writing Read`：文本范围、target_genre、language、reader、evidence_state、`rewrite_scope + rewrite_level`
- 哪些片段划入 protected spans，以及相关修改是否已通过保真回读
- 保留了哪些原结构
- 哪些修改属于直接修改，哪些属于局部补写
- 哪些问题只是提醒，需回到 Step 7 处理
- `revision_ledger.json/md` 是否完整记录了问题分类、验证结果和下一步动作
