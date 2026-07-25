#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "..");
const source = path.join(root, "docs", "assets", "marketing", "marketing-kit.html");
const outputDir = path.join(root, "docs", "assets", "marketing");

function loadPlaywright() {
  try {
    return require("playwright");
  } catch (firstError) {
    const moduleRoot = process.env.CODEX_WORKSPACE_NODE_MODULES;
    if (!moduleRoot) {
      throw new Error(
        "Playwright is not installed. Install it locally or set CODEX_WORKSPACE_NODE_MODULES " +
        "to the bundled workspace node_modules directory."
      );
    }
    return require(path.join(moduleRoot, "playwright"));
  }
}

const assets = [
  { id: "wechat-long", filename: "more-paper-workflow-wechat-long.png", viewport: { width: 1200, height: 1200 } },
  { id: "slide-16x9", filename: "more-paper-workflow-slide-16x9.png", viewport: { width: 2048, height: 1200 } },
  { id: "bilingual-poster", filename: "more-paper-workflow-bilingual-poster.png", viewport: { width: 1200, height: 1200 } },
];

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });

try {
  for (const asset of assets) {
    const page = await browser.newPage({ viewport: asset.viewport, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(source).href, { waitUntil: "load" });
    await page.evaluate(async () => {
      if (document.fonts?.ready) await document.fonts.ready;
    });
    const locator = page.locator(`#${asset.id}`);
    await locator.screenshot({ path: path.join(outputDir, asset.filename), animations: "disabled" });
    const box = await locator.boundingBox();
    console.log(`${asset.filename}: ${Math.round(box.width)}x${Math.round(box.height)}`);
    await page.close();
  }
} finally {
  await browser.close();
}

fs.writeFileSync(
  path.join(outputDir, "export-manifest.json"),
  JSON.stringify({
    schema: "more-paper-workflow.marketing-kit.v1",
    source: "marketing-kit.html",
    generated_at: new Date().toISOString(),
    assets: assets.map(({ id, filename }) => ({ id, filename })),
  }, null, 2) + "\n",
  "utf8",
);
