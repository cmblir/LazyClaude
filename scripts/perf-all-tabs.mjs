#!/usr/bin/env node
/**
 * Walk every tab in nav_catalog.py and sample longtasks for ~600ms after
 * navigation. Sort by total scripting time so the worst remaining lag
 * sources surface at the top.
 */
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';

const BASE = process.env.BASE || `http://127.0.0.1:${process.env.PORT || 8080}`;

function readTabIds() {
  const src = readFileSync(new URL('../server/nav_catalog.py', import.meta.url), 'utf8');
  const idx = src.indexOf('TAB_CATALOG: list[tuple[');
  if (idx < 0) throw new Error('TAB_CATALOG not found');
  return [...src.slice(idx).matchAll(/^\s*\("([a-zA-Z][a-zA-Z0-9_]*)"\s*,/gm)].map(m => m[1]);
}
const tabs = readTabIds();
console.log(`📊 profiling ${tabs.length} tabs`);

const browser = await chromium.launch({ headless: process.env.HEADLESS !== '0' });
const page = await (await browser.newContext({ viewport: { width: 1400, height: 900 } })).newPage();
await page.addInitScript(() => {
  window.__perfTasks = [];
  try {
    new PerformanceObserver(l => {
      for (const e of l.getEntries()) window.__perfTasks.push(e.duration);
    }).observe({ type: 'longtask', buffered: true });
  } catch (_) {}
});
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(400);

const results = [];
for (const tab of tabs) {
  await page.evaluate(() => { window.__perfTasks = []; });
  const t0 = Date.now();
  await page.evaluate(t => location.hash = '#/' + t, tab);
  await page.waitForFunction(t => state && state.view === t, tab, { timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(600);
  const r = await page.evaluate(() => ({ tasks: window.__perfTasks.slice() }));
  const total = r.tasks.reduce((s, x) => s + x, 0);
  const longest = r.tasks.length ? Math.max(...r.tasks) : 0;
  results.push({ tab, count: r.tasks.length, total, longest, elapsed: Date.now() - t0 });
}
await browser.close();

results.sort((a, b) => b.total - a.total);
console.log('\n#tab                       longtasks  total(ms)  longest(ms)');
console.log('—'.repeat(72));
for (const r of results.slice(0, 20)) {
  console.log(
    r.tab.padEnd(25),
    String(r.count).padStart(8),
    String(r.total.toFixed(0)).padStart(10),
    String(r.longest.toFixed(0)).padStart(11)
  );
}
const totalLong = results.reduce((s, r) => s + r.total, 0);
const heavy = results.filter(r => r.longest >= 100).length;
console.log(`\nsummary: ${heavy} tabs with longest ≥ 100ms · sum total = ${totalLong.toFixed(0)}ms across ${tabs.length} tabs`);
