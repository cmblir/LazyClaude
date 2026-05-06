#!/usr/bin/env node
/**
 * v3.70 verification:
 *   - lazyclaude completion bash|zsh prints a shell script (no shell exec)
 *   - lazyclaude daemon probe runs without breaking
 *   - lazyclaude onboard navigates to onboarding tab
 *   - testProvider on a missing provider surfaces error_key + translated msg
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
const page = await (await browser.newContext({ viewport: { width: 1400, height: 900 } })).newPage();
await page.goto(URL, { waitUntil: 'networkidle' });

// 1. completion verb
// Defeat the once-an-hour auto-healthcheck so it doesn't shell out and
// race with our injected commands.
await page.evaluate(() => {
  try {
    localStorage.setItem('cc.lazyclawTerm.healthCheckedAt', String(Date.now()));
    localStorage.setItem('cc.lazyclawTerm.log', JSON.stringify([]));
  } catch (_) {}
});
await page.evaluate(() => window.go && window.go('lazyclawTerm'));
await page.waitForSelector('#lcTermInput', { timeout: 8000 });
await page.waitForFunction(() => window.CC_PREFS && window.CC_PREFS_SCHEMA, { timeout: 8000 }).catch(() => {});
let shellHits = 0;
page.on('request', req => { if (req.url().includes('/api/lazyclaw/term')) shellHits++; });

await page.evaluate(async () => {
  document.getElementById('lcTermInput').value = 'lazyclaude completion bash';
  await window._lcTermRun();
});
await page.waitForTimeout(400);
let termText = await page.evaluate(() => document.getElementById('lcTermLog').textContent || '');
check('completion bash prints script', /complete -F _lazyclaw_completion lazyclaw/.test(termText),
  'has bash completion line');

await page.evaluate(async () => {
  document.getElementById('lcTermInput').value = 'lazyclaude completion zsh';
  await window._lcTermRun();
});
await page.waitForTimeout(400);
termText = await page.evaluate(() => document.getElementById('lcTermLog').textContent || '');
check('completion zsh prints compdef', /compdef _lazyclaw lazyclaw/.test(termText),
  'has zsh compdef line');

// 2. daemon probe
await page.evaluate(async () => {
  document.getElementById('lcTermInput').value = 'lazyclaude daemon';
  await window._lcTermRun();
});
await page.waitForTimeout(2000);
termText = await page.evaluate(() => document.getElementById('lcTermLog').textContent || '');
check('daemon probe outputs port lines', /:3737|:3838/.test(termText),
  'mentions probed ports');

check('all 3 verbs stay client-side', shellHits === 0, `shellHits=${shellHits}`);

// 3. onboard navigates
await page.evaluate(async () => {
  document.getElementById('lcTermInput').value = 'lazyclaude onboard';
  await window._lcTermRun();
});
await page.waitForTimeout(800);
const view = await page.evaluate(() => state.view);
check('onboard navigates to onboarding', view === 'onboarding', `view=${view}`);

// 4. testProvider surfaces error_key
await page.goto(URL, { waitUntil: 'networkidle' });
const testResult = await page.evaluate(async () => {
  const r = await fetch('/api/ai-providers/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ providerId: 'definitely-not-real' }),
  });
  return await r.json();
});
check('testProvider returns error_key for unknown', testResult.error_key === 'err_provider_unknown',
  `error_key=${testResult.error_key}`);

await browser.close();
console.log(exitCode === 0 ? '\nOK' : '\nFAIL');
process.exit(exitCode);
