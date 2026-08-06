# 更新提醒协议（宿主无关）

本协议用于让 more-paper-workflow 在**不依赖宿主原生弹窗能力**的前提下，实现统一的升级提醒交互。

目标：

- 宿主若支持原生按钮/弹窗，优先使用原生选项交互
- 任意宿主只要支持“显示文本 + 接收用户回复”，即可接入
- 原生按钮/弹窗与纯文本回退必须共用同一套动作语义
- 不把升级提醒做成必须修改宿主源码才能使用的能力

---

## 1. 启动时检查

调用 skill 时，先执行：

```bash
python3 "$SKILL_DIR/scripts/check_skill_update.py" --json
```

若返回：

- `should_prompt=true`

则宿主应先显示一次升级提醒，再进入主流程：

- 宿主支持原生按钮/弹窗：优先使用原生选项交互
- 宿主不支持原生按钮/弹窗：回退到标准升级提醒文本

若返回：

- `should_prompt=false`

则直接进入主流程。

版本判定固定遵循以下规则：

- 只检查当前 Git 分支配置的 upstream，不比较无关的远程默认分支
- fetch 远程对象后读取远程 `SKILL.md` 的 `version`
- 只有远程版本号高于本地版本号时才设置 `should_prompt=true`
- 同版本的普通提交变化不作为“新版本”提醒
- 无 upstream、远程不可达或远程版本无法读取时 fail-open，继续当前任务

推荐直接使用：

```bash
python3 "$SKILL_DIR/scripts/check_skill_update.py" --json \
  | python3 "$SKILL_DIR/scripts/render_update_prompt.py"
```

---

## 1.1 推荐接入顺序

推荐的宿主决策顺序固定为：

1. 先执行 `check_skill_update.py --json`
2. 若 `should_prompt=false`，直接进入主流程
3. 若 `should_prompt=true` 且宿主支持原生选项 UI，则显示 3 个按钮：
   - `升级`
   - `本次跳过`
   - `今日不再提醒`
4. 若 `should_prompt=true` 但宿主不支持原生选项 UI，则显示 `render_update_prompt.py` 生成的标准文本
5. 无论按钮还是文本，最终都必须映射到同一标准动作：
   - `upgrade`
   - `skip_once`
   - `snooze_today`

可直接记忆的兼容规则是：若宿主不支持原生按钮/弹窗，则显示 `render_update_prompt.py` 生成的标准文本。

---

## 2. 标准升级提醒文本

标准文本由 `scripts/render_update_prompt.py` 生成，宿主不需要自己拼模板。

约束：

- 选项文案尽量保持固定，避免宿主各写一套
- 若需英文 UI，可翻译展示，但底层动作语义必须保持一致
- 若有 `messages` 字段，可将其中 1-2 行附在正文后面作为补充说明
- 文本回退不是次等协议，而是所有宿主都必须可用的保底路径

---

## 3. 用户回复到动作的映射

宿主对用户暴露的标准回复词固定为：`升级 / 本次跳过 / 今日不再提醒`。

宿主应把用户回复映射为以下 3 个标准动作：

| 用户回复 | 标准动作 | 说明 |
|----------|----------|------|
| `升级` | `upgrade` | 执行升级脚本 |
| `本次跳过` | `skip_once` | 当前会话跳过提醒，不写长期免打扰 |
| `今日不再提醒` | `snooze_today` | 对同一远程 HEAD 写入默认 24 小时抑制 |

推荐同时接受以下同义表达：

- `升级`：`update` / `upgrade`
- `本次跳过`：`跳过` / `skip`
- `今日不再提醒`：`今天不再提醒` / `snooze` / `稍后再说`

但宿主在写回状态时，必须统一归一化为：

- `upgrade`
- `skip_once`
- `snooze_today`

---

## 4. 状态写回

### 4.1 升级

若用户选择 `升级`：

1. 优先执行：

```bash
python3 "$SKILL_DIR/scripts/perform_skill_upgrade.py" --json
```

2. 若升级成功，再执行：

```bash
python3 "$SKILL_DIR/scripts/check_skill_update.py" --record-choice upgrade
```

3. 重新读取 `SKILL.md`
4. 再进入主流程

自动升级前必须同时满足：当前分支有 upstream、工作区无未提交修改、远程历史可 fast-forward。任一条件不满足时不得自动修改工作区，应说明原因并继续使用当前版本。

若升级失败：

- 必须明确提示用户“升级失败，但将继续使用当前本地版本”
- 不得因为联网失败或 `git pull` 失败而阻塞当前版本继续使用
- 宿主可展示 `perform_skill_upgrade.py` 返回的 `message` 与 `details`

### 4.2 本次跳过

若用户选择 `本次跳过`：

- 宿主应在**当前会话内**自行记住“本次已跳过”
- 可选执行：

```bash
python3 "$SKILL_DIR/scripts/check_skill_update.py" --record-choice skip_once
```

说明：

- `skip_once` 不写长期抑制
- 是否在同一会话后续再次提醒，由宿主自行决定；推荐同一会话不再重复提示

### 4.3 今日不再提醒

若用户选择 `今日不再提醒`：

执行：

```bash
python3 "$SKILL_DIR/scripts/check_skill_update.py" --record-choice snooze_today
```

说明：

- 该动作会写入缓存状态
- 默认对同一远程 `HEAD` 抑制 24 小时

---

## 5. 推荐宿主行为

为兼容高频用户与自动化场景，推荐：

- 有原生弹窗时优先使用弹窗/按钮；无原生弹窗时立即回退文本
- 默认使用软提醒，不强拦截
- 同一会话内，用户选择 `本次跳过` 后不重复提醒
- 用户选择 `今日不再提醒` 后，尊重脚本缓存抑制
- 网络失败、git 不可用、远程不可达时直接放行，不阻塞主流程
- 用户选择 `升级` 但升级失败时，提示失败原因后继续使用当前本地版本

不推荐：

- 只要远程落后就每次调用都强制打断
- 不给“本次跳过”或“今日不再提醒”
- 宿主自行发明另一套 incompatible 的动作名

---

## 6. 最小接入要求

一个宿主若满足以下条件，即视为兼容：

1. 能执行 `check_skill_update.py --json`
2. 能把返回文本展示给用户
3. 能读取用户回复
4. 能执行升级脚本或写回 `--record-choice`

因此：

- CLI 宿主兼容
- 聊天式宿主兼容
- Web UI 宿主兼容
- 原生按钮/弹窗宿主也兼容
