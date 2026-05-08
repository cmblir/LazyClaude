// Sandbox — wrap a child process in a Docker container.
//
// `lazyclaw chat --sandbox docker:<image>` (or the equivalent on
// `agent`) routes the underlying `claude` CLI invocation through
//
//   docker run --rm -i --network=<net> \
//              -v <cwd>:<cwd> -w <cwd> \
//              -e <pass-through env vars> \
//              <image> claude -p ...
//
// instead of running `claude` directly on the host. Two reasons:
//
// 1. Filesystem confinement. The default --workdir mount only
//    exposes the current working directory; tools that try to
//    chdir into $HOME or read /etc see an empty container fs.
// 2. Network policy. By default we set --network=none so the
//    sandboxed agent cannot reach the public internet — useful
//    when handing it untrusted prompts. Pass `--network host` /
//    `bridge` via flags when the workflow needs outbound access
//    (e.g. it has to call an API).
//
// Caveats — call out so users aren't surprised:
//
// - The user's `claude` login lives in $HOME/.claude/. The sandbox
//   doesn't expose $HOME by default, so the wrapped CLI can't see
//   that auth and will prompt for login. To run sandboxed under
//   the user's existing subscription, mount $HOME/.claude:
//
//     lazyclaw chat --sandbox docker:node:20 \
//                   --sandbox-mount "$HOME/.claude:/root/.claude:ro"
//
// - Sandboxing only applies when the picked provider goes through
//   a subprocess (currently `claude-cli`). API providers
//   (anthropic / openai / gemini) hit the network from
//   *lazyclaw's* process, not a child — sandboxing them is a
//   no-op and we surface a warning.

import { spawn } from 'node:child_process';

class SandboxError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'SandboxError';
    this.code = code || 'SANDBOX_ERR';
  }
}

/**
 * Parse a `--sandbox` flag. Accepts:
 *   docker:<image>           — Docker with default policy
 *   docker:<image>?<args>     — query-string-style overrides
 *   off | none | -            — explicit "no sandbox"
 *
 * Returns null when sandboxing is off, or
 * { kind: 'docker', image, network, mounts: string[], envPassthrough: string[] }.
 */
export function parseSandboxSpec(spec, flags = {}) {
  if (!spec || /^(off|none|-)$/i.test(String(spec))) return null;
  const m = String(spec).match(/^([a-z]+):(.+)$/i);
  if (!m) throw new SandboxError(`bad sandbox spec "${spec}" — expected "docker:<image>"`, 'SANDBOX_BAD_SPEC');
  const [, kind, rest] = m;
  if (kind.toLowerCase() !== 'docker') {
    throw new SandboxError(`unsupported sandbox kind "${kind}" — only "docker" is implemented`, 'SANDBOX_UNSUPPORTED');
  }
  return {
    kind: 'docker',
    image: rest.trim(),
    // Default to --network=none for safety. Override via:
    //   --sandbox-network host   (or bridge / a named network)
    network: flags['sandbox-network'] || 'none',
    // --sandbox-mount can repeat; cli.parseArgs collects repeats
    // into an array.
    mounts: arrayify(flags['sandbox-mount']),
    envPassthrough: arrayify(flags['sandbox-env']),
  };
}

function arrayify(v) {
  if (v === undefined || v === null) return [];
  return Array.isArray(v) ? v : [String(v)];
}

/**
 * Build the docker run argv that wraps a child invocation. The
 * caller hands us the original [bin, ...args] they were going to
 * spawn; we return [docker, ...dockerArgs] that puts the same
 * thing inside the container.
 */
export function buildDockerArgs(spec, [bin, ...binArgs], opts = {}) {
  if (!spec || spec.kind !== 'docker') {
    throw new SandboxError('buildDockerArgs requires a docker spec', 'SANDBOX_BAD_SPEC');
  }
  const cwd = opts.cwd || process.cwd();
  const args = [
    'run', '--rm', '-i',
    '--network', spec.network || 'none',
    '-v', `${cwd}:${cwd}`,
    '-w', cwd,
  ];
  for (const mount of spec.mounts) {
    if (!mount.includes(':')) {
      throw new SandboxError(`bad mount "${mount}" — expected host:container[:mode]`, 'SANDBOX_BAD_MOUNT');
    }
    args.push('-v', mount);
  }
  for (const envName of spec.envPassthrough) {
    args.push('-e', envName);
  }
  args.push(spec.image, bin, ...binArgs);
  return args;
}

/**
 * Spawn `bin` with `args` either bare (no sandbox) or under the
 * docker wrapper. Returns the child process; the caller drives
 * stdio and handles exit. Mirrors `child_process.spawn`'s shape.
 */
export function spawnSandboxed(spec, bin, args, spawnOpts = {}) {
  if (!spec) return spawn(bin, args, spawnOpts);
  if (spec.kind !== 'docker') {
    throw new SandboxError(`unsupported kind "${spec.kind}"`, 'SANDBOX_UNSUPPORTED');
  }
  const dockerArgs = buildDockerArgs(spec, [bin, ...args], { cwd: spawnOpts.cwd });
  return spawn('docker', dockerArgs, spawnOpts);
}

export { SandboxError };
