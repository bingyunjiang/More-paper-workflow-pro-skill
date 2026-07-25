# 中英文提示词宿主烟测

## 目标

使用同一组真实提示词比较 Codex、Claude、Hermes 对 Step 1-8 的
路由、工件和完成门执行情况。自动化 judge 是确定性的，不调用外部模型；
宿主回答由测试者在各宿主中生成并保存。

## 用例

用例定义位于 `evals/prompt_acceptance.json`。每种语言覆盖八个入口：

- Step 1：模糊方向进入选题澄清
- Step 2：主题直入不可变结构蓝图
- Step 3：base workflow + addons 可组合检索计划
- Step 4：core 检索、来源降级和 run manifest
- Step 5：DOI 直达下载路由
- Step 6：BibTeX/PDF 直入 plan-only Zotero 计划
- Step 7：已有 Zotero/PDF/草稿的章节级写作
- Step 8：不新增证据的保守润色

列出全部提示词：

```bash
python3 scripts/run_prompt_acceptance.py --list
```

## 每个宿主执行三次

1. 记录当前 Git 提交：`git rev-parse HEAD`。
2. 在目标宿主的新对话中粘贴同一条提示词。
3. 不补充额外解释，把完整原始回答分别保存为 `run-1.txt`、`run-2.txt`、
   `run-3.txt`。
4. 运行确定性 judge：

```bash
python3 scripts/run_prompt_acceptance.py \
  --case zh-step7-writing \
  --host codex \
  --response run-1.txt \
  --response run-2.txt \
  --response run-3.txt \
  --out prompt-eval-codex-zh-step7.json
```

将 `--host` 分别设为 `codex`、`claude`、`hermes`。报告保存原始回答、
SHA-256、逐轮失败原因、通过率和一致性。

## 通过标准

- 十六个用例在每个宿主至少执行三次。
- `selected_step`、`entry_mode`、Step 内模式/操作与预期一致。
- 回答列出最低必需工件、风险字段和下一步。
- 不把未登录、未下载、未核验引用或缺证据状态表述成已完成。
- 同一宿主同一用例三次全部通过；若结果不一致，保留原始回答并登记为
  agent regression，不通过修改 judge 掩盖波动。
