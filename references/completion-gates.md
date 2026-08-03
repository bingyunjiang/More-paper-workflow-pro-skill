# Completion Gates

> 跨步骤通用的“完成声明门槛”。本文件约束的不是脚本执行成功，而是：**没有新鲜证据，就不能宣布当前 Step 已完成。**

---

## 1. 适用范围

适用于所有会向用户输出“已完成 / 可进入下一步 / 当前产物可用”的 Step。

优先覆盖：
- Step 2 大纲
- Step 4 检索
- Step 5 下载
- Step 6 Zotero
- Step 7 写作

---

## 2. 通用规则

在任何 Step 中，完成声明必须基于已读取、已区分状态、可追溯的证据；不得把计划、候选、推断或未验证产物表述为完成。只有同时满足以下条件，才可以声明“本步完成”：

1. **核心产物存在**
   - 本步承诺的主产物已经生成，或已明确标注为 direct-entry / plan-only 的替代产物。

2. **状态已区分**
   - 成功项、风险项、失败项、待人工项必须区分，不能只给一个笼统结论。

3. **下一步输入已足够**
   - 产物已经足以支撑下一个 Step 的最小输入契约；若不足，必须显式标记缺口。

4. **没有把候选当结论**
   - 候选证据、候选 DOI、候选集合归属、候选写作论点，不能被表述成已确认事实。

5. **direct-entry 入口敏感**
   - 用户从任何 Step 直接进入时，只检查当前入口的最小产物、风险标记和下一步输入，不强制要求补齐前序 Step。
   - `artifact_passport.json` / artifact graph 中 `inferred`、`unlinked`、`conflict` 关系不得说成 `confirmed`。
   - 只有用户明确要求“全链路可追溯”时，缺失 Step 4→5→6→7 关系才作为阻塞；默认只作为 gaps/risks 呈现。

---

## 3. 各 Step 最小完成门

### Step 1：研究主题可交接

只有同时满足以下条件，才能说“研究主题已确定”：
- `研究主题.md` 的结构化 YAML、五维预审总分和灯号一致
- 主研究问题、scope、至少 3 个评价指标、可证伪条件和最小可行研究均已明确
- `evidence_calibration.status` 为 `executed` 或 `user_supplied`，且至少有 2 条可回查代表记录；若为 `unavailable`，只能称为“暂定选题/可继续聚焦版本”
- `validate_early_step_output.py step1` 已通过；否则只能称为“可继续聚焦版本”

### Step 2：大纲可用

只有同时满足以下条件，才能说“大纲可用”：
- 已输出 `章节大纲`
- 已输出 `关键词清单`
- 已输出 `章节证据需求表`
- 已生成 Step 3/6/7 handoff
- 已按核心章节检查小样本召回、术语来源和歧义；`evidence_calibration.status=unavailable` 时只能称为“可继续校准的大纲版本”
- `section_blueprints.json` 已通过 Step 2 验证，全部核心 RQ 均映射到章节和证据需求
- 输出状态为 `outline_baseline`；该状态足以进入 Step 3，不冒充正式检索后的 `evidence_validated`

### Step 3：检索方案可执行

只有同时满足以下条件，才能说“检索方案可执行”：
- `检索方案.json` 已通过 Step 3 结构验证
- `compiled_queries.json` 无 lint error，每个任务绑定 RQ、章节和证据类型
- 每个任务已完成 pilot search；`zero-result / concept_block_dropout / seed_miss / low_precision` 已在当前执行 Step 修复或明确阻塞，不强制回跑前序 Step
- pilot 已基于标题+摘要检查必需概念块覆盖；有已知相关文献时已计算 seed recall
- 每个来源已通过已查证的 endpoint-specific compiler；无 `invalid`，所有 `degraded/manual_required` 均记录丢失语义、客户端复核或当前 UI 探针要求
- `plan_mode=systematic` 时已记录数据库与平台、完整查询式、检索日期、边界及理由、去重方法、补充检索和 PRESS 审核
- `plan_state=pilot_verified` 时才能称为“已试跑可执行”；`compiled` 或 `offline_unverified` 是有效计划交付，但必须使用相应限定表述

### Step 4：检索完成

只有同时满足以下条件，才能说“检索完成”：
- 已输出去重后的结果
- 已完成评分和分级
- 已说明文献缺口或覆盖边界
- 已区分 VERIFIED / WARN / REJECT 或等价可信度状态
- 五维加权评分保存子分、理由、置信度和 uncertainty flags
- direct-entry 缺少 Step 1/2/3 产物，或出现零结果、查询漂移、过宽和证据空洞时，已在 Step 4 内重建并修复最小检索依据；不得把回跑前序 Step 作为完成门
- 若局部修复实质改变研究对象、核心 RQ 或纳入边界，已在 Step 4 内取得用户确认并保存 before/after 决策记录
- 追溯覆盖矩阵不存在 `uncovered/weak` 必需任务；分层饱和度和偏差审计已完成
- 存在 Step 2 基线时已生成 Step 2 检索对账和证据校准版；无基线或局部任务时已记录 `not_applicable`，不得因此阻塞 direct-entry
- 已按 `core / review / release-systematic` execution profile 校验必需工件；未选择的展示层不得反向阻塞 core 机器交付
- `search_run_manifest.json` 已记录输入哈希、实际输出、来源降级、checkpoint 和下一步

### Step 5：下载完成

只有同时满足以下条件，才能说“下载完成”：
- 已区分 `已下载 / 需登录 / 无法获取 / 待人工`
- 下载记录可追溯
- 未把未解析标题、未确认 DOI 或失败条目算作已完成
- `downloaded` 条目均通过 PDF verifier，manifest summary/readiness 与 checkpoint、attempt log 一致
- 未把源站无法下载的文献自动转向另一数据源尝试绕过
- direct-entry PDF 目录只能标为 `unlinked_pdf` 或 existing PDF pool，除非有下载日志/manifest 明确匹配，不得说来源链完整
- 下载来源、来源优先级和阶段顺序保持既有合同；英文/中文/CDP 阶段必须串行，禁止并发复用浏览器会话

### Step 6：Zotero 已整理完成

只有同时满足以下条件，才能说“Zotero 已整理完成”：
- 已核对集合结构
- 已核对条目导入状态
- 已核对 PDF 附件状态
- 已单列重复、缺附件、待人工确认项
- direct-entry Zotero/BibTeX/PDF 对账必须区分 `matched_attachment`、`missing_attachment`、`unlinked_pdf`、`duplicate_candidate`
- plan-only 只能声明 `plan_ready`；真实写入按 `write_partial / write_complete` 区分，且不要求 Step 4/5 产物存在
- `write_complete` 必须有当前 `plan_fingerprint` 的逐记录 success operation、合法追加日志和原子状态快照；旧计划日志、共享 PDF 冲突或缺失 record operation 不得放行

### Step 7：章节写完

只有同时满足以下条件，才能说“章节写完”：
- 已说明证据基础来自哪里
- 已说明引用风险状态
- 已区分“正文完成”和“证据仍弱但先交草稿”
- `metadata_only`、`abstract_only`、`trace_status=unlinked` 或 `confidence=inferred` 的证据关系必须进入风险说明，不能支撑强 claim
- `draft_ready` 只要求当前写作范围的草稿、执行边界和风险说明；不得因缺少 Step 1-6、证据矩阵、引用审计或 reviewer scorecard 把入口标为 blocked
- `evidence_closed / ready_for_step8` 才要求 `reviewer_scorecard.json` 通过锚定量表：技术可靠性/证据充分性不低于 4，其余维度不低于 3，且无 CRITICAL 未关闭项
- 对外区分 `draft_ready / evidence_closed / ready_for_step8`；后两者要求 claim audit 和 reviewer scorecard 的 `draft_sha256` 与当前稿件一致
- 图表自动匹配不得插入零关键词或低来源质量候选；`ready_for_step8` 的图表解析报告不得有未解决项
- 生成新图时必须记录 `figure_backend`；只插入已有资产用 `not_applicable`，不得伪装成已执行绘图
- `figure_backend=reproduction` 时，只有 `run_report.status=ok`、manifest 状态合格且 bundle `verify.py` 通过，才能声明复现完成
- `semantic_near_pass` 必须公开偏差；`render_only / not_strict / failed` 不得作为复现完成态
- 图片曲线数字化只有在规格确认哈希有效、`review-decisions.json` 完整、`observations.csv` 与正式 `data.csv` 血缘一致、VisualSpec 绑定同一 `data.csv` 哈希时，才可标记 `extraction_status=formal_data_ready / review_status=complete`；候选提取或重绘成功均不能提升这两个状态
- 图形复现状态不得替代 claim evidence audit；复现通过不能自动证明正文 claim 获得支持
- 所有分层状态均不得残留 `missing_equation`、纯文本数学表达或裸 LaTeX/矩阵源码；`ready_for_step8` 的 `equation_audit.json` 与 `equation_register.json` 必须绑定当前稿件哈希并通过 `references/equation-writing-contract.md`

### Step 8：保守修订完成

只有同时满足以下条件，才能说“本轮 Step 8 修订完成”：
- 已说明本轮只处理既有正文，不新增未经确认的证据
- 已保留或标注 artifact graph 中的证据链缺口
- 弱证据、未链接证据或缺引用审计只被降级表达/风险提示/回退建议处理，未被升级为 confirmed
- `论文润色稿.md` 已存在，`polish_fidelity_audit` 无硬失败；纯诊断状态 `ready_to_polish` 不得声明修订完成
- `quick-polish` 只按局部润色稿、修改说明、protected spans 和风险提醒验收；`audited-polish` 才要求完整 ledger、对照表、术语报告、质量报告和请求范围内导出文件
- 自动化使用 `run_step8_ai_trace.py --strict` 时，readiness blocked 必须返回非零；默认诊断模式可返回 0 以保留阻塞报告
- 保真审计已覆盖标题、段落论证单元、claim/限定边界和待补证据标记；若提供 Step 7 结构化审计，其未关闭或过期风险已阻止定稿
- 公式签名、编号、上下标和矩阵结构在润色前后保持一致；DOCX 公式为原生公式对象，且无纯文本数学或 LaTeX 源码残留

---

## 4. 禁止表述

以下表述在没有满足 Completion Gate 时不得使用：
- `已完成`
- `可以直接进入下一步`
- `已经没问题了`
- `Zotero 已整理好`
- `这章已经写完`
- 任何等价的隐含成功表达

如果证据不足，改用：
- `当前已形成可继续版本`
- `主产物已生成，但仍有以下缺口`
- `可进入下一步，但需带风险标记`
- `当前入口可继续版本；全链路仍有以下 gaps/risks`

---

## 5. 与 Quality Gates 的关系

- `Quality Gates` 是 Step 内部检查清单。
- `Completion Gate` 是对用户“能不能宣布完成”的对外门槛。

质量门可以很多；完成门必须短、明确、可执行。
