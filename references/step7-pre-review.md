# Step 7 Pre-Review, Revision and Rereview

预审是审稿人视角的缺陷扫描，不替代引用审计，也不得冒充真实审稿意见。

## 读取条件

当 `operation=pre-review`，或用户要求审稿人视角、投稿前自查、修稿、rebuttal 预演或复评时加载本文件。

同时加载：

- `references/reviewer-protocol.md`
- `references/scientific-writing-quality-rubric.md`
- `references/section-quality-gates.md`
- `references/reviewer-defect-taxonomy.md`

方法细节保留在 references，不硬编码某种写作风格。质量 rubric 只检查章节功能、主谓动作、旧新信息、段落任务、图表先行和 phrasebank 风险；不改变 claim 强度、不替代引用审计，也不能把候选证据包装成强证据。

## 修稿教练

外部审稿意见使用稳定编号 `E.1 / E.2` 与 `R1.1 / R1.2 / R2.1`，每条记录：`comment_id / source_role / original_comment / comment_type / readiness_state / missing_author_input / rollback_target`。

不得编造 reviewer 身份，不得冒充已完成修改。输出：

- `revision_roadmap.md`
- `response_letter_skeleton.md`
- `evidence_gap_list.md`
- `claim_delta_report.md`

问题处理必须形成“问题识别、修订动作、证据状态、验证结果、下一步动作”的闭环。

## 生命周期字段

所有 revision artifact 共用：`issue_id / source / category / severity / evidence_basis / allowed_action / proposed_revision / verification / final_status / next_action`。

状态至少包括 `open / awaiting_author / blocked_by_evidence / revised / verified / closed / new_issue`。只有 verification 通过才能关闭问题。

## 复评

修订后生成 `rereview_report.md`，复用稳定 issue id，区分已关闭、仍开放、证据不足和 `new_issue`。新证据需求回到 Step 7 citation audit 或 Step 4/5/6，不在 Step 8 静默补文献。

## 章节门与缺陷分类

运行 `scripts/audit_scientific_writing_quality.py` 和按领域需要运行 `scripts/audit_engineering_claims.py`，输出 `scientific_writing_quality_audit.json/md`、`engineering_claim_audit.json/md` 和可选 `reviewer_defect_report.md`。

摘要、引言、讨论、结论分别检查章节功能；审稿缺陷至少覆盖 novelty/positioning、evidence/citation、method/reproducibility、result/figure、discussion/claim 和领域专项问题。任何 rollback target 必须进入 revision roadmap 或 evidence gap，不能只靠润色关闭。
