# Step 7 遮挡缺口回归实例

这是可重复生成的合成测试实例，不冒充论文实验数据。原始连续曲线中部被图例
遮挡；`observations.csv` 保留证据缺口，`data.csv` 的正式断点为 0，solid / dashed /
dashdot 三种重绘共享完全相同的正式数据哈希。

```bash
python examples/figure_data_pipeline/build_example.py
```

关键证据：

- `source-occluded.png` 与 `spec/spec-review.png`
- `candidates.csv → observations.csv → data.csv`
- `review-decisions.json` 与 `data.provenance.json`
- `visualspec-solid.json`、`visualspec-dashed.json`、`visualspec-dashdot.json`
- `render-solid/render.png`（连续实线）、另两种样式的 PNG/SVG/PDF
- `evidence-summary.json`（证据缺口、正式断点、数据哈希和验收状态）
