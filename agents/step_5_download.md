# Step 5: 统一批量下载 (Unified Download Router)

> ⚠️ **前置提醒：**
> 1. 进入真实下载前，如命中机构登录场景，agent 必须先提示用户在**同一个 CDP 浏览器**里完成机构登录，再继续执行下载。
> 2. 如果宿主无法读取 `input()`，不得把下载脚本丢到后台硬跑；必须保留 `paper-temp/login_checkpoint.json`，并把该状态视为待用户确认登录，不是用户主动 skip。
> 3. 用户完成机构登录后，恢复路径固定为 `python3 scripts/unified_download_router.py --resume-login-checkpoint paper-temp/login_checkpoint.json --output paper-temp/ --confirmed`。
> 4. **未先问用户登录就直接启动真实下载是错误执行方式，不是 skill 缺陷。**
>
> **默认串行可靠 / 英文优先串行可靠：** 英文默认顺序为 `2021 年及以前：Sci-Hub → OA fast → IEEE CDP / Generic CDP grouped by publisher`，`2022 年及以后/年份未知：OA fast → IEEE CDP / Generic CDP grouped by publisher`。拿到 Step 5 下载清单后，英文 DOI 只做 `oa_candidate / no_oa_hint / unknown` 提示分层，真实 OA 仍必须由 OA fast 验证；中文条目先稳定排序为 CNKI → 万方，再在英文 DOI 路径完成或被明确跳过后执行，避免共享浏览器状态互相干扰。ScienceDirect / Elsevier 归入 Generic CDP；IEEE 默认走独立 `download_via_ieee.py`，Generic fallback 只保留为内部兜底。

---

## 启动前读取 (Pre-read Checklist)

执行本步骤前，必须确认以下文件已加载：

- [ ] `agents/step_4_search_score.md` — 检索文献表（含 DOI 和 Tier 分级；直达下载模式下可缺失）
- [ ] `config/publishers.toml` — 出版社下载策略配置
- [ ] `references/publisher-access-matrix.md` — 各出版商下载可行性对照表
- [ ] `.skill-state/error_log.md` — 已知下载错误及修复规则
- [ ] `.skill-state/decision_log.md` — 下载策略相关决策

---

## 适用任务 (Applicable Tasks)

- 从检索文献表批量下载 PDF
- 用户直接提供 DOI 列表、论文标题列表、BibTeX、URL 或混合参考文献时，先归一化为下载清单再下载
- 按 DOI 前缀自动路由到最优下载策略
- 单篇测试下载
- 会话状态检查
- 下载记录追踪

---

## 不适用任务 (Non-applicable Tasks)

- 文献检索 → 路由到 `agents/step_4_search_score.md`
- Zotero 文库管理 → 路由到 `agents/step_6_zotero.md`
- 浏览器中人工逐篇点击下载 → 使用各专用脚本或用户手动处理

## When to use this Step

- 用户已经有 DOI、标题、URL、BibTeX、参考文献段落，或 Step 4 的检索结果，需要把它们变成真实 PDF。
- 用户明确在问下载、补下、重试、恢复登录中断，或要从 publisher/source 路由到实际文件落地。
- 用户不想回跑 Step 1-4，只要求把当前输入归一化为可下载清单并执行下载。

## When NOT to use this Step

- 任务只是检索、筛选、打分，去 Step 4。
- 任务只是 Zotero 入库、条目整理或附件挂回，去 Step 6。
- 任务只是写作、证据整合或引用审计，去 Step 7。
- 任务只是成稿修订或表达收口，去 Step 8。

---

## 输入要求 (Input Requirements)

| 输入 | 来源 | 格式 | 必选 |
|------|------|------|:--:|
| 检索文献表 | Step 4 | .md | 批量模式必选 |
| workflow search results | Step 4 / 用户提供 | workflow JSON | 可直接作为下载入口 |
| DOI/标题/URL/参考文献列表 | 用户直接提供 | pasted text / .txt / .md / .bib | 直达下载模式必选其一 |
| direct_download_manifest | Step 5 生成 / 用户提供 | .md/.json | 标题/混合输入时必选 |
| 中文论文元数据 | Step 4 或 Step 5 生成 | 中文论文元数据.json | 中文下载必选 |
| CDP Chrome 浏览器 | 用户启动 | 端口 9223 | ✅ |

> **输入约束：** `中文论文元数据.json` 是 Step 4/Step 5 产出的**下载清单**，不是审计报告。
> - 当条目 `status=ready` 时，表示该条目已满足 Step 5 下载前提，可直接进入下载流程。
> - Step 5 **禁止** 因 `zotero_item_key` 去查询 Zotero 附件状态、元数据完整性或集合结构。
> - `zotero_item_key` 不是 Step 5 的前置检查条件；若存在，只可作为下载记录关联字段或供后续步骤使用。
> - Zotero 附件挂回、条目修补、集合调整属于 Step 6 职责，Step 5 不得因为看到 `zotero_item_key` 而跳转到 Zotero 审计流程。

---

## 标准输出 (Standard Outputs)

| 输出 | 格式 | 说明 |
|------|------|------|
| 下载的 PDF | .pdf | 保存到 paper-temp/ |
| 下载记录 | paper-temp/download_log.md | 逐篇追踪状态 |
| `download_manifest.json` | JSON | 下载机器主状态：逐条路由、结果、readiness、checkpoint 和 run_id |
| `download_attempts.jsonl` | JSONL | append-only 尝试历史；相同 attempt_id 幂等，新 run_id 保留新一轮事件 |
| `pdf-附件池索引.json` | JSON | 已有/新下载 PDF、来源、匹配状态和完整路径，供 Step 6/7 继续消费 |
| 英文登录恢复点 | paper-temp/login_checkpoint.json | 英文 CDP 登录未完成或宿主无法继续交互时生成，只包含待登录 DOI |
| direct_download_manifest.md/json | .md/.json | 直达下载模式的临时归一化清单 |
| unresolved_download_items.md | .md | 标题无法唯一解析、缺少 URL 或需要人工确认的条目 |

## Artifact Passport / Direct-entry Graph

Step 5 可从 DOI 列表、BibTeX、检索表、失败清单、出版社 URL、中文 article URL 或已有 PDF 目录直接进入；不得因为缺少 Step 4 历史就要求用户回跑前序步骤。

- 进入 Step 5 前后可用 `scripts/artifact_passport.py --entry-step step5 --add <path>` 登记输入材料。
- DOI/BibTeX/检索结果应登记为 `download_item` 或 `search_record` 节点；已有 PDF/PDF 目录登记为 `pdf_attachment` 节点。
- 只有下载 manifest、日志或明确文件匹配能证明来源时，`downloaded_as` 关系才能视为 `confirmed`；仅因同目录共存推断的关系只能是 `inferred`。
- PDF 直入但无法确认来源时必须标记 `unlinked_pdf` / `source_unlinked`，可继续做清单核对或补下载，但不得宣称下载来源链完整。
- 登录中断、`pending_user_login`、`failed_dois.json` 和 checkpoint 状态应保留为下载 graph 风险，不得覆盖为成功下载。

**崩溃恢复与幂等写入合同：**

- `download_manifest.json`、`pdf-附件池索引.json`、登录 checkpoint 和 reconcile 报告使用同目录临时文件、flush/fsync 和原子替换；进程中断时不得暴露半截 JSON。
- `download_attempts.jsonl` 追加后必须 flush/fsync；相同 `attempt_id` 不重复追加，新 `run_id` 仍完整保留新一轮历史。
- 登录/captcha checkpoint 全部完成后保留文件，但将 `status` 原子更新为 `resolved`，并记录 `resolved_at / resolved_items`；有剩余项时继续保持 pending。
- resume/reconcile 后重新运行 `python3 scripts/validate_step5_output.py <output-dir>`；重复 identifier、损坏 checkpoint、checkpoint/manifest 状态冲突不得静默忽略。

## Step 5 execution discipline

**已锁定的下载执行合同：** 下载来源、来源优先级和阶段顺序保持本版本既有定义，不由全局优化重新排序。英文 DOI、English CDP、CNKI、万方及其恢复流程继续串行运行；`--parallel-phase1` 仍为 deprecated/ignored。不得同时运行多个下载队列，也不得让不同队列并发复用 CDP。若需要隔离浏览器状态，只能在串行阶段边界切换独立端口/profile，并在前一阶段完全停止或 checkpoint 挂起后继续。

- `交付定义`：本步交付的是 PDF、下载日志、manifest、失败分流和恢复点；不是 Zotero 入库、引用审计或全文证据判定。
- `输入依赖`：真实下载至少需要 DOI、article_url、source_id、publisher URL 或已确认的 manifest 条目之一；标题只能先解析，不得直接下载。
- `可委派边界`：脚本可执行解析、路由、probe、下载和日志；用户仍负责机构登录、验证码、订阅权限和是否改走其他来源。
- `最小实验优先`：未知出版商、混合来源或高风险批次先做 dry-run、单篇测试或小批次 probe，再扩大到全量下载。
- `快速通道不跳质量门`：直达下载可以跳过 Step 4 评分，但不能跳过清单归一化、登录门控、PDF verifier、失败原因记录和 checkpoint。

---

## 执行流程 (Execution Flow)

### 5.1. 直达下载入口判定 🆕

当用户没有经过 Step 1-4，直接发送 DOI、论文标题、URL、BibTeX 或参考文献列表时，不要求用户补跑完整检索流程。Agent 必须先把输入归一化为可下载清单，再进入原有下载路由。

> **Step 5 / Step 6 分流强约束：**
> - `.bib` / BibTeX 在 Step 5 中首先视为**下载输入载体**，不是 Zotero 写入指令。
> - 当用户表达的是“下载 / 下 PDF / 批量下载 / 下载这些 BibTeX 条目”时，必须停留在 Step 5，先抽 DOI / URL / source 并执行下载。
> - 只有用户明确表达“导入 Zotero / 建条目 / 入库 / 建集合 / 关联附件”时，才切换到 Step 6。
> - 不得因为看见 `.bib` 文件就自动推断为“往 Zotero 建条目”。

| 输入类型 | 识别方式 | 处理路径 | 是否需要用户确认 |
|----------|----------|----------|------------------|
| DOI 列表 | `10.xxxx/...`、`doi:`、`https://doi.org/...` | 归一化 DOI → `--papers` 或 DOI 文件 → 英文路由 | 不需要，除非 DOI 异常 |
| 英文论文标题 | 无 DOI，英文标题/参考文献文本 | 先查 DOI / OA URL / 出版社页 → 生成 manifest | 多候选或低置信度时需要 |
| 中文论文标题 | 中文题名、无 DOI | 先查 CNKI/万方 article_url/source_id → 生成 `中文论文元数据.json` | 多候选或缺链接时需要 |
| BibTeX / RIS / 参考文献段落 | 含 title/doi/url/year/journal | 优先抽 DOI；无 DOI 的标题进入解析队列 | 解析不唯一时需要 |
| 出版社 URL / CNKI / 万方 URL | URL 域名可识别 | 英文 URL 尝试抽 DOI；中文 URL 直接生成中文元数据 | 通常不需要 |

**直达模式原则：**

1. DOI 是最高优先级下载键；能抽到 DOI 时，不再要求用户提供 Step 4 的检索文献表。
2. 标题不能直接进入下载器，必须先解析为 DOI、OA PDF URL、出版社 article URL，或中文 `article_url`。
3. 不得为了推进下载猜测 DOI。标题匹配到多个候选、年份/作者冲突或置信度不足时，写入 `unresolved_download_items.md` 并请用户确认。
4. 中文论文以 `source` 字段路由，不以 `doi` 字段路由。
   - **路由键是 `source=cnki|wanfang`，不是 DOI。** 即使 CNKI/万方论文注册了真实 DOI，也只能走中文 `article_url` / `source_id` → `chinese_cdp` 路径，不得进入英文 DOI 路由器，不得尝试 OA fast / Sci-Hub / Generic CDP。
   - `cnki.xxx` / `wanfang.xxx` 合成标识符自然更不进入英文 DOI 路由。
   - 中文论文上的 DOI 在 Step 5 中仅作为元数据字段保留，用于引用/关联，不作为下载通道选择依据。
5. 直达模式只做“用户指定文献下载”，不生成 Step 4 的评分、Tier、饱和度或 PRISMA 报告。
6. 直达模式只需要确认下载清单和登录状态；不得要求用户补跑 Step 1-4。
7. 所有入口先归一化为 `DownloadManifestItem` 语义：`item_id`、`title`、`doi`、`source`、`source_id`、`article_url`、`route_key`、`status`、`confidence`。旧 `direct_download_manifest.md/json` 可继续使用，但内部语义以 workflow contract 为准。
8. Step 4 workflow JSON 若包含 `oa_status`、`oa_source`、`oa_pdf_url`、`oa_landing_url`、`oa_license`、`oa_checked_at`，Step 5 只能把它们视为 OA 候选线索；真实成功以下载后的 PDF verifier 为准。
9. BibTeX / `.bib` / 参考文献段落只要当前任务意图是“下载”，就只进入下载清单归一化和下载路由；不得提前跳到 Zotero 入库或条目创建。

**Direct-entry input contract：**

| 可接受输入 | 推荐命令/处理 | 降级规则 |
|------------|---------------|----------|
| DOI 列表或 `--papers` | `unified_download_router.py --papers "...“ --dry-run` | DOI 异常进入 unresolved |
| `workflow-contracts.v1` search results JSON | `unified_download_router.py --workflow-results results.json --dry-run` | 缺 DOI 但有中文 article_url 仍可下载 |
| direct download manifest JSON | `unified_download_router.py --download-manifest manifest.json --dry-run` | 只下载 `status=ready` |
| CNKI/Wanfang URL | 转为 `source=cnki|wanfang` + `article_url` | 缺 URL 不猜测，进入 unresolved |
| 标题或参考文献文本 | 先解析 DOI/article_url/source_id | 多候选或低置信度时等待用户确认 |

**direct_download_manifest 推荐格式：**

```markdown
# Direct Download Manifest

| item_id | input_text | title | doi | source | article_url | publisher | confidence | status |
|---------|------------|-------|-----|--------|-------------|-----------|------------|--------|
| dd-001 | 10.1016/... | ... | 10.1016/... | doi |  | Elsevier | 1.00 | ready |
| dd-002 | 中文论文标题 | ... | wanfang.xxxx | wanfang | https://... | 万方 | 0.92 | ready |
| dd-003 | ambiguous title | ... |  | unresolved |  |  | 0.55 | needs_user_confirm |
```

**执行分流：**

- DOI-only：直接运行 `python3 scripts/unified_download_router.py --papers "10.x,10.y" --dry-run` 预览路由。
- workflow JSON：直接运行 `python3 scripts/unified_download_router.py --workflow-results workflow_search_results.json --dry-run` 预览 DOI + 中文 URL 混合路由。
- DOI + 中文 URL：优先生成 manifest JSON 后用 `--download-manifest`；兼容路径是英文 DOI 用 `--papers`，中文条目写入 `中文论文元数据.json` 后用 `--chinese-input`。
- 标题-only：先完成解析和 manifest，再只对 `status=ready` 的条目启动下载。

### 5.2. CHECKPOINT W — CP-DOWNLOAD-LOGIN 🚧 精准触发规则

> **两个独立门控，分阶段触发。Sci-Hub 不需要门控。中文和英文各自独立确认。门控由 PDF / article probe 结果触发，不由 publisher strategy 或校园 IP 一刀切触发。**

**不触发范围：** Sci-Hub、OA / `direct_http`、`skip`、已通过实际 PDF probe 的条目。

**触发范围：** login wall、access denied、CARSI required、PDF link 缺失、PDF probe unknown、页面显示权限不足。

**probe 判定表：**

| probe 状态 | 含义 | 是否触发 CP-DOWNLOAD-LOGIN |
|--------------|------|:--:|
| `scihub` | Sci-Hub 轮次处理，免费路径 | 否 |
| `direct_http` / `oa` | OA 或直接 HTTP 下载 | 否 |
| `skip` | 自动化不可行或需人工下载 | 否 |
| `pdf_probe_ok` | 已实际观察到 PDF URL / PDF bytes，可进入下载 | 否 |
| `pdf_probe_blocked` | login wall、access denied、未订阅、CARSI required | 是 |
| `pdf_probe_unknown` | 只看到文章页/过渡页，未证明 PDF 可访问 | 是 |
| `login_required` | 出版商登录墙或 SSO 页面 | 是 |
| `access_denied` | 页面显示无权限/未订阅/无法下载 | 是 |
| `carsi_required` | CNKI/万方需要 CARSI 机构登录 | 是 |

> **重要：** 校园 IP、VPN、cookie/session 只作为原因说明，不作为放行条件。只有实际 PDF probe 成功（例如出现 PDF URL 或捕获到 PDF bytes）才可判为 `pdf_probe_ok`。只看到文章页或平台首页时，应判为 `pdf_probe_unknown` 并触发登录/人工确认。

**中文门控（Phase 3）：** 仅在英文 DOI 路径全部完成或被用户明确跳过后触发。CNKI/万方 preflight 或 article/download probe 返回 `pdf_probe_blocked` / `pdf_probe_unknown` / `carsi_required` / `login_required` / `access_denied` 时，脚本必须先按本轮中文清单的 `source=cnki|wanfang` 去重，并在同一个 CDP Chrome 中自动打开对应中文文库入口（同一文库只开一次），再等待用户明确确认登录或写出中文 checkpoint。

**英文门控（Phase 2）：** Sci-Hub（仅 `year <= 2021`）完成后，先执行 OA fast；OA fast 只接受真实公开 PDF URL，下载后必须通过 `%PDF`、最小大小、非 HTML、可读页数验证。OA fast 剩余条目进入 English CDP 前必须先做预下载登录门控：若剩余 DOI 中存在 `strategy=generic` 或 `strategy=ieee_cdp` 且 `requires_auth != none` 的登录敏感条目，并且当前会话没有 `pdf/article probe ok` 级别的可信访问证据，脚本必须先按本轮待登录 DOI 去重 publisher，并在同一个 CDP Chrome 中自动打开这些 publisher 的登录/首页 tab（包括 IEEE 的 `https://ieeexplore.ieee.org/`），再提示用户登录 / 跳过 / 稍后重试，不能只把网址列给用户复制，也不能固定打开未参与本轮下载的常用出版社。若显式使用 `--require-login-confirm`，则对所有登录敏感 English CDP 条目强制提示。用户确认后才进入 IEEE CDP 与 Generic CDP 下载；若放行后仍出现 `manual_confirmation_required` / `login_required` / `login_wall` / `access_denied` / `pdf_probe_blocked` / `pdf_probe_unknown` 等登录类失败，再统一提示并只对这些失败 DOI 分组重试一次。

**交互兼容规则：**

- 若宿主支持弹窗/结构化选项（如 Codex），优先显示三选一：
  - `已登录，继续`
  - `跳过登录`
  - `稍后重试`
- 若宿主不支持弹窗，则退化为文本编号输入：
  - `1` = 已登录，继续
  - `2` = 跳过登录
  - `3` = 稍后重试
- 三选项前必须显示短说明：`已打开本轮需要登录的网站。` 与 `只有部分权限也选 1；无权限论文会在下载结果中单独记录。`
- `1` 表示“已完成能完成的登录”，不承诺所有论文都有订阅；部分机构权限也选 `1`，后续由真实下载结果分流。
- 运行语义必须一致：`2` 不能终止整批流程，只能跳过当前登录型路径并继续 OA / direct_http / 已完成结果汇总。
- **英文 checkpoint 特殊规则：** 如果宿主无法继续 `stdin` 交互、`input()` 抛出 `EOFError / KeyboardInterrupt`、用户选择 `3 / 稍后重试`，或输入无法识别，必须视为“当前宿主无法确认登录”，不是“用户主动 skip”。此时写出 `paper-temp/login_checkpoint.json`，把相关 DOI 标记为 `pending_user_login`，等待后续恢复。
- **恢复入口：** 用户完成机构登录后，应优先运行 `python3 scripts/unified_download_router.py --resume-login-checkpoint paper-temp/login_checkpoint.json --output paper-temp/ --confirmed`，脚本会只读取 checkpoint 内 DOI、只打开 checkpoint 涉及的 publisher tab，并只重跑待登录 DOI，不整批重来。`--confirmed` / `--assume-login-confirmed` 表示外层宿主或用户已经确认登录完成；确认后仍失败的条目必须转为真实策略失败（如 `generic_failed` / `access_denied` / `pdf_probe_unknown`），不得继续写回 `pending_user_login`。
- **中文非交互特殊规则：** 如果 CNKI/万方门控无法读取用户输入，或用户选择 `3 / 稍后重试`，必须视为“中文登录待确认”，不是用户主动 skip。此时写出 `paper-temp/chinese_login_checkpoint.json`，把中文条目标记为 `pending_user_login`，不得继续误判为跳过。
- **中文恢复入口：** 用户完成 CNKI/万方机构登录后，应运行 `python3 scripts/unified_download_router.py --resume-chinese-login-checkpoint paper-temp/chinese_login_checkpoint.json --output paper-temp/ --require-login-confirm`，脚本会只读取 checkpoint 内 source，按需打开 CNKI/万方入口，并只重跑 checkpoint 内的中文条目。

**GUI / agent 宿主推荐流程：**

1. 首次使用 CDP 下载时，默认先运行 `--check-session` 或等价 article/PDF probe，先确认当前浏览器会话属于“可直接尝试下载 / 需要先人工登录或验证 / 信号不足，需实际下载验证”中的哪一类。
2. 若 session 结论为“需要先人工登录/验证”或“信号不足，需实际下载验证”，agent 必须先提示用户在同一个 CDP 浏览器里完成机构登录，再进入真实下载；`--check-session` 只是诊断入口，不是下载成功证明。
3. 也可以直接进入正常下载，让脚本自动打开本轮 publisher 登录页；真正放行仍以 Phase 2 / 中文 probe 与登录门控为准。
4. 如果宿主无法读取 `input()`，保留 `login_checkpoint.json`，不要把该状态视为用户 skip。
5. 用户在 CDP 浏览器完成机构登录后，由 agent 使用 `--resume-login-checkpoint ... --confirmed` 续跑。
6. 续跑后只保留真实待登录项到 checkpoint；已确认登录仍失败的条目进入 `failed_dois.json`，用于区分“继续登录”与“修下载策略/手动下载”。

**执行流程：**

```
Phase 1:
1. 获取 Step 5 下载锁；若已有下载进程存活，提示“上一进程下载中，请等一等，下载完再运行中文下载”，不启动浏览器自动化
2. Sci-Hub 执行（免费，不需登录）

Phase 2:
1. 对英文 DOI 清单先做 OA hint 分层：`oa_candidate` / `no_oa_hint` / `unknown`，该分层只用于提示，不代表已验证可下载
2. 对剩余英文论文先执行 OA fast
   ├─ Step 4 `oa_pdf_url` 或轻量 OA resolver 命中真实 PDF URL → 下载并验证 → `public_pdf_verified`
   ├─ HTML / 小文件 / 损坏 PDF / landing page → `invalid_oa_candidate`；已知 OA 白名单验证失败记为 `oa_whitelist_but_verification_failed`，继续后续英文路径
   └─ 无 OA 线索 / unknown → 继续 Generic CDP
3. 对 OA fast 剩余论文先做 English CDP 预下载登录门控
   ├─ 仅 OA / direct_http / skip / `requires_auth=none` → 不触发门控
   ├─ IEEE CDP / Generic CDP + 登录敏感 + `pdf/article probe ok` → 直接放行
   ├─ IEEE CDP / Generic CDP + 登录敏感 + cookie-only / unknown / blocked → 按本轮 DOI 自动打开所需 publisher tab（包括 IEEE），再提示登录、跳过或写 `login_checkpoint.json`
   └─ 用户 skip → 只跳过登录敏感 DOI，继续保留 OA / direct_http / 已完成结果汇总
4. 用户确认登录后，先执行 IEEE CDP，再对其余放行论文按 publisher 分组执行 Generic CDP 下载
   ├─ pdf_probe_ok / 成功捕获 PDF bytes → 直接完成
   └─ 登录/权限/unknown probe 类失败 → 记录失败原因，继续跑完后续 publisher 组
   Agent 执行同样的交互式 CDP 启动，并只为本轮待登录 DOI 涉及的 publisher 打开 tab：
   "[Generic CDP]  elsevier (sciencedirect.com), ieee (ieeexplore.ieee.org),
    acs (pubs.acs.org), ..."
5. 放行后的第一轮所有 English CDP publisher 组结束后，若仍存在登录类失败，统一触发英文登录重试门控
6. 🚀 Agent 自动启动交互式 CDP 会话（同一条命令内）：
   a) 启动 exec_command：检查/启动 CDP Chrome → 导航到出版社首页
   b) 打印 === LOGIN_REQUIRED === → 用户登录后告知；如果用户没有机构账号，明确允许 `skip`，Agent 应继续后续 OA/已完成结果汇总，不得把整批任务视为失败
   c) 脚本确认 CDP 可用后退出
7. 用户确认后，Agent 只对登录类失败 DOI 按 publisher 分组重试一次；仍失败则进入 final remaining 或 checkpoint

Phase 3:
1. 英文 DOI 路径完成后，才进入排序后的中文清单：CNKI → 万方
   ⚠️ **强制规则：** 中文清单中的条目不论是否含有真实 DOI，一律以 `article_url` + `source/source_id` 进入 `chinese_cdp`。不得因为某条中文论文带有 DOI，就将它提前到 Phase 1/2 的英文路由中执行。
2. 🔍 中文源 article/download probe
   ├─ pdf_probe_ok → 直接执行中文下载
   └─ pdf_probe_blocked / pdf_probe_unknown / carsi_required / login_required / access_denied → 显示中文登录门控
3. 🚧 中文登录门控（仅 probe 需要时显示；按 source 去重自动打开 CNKI/万方入口）
   "CNKI/万方需要 CARSI 机构登录。
    🚀 Agent 将自动启动交互式 CDP 会话（同一条命令内，不会断连）。"
4. Agent 执行 Chinese CDP 下载（unified_download_router.py 连接同一 9223 端口）
```

**强制要求：**
- Agent 禁止在用户确认登录前调用 `unified_download_router.py`（除 `--dry-run` 外）
- Agent 必须先运行 `--dry-run` / `--test` / `--check-session` 或等价 article/PDF access probe，再提示登录
- 首次使用 CDP 下载时，应优先用 `--check-session` 或等价 probe 暴露会话状态；但它不是唯一前置条件，也不是下载成功证明
- 推荐使用 `--require-login-confirm` 参数启动路由器，由脚本层面再次门控
- **CDP 启动和下载如果跨命令，必须在同一条 exec_command session 内完成**
- 同一时间只允许一个 Step 5 真实下载进程使用 CDP 浏览器；另一个进程必须等待下载锁释放
- `--parallel-phase1` 仅为旧命令兼容保留，运行时会提示已停用，不再并发启动中文下载
- checkpoint 块的 `route_mode` 可为 `normal_chain` 或 `direct_entry`；`status` 必须在用户明确“已登录，确认 CP-DOWNLOAD-LOGIN”或等价明确语义后才可视为 confirmed。

**命令示例：**

```bash
# 示例 A：先 dry-run 查看路由和潜在登录型出版社
python3 scripts/unified_download_router.py 检索文献表.md --dry-run

# 示例 B：交互式启动 CDP + 登录（英文门控优先；中文在英文完成后才进入）
#   Agent 启动长驻命令，等待用户登录后 write_stdin 继续
python scripts/batch_chinese_search.py --login-only

# 示例 C：用户确认后执行完整下载；脚本会先英文、后中文
#   Agent 新开命令（CDP 端口仍然存活）
python3 scripts/unified_download_router.py 检索文献表.md \
  --chinese-input 中文论文元数据.json \
  --output paper-temp/ --require-login-confirm

# 完整下载流程（未显式强制登录；若 Generic CDP 登录信号不足，脚本仍会自动预门控）
python3 scripts/unified_download_router.py 检索文献表.md --output paper-temp/

# 单篇测试
python3 scripts/unified_download_router.py --test 10.1021/acsnano.4c00001 --port 9223

```

**流程摘要：**

- Phase 1：获取下载锁；旧英文 DOI 先走 Sci-Hub 免费路径。
- Phase 2：英文 DOI 先走 OA fast；命中机构登录的 IEEE / Generic 条目统一先做预下载登录门控；用户确认后先跑独立 IEEE CDP，再跑剩余 Generic CDP；若放行后仍出现登录类失败，只重试这些失败 DOI。
- Phase 3：英文路径完成、跳过或 checkpoint 挂起后，才进入排序后的中文清单（CNKI → 万方）；中文登录问题写 `chinese_login_checkpoint.json`。
- Phase 4：合并 Sci-Hub、OA fast、English CDP、Chinese CDP 结果，生成 `download_log.md`、失败清单和 final summary。

> **Sci-Hub 不受任何登录门控。** 英文门控先于中文门控；中文门控只在英文路径完成或明确跳过后触发。共享同一 CDP 端口 9223，并由 Step 5 下载锁防止多个进程同时冲击浏览器。

### 5.3. 英文路由矩阵（DOI 前缀驱动）

| 轮次 | DOI 前缀 | 出版商 | 策略 | 成功率 |
|------|----------|--------|------|--------|
| **R1: Sci-Hub** | 不限（`year <= 2021`） | 全部 | Sci-Hub CDP；`--skip-scihub` 可跳过 | 旧论文优先 |
| **R2: OA fast** | 不限 | OpenAlex / Semantic Scholar / Unpaywall 等公开 PDF 线索 | `oa_pdf_url` / 轻量 resolver → PDF verifier；`--skip-oa-fast` 可跳过 | 仅公开 PDF |
| **R3: IEEE CDP** | `10.1109/` | IEEE | 独立 `download_via_ieee.py`：文章页提取 stamp URL → `stamp/getPDF` 捕获 | 需 SSO |
| **R4: Generic CDP** | `10.1016/` | Elsevier / ScienceDirect | Generic CDP 内部 SD 适配器（DOI→PII→pdfft） | 复用 SD 成熟路径 |
| | `10.1002/` | Wiley | pdfdirect URL → 文章页选择器 | 策略A优先 |
| | `10.1021/` | ACS | 直连 PDF URL → 文章页选择器 | 策略A优先 |
| | `10.1039/` | RSC | 文章页 articlepdf 选择器 | 策略B为主 |
| | `10.1007/` | Springer | 直连 content/pdf URL | 策略A优先；机构登录优先用 `https://idp.springer.com/authorize?response_type=cookie&client_id=springerlink&redirect_uri=https%3A%2F%2Flink.springer.com%2F` 或 `https://wayf.springernature.com/?redirect_uri=https%3A%2F%2Flink.springer.com%2F` |
| | `10.1063/` | AIP | 文章页 + 加载页等待 | 含"请稍候"检测 |
| | `10.1038/` | Nature | 直连 article.pdf / OA HTTP | OA可直连 |
| | `10.1126/` | Science | 直连 PDF URL | 策略A优先 |
| | `10.1073/` | PNAS | 直连 PDF URL | 策略A优先 |
| | `10.1103/` | APS | 文章页 slug 解析 + 选择器 | slug解析 |
| | `10.1088/` | IOP | 直连 article/pdf URL | 策略A优先 |
| | `10.1080/` | T&F | 文章页选择器提取 | 策略B为主 |
| | `10.1116/` | AVS | AIP平台 加载页等待 | 同AIP |
| | `10.1149/` | ECS | IOP平台 文章页提取 | IOP族 |
| | `10.1364/` | OSA | 文章页选择器提取 | 策略B为主 |
| | `10.3762/` | Beilstein | 直连 OA | 开源 |
| | `10.31635/` | CCS Chem | 文章页选择器提取 | Cloudflare风险 |
| | `10.3389/` | Frontiers | 直连 HTTP（OA） | 无需认证 |
| | `10.3390/` | MDPI | Generic CDP（OA） | HTTP 直连可能 Akamai 403；真实浏览器详情页提取 `Download PDF`，失败则人工点击兜底 |
| | `10.2139/` | SSRN | 文章页选择器提取 | 预印本 |

### 5.4. 中文路由矩阵（source 字段驱动）🆕

| 数据库 | 识别方式 | 下载入口 | 登录方式 |
|--------|----------|----------|----------|
| 中国知网 (CNKI) | `source=cnki` + `文章链接` 列 | 文章详情页 → 只点击 `PDF下载` → 浏览器落盘监视 | 校园网 IP 或 CARSI SSO；安全验证单独标记 |
| 万方数据 (Wanfang) | `source=wanfang` + `文章链接` 列 | 文章详情页 → 按类型点击白名单下载入口 → 浏览器落盘监视 | 校园网 IP 或 CARSI SSO |

> **中文论文路由说明：** CNKI/万方论文多数无真实 DOI（使用 `cnki.{hash}` / `wanfang.{hash}` 合成标识符），但**即使条目带有真实 DOI，也仍然属于中文路由，不进入英文 DOI 路由器**。Step 5 对中文论文的路由键始终是 `source=cnki|wanfang` + `article_url/source_id`，不是 `doi`。**优先使用 Step 4 产出的 `中文论文元数据.json`**（字段显式、无 Markdown 解析歧义；旧名 `chinese_papers.json` / `chinese_metadata.json` 仍可作为兼容输入）。当该 JSON/manifest 条目标记 `status=ready` 时，表示该条目已具备下载前提，Step 5 直接下载，不因 `zotero_item_key` 再去查询 Zotero。Step 5 拿到中文下载清单后先稳定排序：CNKI 条目在前、万方条目在后，同一数据库内部保留原输入顺序；排序后的清单用于路由 summary、登录门控、checkpoint、下载和 download log。中文 CDP 不与英文下载并发，必须等待英文 DOI 路径完成或明确跳过后再启动。若 JSON 缺失，回退到 Markdown 表格解析（`--chinese-input 检索文献表.md`）。缺少 `article_url` 的论文将被跳过。

**CNKI 实测状态分流（Windows/CARSI/CDP）：**

| 状态 | 触发条件 | Agent 行为 |
|------|----------|------------|
| `status=ready` | `中文论文元数据.json` / direct manifest 条目已标记为可下载 | 直接进入 Step 5 下载流程；不额外查询 Zotero，不额外做附件审计 |
| `captcha_required` | URL 命中 `/verify/home`、标题含「安全验证」或正文含「请完成安全验证」 | 不得记为普通失败；保留页面；脚本必须先自动监控当前篇 CNKI 验证页，检测到用户完成图形验证并回到目标详情页后自动重试当前篇；若等待超时、页面丢失或自动监控无法确认，再回退到短语确认/`chinese_login_checkpoint.json`；不得尝试绕过图形验证 |
| `pdf_probe_unknown` | 已进入详情页但未证明存在可下载入口 | 触发人工确认或重试，不得声称论文不可下载 |
| `manual_required` | 存在人工路径，或自动点击后未监视到 PDF 落盘 | 允许用户手动点击 `PDF下载`，Agent 只监视落盘并归档 |
| `chapter_download_mode` | 未识别到 `PDF下载`，但页面出现「章节下载」「分页下载」 | 不自动点击章节/分页入口；单独列为人工判断状态 |
| `fulltext_delivery_mode` | 万方详情页未出现直接 PDF/整篇下载，但出现「原文传递」 | 不声称 PDF 不存在；本轮跳过该条下载并记录原因，继续下一条；**不得自动转向其他数据库（如 CNKI）重新尝试该文献** |
| `ok` | `PDF下载` 入口触发后 PDF 已落盘并通过大小检查 | 记录成功 PDF 路径 |

**CNKI 自动点击白名单：** 期刊论文和学位论文的详情页使用同一规则：只允许自动点击明确的 `PDF下载` / `PDF 下载` / `#pdfDown`。不得自动点击 `AI阅读`、`原版阅读`、`CAJ下载`、`章节下载`、`分页下载`、`我是作者`、`免费下载`、`在线阅读`、`整本下载`，即使这些入口看起来可能免费或能进入阅读页。只有在未识别到 PDF 入口时，`章节下载/分页下载` 才标记为 `chapter_download_mode`，作为人工判断状态。其它非 PDF 入口由用户人工判断，Agent 只负责监视落盘并归档。

**已验证详情页复用规则：** 若用户已经手动完成 CNKI 安全验证并停留在目标论文详情页，Agent 后续应优先复用该已验证详情页标签进行下载/落盘监视；不要默认重新 `Target.createTarget(article_url)` 打开原始链接，以免再次触发验证码。脚本会先扫描现有 CNKI 标签页，按目标详情页 URL 优先、题名匹配其次复用；匹配到安全验证页时返回 `captcha_required` 并保留页面，匹配到已验证详情页时只在该页点击白名单 `PDF下载` 并监视落盘。找不到可复用标签页时才新开详情页。

**CNKI 验证页自动续跑规则：** 当当前篇命中 `captcha_required` 时，脚本必须先显示短提示，并自动监控当前篇 CNKI 标签页状态。只要检测到用户已完成图形验证且页面回到目标论文详情页，脚本就自动重试当前篇下载，不再要求外层 agent 或用户手动回复 `已验证继续`。若等待超时、验证页丢失或跳转到无关页面，才回退到对话/终端短语确认；用户输入 `稍后重试`、输入不可识别或宿主无法读取输入时，把当前篇及后续未执行的中文条目写入 `paper-temp/chinese_login_checkpoint.json`，后续由 agent 使用既有 `--resume-chinese-login-checkpoint ... --require-login-confirm` 恢复。

**独立中文会话规则：** 当 CNKI/万方反复命中验证码、入口异常，或怀疑英文出版社页面污染 CDP 状态时，优先使用独立中文 CDP 端口或独立 profile（例如 `--port 9225`）重试。

**万方自动点击白名单：** 万方与 CNKI 是两条不同入口策略。万方期刊论文详情页优先点击 `下载`，不得点击 `在线阅读`、`评审材料`。万方学位论文详情页优先点击 `整篇下载`，不得点击 `在线阅读`、`分章下载`。若详情页没有直接 PDF/整篇下载但出现 `原文传递`，脚本记录为 `fulltext_delivery_mode` 并跳过当前条，继续下一条，不再笼统归为 `pdf_probe_unknown`。Agent **不得** 以该文献在其他数据库（如 CNKI）有收录为由，自行跳转尝试。点击白名单入口后，如进入 `f.wanfangdata.com.cn/download/...` 中转页，再点击 `点击此处` 并监视 PDF 落盘。

### 5.5. 命令参考

```bash
# 前检查：验证 CDP 浏览器 + 各出版商会话状态
python3 scripts/unified_download_router.py --check-session --port 9223

# 查看路由决策（不下载，不受登录门控限制）
python3 scripts/unified_download_router.py 检索文献表.md --dry-run

# 完整下载流程（带登录门控） 🆕
python3 scripts/unified_download_router.py 检索文献表.md --output paper-temp/ --require-login-confirm

# 跳过登录门控（仅 OA/免费来源，Agent 需确认无付费墙出版社）
python3 scripts/unified_download_router.py 检索文献表.md --output paper-temp/

# 中文+英文下载（推荐，使用 Step 4 产出的 中文论文元数据.json） 🆕
python3 scripts/unified_download_router.py 检索文献表.md --chinese-input 中文论文元数据.json --output paper-temp/ --require-login-confirm

# 仅中文下载（无英文 DOI）
python3 scripts/unified_download_router.py --chinese-input 中文论文元数据.json --output paper-temp/

# 中文下载兜底（JSON 缺失时，从 Markdown 表格解析）
python3 scripts/unified_download_router.py 检索文献表.md --chinese-input 检索文献表.md --output paper-temp/ --require-login-confirm

# 中文单篇测试 🆕
python3 scripts/unified_download_router.py --test-cnki "https://kns.cnki.net/kcms2/article/abstract?..." --port 9223
python3 scripts/unified_download_router.py --test-wanfang "https://www.wanfangdata.com.cn/details/..." --port 9223

# 跳过免费路径
python3 scripts/unified_download_router.py 检索文献表.md --skip-scihub   # 旧论文也跳过 Sci-Hub，直接 OA fast
python3 scripts/unified_download_router.py 检索文献表.md --skip-oa-fast  # 调试机构 CDP

# 下载辅助材料（Supplementary Info）
python3 scripts/unified_download_router.py 检索文献表.md --include-si

# 内联 DOI 列表
python3 scripts/unified_download_router.py --papers "10.1021/x,10.1002/y,10.1016/z"

# 直达下载：用户只给 DOI 列表时先 dry-run，再正式下载
python3 scripts/unified_download_router.py --papers "10.1021/x,10.1002/y" --dry-run
python3 scripts/unified_download_router.py --papers "10.1021/x,10.1002/y" --output paper-temp/ --require-login-confirm

# 不同 CDP 端口
python3 scripts/unified_download_router.py 检索文献表.md --port 9225
```

### 5.6. 下载记录

路由器自动生成 `paper-temp/download_log.md`，逐篇追踪：

下载器报告成功后仍必须经过统一 PDF verifier。HTML 伪 PDF、过小文件、缺 `%PDF` 或无可读页的文件标记为 `invalid_pdf`；`download_attempts.jsonl` 采用 append-only 事件记录，不覆盖前次运行历史。

| # | DOI | Status | Source | Size | Path |
|---|-----|--------|--------|------|------|
| 1 | `10.1016/...` | ✅ | Generic CDP | 1024KB | paper_001.pdf |
| 2 | `10.1002/...` | ✅ | Generic CDP | 856KB | paper_002.pdf |
| 3 | `cnki.a1b2c3d4...` 🆕 | ✅ | Chinese CDP (CNKI) | 512KB | paper_003.pdf |
| 4 | `10.3390/...` | ⏳ | — | - | - |

### 5.7. 出版社配置

所有出版社的下载策略（URL 模板、CSS 选择器、屏障检测规则）集中维护在：
[`config/publishers.toml`](../config/publishers.toml)

新增出版商时，只需在该文件中添加一个 `[publishers.xxx]` 段落即可。

### 5.8. 保留的专用脚本

以下脚本保持不变，路由器通过子进程调用它们（也可单独使用）：

| 脚本 | 用途 | 何时单独使用 |
|------|------|-------------|
| `download_via_scihub.py` | Sci-Hub 批量下载 | 只缺老论文时 |
| `download_via_ieee.py` | IEEE CDP 下载 | 默认 IEEE 路由；也可单独调试 |
| `auto_sd_downloader.py` | SD 全自动下载 | 只下 Elsevier 论文、且需要独立批量调试时 |
| `generic_publisher_downloader.py` | 通用CDP下载引擎 | 测试特定非SD/IEEE论文 |

统一路由中 ScienceDirect 已归入 Generic CDP，默认只使用一个 CDP 浏览器，以复用用户已经完成机构登录的会话：

```bash
# 默认 Chrome
python3 scripts/unified_download_router.py dois.txt --browser chrome

# 用户默认 Edge 或机构账号已在 Edge 中登录
python3 scripts/unified_download_router.py dois.txt --browser edge

# 独立调试 Elsevier 批量下载时才直接使用专用脚本
python3 scripts/auto_sd_downloader.py --browser edge --pii-map sd_pii_map.json
```

**浏览器一致性规则：** 用户在哪个浏览器完成机构认证，下载命令就必须使用同一个 `--browser`。统一路由会检查 9223 端口背后的浏览器产品；例如请求 `--browser chrome` 但端口实际是 Edge 时，会重启 Chrome，而不是复用 Edge 的未登录会话。

### 5.9. 核心设计原则

1. **默认所有论文都有访问权限** — 下不到是策略问题，不是权限问题
2. **英文先行，中文排序后最后执行** — CNKI/万方不再与英文下载并行；中文清单固定 CNKI → 万方；`--parallel-phase1` 仅兼容旧命令，运行时提示停用
3. **英文按 DOI 前缀路由，中文按 source 字段路由** — 两条线泾渭分明，互不污染
4. **`Fetch.enable` 必须在 `Page.navigate` 之前调用**（IEEE v1.0.1 验证）— 否则 Chrome PDF 查看器消费响应体
5. **出版商知识库集中维护** — `config/publishers.toml`，新增出版商只需加一个 `[publishers.xxx]` 段落
6. **ScienceDirect / Elsevier 归入 Generic CDP，IEEE 默认走独立 CDP**，`auto_sd_downloader.py` 保留为 SD 专用调试，`download_via_ieee.py` 是 IEEE 默认实现，Generic IEEE fallback 只保留为内部兜底
7. **直达下载先归一化、再下载** — DOI 可直接路由，标题必须先解析为 DOI/URL/中文 article_url
8. **checkpoint 不是入口锁** — `CP-DOWNLOAD-LOGIN` 只阻塞需要登录态的下载执行，不阻塞 manifest 生成、dry-run、OA/Sci-Hub/direct_http 路径
9. **SD 默认跟随 Generic CDP 浏览器选择** — `--browser edge` 则 ScienceDirect 也用 Edge；`--browser chrome` 则 ScienceDirect 也用 Chrome；统一路由会校验端口上的浏览器类型，不在统一路由里默认启动双浏览器。
10. **OA fast 是候选验证层** — Step 4 的 OA 字段只提供候选；Step 5 必须验证真实 PDF 后才记录 `public_pdf_verified`，无效候选记录 `invalid_oa_candidate`，已知 OA 白名单验证失败记录 `oa_whitelist_but_verification_failed`，并继续后续英文路径。
11. **Step 5 只做当前源站的下载尝试** — 当源站明确返回不可下载状态（`fulltext_delivery_mode`、`chapter_download_mode`、`access_denied` 等）时，Agent 不得自动转向其他数据库或数据源绕过。由用户自行决定是否从其他途径补下该文献。

---

## 质量门槛 (Quality Gates)

- [ ] 如为直达下载模式：输入已分类为 DOI / 英文标题 / 中文标题 / URL / BibTeX
- [ ] 如含标题：已生成 `direct_download_manifest.md/json`，且仅下载 `status=ready` 条目
- [ ] 如有无法唯一解析条目：已写入 `unresolved_download_items.md`，未擅自猜 DOI
- [ ] CDP 登录门控已执行：Agent 已提示用户完成机构登录，用户已确认"已登录" 🆕
- [ ] CDP 浏览器已启动且端口可访问，并且与下载命令的 `--browser` 一致（`python scripts/start_cdp_browser.py --browser chrome --port 9223` 可启动/复用；也可用 `/json/version` 检查 `Browser` 字段）
- [ ] 会话状态已检查（`--check-session`）
- [ ] 下载已通过 `--require-login-confirm` 门控参数启动（或 Agent 已手动确认登录） 🆕
- [ ] 下载记录完整追踪每篇论文状态
- [ ] 下载失败的论文有明确的失败原因（非"未知错误"）
- [ ] `python3 scripts/validate_step5_output.py paper-temp` 已通过
- [ ] `downloaded` 条目均为 `verification_status=verified`，checkpoint 条目已计入 Failed/Pending
- [ ] manifest、PDF 索引和 checkpoint 已原子写入；attempt journal 已耐久追加且重复恢复不产生相同 attempt_id
- [ ] 已完成 checkpoint 为 `resolved`；pending checkpoint 只包含仍待处理且不重复的 identifier

---

## 收尾检查 (Closing Checks)

### 产出完整性
- [ ] PDF 已保存到 paper-temp/
- [ ] `paper-temp/download_log.md` 已生成
- [ ] 如为直达下载模式：`direct_download_manifest.md/json` 已保存；未解析条目已进入 `unresolved_download_items.md`
- [ ] 下载成功率和失败原因统计已输出

### 错误日志更新 🆕
- [ ] 本轮执行中是否出现新的下载失败模式？
  - 新的出版商屏障 → 追加到 `.skill-state/error_log.md` + 更新 `config/publishers.toml`
  - 新的 CDP 陷阱 → 追加到 `.skill-state/error_log.md` + 更新 `agents/known_pitfalls.md`
  - 会话过期的新触发条件 → 追加到 `.skill-state/error_log.md`

### 决策日志更新 🆕
- [ ] 是否调整了下载策略？（如新增 skip 规则）→ 记录到 `.skill-state/decision_log.md`

### 下一步提示
- [ ] 向用户明确说明下一步：管理 Zotero 文库（Step 6）
  > **下一步 → Step 6：** 下载完成后，管理 Zotero 文库：先生成架构，再将 PDF 导入对应集合。

### 成功判据
- [ ] 下载结果已区分 `已下载 / 需登录 / 无法获取 / 待人工`
- [ ] 用户和后续 Step 都能看懂哪些条目真的拿到了 PDF

### 完成前必须确认
- [ ] 只有在状态已分流且下载日志可追溯时，才能声称“下载完成”
- [ ] `download_manifest.json` 的 summary/readiness 与逐条状态一致，且 Step 5 完成校验器通过
- [ ] 未解析标题、未确认 DOI、失败条目不得被表述为已完成

### 失败分流
- 下载失败：先按 `references/failure-triage.md` 判定是元数据层、登录权限层还是出版社策略层
- 中文条目失败：先查 `article_url/source_id`，不要直接改走英文 DOI 路由，**更不得自动转向另一中文数据库（如万方→CNKI 或反之）重新尝试**
- 同一篇文献如果原站明确返回「无法下载」状态（如 `fulltext_delivery_mode`），标记为「无法直接下载」交用户决定是否补查其他数据源，Agent 不替用户做转向决策
- 会话问题：标为登录/会话层问题，而不是泛化成”网络错误”

---

## 故障排除 (Troubleshooting)

常见问题参见 `agents/known_pitfalls.md`。本 Step 特有的问题：

- **CDP 端口无法连接**：检查 Chrome 是否以 `--remote-debugging-port=9223` 启动
- **用户只给标题**：先解析 DOI/URL；无法唯一匹配时不要下载，写入 `unresolved_download_items.md`
- **中文标题没有 DOI**：先通过 CNKI/万方补 `article_url`，再走中文 CDP，不进入英文 DOI 路由
- **会话过期**：`auto_sd_downloader.py` 自动检测并重启浏览器
- **PDF 标签页残留**：已修复（v2.1），每篇下载后自动关闭 PDF 标签页
- **重启死循环**：`skip_set` 机制自动跳过无权限论文
