# Workflow Run Envelope

八个 Step 可以保留各自的领域状态，但跨 Step 交接必须使用同一个全局状态外壳。领域状态不直接替代全局 `readiness`。

## 必需字段

```json
{
  "schema_version": "morepaper.workflow-run.v1",
  "run_id": "step4-20260726-example",
  "step": 4,
  "entry_mode": "direct-query",
  "route_mode": "direct_entry",
  "execution_profile": "core",
  "input_hashes": {},
  "outputs": [],
  "domain_state": "search_complete",
  "readiness": "partial",
  "can_continue": true,
  "blocking": [],
  "warnings": [],
  "checkpoint_state": {},
  "recommended_next_step": "Step 5"
}
```

## 解释规则

- `domain_state`：本 Step 内部状态，例如 `plan_ready`、`draft_ready`、`ready_for_step8`。
- `entry_mode`：材料/任务入口，例如 `direct-topic / direct-query / direct-bib / direct-draft`。
- `route_mode`：执行生命周期，例如 `normal_chain / direct_entry / plan_only / repair / resume / partial_artifact`；不得与 `entry_mode` 混用。
- `readiness`：只允许 `blocked / partial / complete`，供任意宿主和下游统一判断。
- `can_continue`：表示能否在当前证据边界下继续，不等于当前 Step 已完整完成。
- `blocking`：只列真正阻塞当前请求的条件；非阻塞缺口进入 `warnings`。
- `checkpoint_state`：记录 checkpoint 是否未触发、pending、confirmed、skipped 或 resolved；不得把 pending 覆盖为成功。
- `input_hashes`：机器输入按路径记录 SHA-256，展示层缺失不影响机器主工件的可复用性。
- `outputs`：列出实际存在的工件，不列计划生成但尚未生成的文件。

各 Step 的允许轴、领域状态和稳定工件以 `schemas/workflow-contract-registry.json` 为准。`scripts/workflow_run_envelope.py` 用于生成和校验该外壳。
