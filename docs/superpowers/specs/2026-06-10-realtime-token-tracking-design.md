# Real-time token usage tracking — design

Date: 2026-06-10
Status: approved (user, 2026-06-10)

## Problem

Today's token usage never shows up in the Usage tab. Two stacked causes:

1. **Boot-only indexing.** `background_index()` runs once at server start
   (`server.py`). Sessions created or extended after boot are invisible until
   restart or a manual `/api/sessions/reindex`.
2. **Start-day attribution.** The daily timeline buckets a session's *entire*
   token total to `started_at` day (`server/system.py:194`). A session that
   started yesterday and is still running today credits all of today's tokens
   to yesterday. There is no per-turn timestamped usage record (only
   `tool_uses.turn_tokens`, which misses tool-less turns).

## Approach (selected)

Incremental tail parser + per-turn usage events + "today" widget. Rejected
alternatives: periodic full reindex only (keeps wrong day attribution,
re-parses large active files), SSE push ticker (extra complexity for little
felt difference over 5 s polling).

## Design

### Data model (`server/db.py`)

```sql
CREATE TABLE IF NOT EXISTS usage_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  ts INTEGER,            -- message timestamp, epoch ms
  model TEXT,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0
);
CREATE INDEX idx_usage_ts ON usage_events(ts);
CREATE INDEX idx_usage_session ON usage_events(session_id);

CREATE TABLE IF NOT EXISTS jsonl_offsets (
  jsonl_path TEXT PRIMARY KEY,
  session_id TEXT,
  offset INTEGER DEFAULT 0,  -- bytes consumed
  mtime INTEGER DEFAULT 0    -- file mtime at last consume, epoch ms
);
```

One `usage_events` row per assistant message that carries non-zero `usage`.

### Indexer changes (`server/sessions.py`)

- `_index_jsonl` switches to binary line iteration and counts consumed bytes.
  On upsert it now also: deletes + reinserts the session's `usage_events`,
  and upserts `jsonl_offsets` with the consumed byte offset. Full reindex and
  tail parser therefore stay mutually consistent (full parse resets the tail
  cursor to end-of-parsed-bytes).
- A module-level `INDEX_LOCK` (`threading.Lock`) serializes `_index_jsonl`
  and tail cycles so boot-time full indexing and the tailer never double-write
  the same bytes.

### Tail parser (`server/usage_live.py`, new module)

Daemon thread, 5 s cycle, started from `server.py` via `start_usage_tailer()`:

1. Load `jsonl_offsets` map; scan `PROJECTS_DIR/*/*.jsonl`.
2. Per file: skip when `size == offset` and `mtime` unchanged.
   - **No offset row**: file mtime within last 48 h → full `_index_jsonl`
     (backfills events); older → write `offset = size` *without* events
     (history before feature install is not backfilled; bounded one-time cost).
   - **`size < offset`** (rewrite/truncation): full `_index_jsonl` re-parse.
   - **`size > offset`**: open binary, `seek(offset)`, parse only complete
     appended lines (a trailing partial line is left for the next cycle).
     Insert `usage_events`, then incrementally `UPDATE sessions SET
     input_tokens = input_tokens + ?, …, total_tokens = total_tokens + ?,
     ended_at = MAX(ended_at, ?)` and advance the offset row.
3. The tailer does **not** bump `sessions.mtime`, so the boot-time full
   reindex still refreshes message counts / scores / tool rows later;
   token columns stay live in the meantime.
4. Unknown session (no `sessions` row): full `_index_jsonl`.

### API (`server/routes.py`)

`GET /api/usage/today` → `usage_live.api_usage_today()`. Local-midnight
window over `usage_events`:

- totals: input / output / cache-read / cache-create / total, event count,
  active session count
- `hourly`: 24 local-hour buckets
- `byModel`: per-model totals
- `topSessions`: top 5 sessions today (joined with `sessions` for prompt/project)
- `burnRate`: tokens over the last 5 minutes (per-minute rate)
- `lastEventTs`

### Frontend (`dist/app.js`)

New "오늘 실시간" section at the top of `VIEWS.usage`: 4 total cards +
hourly CSS bar chart + per-model rows + burn rate. `AFTER.usage` starts a 5 s
`setInterval` poll of `/api/usage/today` that updates the section in place and
clears itself when the view unmounts (existing `pollTimer` conventions).
All user-visible strings go through `t('한국어')`; EN/ZH added to a new
`tools/translations_manual_48.py`.

### Out of scope

- Rewriting the existing 30-day `dailyTimeline` to event-based attribution
  (stays `started_at`-based).
- Cost (USD) estimation for usage events.
- SSE push.

## Verification

- In-process smoke: temp `CLAUDE_DASHBOARD_DB` + fake `PROJECTS_DIR`; append
  assistant lines to a fake session JSONL, run one tail cycle, assert
  `usage_events` rows + `sessions` token sums + offset advance; append more,
  re-run, assert no duplicates; truncate file, assert re-parse.
- `/api/usage/today` returns correct totals for the fake data.
- Playwright: usage tab renders the today section without console errors.
- `make i18n-verify` reports 0 missing.
