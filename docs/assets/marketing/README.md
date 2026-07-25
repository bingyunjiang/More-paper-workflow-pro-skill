# more-paper-workflow 宣传视觉资产

本目录包含基于当前 Step 1–8、direct-entry、Checkpoint 和 Completion Gate 契约制作的宣传视觉。

## 资产清单

- `more-paper-workflow-wechat-long.png`：公众号长图，1080 × 3200。
- `more-paper-workflow-slide-16x9.png`：16:9 演示页，1920 × 1080。
- `more-paper-workflow-bilingual-poster.png`：中英双语海报，1080 × 1440。
- `marketing-kit.html`：三张视觉的可编辑 HTML/CSS 源文件。
- `export-manifest.json`：导出清单。
- `social-carousel.html`：朋友圈八图的可编辑 HTML/CSS 源文件。
- `social-carousel/social-01.png` 至 `social-08.png`：朋友圈发布图组，单张 1080 × 1440。
- `social-carousel/social-contact-sheet.png`：八图总览联系表。

## 重新导出

需要 Node.js 和 Playwright：

```bash
node scripts/export_marketing_kit.mjs
```

在 Codex Desktop bundled runtime 中可显式指定依赖目录：

```bash
CODEX_WORKSPACE_NODE_MODULES=/path/to/workspace/node_modules \
node scripts/export_marketing_kit.mjs
```

朋友圈八图重新导出：

```bash
CODEX_WORKSPACE_NODE_MODULES=/path/to/workspace/node_modules \
node scripts/export_social_carousel.mjs
```

## 朋友圈发布顺序

按文件名顺序上传 `social-01.png` 至 `social-08.png`：

1. 封面钩子：从研究问题到可核验论文。
2. 用户痛点：论文真正难在证据链。
3. 八步全景：三阶段、八个 Step。
4. Phase A：研究设计。
5. Phase B：证据获取与管理。
6. Phase C：写作、图表和终验。
7. Direct Entry：已有材料可直接进入。
8. 质量门与开始提示词。

建议朋友圈配文：

> 最近把自己在用的学术论文工作流重新整理成了 `more-paper-workflow`：从定题、检索、PDF、Zotero，到证据化写作、科研图表、引用审计和保守润色。它不是让 AI 一键生成论文，而是让每一步的证据、风险和交付状态都能回查。已有 DOI、PDF、文库或草稿，也可以从对应 Step 直接开始。项目地址见最后一张。

宣传内容不得加入未经当前仓库验证的成功率、脚本数量、出版社数量或平台绕过能力声明。
