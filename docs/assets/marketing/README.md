# more-paper-workflow 宣传视觉资产

本目录包含基于当前 Step 1–8、direct-entry、Checkpoint 和 Completion Gate 契约制作的宣传视觉。

## 资产清单

- `more-paper-workflow-wechat-long.png`：公众号长图，1080 × 3200。
- `more-paper-workflow-slide-16x9.png`：16:9 演示页，1920 × 1080。
- `more-paper-workflow-bilingual-poster.png`：中英双语海报，1080 × 1440。
- `more-paper-workflow-x-bilingual.png`：X.com 横版双语发布图，1672 × 941。
- `x-carousel/x-01-cover.png` 至 `x-04-start.png`：X.com 首发四图组，单张 1672 × 941。
- `x-carousel/README.md`：四图发布顺序、双语主帖、回复文案和图片替代文本。
- `x-carousel-en/x-en-01-cover.png` 至 `x-en-04-start.png`：English-first X.com 四图组，英文为主要视觉层级。
- `x-carousel-en/README.md`：面向国际研究者和 GitHub 用户的英文主帖、回复文案与 ALT text。
- `more-paper-workflow-latest-update-8-card.png`：最近更新横版总览，融合朋友圈八图，1672 × 941。
- `marketing-kit.html`：三张视觉的可编辑 HTML/CSS 源文件。
- `export-manifest.json`：导出清单。
- `social-carousel.html`：朋友圈八图的可编辑 HTML/CSS 源文件。
- `social-carousel/social-01.png` 至 `social-08.png`：朋友圈发布图组，单张 1080 × 1440。
- `social-carousel/social-contact-sheet.png`：八图总览联系表。
- `social-nine-grid/grid-01-latest-update.png` 至 `grid-09-quality-gates.png`：朋友圈九图发布包，单张 1080 × 1440；上传顺序见目录内 `README.md`。
- `more-paper-workflow-social-nine-grid.zip`：九张发布图与顺序说明的打包文件。
- `v1.0.26-wechat-update/wechat-v1.0.26-update.png`：v1.0.23 至 v1.0.26 更新合辑朋友圈主图，1080 × 1440。

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

## X.com 双语发布文案

配图使用 `more-paper-workflow-x-bilingual.png`：

```text
Research question → verifiable paper.

An 8-step open workflow for search, PDFs, Zotero, evidence-based writing, citation audit, and revision.

从研究问题到可核验论文。任意步骤直达，证据边界不越界。

Open source ↓
https://github.com/bingyunjiang/more-paper-workflow

#AcademicWriting #OpenSource
```

宣传内容不得加入未经当前仓库验证的成功率、脚本数量、出版社数量或平台绕过能力声明。
