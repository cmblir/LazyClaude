// Verify the live "today" widget on the Usage tab renders and updates.
import { chromium } from 'playwright';

const BASE = process.env.BASE || `http://127.0.0.1:${process.env.PORT || 19500}`;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));

  await page.goto(`${BASE}/#/usage`, { waitUntil: 'networkidle', timeout: 25000 });
  // Account-picker landing (shown on fresh browser contexts) — continue past it.
  const cont = page.locator('text=Continue').first();
  if (await cont.isVisible({ timeout: 3000 }).catch(() => false)) {
    await cont.click();
    await page.waitForTimeout(800);
    await page.evaluate(() => { location.hash = '#/usage'; });
  }
  await page.waitForSelector('#tdTotal', { timeout: 10000 });
  // First poll fires immediately from AFTER.usage — wait for cards to fill.
  await page.waitForFunction(
    () => document.getElementById('tdTotal').textContent !== '—',
    { timeout: 10000 },
  );

  const snap = await page.evaluate(() => ({
    total: document.getElementById('tdTotal').textContent,
    input: document.getElementById('tdIn').textContent,
    date: document.getElementById('tdDate').textContent,
    sessions: document.getElementById('tdSess').textContent,
    burn: document.getElementById('tdBurn').textContent,
    hourlyBars: document.querySelectorAll('#tdHourly > div').length,
    modelRows: document.getElementById('tdModels').children.length,
  }));
  console.log('widget:', JSON.stringify(snap, null, 2));

  if (snap.hourlyBars !== 24) throw new Error(`expected 24 hourly bars, got ${snap.hourlyBars}`);
  if (!snap.date.match(/^\d{4}-\d{2}-\d{2}$/)) throw new Error(`bad date: ${snap.date}`);

  // 320px mobile pass — widget must not overflow.
  await page.setViewportSize({ width: 320, height: 700 });
  await page.waitForTimeout(500);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  console.log('mobile overflow px:', overflow);

  await page.screenshot({ path: '/tmp/usage-today.png', fullPage: false });
  await browser.close();

  if (errors.length) {
    console.error('CONSOLE ERRORS:', errors.slice(0, 10));
    process.exit(1);
  }
  if (overflow > 2) {
    console.error(`mobile horizontal overflow: ${overflow}px`);
    process.exit(1);
  }
  console.log('E2E PASS');
})();
