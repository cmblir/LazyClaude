#!/usr/bin/env node
/**
 * E2E for /delegate and /parallel chat slash commands.
 *
 * The v3.67 verify script only checked that the slash returns
 * `true` (handled by the dispatcher). This script verifies the full
 * round-trip:
 *   1. The slash posts to the correct backend endpoint with the
 *      expected body.
 *   2. A placeholder bubble appears immediately.
 *   3. The placeholder body updates with the mocked response after
 *      the API resolves.
 *   4. /parallel renders one section per assignee with the correct
 *      header.
 */
import { chromium } from 'playwright';

const URL = process.env.URL || `http://127.0.0.1:${process.env.PORT || 8080}/`;
let exitCode = 0;
function check(label, ok, detail) {
  const tag = ok ? '\x1b[32m✅\x1b[0m' : '\x1b[31m❌\x1b[0m';
  console.log(`${tag} ${label}${detail ? ' — ' + detail : ''}`);
  if (!ok) exitCode = 1;
}

const browser = await chromium.launch({ headless: process.env.HEADLESS !== '0' });
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await ctx.newPage();

const consoleErrs = [];
page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text()); });
page.on('pageerror', e => consoleErrs.push('[pageerror] ' + e.message));

// ── Mocks ──
let chatPostBody = null;
await page.route('**/api/lazyclaw/chat', async (route) => {
  if (route.request().method() === 'POST') {
    chatPostBody = JSON.parse(route.request().postData() || '{}');
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true, output: 'mocked delegate output',
      provider: 'mock', model: 'mock-1',
      durationMs: 42,
    }),
  });
});

let comparePostBody = null;
await page.route('**/api/ai-providers/compare', async (route) => {
  if (route.request().method() === 'POST') {
    comparePostBody = JSON.parse(route.request().postData() || '{}');
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      results: [
        { providerId: 'mockA', model: 'mA', status: 'ok', output: 'parallel reply A', duration_ms: 33 },
        { providerId: 'mockB', model: 'mB', status: 'ok', output: 'parallel reply B', duration_ms: 47 },
      ],
    }),
  });
});

await page.goto(URL, { waitUntil: 'networkidle' });

// Seed an empty session so /delegate has a clean canvas.
await page.evaluate(() => {
  _lcSaveSessions([{ id: 'e2e-del', label: 'e2e', ts: Date.now(), preview: '' }]);
  _lcSaveHistory('e2e-del', []);
  _lcSetCurrentId('e2e-del');
});
await page.evaluate(() => window.go && window.go('lazyclawChat'));
await page.waitForSelector('#lcChatInput', { timeout: 8000 });

// ── /delegate ──
const delResult = await page.evaluate(async () => {
  return await _lcChatSlashCommand('/delegate fakeProvider:fakeModel build a sample greeting');
});
check('/delegate handler returns true', delResult === true, `r=${delResult}`);

// Wait for the placeholder bubble to appear (sync render after slash)
await page.waitForFunction(() => {
  const log = document.getElementById('lcChatLog');
  return log && log.children.length >= 2;
}, { timeout: 4000 });
const afterDispatch = await page.evaluate(() => {
  const log = document.getElementById('lcChatLog');
  return {
    bubbles: log ? log.children.length : 0,
    bodies: Array.from(log ? log.querySelectorAll('.lc-msg-body-host') : []).map(b => b.textContent.trim().slice(0, 60)),
  };
});
check('two bubbles after /delegate (user note + assistant placeholder)',
  afterDispatch.bubbles >= 2,
  `bubbles=${afterDispatch.bubbles}`);

// Wait for the placeholder to be filled with the mocked response.
await page.waitForFunction(() => {
  const log = document.getElementById('lcChatLog');
  if (!log || log.children.length < 2) return false;
  const last = log.lastElementChild;
  const body = last && last.querySelector('.lc-msg-body-host');
  return body && /mocked delegate output/.test(body.textContent || '');
}, { timeout: 4000 });
check('/delegate response replaces placeholder', true, '');

check('/delegate posted with expected body fields',
  chatPostBody && chatPostBody.assignee === 'fakeProvider:fakeModel'
   && chatPostBody.message === 'build a sample greeting',
  `body=${JSON.stringify(chatPostBody || {}).slice(0, 120)}`);

// ── /parallel ──
chatPostBody = null;
const parResult = await page.evaluate(async () => {
  return await _lcChatSlashCommand('/parallel mockA:mA,mockB:mB make a haiku about commits');
});
check('/parallel handler returns true', parResult === true, `r=${parResult}`);

await page.waitForFunction(() => {
  const log = document.getElementById('lcChatLog');
  if (!log) return false;
  const last = log.lastElementChild;
  const body = last && last.querySelector('.lc-msg-body-host');
  // Body should now contain both mock results' headers + outputs.
  if (!body) return false;
  const txt = body.textContent || '';
  return /mockA/.test(txt) && /mockB/.test(txt) && /parallel reply A/.test(txt) && /parallel reply B/.test(txt);
}, { timeout: 4000 });
check('/parallel renders both assignee outputs in one bubble', true, '');

check('/parallel posted with both targets + the task',
  comparePostBody && comparePostBody.prompt === 'make a haiku about commits'
   && Array.isArray(comparePostBody.providers)
   && comparePostBody.providers.length === 2
   && comparePostBody.providers[0].providerId === 'mockA'
   && comparePostBody.providers[1].providerId === 'mockB',
  `body=${JSON.stringify(comparePostBody || {}).slice(0, 160)}`);

if (consoleErrs.length) {
  console.log('\nconsole errors during run:');
  for (const e of consoleErrs.slice(0, 5)) console.log('  ', e);
  exitCode = 1;
}

await browser.close();
console.log(exitCode === 0 ? '\nOK' : '\nFAIL');
process.exit(exitCode);
