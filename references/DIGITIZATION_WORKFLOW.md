# 图片数据提取与重绘协议（Step 7）

仅当用户明确要求数字化或重绘时使用；默认仍优先插入论文 PDF/MinerU
原图，并保留 `figure_transform_authorization=explicit_user_request` 门禁。

## 唯一正式数据链

```text
原始图/PDF → 来源锁定 → spec-review 规格叠图 → 用户确认规格
→ candidates.csv → 自动质量评估与异常诊断 → review-decisions.json
→ observations.csv → 正式 data.csv → VisualSpec → PNG/SVG/PDF → validate/QA
```

### 工件职责

- `candidates.csv`：算法候选，`extraction_status=candidate_ready`、
  `review_status=not_reviewed`；不能进入 VisualSpec、正文数值或正式交付。
- `observations.csv`：只含复核接受的可见像素观测，保留原始像素坐标、
  数据坐标、候选编号、不确定度、来源哈希、复核动作和
  `evidence_segment_break_before`。虚线空白、遮挡、JPEG 缺色都是证据缺口，
  不自动代表物理断裂。
- `data.csv`：唯一正式重绘数据；样式无关。每行保留曲线顺序、来源、
  原证据缺口和 `formal_segment_break_before`。只有用户确认的
  `curve_topology=segmented` 可以产生正式断点；`continuous` 必须保持正式连续。
- `VisualSpec`：只能由正式 `data.csv` 构建，并绑定其 SHA-256 和完整血缘。
  `line_style / color / line_width_pt / marker` 只控制渲染。

## 规格确认门

```bash
python scripts/figure_evidence_pipeline.py inspect \
  --input source.png --chart-type line --output-project figure-project.json

python scripts/figure_evidence_pipeline.py spec-review \
  --project figure-project.json \
  --plot-bounds 40,20,620,420 \
  --x-anchor 40,0 --x-anchor 620,100 \
  --y-anchor 420,0 --y-anchor 20,1 \
  --series response=#cc2244 \
  --series-topology response=continuous \
  --exclude-region 460,30,610,95 \
  --output-dir digitized/spec
```

必须同时展示 `spec-review-report.json.source_measurement_raster` 指向的原始
测量栅格与 `spec-review.png`。用户确认绘图区、轴锚点、系列语义、曲线拓扑和
排除区后，才写入哈希绑定的确认记录：

```bash
python scripts/figure_evidence_pipeline.py confirm-spec \
  --project figure-project.json \
  --spec digitized/spec/figure-spec.json \
  --overlay digitized/spec/spec-review.png \
  --confirmation explicit_user_confirmation \
  --output digitized/spec/spec-confirmation.json
```

原图、项目规格、`figure-spec.json` 或叠图任一哈希变化，确认自动失效。

## 候选提取与复核

保留原命令名，但 `extract-*` 只生成候选和自动质量报告：

```bash
python scripts/figure_evidence_pipeline.py extract-line \
  --project figure-project.json \
  --spec-confirmation digitized/spec/spec-confirmation.json \
  --plot-bounds 40,20,620,420 \
  --x-anchor 40,0 --x-anchor 620,100 \
  --y-anchor 420,0 --y-anchor 20,1 \
  --series response=#cc2244 \
  --output-dir digitized

python scripts/figure_evidence_pipeline.py init-review \
  --candidates digitized/candidates.csv \
  --quality digitized/quality-assessment.json \
  --spec-confirmation digitized/spec/spec-confirmation.json \
  --output digitized/review-decisions.json
```

Agent 先完成质量阈值、缺口长度、顺序/数值异常诊断和安全重提取；普通候选在
无异常时可由用户回复“继续/下一步”批量接受。异常候选必须逐项
`accept / reject / correct / reassign`，不要求用户逐点检查全部普通候选。
每条系列拓扑还必须 `confirmed_by_user=true`。

```bash
python scripts/figure_evidence_pipeline.py build-observations \
  --candidates digitized/candidates.csv \
  --quality digitized/quality-assessment.json \
  --review-decisions digitized/review-decisions.json \
  --output digitized/observations.csv
```

## 正式数据、VisualSpec 与重绘

```bash
python scripts/figure_evidence_pipeline.py build-data \
  --observations digitized/observations.csv \
  --review-decisions digitized/review-decisions.json \
  --output digitized/data.csv \
  --provenance digitized/data.provenance.json

python scripts/figure_evidence_pipeline.py build-visualspec \
  --data digitized/data.csv \
  --provenance digitized/data.provenance.json \
  --styles digitized/styles.json \
  --output digitized/visualspec.json

python scripts/run_reproduction.py \
  --spec digitized/visualspec.json --source source.png \
  --out-dir digitized/bundle --require-strict \
  --transform-authorization explicit_user_request
```

`styles.json` 只改变线色、`solid/dashed/dashdot/dotted`、粗细和 marker。
更换样式前后必须复核 `data.csv` 的 SHA-256、行数、字节顺序、坐标和正式断点
完全不变。

## `curve_data_mode`

- `observations`：正式数据由复核观测形成；连续曲线直接连接相邻正式数据行，
  证据缺口只留在证据字段中。
- `guide_constrained`：若用户确认需要根据引导路径形成稠密数据，必须把
  `guide_path_sha256` 写入 `review-decisions.json`，使用 `build-data --guide-path`
  将派生点、最近可见观测残差、方法和哈希血缘写入 `data.csv` 与 provenance。

渲染阶段禁止重新读取原图颜色、guided path、插值或桥接缺口；禁止只修
PNG/SVG；禁止 display-only bridge；禁止把 `digitized_lines.csv` 当正式数据。

## 旧输入迁移

```bash
python scripts/figure_evidence_pipeline.py migrate-legacy \
  --legacy digitized_lines.csv \
  --source-sha256 <source_sha256> --spec-sha256 <spec_sha256> \
  --output candidates.csv
```

迁移结果固定为 `candidate_only_not_reviewed`，必须重新走质量评估、复核、
observations 和 data 构建链。

## 状态与验收

分别维护 `extraction_status / review_status / render_status /
delivery_status`。重绘成功不得提升提取或复核状态。缺少完整
`review-decisions.json` 不得生成 `data.csv`；缺少正式 `data.csv` 不得生成
数字化 VisualSpec；未复核结果只能称 candidate/not reviewed。

最终运行：

```bash
python scripts/figure_evidence_pipeline.py validate-data-chain \
  --candidates digitized/candidates.csv \
  --observations digitized/observations.csv \
  --review-decisions digitized/review-decisions.json \
  --data digitized/data.csv --provenance digitized/data.provenance.json \
  --visualspec digitized/visualspec.json \
  --render-manifest digitized/render/render_manifest.json
```

当前原生候选提取器覆盖彩色折线、紧凑实心散点和竖向纯色柱/直方图；
本协议的连续/分段曲线正式构建与回归重点针对折线。直接 PDF 矢量恢复、
复杂交叉同色曲线、误差带和三维图仍需独立、通用且经过测试的提取器。
