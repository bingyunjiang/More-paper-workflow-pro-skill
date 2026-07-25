#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "..");
const source = path.join(root, "docs", "assets", "marketing", "social-carousel.html");
const outputDir = path.join(root, "docs", "assets", "marketing", "social-carousel");
fs.mkdirSync(outputDir, { recursive: true });

function loadPackage(name) {
  try { return require(name); }
  catch {
    const moduleRoot = process.env.CODEX_WORKSPACE_NODE_MODULES;
    if (!moduleRoot) throw new Error(`Missing ${name}; set CODEX_WORKSPACE_NODE_MODULES.`);
    return require(path.join(moduleRoot, name));
  }
}

const { chromium } = loadPackage("playwright");
const sharp = loadPackage("sharp");
const browser = await chromium.launch({ headless: true });
const outputs = [];

try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 1500 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(source).href, { waitUntil: "load" });
  await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready; });

  for (let index = 1; index <= 8; index += 1) {
    const id = `social-${String(index).padStart(2, "0")}`;
    const filename = `${id}.png`;
    await page.locator(`#${id}`).screenshot({ path: path.join(outputDir, filename), animations: "disabled" });
    outputs.push(filename);
    console.log(`${filename}: 1080x1440`);
  }
  await page.close();
} finally {
  await browser.close();
}

const thumbWidth = 270;
const thumbHeight = 360;
const composites = [];
for (let index = 0; index < outputs.length; index += 1) {
  const buffer = await sharp(path.join(outputDir, outputs[index])).resize(thumbWidth, thumbHeight).png().toBuffer();
  composites.push({ input: buffer, left: (index % 4) * thumbWidth, top: Math.floor(index / 4) * thumbHeight });
}
await sharp({ create: { width: 1080, height: 720, channels: 3, background: "#101713" } })
  .composite(composites)
  .png()
  .toFile(path.join(outputDir, "social-contact-sheet.png"));

fs.writeFileSync(path.join(outputDir, "manifest.json"), JSON.stringify({
  schema: "more-paper-workflow.social-carousel.v1",
  source: "../social-carousel.html",
  dimensions: { width: 1080, height: 1440 },
  order: outputs,
  contact_sheet: "social-contact-sheet.png",
}, null, 2) + "\n");
