# 图表与写作接口

本文件只定义 Step 7 中文字与图表任务的接口，不替代具体绘图规范。

## 目标

明确一张图在写作中承担什么功能，并把“写文 + 插图”视作同一条图文证据链。

## 图表接口字段

- figure_id
- table_id
- panel_id
- purpose
- related_section
- claim_supported
- claim_id
- claim_text
- claim_strength
- required_data
- status
- figure_source
- figure_asset_mode
- figure_intent
- evidence_basis
- caption_anchor
- text_anchor
- evidence_modality
- support_type
- support_status
- figure_table_panel_binding
- downgrade_required
- replacement_hint
- figure_risk_note
- risk_flags
- generation_backend
- visualspec_path
- reproduction_bundle
- manifest_path
- reproduction_status
- qa_profile
- verification_status
- figure_asset_action
- figure_transform_authorization
- extraction_project_path
- extraction_report_path
- extraction_status
- value_delivery_authorized

## 图-表-panel 绑定矩阵

所有图表相关 claim 必须生成 `figure_table_panel_binding`，而不是只写“如图所示”。最小记录：

```json
{
  "claim_id": "C-001",
  "claim_text": "",
  "claim_strength": "background|trend|parameter|numeric_comparison|mechanism|novelty",
  "figure_id": "",
  "table_id": "",
  "panel_id": "",
  "caption_anchor": "",
  "text_anchor": "",
  "evidence_modality": "EBSD|TEM|SEM|XRD|flow_curve|mechanical_test|waveform|efficiency_curve|loss_breakdown|thermal_map|grid_metric|optimization_result|hardware_prototype|HIL|field_data|standard|simulation|user_data",
  "support_type": "direct|partial|contextual|not_supported",
  "support_status": "support|weak-support|not-supported|cannot-judge",
  "downgrade_required": false,
  "risk_flags": []
}
```

材料/机械基础 `evidence_modality` 子集保持为：`EBSD|TEM|SEM|XRD|flow_curve|mechanical_test|simulation|user_data`。电力电子/能源系统任务可在此基础上扩展 `waveform / efficiency_curve / loss_breakdown / thermal_map / grid_metric / optimization_result / hardware_prototype / HIL / field_data / standard`。

若 `claim_strength=mechanism / numeric_comparison / parameter`，但缺少图/表/panel、图注或正文锚点，应标记 `downgrade_required=true`，并把正文改成保守表达或写入 `evidence_gap_list.md`。

## 最小图文单元

- 正文引出句
- 图或表
- 图后解释句

三者必须回答同一条 claim。正文引出句提出要观察的问题，图或表提供可见证据，图后解释句只解释图中能支撑的范围，不得补写图中看不出来的机制、数值或统计结论。

## 常见用途

- 背景示意
- 方法流程
- 实验结果
- 对比分析
- 案例展示

## 边界

- 图表任务可以在 Step 7 发起
- `auto_insert_figures=true` 时，优先要求条目下存在 `LLM-for-Zotero-MinerU-cache-*.zip` 或等价图文资产包
- 用户要求基于 Zotero 集合撰写完整论文、章节或重写论文，且 Zotero child attachments / 本地证据包中存在 MinerU ZIP、图片目录或已有 `figure_index.json` 时，默认进入“写文 + 插图”的图文联合路径；除非用户明确要求纯文字稿，不得静默省略插图
- 用户要求撰写“期刊论文 / 完整论文 / 章节论文 / 重写论文”时，默认交付物应当图文并茂；Markdown 不是纯文字豁免。最小图文交付必须包含：已插入的项目内 `figures/` 相对路径图片，或可解析图位标记 + `figure_evidence_report.md/json`，或带 `figure_mode=skip` 原因的 `draft_risk_summary.md`
- `figure_asset_check` 必须覆盖 Zotero child attachments、MinerU ZIP、已有 `figure_index.json`、本地图片目录和可读 PDF；没有执行该检查时，不得把无图初稿标记为完成
- 使用 `scripts/build_figure_asset_check.py` 生成 `figure_asset_check.json/md`；只有脚本记录的 `figure_asset_action / figure_backend / figure_transform_authorization` 才能进入后续自动验证
- 纯文字降级只允许两种情况：用户明确要求纯文字，或 `figure_asset_check` 后确认没有可用图片/候选图。两种情况都必须记录 `figure_mode=skip`、已检查资产范围和后续补图动作
- Markdown 初稿也是图文稿承载层：已确认图片应使用项目内 `figures/` 相对路径插入；尚未确认的图片应保留可解析图位和 `figure_evidence_report` 缺口，而不是删除图位
- 没有 MinerU ZIP 但本地 PDF 可读时，允许通过 PyMuPDF 直接抽取 `pdf_direct` 候选图；该候选必须标记为低置信、无 caption、待人工确认，并记录 `figure_evidence_status=pdf_direct_candidate_pending_manual_check`
- 没有 MinerU ZIP 且 PDF 不可读或无候选图时，才只保留正文图位占位，不自动选图
- 任何 `figure_mode=skip` 都必须记录跳过原因、已检查资产范围和后续补图动作
- 没有 figure/table/panel 绑定时，不得自动写“如图 X 所示”“图中可见”“由图证明”
- 图位描述与候选图关键词得分为 0，或候选图缺少最低来源质量时，不得自动插入；必须保留 `manual_confirmation_required` 图位，并写入 `figure_resolution_report.json`
- `ready_for_step8` 要求 `figure_resolution_report.json.output_sha256` 与当前稿件一致，且 `unresolved_count=0`；`figure_mode=skip` 不适用此门
- 具体图形设计和导出细节可继续由现有图表参考处理
- `figure_mode=skip` 时不运行绘图；只插入已有资产时使用 `generation_backend=not_applicable`
- 论文 PDF/MinerU/本地原图默认直接插入：`figure_asset_action=insert_original`、`generation_backend=not_applicable`、`figure_transform_authorization=not_required`
- 用户明确要求从可信数据生成新图时使用 `generation_backend=quick`
- 用户明确要求论文原图/截图重绘、数字化、严格 QA 或可复现交付时使用 `generation_backend=reproduction`，并记录 `figure_transform_authorization=explicit_user_request`
- 原图插入完成后应提醒用户本 skill 具有图表重绘、曲线数字化、可编辑 SVG/PDF 和严格 QA 能力；提醒只出现一次且不构成重绘授权
- 原图解析使用 `resolve_figure_refs.py` 时，必须保留源 ZIP、ZIP 内部路径、源图哈希、物化文件哈希和稿件相对路径；只复制最终选中的图片
- `reproduction` 模式必须记录 VisualSpec、bundle、manifest、QA profile 和 `verify.py` 结果；详细协议见 `scientific-figure-reproduction.md`
- 图形复现通过只证明产物完整性，不能自动把 `support_status` 升级为 `support`
- 数字化值进入正文数值比较、参数或趋势 claim 前，必须绑定
  `figure_project.result.json` 与 `extraction_report.json`；若
  `value_delivery_authorized=false`，只能保留图位、缺口或保守定性描述。
- 官方源数据验证不得覆盖图片提取 CSV；两者必须以独立工件进入
  `figure_evidence_report`。

## 可复现图表报告扩展

```json
{
  "generation_backend": "quick|reproduction|not_applicable",
  "visualspec_path": "visualspec.json",
  "reproduction_bundle": "figures/fig_1_bundle",
  "manifest_path": "figures/fig_1_bundle/reproduction_manifest.json",
  "reproduction_status": "semantic_strict_pass|semantic_validated_pass|semantic_near_pass|render_only|not_strict|failed",
  "qa_profile": "semantic|visual|trace",
  "verification_status": "pass|failed|not_run",
  "figure_asset_action": "insert_original|generate_new|redraw|digitize",
  "figure_transform_authorization": "not_required|explicit_user_request",
  "extraction_project_path": "figures/fig_1/figure_project.result.json",
  "extraction_report_path": "figures/fig_1/extraction_report.json",
  "extraction_status": "needs_review|authorized_candidate|partial_visible|not_extracted|failed",
  "value_delivery_authorized": false
}
```

`semantic_near_pass` 必须带视觉偏差；`render_only/not_strict/failed` 不得声明复现完成。原图能否支撑正文 claim 继续由图注、正文锚点、panel 绑定和来源证据共同决定。
