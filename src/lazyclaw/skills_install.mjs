// Remote skill installer.
//
// Resolves an OpenClaw-style spec into a set of locally-installed
// skills:
//
//   lazyclaw skills install <user>/<repo>           — main branch
//   lazyclaw skills install <user>/<repo>@<ref>     — branch / tag / sha
//   lazyclaw skills install <user>/<repo>@<ref>:<path>
//                                                    — only files under <path>
//
// The "registry" is just GitHub. `lazyclaw skills install
// anthropic-skills/code-review@v1.2` fetches the tarball at
//   https://codeload.github.com/anthropic-skills/code-review/tar.gz/v1.2
// and installs every `.md` it finds at the repo root and under
// `skills/` (or under the explicit subpath after the colon).
//
// Why GitHub directly instead of a hosted ClawHub: zero new
// infrastructure, the public-pasteable URL is what users already
// share, and tag pinning is reproducible.
//
// We deliberately do NOT auto-execute anything — skills are .md
// files whose content goes into the LLM's system prompt. No code
// runs. The worst-case ingest is "the prompt makes the model
// behave oddly", which is recoverable by `lazyclaw skills remove`.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { Readable } from 'node:stream';

const GITHUB_SPEC = /^([\w.-]+)\/([\w.-]+)(?:@([^:]+))?(?::(.+))?$/;
const SKILL_EXT = '.md';
const MAX_TARBALL_BYTES = 16 * 1024 * 1024; // 16 MiB
const FETCH_TIMEOUT_MS = 30_000;

export class SkillInstallError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'SkillInstallError';
    this.code = code || 'SKILL_INSTALL_ERR';
  }
}

export function parseGithubSpec(spec) {
  const m = String(spec || '').match(GITHUB_SPEC);
  if (!m) return null;
  const [, owner, repo, ref, subpath] = m;
  return {
    owner,
    repo,
    ref: ref || 'main',
    subpath: subpath ? normaliseSubpath(subpath) : '',
  };
}

function normaliseSubpath(p) {
  // Refuse absolute paths and `..` components — the extracted
  // archive is treated as untrusted and we never want to walk
  // outside it.
  const s = String(p || '').replace(/^\.?\//, '').replace(/\\/g, '/');
  if (path.isAbsolute(s) || s.split('/').includes('..')) {
    throw new SkillInstallError(`bad subpath "${p}"`, 'SKILL_BAD_SUBPATH');
  }
  return s;
}

export function tarballUrl({ owner, repo, ref }) {
  return `https://codeload.github.com/${owner}/${repo}/tar.gz/${encodeURIComponent(ref)}`;
}

/**
 * Download + extract a GitHub tarball into <tmpdir>/<random>/.
 * Returns the absolute path of the extracted top-level directory
 * (codeload puts everything under <repo>-<sha>/ so we follow that).
 */
export async function fetchAndExtract(spec, opts = {}) {
  const fetchFn = opts.fetch || globalThis.fetch;
  if (!fetchFn) throw new SkillInstallError('no fetch implementation', 'SKILL_NO_FETCH');
  const url = tarballUrl(spec);
  const maxBytes = Number(opts.maxBytes) > 0 ? Number(opts.maxBytes) : MAX_TARBALL_BYTES;

  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(new Error(`timeout after ${FETCH_TIMEOUT_MS}ms`)), opts.timeoutMs || FETCH_TIMEOUT_MS);
  let res;
  try {
    res = await fetchFn(url, {
      headers: { 'user-agent': 'lazyclaw-skills/1.0' },
      redirect: 'follow',
      signal: ac.signal,
    });
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    throw new SkillInstallError(`fetch ${url} → ${res.status}`, 'SKILL_FETCH_FAIL');
  }

  // Stream the tarball into a temp dir using the system `tar` binary.
  // Cheaper than pulling a Node tar dependency, and `tar` is on PATH
  // wherever lazyclaw runs (macOS / Linux / WSL / modern Windows).
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lazyclaw-skill-'));
  const child = spawn('tar', ['-xz', '-C', tmp], {
    stdio: ['pipe', 'inherit', 'pipe'],
  });
  let stderrBuf = '';
  child.stderr.on('data', (chunk) => { stderrBuf += chunk; });

  // Cap how much we'll feed into tar so a malicious upstream can't
  // exhaust disk. Counts the gzipped bytes; uncompressed could be
  // 10× larger but skill bundles are typically << 1 MB compressed.
  let total = 0;
  const exited = new Promise((resolve, reject) => {
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) reject(new SkillInstallError(`tar exited ${code}: ${stderrBuf.slice(0, 300)}`, 'SKILL_TAR_FAIL'));
      else resolve();
    });
  });

  // Convert the WHATWG ReadableStream from `fetch` to a Node Readable
  // and pipe to tar. Node 18+ exposes the conversion natively.
  const nodeStream = res.body && typeof res.body.getReader === 'function'
    ? Readable.fromWeb(res.body)
    : res.body;
  if (!nodeStream || typeof nodeStream.on !== 'function') {
    child.stdin.end();
    await exited.catch(() => {});
    fs.rmSync(tmp, { recursive: true, force: true });
    throw new SkillInstallError('tarball body is not a stream', 'SKILL_BAD_BODY');
  }
  await new Promise((resolve, reject) => {
    nodeStream.on('data', (chunk) => {
      total += chunk.length;
      if (total > maxBytes) {
        nodeStream.destroy(new SkillInstallError(`tarball exceeds ${maxBytes} bytes (override with --max-bytes)`, 'SKILL_TOO_BIG'));
        return;
      }
      if (!child.stdin.write(chunk)) nodeStream.pause();
    });
    child.stdin.on('drain', () => nodeStream.resume());
    nodeStream.on('error', reject);
    nodeStream.on('end', () => { child.stdin.end(); resolve(); });
  });
  await exited;

  // codeload tarballs always have a single top-level dir named
  // <repo>-<sha-or-ref>/. Find it.
  const entries = fs.readdirSync(tmp);
  const top = entries.find((n) => fs.statSync(path.join(tmp, n)).isDirectory());
  if (!top) {
    fs.rmSync(tmp, { recursive: true, force: true });
    throw new SkillInstallError('extracted archive is empty', 'SKILL_EMPTY');
  }
  return { tmpRoot: tmp, extracted: path.join(tmp, top) };
}

/**
 * Walk an extracted repo and pick the .md files that look like
 * skills. Heuristic:
 *   - if a `skills/` directory exists at the root, only files
 *     under there count
 *   - else, .md files at the repo root only (one level deep)
 *   - if `subpath` is set in the spec, that wins absolutely —
 *     all .md under spec.subpath are eligible
 */
export function pickSkillFiles(extractedRoot, subpath = '') {
  const root = subpath ? path.join(extractedRoot, subpath) : extractedRoot;
  if (!fs.existsSync(root)) return [];
  if (subpath) return collectMd(root, root, /* recurse */ true);
  const skillsDir = path.join(extractedRoot, 'skills');
  if (fs.existsSync(skillsDir)) return collectMd(skillsDir, skillsDir, true);
  // Fallback: top-level only — README is the only meaningful .md
  // most repos ship at the root, and that usually IS the skill.
  return collectMd(extractedRoot, extractedRoot, false);
}

function collectMd(dir, baseRoot, recurse) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (recurse) out.push(...collectMd(full, baseRoot, true));
      continue;
    }
    if (!entry.isFile()) continue;
    if (!entry.name.toLowerCase().endsWith(SKILL_EXT)) continue;
    out.push({ relative: path.relative(baseRoot, full), abs: full });
  }
  return out.sort((a, b) => a.relative.localeCompare(b.relative));
}

/**
 * Install every picked skill into <configDir>/skills/<name>.md.
 * Default name: file basename without .md, lower-cased, slashes
 * replaced with `-`. `--prefix foo/` prepends `foo-` to every
 * installed name so a multi-skill repo doesn't clobber adjacent
 * locally-managed skills.
 *
 * Skips files that already exist unless `force` is true.
 */
export function installPickedSkills(picked, configDir, opts = {}) {
  const skillsRoot = path.join(configDir, 'skills');
  fs.mkdirSync(skillsRoot, { recursive: true });
  const installed = [];
  const skipped = [];
  for (const f of picked) {
    const base = path.basename(f.relative, SKILL_EXT).toLowerCase();
    const safe = base.replace(/[^a-z0-9_.-]+/g, '-');
    const name = (opts.prefix ? opts.prefix.replace(/[^a-z0-9_.-]+/g, '-') + '-' : '') + safe;
    const dst = path.join(skillsRoot, name + SKILL_EXT);
    if (fs.existsSync(dst) && !opts.force) {
      skipped.push({ name, reason: 'exists', dst });
      continue;
    }
    fs.copyFileSync(f.abs, dst);
    installed.push({ name, src: f.relative, dst, bytes: fs.statSync(dst).size });
  }
  return { installed, skipped };
}

export async function installFromGithub(spec, configDir, opts = {}) {
  const parsed = typeof spec === 'string' ? parseGithubSpec(spec) : spec;
  if (!parsed) throw new SkillInstallError(`bad spec — expected user/repo[@ref][:path]`, 'SKILL_BAD_SPEC');
  const { tmpRoot, extracted } = await fetchAndExtract(parsed, opts);
  try {
    const picked = pickSkillFiles(extracted, parsed.subpath);
    if (!picked.length) {
      throw new SkillInstallError(
        `no .md skills found in ${parsed.owner}/${parsed.repo}@${parsed.ref}${parsed.subpath ? ':' + parsed.subpath : ''}`,
        'SKILL_NONE_FOUND'
      );
    }
    const r = installPickedSkills(picked, configDir, opts);
    return { spec: parsed, ...r };
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
}
