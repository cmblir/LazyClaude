# 🦞 lazyclaw

[![npm](https://img.shields.io/npm/v/lazyclaw.svg)](https://www.npmjs.com/package/lazyclaw)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Node](https://img.shields.io/badge/node-%E2%89%A518-blue.svg)](https://nodejs.org/)

**A lazy, elegant terminal CLI for Claude / OpenAI / Gemini / Ollama.**

One Node CLI that talks to every major LLM provider, runs multi-step workflows as a DAG, exposes a local HTTP gateway, and ships with the niceties you actually want at the prompt: an ASCII banner on launch, Cursor-style slash-command ghost autocomplete (right-arrow accepts), persistent chat sessions, and cost rate cards.

> Part of the [LazyClaude](https://github.com/cmblir/LazyClaude) project — published standalone so you can `npm i -g lazyclaw` without cloning the dashboard.

---

## Install

```bash
npm install -g lazyclaw
lazyclaw version
```

Requires **Node 18+**. Works on macOS / Linux / WSL. Windows native PowerShell mostly works but the ghost-text + ANSI banner are TTY-gated and may fall back to plain prompts.

## First run

```bash
lazyclaw onboard         # arrow-key picker; defaults to claude-cli (no key)
lazyclaw status          # current provider/model + masked key
lazyclaw doctor          # validate config + provider registry
```

`onboard` writes `~/.lazyclaw/config.json`. Move it with `LAZYCLAW_CONFIG_DIR=/elsewhere`. For automation: `--non-interactive --provider X --model Y [--api-key Z]`.

### Subscription mode (no API key)

If you already have **Claude Code** installed and signed in (Pro / Max / Team subscription), pick the **`claude-cli`** provider during onboard. lazyclaw shells out to the local `claude` binary, so requests bill against your existing subscription quota instead of pay-per-token API credit. No `sk-ant-` key needed.

```bash
lazyclaw onboard --non-interactive --provider claude-cli --model claude-opus-4-7
lazyclaw status
# → { provider: "claude-cli", model: "claude-opus-4-7", hasApiKey: false }
```

Same flow for `ollama` (local models, also keyless).

### Pay-per-token mode (API key)

Pick `anthropic` / `openai` / `gemini` and supply the matching key:

```bash
lazyclaw onboard --non-interactive --provider openai \
  --model gpt-4.1 --api-key sk-...
```

`onboard` only prompts for an api-key when the picked provider's `requiresApiKey` is true (the picker labels each row `[subscription]` / `[api key]` / `[no key]` so the choice is explicit).

### Built-in OpenAI-compatible vendors

Eight popular OpenAI-compatible services ship as first-class providers — pick one in the setup picker (no `+ Add custom` walkthrough needed) or set the matching environment variable and they Just Work:

| Provider | Models include | Env var |
|---|---|---|
| `nim`        | `meta/llama-3.1-405b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`, `deepseek-ai/deepseek-r1`, `mistralai/mixtral-8x22b-instruct-v0.1` | `NVIDIA_API_KEY` (or `NIM_API_KEY`) |
| `openrouter` | `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `meta-llama/llama-3.1-405b-instruct`, `deepseek/deepseek-r1` | `OPENROUTER_API_KEY` |
| `groq`       | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`, `deepseek-r1-distill-llama-70b` | `GROQ_API_KEY` |
| `together`   | `meta-llama/Llama-3.3-70B-Instruct-Turbo`, `Qwen/Qwen2.5-72B-Instruct-Turbo`, `deepseek-ai/DeepSeek-V3` | `TOGETHER_API_KEY` |
| `xai`        | `grok-2-latest`, `grok-2-vision-1212` | `XAI_API_KEY` (or `GROK_API_KEY`) |
| `deepseek`   | `deepseek-chat`, `deepseek-reasoner` | `DEEPSEEK_API_KEY` |
| `mistral`    | `mistral-large-latest`, `codestral-latest`, `pixtral-large-latest` | `MISTRAL_API_KEY` |
| `fireworks`  | `accounts/fireworks/models/llama-v3p3-70b-instruct`, `…/deepseek-r1` | `FIREWORKS_API_KEY` |

```bash
# NVIDIA NIM via env var — no `lazyclaw onboard` needed
export NVIDIA_API_KEY=nvapi-...
lazyclaw chat --provider nim --model meta/llama-3.1-405b-instruct

# Or commit the choice to ~/.lazyclaw/config.json
lazyclaw onboard --non-interactive --provider nim \
  --model nvidia/llama-3.1-nemotron-70b-instruct --api-key nvapi-...
```

Need a vendor that's **not** built-in? `+ Add a custom OpenAI-compatible endpoint…` inside the setup picker (or `lazyclaw providers add <name> --base-url <url>`) still works for vLLM / LM Studio / private gateways / anything else that speaks the OpenAI v1 wire format.

## Launcher (no-arg `lazyclaw`)

Running `lazyclaw` with no subcommand drops into an arrow-key launcher with every subcommand laid out as a menu. Navigation:

| Key | What it does |
|---|---|
| `↑` / `↓` / `Home` / `End` / `PgUp` / `PgDn` | Move the selection |
| `Enter` | Run the highlighted item |
| `q` / `Esc` / `Ctrl-C` | Leave lazyclaw |
| `/` | Open an inline slash-command prompt |

Slash commands at the launcher (typed after `/`):

| Slash | What it does |
|---|---|
| `/exit` / `/quit` | Leave lazyclaw |
| `/help` | List launcher slash commands inline |
| `/version` | Print version + node + platform |

The slash buffer lives just below the menu — backspace edits it, deleting past `/` returns to menu mode, and `Esc` cancels slash mode without leaving lazyclaw.

## Interactive chat

```bash
lazyclaw chat                      # banner + active provider/model + REPL
lazyclaw chat --pick               # arrow-key picker before the prompt
lazyclaw chat --session daily      # persist turns to ~/.lazyclaw/sessions/daily.jsonl
lazyclaw chat --skill review,style # compose named skills as the system prompt
```

What you see on launch (TTY only):

```text
  ╭──────────────────────────────╮
  │   _                          │
  │  | |__ _ _____  _ _          │
  │  | / _` |_ / || | '_|         │
  │  |_\__,_/__\_, |_|            │
  │  LazyClaw  |__/  3.99.11     │
  ╰──────────────────────────────╯

  provider · anthropic
  model    · claude-opus-4-7
  slash    · /help · /model · /provider · /exit
  hint     · → to accept the suggested command, Tab to cycle

›
```

Slash commands inside the REPL:

| Slash | What it does |
|---|---|
| `/help` | List slash commands |
| `/status` | Print provider + model + masked key |
| `/provider` | Open the family / provider / model arrow picker |
| `/provider X` | Switch active provider directly by name |
| `/model` | Open the per-provider model picker (type-filter + live `/v1/models` fetch) |
| `/model X` | Switch model directly. Accepts unified `provider/model` form |
| `/skill a,b` | Replace the system prompt with a composition of named skills |
| `/usage` | Message count + chars + cumulative token totals |
| `/new` / `/reset` | Wipe history and start over |
| `/exit` | Leave the chat REPL (returns to the launcher when chat was opened from it) |

**Cursor-style ghost autocomplete**: type `/` and the longest matching slash command appears in dim grey after the cursor. **`→`** accepts; **`Tab`** cycles. **Ctrl-C** during a streaming reply aborts that turn (not the whole process); **Ctrl-C** at an empty prompt exits.

## One-shot (no REPL)

```bash
lazyclaw agent "summarize: $(cat file.md)"
lazyclaw agent - < prompt.txt                 # stdin
lazyclaw agent "..." --provider openai --model gpt-4.1
lazyclaw agent "..." --skill review           # compose system prompt
lazyclaw agent "..." --usage                  # token counts on stderr
lazyclaw agent "..." --cost                   # USD when rates configured
```

## Providers / sessions / skills

```bash
lazyclaw providers list                       # all registered providers
lazyclaw providers info anthropic
lazyclaw providers test anthropic             # 1-token reachability probe

lazyclaw sessions list                        # persisted chats
lazyclaw sessions show daily
lazyclaw sessions search "deploy"
lazyclaw sessions export daily > daily.md
lazyclaw sessions clear daily

lazyclaw skills list                          # markdown skill bundles
lazyclaw skills show review
lazyclaw skills install ./my-skill.md
lazyclaw skills remove review
```

## Workflows (DAG / sequential / persistent)

```bash
lazyclaw run my-job ./flow.mjs                              # sequential, resumable
lazyclaw run my-job ./flow.mjs --parallel --concurrency 4   # in-memory DAG
lazyclaw run my-job ./flow.mjs --parallel-persistent        # DAG + checkpoints
lazyclaw resume my-job ./flow.mjs                           # resume a stalled run

lazyclaw inspect                                            # list every session
lazyclaw inspect my-job --summary
lazyclaw inspect my-job --critical-path ./flow.mjs          # bottleneck finder
lazyclaw inspect my-job --slowest 5
```

State at `./.workflow-state/<id>/` (override with `LAZYCLAW_WORKFLOW_STATE_DIR=...`).

## Local HTTP gateway

```bash
lazyclaw daemon                               # bind a free port; prints { port, url }
lazyclaw daemon --port 19600
lazyclaw daemon --auth-token $(openssl rand -hex 16)
lazyclaw daemon --rate-limit 60 --log info    # 60 req/min/IP, JSON access logs
lazyclaw daemon --once                        # serve a single request, then exit
```

## Cost rate cards

```bash
lazyclaw rates list
lazyclaw rates set anthropic/claude-opus-4-7 \
  --in 15 --out 75 --cache-read 1.5 --cache-create 18.75
lazyclaw rates copy anthropic/claude-opus-4-7 anthropic/claude-opus-4-6
lazyclaw rates delete openai/gpt-3.5-turbo
lazyclaw rates validate
```

`/usage` and `--cost` use these to compute USD totals locally — no provider call.

## Config + bundles

```bash
lazyclaw config path                          # → ~/.lazyclaw/config.json
lazyclaw config get provider
lazyclaw config set provider openai
lazyclaw config list
lazyclaw config edit                          # opens $EDITOR
lazyclaw config validate

lazyclaw export > backup.json                 # config + skills (+ optional sessions)
lazyclaw import --from backup.json
```

## Shell completion

```bash
lazyclaw completion bash >> ~/.bashrc
lazyclaw completion zsh  >> ~/.zshrc
```

## File locations

| Path | Purpose |
|---|---|
| `~/.lazyclaw/config.json` | provider, model, api-key, skills, rates |
| `~/.lazyclaw/sessions/*.jsonl` | persisted chat sessions |
| `~/.lazyclaw/skills/*.md` | installed skill bundles |
| `./.workflow-state/<id>/` | per-session workflow checkpoints (cwd-relative) |

`LAZYCLAW_CONFIG_DIR=...` moves the first three; `LAZYCLAW_WORKFLOW_STATE_DIR=...` moves the last.

---

## Issues / contributing

Source lives in [cmblir/LazyClaude](https://github.com/cmblir/LazyClaude) under [`src/lazyclaw/`](https://github.com/cmblir/LazyClaude/tree/main/src/lazyclaw). Issues and PRs welcome on the parent repo.

## License

[MIT](./LICENSE)
