#!/usr/bin/env node
/**
 * Workflow node-failure surface E2E.
 *
 * Build a 3-node workflow whose middle HTTP node points at 127.0.0.1
 * (blocked by the SSRF guard — fails fast, no network round-trip).
 * Run it. Assert:
 *   - Run reaches `err` status (not stuck running, not silently `ok`).
 *   - The HTTP node has `status: 'err'` plus a non-empty `error` string.
 *   - The downstream `output` node is either also `err` (sibling cancel)
 *     or skipped — but never silently `ok` against an empty input.
 *   - /api/workflows/runs cross-listing surfaces the failed run with
 *     `status === 'err'`.
 */
const PORT = process.env.PORT || 8080;
const BASE = process.env.BASE || `http://127.0.0.1:${PORT}`;

let exitCode = 0;
function check(label, ok, detail) {
  const tag = ok ? '\x1b[32m✅\x1b[0m' : '\x1b[31m❌\x1b[0m';
  console.log(`${tag} ${label}${detail ? ' — ' + detail : ''}`);
  if (!ok) exitCode = 1;
}
async function jpost(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  return r.json();
}
async function jget(path) { return (await fetch(BASE + path)).json(); }

const wf = {
  name: 'e2e-fail-http',
  description: 'Triggers SSRF guard on the http node so we can verify the failure surface',
  nodes: [
    { id: 'n-start',  type: 'start', title: 'Start', x: 80, y: 80, data: {} },
    {
      id: 'n-http', type: 'http', title: 'HTTP (blocked)',
      x: 320, y: 80,
      data: {
        // 127.0.0.1 is in _HTTP_BLOCKED_HOSTS → SSRF guard rejects immediately.
        url: 'http://127.0.0.1:1/ping',
        method: 'GET',
        headers: {},
        body: '',
        allowInternal: false,
      },
    },
    { id: 'n-out', type: 'output', title: 'Out', x: 560, y: 80, data: {} },
  ],
  edges: [
    { id: 'e1', from: 'n-start', to: 'n-http' },
    { id: 'e2', from: 'n-http',  to: 'n-out'  },
  ],
};
const saveR = await jpost('/api/workflows/save', wf);
check('workflow saves', !!saveR.ok && !!saveR.id, JSON.stringify(saveR).slice(0, 200));
const wfId = saveR.id;

const runR = await jpost('/api/workflows/run', { id: wfId });
check('run starts', !!runR.ok && !!runR.runId, JSON.stringify(runR).slice(0, 200));
const runId = runR.runId;

let last;
const t0 = Date.now();
while (Date.now() - t0 < 8000) {
  last = await jget('/api/workflows/run-status?runId=' + encodeURIComponent(runId));
  if (last && last.run && (last.run.status === 'ok' || last.run.status === 'err')) break;
  await new Promise(r => setTimeout(r, 200));
}
const elapsed = Date.now() - t0;
const run = (last && last.run) || {};
check('run reaches terminal in 8s', run.status === 'ok' || run.status === 'err',
  `status=${run.status} elapsed=${elapsed}ms`);
check('run terminal status is err (not ok)', run.status === 'err', `status=${run.status}`);

const results = run.nodeResults || {};
const httpRes = results['n-http'];
check('http node ran err', httpRes && httpRes.status === 'err',
  `status=${httpRes && httpRes.status}`);
check('http node has non-empty error string',
  !!(httpRes && httpRes.error && httpRes.error.length > 0),
  `error=${httpRes && (httpRes.error || '').slice(0, 80)}`);
check('error mentions SSRF/blocked', !!(httpRes && /차단|blocked|SSRF|내부/.test(httpRes.error || '')),
  `error=${httpRes && (httpRes.error || '').slice(0, 60)}`);

// Downstream output node should NOT be silently `ok` — it should be err
// (sibling-cancel) or absent.
const outRes = results['n-out'];
check('downstream output is not silently ok',
  !outRes || outRes.status !== 'ok' || (outRes.output || '').length === 0,
  `outStatus=${outRes && outRes.status} outLen=${outRes && (outRes.output || '').length}`);

// Cross-workflow listing surfaces this failed run as err.
const list = await jget('/api/workflows/runs?limit=10');
const found = ((list && list.runs) || []).find(r => r.runId === runId);
check('failed run surfaces in /workflows/runs', !!found && found.status === 'err',
  `found=${!!found} status=${found && found.status}`);

await jpost('/api/workflows/delete', { id: wfId });
console.log(exitCode === 0 ? '\nOK' : '\nFAIL');
process.exit(exitCode);
