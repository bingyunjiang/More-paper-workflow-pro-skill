# Step 7: 论文写作轻量总合同

> Step 7 把 Zotero、PDF、BibTeX、证据包、已有草稿和图表资产转成可审计正文。它支持 direct-entry，但不能跳过证据边界、引用审计、公式门、图表授权和分层完成状态。

## 适用任务

- 撰写全文、指定章节、综述、摘要，或续写已有草稿。
- 基于审稿意见做 `revision-only`，生成修稿路线、回应骨架和证据缺口。
- 执行 claim/citation 审计、图文联合、机理写作、科研图表或投稿前预审。
- `full-document / chapter-only / continue-existing / abstract-only / review-only / revision-only` 均可直接进入。

不适用于单纯检索、下载、Zotero 写入或成稿级全文润色；这些任务分别路由到 Step 4-6 或 Step 8。

## 输入要求

**Direct-entry input contract：**

- 最小输入是“写作目标或现有文本”加下列任一证据入口：Zotero、PDF、BibTeX/CSL JSON、MinerU ZIP、`evidence_pack`、用户粘贴材料或已有草稿。
- 不要求补跑 Step 1-6，也不要求安装 Zotero；但缺少全文、锚点或可核验数据时，只能形成低风险草稿、候选表述和 `evidence_gap_list`。
- 已有草稿必须同时给出本轮范围；`chapter-only / continue-existing / revision-only` 不得扩写到未授权章节。
- Direct-entry 是快速入口，不是证据升级通道。`metadata_only / abstract_only / candidate / inferred / unlinked` 不得冒充 confirmed evidence。

启动时确认以下轴：

- `mode`: `full-document|chapter-only|continue-existing|abstract-only|review-only|revision-only`
- `operation`: `write|citation-audit|figure|pre-review`
- `target_genre`: `thesis|journal|review|report|proposal|conference|course-paper`
- `figure_mode`: `auto_insert|post_write|skip`
- `figure_backend`: `auto|quick|diagram|reproduction|not_applicable`
- `figure_asset_action`: `insert_original|generate_new|redraw|digitize`

若输入仍不稳定，先生成 `step7_execution_card.md`、最小证据映射或 `argument_plan`，不要直接生成完整正文。

## 标准输出

正式输出至少说明：

- `mode / operation / target_genre`
- `figure_mode / figure_backend / figure_asset_action`
- `evidence_basis / citation_risk_summary / evidence_gap_list`
- `equation_audit_status / unresolved_equation_count / needs_author_check`
- `completion_state / readiness / can_continue / recommended_next_step`

按任务生成的稳定工件包括：

- `step7_execution_card.md`
- `writing_blueprints.json/md` 与 `argument_plan.json/md`
- 章节/全文草稿、`claim_evidence_audit.json`、`citation_audit.md`
- `figure_asset_check.json/md`、`figure_index.json/md`、`figure_evidence_report.json/md`
- 机理任务的 `mechanism_trigger_decision`、`mechanism_cards`、`mechanism_argument_plan`、`mechanism_claim_audit`
- 修稿任务的 `revision_roadmap.md`、`response_letter_skeleton.md`、`evidence_gap_list.md`、`rereview_report.md`

## 执行流程

1. 按 `agents/step_7_entry.md` 和 `manifest.step7.yaml` 识别 mode、operation、领域、目标体裁与图表后端。
2. 读取 Artifact Passport 或最小证据入口，记录实际 `reading_depth`、证据等级、冲突证据和缺口。
3. 生成 `writing_blueprints` 和 `argument_plan`，确认 claim、evidence、boundary、段落任务和禁止写入项。
4. 机理类任务先完成 `mechanism_trigger_decision`；进入机理分析时，必须先完成三件机理工件。
5. 正文按章节功能逐段绑定 claim、引用、图表、公式与证据锚点；证据不足时降强度或保留占位。
6. 按 operation 运行引用审计、图表工作流、预审或修稿复评。
7. 运行 `scripts/validate_step7_output.py`，只在相应完成门通过后声明状态。

详细规则必须由 manifest 一步可达：

- 证据入口：`references/step7-evidence-intake.md`
- 正文与蓝图：`references/step7-drafting-contract.md`
- 引用审计：`references/step7-citation-audit.md`
- 图文联合：`references/step7-figure-workflow.md`
- 预审、修稿和复评：`references/step7-pre-review.md`
- 完成验收：`references/step7-completion-validation.md`
- 机理分析：`references/mechanism-analysis-writing-contract.md`
- 公式与 DOCX/OMML：`references/equation-writing-contract.md`

## 质量门槛

- 正文前必须存在当前范围的执行卡、证据入口判断和 argument plan；claim/evidence/boundary 未确认时停止完整正文生成。
- 强参数、数值比较、机理和创新 claim 必须满足对应证据等级；候选检索、RAG、摘要和元数据不能自动升级。
- 机理类任务缺少 `mechanism_trigger_decision`，或进入机理分析后缺少任一机理工件，均不得通过 `evidence_closed`。
- 图文任务必须满足原图已插入、可解析图位加证据报告、或带原因的 `figure_mode=skip` 三者之一。
- 发现论文原图不等于获得重绘授权；只有明确用户请求才能进入 redraw、digitize 或 reproduction。
- 公式必须通过 `equation_guard.py`；DOCX 交付还要回读 OMML/原生公式对象。
- Step 7 只做最小术语统一和轻量可读性整理，不替代 Step 8 的成稿级保守精修。

## CHECKPOINT W - CP-CITATION-WARN

当弱证据、摘要级证据、无 PDF 条目或不支撑引用将用于关键 claim 时，状态设为 `blocked` 并请求用户选择：删除/替换、降为背景、回退补证据、或逐条人工审查。

Checkpoint 是当前 Step 的输入与风险确认协议，不是线性流程锁。背景性候选记录、待补查清单和低风险描述整理不触发本门；`REJECT` 证据不得进入关键 claim。

## 收尾检查

- 当前草稿、argument plan、引用风险、图表状态和公式状态均绑定本轮范围。
- `draft_ready` 只表示已有可读草稿；`evidence_closed` 表示当前范围的强 claim 和工件链已闭合；`ready_for_step8` 才表示可以进入成稿级精修。
- `can_continue=true` 不等于当前 Step 已完整完成。
- 所有未解决风险进入 run envelope 的 `blocking / warnings / recommended_next_step`。
- 当前范围完成后再询问是否导出 DOCX，不在每个写作增量后自动导出。

## 故障排除

- 写不出来：先判定是证据不足、章节功能不清还是 argument plan 未确认。
- 引用支撑弱：回到 citation audit 或 Step 4/5/6 的最小补证据闭环，不让模型硬写。
- 机理链不足：保留竞争机制和反例风险，降级 claim，不用常识补齐。
- 图表资产不足：按 MinerU manifest、full.md、images、PDF direct 顺序降级，仍不足则保留可解析图位或显式 skip。
- 体裁或术语不稳：修正 style profile、writing axes 或术语状态后再继续。
- 验证失败：按 `references/failure-triage.md` 修复对应工件，不绕过 `scripts/validate_step7_output.py`。
