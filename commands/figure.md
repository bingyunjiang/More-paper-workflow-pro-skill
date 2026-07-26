# Figure

## 何时使用

- 从 CSV、实验数据或统计结果生成论文图表
- 重绘论文原图、截图、裁剪图或光栅曲线
- 做曲线数字化、视觉对齐、语义审计或矢量验证
- 生成带 manifest、QA、checksums 和可移植验证的复现包

## 自动路由

1. 只选择并插入已有 MinerU/PDF/论文原图时，默认 `not_applicable`，不启动绘图后端。
2. 只有用户明确要求基于可信结构化数据生成普通新图时，使用 `quick`。
3. 只有用户明确要求重绘或从图片/PDF恢复数值时，才进入 `reproduction`；恢复数值先运行 `figure_evidence_pipeline.py inspect`。
4. 当前原生数值提取候选路线包括彩色折线、紧凑实心散点、竖向纯色柱状图和直方图；其余图型必须返回 `recognized_not_implemented`、使用项目级实现，或保留人工确认状态。
5. 数字化必须先形成复核完成、拓扑明确、样式无关的正式 `data.csv`；只有由该文件构建的 VisualSpec 才能进入 `reproduction`。
6. 参考图片、截图或曲线的存在不等于重绘授权；记录 `figure_transform_authorization=explicit_user_request` 后才能运行绘图代码。
7. 用户显式指定 backend 时覆盖自动判断；严格后端缺依赖时必须失败，不得降级。

## 原图插入后的能力提醒

默认插入论文原图后，向用户提醒一次：

> 已按论文原图插入。本 skill 也支持图表重绘、曲线数字化、可编辑
> SVG/PDF 和严格 QA；如需启用，请明确指定要重绘的图及目标。

提醒不等于授权，不自动运行 `quick`、`figure_evidence_pipeline.py` 或
`reproduction`。

## 统一入口

```bash
python scripts/generate_figures.py --backend quick --spec figures.json --output figures
python scripts/figure_evidence_pipeline.py inspect --input source.png --chart-type line --output-project figure-project.json
python scripts/figure_evidence_pipeline.py spec-review --project figure-project.json --plot-bounds 40,20,620,420 --x-anchor 40,0 --x-anchor 620,100 --y-anchor 420,0 --y-anchor 20,1 --series response=#cc2244 --series-topology response=continuous --output-dir digitized/spec
python scripts/figure_evidence_pipeline.py confirm-spec --project figure-project.json --spec digitized/spec/figure-spec.json --overlay digitized/spec/spec-review.png --confirmation explicit_user_confirmation --output digitized/spec/spec-confirmation.json
python scripts/figure_evidence_pipeline.py extract-line --project figure-project.json --spec-confirmation digitized/spec/spec-confirmation.json --plot-bounds 40,20,620,420 --x-anchor 40,0 --x-anchor 620,100 --y-anchor 420,0 --y-anchor 20,1 --series response=#cc2244 --output-dir digitized
python scripts/figure_evidence_pipeline.py init-review --candidates digitized/candidates.csv --quality digitized/quality-assessment.json --spec-confirmation digitized/spec/spec-confirmation.json --output digitized/review-decisions.json
python scripts/figure_evidence_pipeline.py build-observations --candidates digitized/candidates.csv --quality digitized/quality-assessment.json --review-decisions digitized/review-decisions.json --output digitized/observations.csv
python scripts/figure_evidence_pipeline.py build-data --observations digitized/observations.csv --review-decisions digitized/review-decisions.json --output digitized/data.csv --provenance digitized/data.provenance.json
python scripts/figure_evidence_pipeline.py build-visualspec --data digitized/data.csv --provenance digitized/data.provenance.json --output digitized/visualspec.json
python scripts/generate_figures.py --backend reproduction --spec visualspec.json --source source.png --output bundle --require-strict --transform-authorization explicit_user_request
```

`extract-*` 只生成 `candidates.csv`、自动质量报告和观测叠图；不得生成
VisualSpec。普通候选可在无异常时经用户回复“继续/下一步”批量接受，异常候选
必须逐项处理。完整职责和状态门见数字化证据合同。

数字化证据合同见 `references/DIGITIZATION_WORKFLOW.md`；重绘与交付协议见 `references/scientific-figure-reproduction.md`。
