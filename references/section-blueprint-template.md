# 章节蓝图模板规范

> 面向 `generate_section_blueprints.py` 和 Step 7.2 的参考文档。定义 `writing_blueprints.json/md` 的标准格式、claim-evidence 映射规则、图表放置规范；Step 2 `section_blueprints.json` 是不可变结构基线。

## 章节蓝图标准格式

每节蓝图包含以下字段：

```markdown
### {section_number} {section_name}

**用途：** {一句话描述本节在论文论证链中的角色}

**预估篇幅：** {词数/段落数估计}

**关键声明：**
- {claim_1}
- {claim_2}
- ...

**证据映射：**
| claim_id | 声明 | claim_strength | required_evidence | 支撑证据 | evidence_anchor | downgrade_required |
|------|------|------|------|---------|------|------|
| C-001 | {claim_1} | background/trend/parameter/numeric_comparison/mechanism/novelty | {最低证据要求} | {evidence_refs} | {PDF/page/chunk/figure/table/panel/note} | false |

**建议图表位置：**
- {figure_1_placement}
- ...

**图表绑定：**
| claim_id | figure/table | panel | support_type | risk_flags |
|------|------|------|------|------|
| C-001 | Fig. 1 / Table 1 | a,b | direct/partial/contextual/not_supported | {risk_flags} |

**承上：** {与上一节的逻辑衔接}
**启下：** {引出下一节的过渡}
**期刊风格提示：**
- {style_note_1}
- ...
```

## Claim-Evidence 映射规则

每条 key claim 必须至少映射到一条证据：

| 证据类型 | 优先级 | 来源 | 示例 |
|---------|:---:|------|------|
| **直接数据** | 1 | 你自己实验/仿真的结果 | "5 kW 加热功率下温度降低 8.5°C" |
| **文献支撑** | 2 | 综述矩阵的可引用摘录 | "Kim (2023) 也观察到类似拐点" |
| **理论推导** | 3 | 公认的物理/数学定律 | "根据牛顿冷却定律..." |
| **基准对比** | 4 | baseline 方法的公开结果 | "比标准方案提升 12%" |

**红线：** 不接受无证据的声明。如果一条 claim 找不到任何证据支撑 → 要么补充证据，要么删除 claim。

### 句子强度与证据最低要求

| claim_strength | 最低证据要求 | 蓝图处理 |
|---|---|---|
| `background` | 综述、摘要、元数据可作为低风险支撑 | 可写背景，不写具体结论 |
| `trend` | 多篇文献或系统性证据 | 单篇支撑时标记 `risk_flags=single_source_trend` |
| `parameter` | PDF 原文、方法表、用户数据或标准文件 | 无锚点时不得写入强参数句 |
| `numeric_comparison` | 页码、图、表或数据文件 | 必须填 `evidence_anchor` |
| `mechanism` | 全文级证据，优先图表/实验/仿真 | 必须说明竞争机制或适用边界 |
| `novelty` | 检索覆盖和对比文献 | 无检索覆盖不得写“首次/创新” |

蓝图中 `downgrade_required=true` 的 claim 不能以强结论进入正文，只能保守表达、保留 `[待补证据: claim]`，或回退 Step 4/5/6 补证据。

## 图表放置规范

基于目标期刊风格画像和学科惯例：

| 章节 | 典型图表 | 格式要求 |
|------|---------|---------|
| 引言 | 研究动机示意图（可选） | 无需数据图，仅概念性 |
| 方法 | 系统架构图、算法流程图 | 矢量图（SVG/PDF），无需 TIFF |
| 实验 | 核心对比结果图、消融图 | 矢量图优先；热力图/散点图可 TIFF 600dpi |
| 讨论 | 深入分析图（可选） | 与实验图不同视角 |
| 结论 | 一般不放置新图 | — |

**图表自包含检查清单（用于 Step 7.14 生成图表时）：**
- [ ] 图题（caption）写全：什么实验 + 什么条件 + 什么观察 + 什么结论
- [ ] 坐标轴有标签 + 单位
- [ ] 颜色有图例
- [ ] 字体大小在最终尺寸下可读（≥6pt）
- [ ] 不使用仅靠颜色区分的元素（考虑色盲/黑白打印）

## 蓝图使用方式

在 Step 7 写作时，每开始一章：

1. 打开 `writing_blueprints.md`，找到对应章节；需要追溯 RQ 时通过 `source_lineage` 回查 Step 2 基线
2. 确认"关键声明"列表——这就是这章要传达的核心信息
3. 按"证据映射"列逐一检查——每条声明是否都有证据？
4. 参照"期刊风格提示"调整句长/语态/段落结构
5. 写完该章后，回到蓝图检查"启下"过渡是否确实写在了章末
