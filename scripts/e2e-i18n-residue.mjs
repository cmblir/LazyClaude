// Runtime Korean-residue sweep: walk every tab in en/zh and collect text
// nodes + attributes that still contain Hangul after _translateDOM and the
// async fills have run. Complements tools/runtime_ko_scan.py, which only
// simulates the static index.html DOM — this catches app.js-rendered views
// and post-render JS writes (pollers, loaders).
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';

const BASE = process.env.BASE || `http://127.0.0.1:${process.env.PORT || 19500}`;
const LANGS = (process.env.LANGS || 'en,zh').split(',');
const SETTLE_MS = Number(process.env.SETTLE_MS || 1500);
const OUT = process.env.OUT || '/tmp/i18n-residue.json';

function readTabIds() {
  const src = readFileSync(new URL('../server/nav_catalog.py', import.meta.url), 'utf8');
  const idx = src.indexOf('TAB_CATALOG: list[tuple[');
  if (idx < 0) throw new Error('TAB_CATALOG not found');
  return [...src.slice(idx).matchAll(/^\s*\("([a-zA-Z][a-zA-Z0-9_]*)"\s*,/gm)].map(m => m[1]);
}

const tabIds = process.env.TAB_ID ? [process.env.TAB_ID] : readTabIds();
const findings = [];

const browser = await chromium.launch({ headless: true });
for (const lang of LANGS) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addCookies([{ name: 'cc-lang', value: lang, url: BASE }]);
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
  const cont = page.locator('text=Continue').first();
  if (await cont.isVisible({ timeout: 2500 }).catch(() => false)) {
    await cont.click();
    await page.waitForTimeout(600);
  }
  await page.waitForSelector('#nav', { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(500);

  for (const id of tabIds) {
    try {
      await page.evaluate(tid => { location.hash = '#/' + tid; }, id);
      await page.waitForTimeout(SETTLE_MS);
      const res = await page.evaluate(() => {
        const KO = /[가-힣]/;
        const out = [];
        const root = document.getElementById('view') || document.body;
        // data-no-i18n zones are user/remote content — intentionally Korean.
        const excluded = el => !!(el && el.closest && el.closest('[data-no-i18n]'));
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const t = (node.textContent || '').trim();
          if (t && KO.test(t) && !excluded(node.parentElement)) out.push({ kind: 'text', s: t.slice(0, 160) });
        }
        root.querySelectorAll('[placeholder],[title],[alt],[aria-label]').forEach(el => {
          if (excluded(el)) return;
          for (const a of ['placeholder', 'title', 'alt', 'aria-label']) {
            const v = el.getAttribute(a);
            if (v && KO.test(v)) out.push({ kind: 'attr:' + a, s: v.slice(0, 160) });
          }
        });
        return out;
      });
      for (const r of res) findings.push({ lang, tab: id, ...r });
      if (res.length) console.log(`  [${lang}] ${id}: ${res.length} residue`);
    } catch (e) {
      console.log(`  [${lang}] ${id}: ERROR ${e.message.slice(0, 80)}`);
    }
  }
  await ctx.close();
}
await browser.close();

const uniq = [...new Set(findings.map(f => f.s))];
writeFileSync(OUT, JSON.stringify({ findings, uniqueStrings: uniq }, null, 2));
console.log(`\ntotal: ${findings.length} findings, ${uniq.length} unique strings → ${OUT}`);
process.exit(0);
