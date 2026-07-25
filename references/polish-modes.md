# Step 8 润色模式

## output_mode

### `quick-polish`

局部低风险语言润色。只交付实际润色文本、3-5 条修改说明、protected spans 边界和必要的风险提醒，不声称完成全文审计。

### `audited-polish`

章节或全文的受约束修订。要求 diagnostics、revision ledger、修改对照、术语与质量报告，并在请求范围内执行导出和保真验证。

## revision_scope

### `local-polish`

只做局部语言优化和有限结构修订。

### `section-revision`

在单章或单节内做较完整的结构与节奏修订。

### `full-manuscript-pass`

对全稿做一轮保守精修，但不重构整篇论证。

## 默认原则

- Step 8 默认保守
- 大幅重写应回到 Step 7
- 引用安全问题只提示，不替代完整审计
- `rewrite_scope=in-place|bounded|structural` 控制能否调整结构；默认 `bounded`
- `rewrite_level=minimal|standard|aggressive` 控制改写力度；默认 `standard`
- quick 和 audited 使用不同完成门，不能用 audited 的派生工件要求阻塞局部 quick-polish
