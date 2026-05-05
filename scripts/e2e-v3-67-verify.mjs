#!/usr/bin/env node
/**
 * v3.67 verification — covers:
 *   - lazyclawDashboard view renders without errors
 *   - /delegate, /parallel slash commands handled (return true)
 *   - lazyclaude agents/sessions/skills/doctor verbs handled
 *   - saveDefaultModel hits the right backend endpoint (default persisted)
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
const consoleErrs = [];
page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text()); });
page.on('pageerror', e => consoleErrs.push('[pageerror] ' + e.message));

await page.goto(URL, { waitUntil: 'networkidle' });

// 1. Dashboard view
await page.evaluate(() => window.go && window.go('lazyclawDashboard'));
await page.waitForTimeout(900);
const dashAlive = await page.evaluate(() => state && state.view === 'lazyclawDashboard');
const dashHasTiles = await page.evaluate(() => {
  const v = document.querySelector('#view');
  return !!v && /LazyClaw 대시보드|LazyClaw Dashboard/.test(v.textContent || '');
});
check('lazyclawDashboard renders', dashAlive && dashHasTiles, `view=${dashAlive} text=${dashHasTiles}`);

// 2. Slash commands /delegate and /parallel are handled (return true)
await page.evaluate(() => window.go && window.go('lazyclawChat'));
await page.waitForSelector('#lcChatInput', { timeout: 8000 });
await page.evaluate(() => { window.confirm = () => true; });

const delResult = await page.evaluate(async () => {
  return await _lcChatSlashCommand('/delegate claude:opus hello');
});
check('/delegate handled', delResult === true, `r=${delResult}`);

const parResult = await page.evaluate(async () => {
  return await _lcChatSlashCommand('/parallel claude:opus,ollama:llama3.1 hello');
});
check('/parallel handled', parResult === true, `r=${parResult}`);

// 3. Terminal verbs agents/sessions/skills/doctor handled (no shell exec)
await page.evaluate(() => window.go && window.go('lazyclawTerm'));
await page.waitForSelector('#lcTermInput', { timeout: 8000 });
await page.waitForFunction(() => window.CC_PREFS && window.CC_PREFS_SCHEMA, { timeout: 8000 }).catch(() => {});
// Wait for the auto-healthcheck to finish (it shells out internally).
await page.waitForFunction(() => {
  const log = document.getElementById('lcTermLog');
  if (!log) return false;
  const t = log.textContent || '';
  return /헬스체크 완료|Healthcheck complete|Health check complete/.test(t) || log.children.length === 0;
}, { timeout: 12000 }).catch(() => {});
let shellHits = 0;
page.on('request', req => { if (req.url().includes('/api/lazyclaw/term')) shellHits++; });

// agents/sessions/skills hit JSON APIs — never the shell whitelist.
// `doctor` legitimately shells out (it's the diag healthcheck); excluded
// from the no-shell expectation.
for (const verb of ['agents', 'sessions', 'skills']) {
  await page.evaluate(async (cmd) => {
    const inp = document.getElementById('lcTermInput');
    inp.value = cmd;
    await window._lcTermRun();
  }, `lazyclaude ${verb}`);
  await page.waitForTimeout(400);
}
check('agents/sessions/skills stay client-side', shellHits === 0, `shellHits=${shellHits}`);

// `doctor` should produce some output and remain alive.
await page.evaluate(async () => {
  const inp = document.getElementById('lcTermInput');
  inp.value = 'lazyclaude doctor';
  await window._lcTermRun();
});
await page.waitForTimeout(800);
const docAlive = await page.evaluate(() => !!document.getElementById('lcTermInput'));
check('doctor runs without breaking the term DOM', docAlive, `alive=${docAlive}`);

// 4. saveDefaultModel hits /api/ai-providers/default-model (not save-key)
let defaultModelHit = 0;
let saveKeyHit = 0;
await page.route('**/api/ai-providers/default-model', async (route) => { defaultModelHit++; await route.continue(); });
await page.route('**/api/ai-providers/save-key', async (route) => { saveKeyHit++; await route.continue(); });
await page.evaluate(async () => {
  await window.saveDefaultModel('claude-cli', 'claude-sonnet-4-6');
});
await page.waitForTimeout(500);
check('saveDefaultModel routes to default-model endpoint', defaultModelHit === 1 && saveKeyHit === 0,
  `defaultModelHit=${defaultModelHit} saveKeyHit=${saveKeyHit}`);

// Verify backend persisted it
const persisted = await page.evaluate(async () => {
  // bypass the cached version
  const r = await fetch('/api/ai-providers/list?_=' + Date.now());
  const j = await r.json();
  const p = (j.providers || []).find(x => x.id === 'claude-cli');
  return { defaultModel: p && p.defaultModel, isDefault: (p.models || []).some(m => m.isDefault && m.id === 'claude-sonnet-4-6') };
});
check('default model persists + flagged', persisted.defaultModel === 'claude-sonnet-4-6' && persisted.isDefault,
  `defaultModel=${persisted.defaultModel} flag=${persisted.isDefault}`);

if (consoleErrs.length) {
  console.log('\nconsole errors:');
  for (const e of consoleErrs.slice(0, 10)) console.log('  ', e);
}

await browser.close();
console.log(exitCode === 0 ? '\nOK' : '\nFAIL');
process.exit(exitCode);
