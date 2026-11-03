// Turn the demo print pages (site/print/*.html) into PDFs (site/pdf/*.pdf) with headless Chromium.
// Usage: node scripts/make_pdfs.js   (needs the `playwright` npm package + a Chromium)
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const root = path.join(__dirname, "..", "site");
  const src = path.join(root, "print");
  const out = path.join(root, "pdf");
  fs.mkdirSync(out, { recursive: true });
  const files = fs.readdirSync(src).filter((f) => f.endsWith(".html"));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const f of files) {
    await page.goto("file://" + path.join(src, f));
    await page.pdf({ path: path.join(out, f.replace(/\.html$/, ".pdf")), format: "A4", printBackground: true,
      margin: { top: "12mm", bottom: "12mm", left: "12mm", right: "12mm" } });
  }
  await browser.close();
  console.log(`made ${files.length} PDFs in ${out}`);
})().catch((e) => { console.error(e); process.exit(1); });
