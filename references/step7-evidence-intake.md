# Step 7 Evidence Intake

本合同定义 Step 7 的多入口证据读取、证据等级和 direct-entry 边界。

## 入口模式

- `zotero_full`: Zotero 条目、PDF、notes、annotations 和 fulltext。
- `zotero_mineru`: 在 `zotero_full` 之外读取 `LLM-for-Zotero-MinerU-cache-*.zip` 的 `manifest.json`、`full.md` 与 `images/`。
- `evidence_pack`: 本地 PDF、BibTeX/CSL JSON、报告、数据、标准、图片或用户材料，登记到 `evidence_pack.json`。
- `deep_read_refine`: 对当前章节的 1-5 篇核心文献生成 `deep_read_cards.json/md`。
- `draft_only`: 只有草稿或写作需求时，只生成结构稿、待补引用和风险清单。
- `mixed`: 以 claim 为中心合并多来源，不按文件来源堆材料。

Zotero/MinerU 是推荐资产层，不是 Step 7 的硬依赖。场景只决定读取路径，证据等级决定能写多强。

## PDF-only 正式入口

PDF-only evidence_pack 是 Step 7 的正式入口，不是降级补丁。最小输入是 PDF 文件夹、写作目标，以及可选的大纲、草稿或目标期刊要求；不要求补跑其他 Step。

可读 PDF 优先生成或复用 `prepared_pdf_artifacts.json`、clean Markdown、chunks 和 extraction report。扫描件、OCR 差、公式/表格密集或页码锚点缺失的 PDF 保持候选状态。

全文读取层级为：`zotero_mineru > zotero_fulltext > zotero_note/annotation > PyMuPDF/pdfplumber > abstract_only > metadata_only`。图文读取层级为：`MinerU ZIP / Zotero 图文资产 > 主抽图 > preview fallback`。

## 证据等级

- `confirmed`: 有 PDF 原文、页码/段落、图表 panel、标注、笔记、标准或用户数据等可核验锚点。
- `candidate`: 检索命中、RAG 候选、摘要片段、metadata-only、unlinked PDF 或模型召回，只用于定位与风险提示。
- `missing`: 当前 claim 无可核验来源，进入 `evidence_gap_list`。

`metadata_only / abstract_only / inferred / unlinked` 不能支撑强参数、定量比较、强机理或创新 claim。`negative_or_conflicting_evidence` 必须保留，不得静默删除。

## RAG 候选边界

`retrieval_index_manifest.json` 与 `retrieval_candidates.json` 是候选定位加速层，不是正文证据。必要时可以读取候选文件回查来源，但不得直接升级为 `VERIFIED` / `VERIFIED_LOCAL`，也不得扩大原始 evidence boundary。

`deep_read_refine` 至少记录：`claim_summary / method_summary / experiment_summary / mechanism_hints / usable_for / not_usable_for / reading_depth`。它不能提高原始 reading depth；`mechanism_hints` 只进入机理候选链。

## 最小输出

- `evidence_basis`
- `evidence_entry_mode`
- `citation_risk_summary`
- `evidence_gap_list`
- `negative_or_conflicting_evidence`
- `readiness: blocked|partial|complete`

Artifact Passport 只提供材料图谱和 readiness，不覆盖 Step 7 的 mode、operation、target_genre 或证据等级。
