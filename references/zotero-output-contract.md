# Zotero 输出契约

Step 6 每次整理至少应产出“双工件”。

## 必需产物

### 1. 可机读 JSON

至少包含：

- root collection
- records
- collection path
- import status
- attachment status
- item state
- attachment state
- completion state
- readiness
- warnings

### 2. 可审阅 Markdown

至少包含：

- 本轮输入依据
- 阻塞项
- 非阻塞项
- 文库对照表
- 下一步建议

## 目标

让 Step 7 可以优先读 JSON，人工优先看 Markdown。

## 状态契约

- `item_state`: `planned / existing_confirmed / imported / duplicate_candidate / metadata_conflict / import_failed / rejected_do_not_import / manual_confirmation_required`
- `attachment_state`: `matched_attachment / missing_attachment / unlinked_pdf / duplicate_attachment / invalid_attachment / attachment_conflict / manual_attach_required / rejected`
- `completion_state`: `plan_ready / write_partial / write_complete / blocked`

`plan_ready` 只表示整理计划可审阅，不冒充真实 Zotero 写入。Step 6 可从 Zotero 只读扫描、BibTeX、CSL/workflow JSON、既有对照表或 PDF-only 直接进入；这些入口互为替代，不要求 Step 5 已执行。

执行档位固定为 `plan-only / write / repair`。档位决定必需工件和允许动作，但不改变同一 `plan_fingerprint`、operation journal 和回读验证合同。

兼容字段 `execution_mode=local|cloud|skip|plan-only` 继续表示连接/后端模式；`execution_profile` 表示生命周期阶段。`validate_step6_output.py --profile` 同时检查两者是否冲突。

真实写入应把事件追加到 `zotero_write_operations.jsonl`，并维护 `zotero_execution_state.json`。相同 `operation_id` 的成功操作必须幂等跳过。

完成声明前运行：

```bash
python3 scripts/validate_step6_output.py <step6-output-dir>
```
