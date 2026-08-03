# Equation Writing Contract

本合同用于 Step 7 公式撰写和 Step 8 成稿终验，解决三类阻断问题：应有公式但正文缺失、数学表达退化为纯文本、LaTeX/矩阵源码进入最终稿。

## 适用范围

- 方法、模型、控制方程、目标函数、状态方程、传递函数、矩阵、统计量和机理方程。
- Markdown、LaTeX、DOCX 与由这些格式生成的 PDF。
- direct-entry 草稿同样执行本合同，不要求补跑 Step 1-6。

## 写作前登记

每个公式在 `equation_register.json` 中至少记录：

| 字段 | 要求 |
|------|------|
| `equation_id` | 稳定 ID，如 `EQ-001` |
| `section_id` | 公式所在章节或标题 |
| `purpose` | 公式在论证中的用途 |
| `latex_source` | 可复现的规范数学源；DOCX-only 原生公式无法回收时允许为空，但必须 `needs_author_check=true` |
| `plain_language_explanation` | 公式后的直觉解释或物理意义 |
| `variables` | 变量、定义、类型和取值范围 |
| `units` | 单位或无量纲说明 |
| `assumptions` | 假设、边界条件和适用范围 |
| `evidence_anchor` | 自建推导、标准、数据或原文页码锚点 |
| `where_referenced` | 正文引用位置 |
| `derivation_status` | `source_preserved / independently_derived / partial / not_audited` |
| `validation_status` | `pass / needs_repair / needs_author_check` |

`equation_register.md` 是人工审阅层；JSON 是机器主源。不得用展示层反向覆盖 JSON。

## 正文规则

1. 先定义符号，再给公式；首次出现后说明变量、单位、假设和边界条件。
2. 每个独立公式后至少有一句解释，说明公式表达什么以及如何支撑当前论点。
3. 出现“如下式所示、可表示为、定义为、目标函数为、状态方程为、控制方程为”等引导语时，当前段或紧随其后的内容必须有可渲染公式。
4. 正文引用“式（n）/Eq. (n)”时，必须存在对应编号；公式编号和交叉引用不得断链。
5. 外部公式必须保留来源和证据锚点；摘要、元数据和候选提取文本不能支撑精确公式、参数或推导。
6. 不能确认公式时，不得静默删除或猜写；保留占位并设置 `needs_author_check=true`。

## 格式规范

- Markdown：行内公式使用 `$...$`，独立公式使用 `$$...$$`；不使用可能在 DOCX 导出时原样残留的 `\(...\)` 或 `\[...\]`。
- LaTeX：公式必须位于有效数学环境中，环境、花括号和矩阵行分隔符必须闭合。
- DOCX：公式必须是 OMML/Word 原生公式对象；普通文本中的反斜杠命令、花括号下标或裸下划线不算公式。
- PDF：必须由通过审计的 Markdown/LaTeX/DOCX 生成，并抽查矩阵、分式、上下标、希腊字母、编号和引用。

规范示例：

```latex
$$
\begin{bmatrix}
F_{i+1}(\omega) \\
V_{i+1}(\omega)
\end{bmatrix}
$$
```

## 风险代码

| code | 含义 | 默认动作 |
|------|------|----------|
| `missing_equation` | 引导语或公式引用存在，但公式本体/编号不存在 | 阻断，回到模型或证据源补齐；不能确认则标记作者检查 |
| `plain_text_math_leak` | `T(omega)`、`(omega)`、`F_{i+1}`、`X_in` 等未渲染表达 | 阻断，按变量语义转成正式数学表达 |
| `noncanonical_math_delimiter` | `\(...\)`、`\[...\]` 进入 Markdown/普通文本/DOCX | 阻断，转换为目标格式的规范公式 |
| `latex_source_leak` | `\frac`、`\sum`、`\left`、`\right` 等命令裸露 | 阻断，放入有效数学环境或转为原生公式对象 |
| `matrix_source_leak` | `\begin{bmatrix}` 等矩阵源码裸露 | 阻断，修复数学环境、行分隔和括号 |
| `malformed_matrix_rows` | 矩阵行只剩单个反斜杠或对齐损坏 | 阻断，恢复 `\\` 行分隔 |
| `unclosed_math_environment` | 环境、花括号或数学定界符不闭合 | 阻断，修复后重新审计 |
| `broken_equation_reference` | 正文公式编号无定义 | 阻断，补公式或修正引用 |

自动修复只能处理语义确定的格式问题。例如 `T(omega)` 可规范为 `$T(\omega)$`；`X_in` 只有确认 `in` 是文本下标后才能改为 `$X_{\mathrm{in}}$`。程序字段、文件名或无法确定的符号进入 `needs_author_check`，不得批量盲改。

## 执行与工件

推荐在 Markdown 主稿完成后、DOCX 导出前运行：

```bash
python3 scripts/equation_guard.py 论文初稿.md --output-dir .
```

标准产物：

- `equation_audit.json`：机器审计结果，绑定当前稿件 SHA-256。
- `equation_audit.md`：人工审阅报告。
- `equation_register.json`：公式登记机器主源。
- `equation_register.md`：公式登记人工审阅层。

## 完成门

- `draft_ready`：不得有 `missing_equation`、纯文本数学泄漏、裸 LaTeX/矩阵源码或损坏数学环境。
- `evidence_closed`：在上述基础上，公式来源、变量、假设和证据边界必须可回查。
- `ready_for_step8`：`equation_audit.json` 和 `equation_register.json` 必须与当前稿件哈希一致，且审计状态为 `pass`。
- Step 8 `ready_for_finalize`：润色前后公式签名一致，目标 DOCX 中公式为原生公式对象，PDF 抽查无渲染残留。
