"""Exportable usage reports — feature #17.

Read-only report generation from the SQLite ``sessions`` index, priced with
the existing ``cost_timeline`` rate card (single source of truth — no pricing
is re-hardcoded here). Two public handlers:

- ``api_report_generate(query)`` → a self-contained **Markdown** report
  (period totals, daily trend table, top projects, by-model split, top
  sessions). Suitable for pasting into an issue / wiki / commit body.
- ``api_report_html(query)``     → the *same* numbers rendered as a
  **self-contained printable HTML page** (inline CSS, no external assets,
  print-friendly ``@media print`` block). The user saves/shares the file or
  uses the browser's *print → Save as PDF*.

PDF note: this server is pure-stdlib Python. The standard library has **no**
binary-PDF writer, so we deliberately do NOT emit a fake ``.pdf``. The honest
path to a PDF is browser print-to-PDF from the HTML report. ``meta.pdfNote``
in every response states this so the UI can surface it.

Everything is computed READ-ONLY: only ``SELECT`` statements run against the
sessions table. No writes, no schema changes.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import time
from typing import Any

from .cost_timeline import _PRICING, _estimate
from .db import _db, _db_init
from .logger import log


# ── period config ──────────────────────────────────────────────────────────
# started_at is stored in **milliseconds** (see server/sessions.py upsert).
_PERIODS: dict[str, dict[str, Any]] = {
    "week":  {"days": 7,  "labelKo": "최근 7일",  "labelEn": "Last 7 days"},
    "month": {"days": 30, "labelKo": "최근 30일", "labelEn": "Last 30 days"},
}

_PDF_NOTE = (
    "PDF는 서버에서 직접 생성하지 않습니다 (순수 stdlib 한계 — 바이너리 PDF 라이브러리 없음). "
    "‘인쇄용 HTML 열기’ 후 브라우저의 인쇄 → PDF로 저장을 사용하세요."
)


def _norm_period(query: dict | None) -> str:
    q = query or {}
    raw = q.get("period")
    if isinstance(raw, list):  # parse_qs gives lists
        raw = raw[0] if raw else None
    p = (raw or "week").strip().lower()
    return p if p in _PERIODS else "week"


def _usd(n: float) -> str:
    """Currency string, locale-stable (we ship a fixed en-US $ format)."""
    return f"${n:,.2f}"


def _tokens(n: int) -> str:
    """Compact token count mirroring the frontend fmtTokens (k / M)."""
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        n = 0
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _clean_model(model: str | None) -> str:
    m = (model or "").strip()
    if not m or m == "<synthetic>":
        return "(unknown)"
    return m


def _priced_models() -> str:
    """Human-readable summary of the rate card actually used for estimates."""
    parts = []
    seen: set[tuple[float, float]] = set()
    for mid, p in _PRICING.items():
        key = (p["in"], p["out"])
        if key in seen:
            continue
        seen.add(key)
        parts.append(f"{mid} (${p['in']:g}/${p['out']:g} per Mtok)")
    return ", ".join(parts)


def _gather(period: str) -> dict[str, Any]:
    """Run all read-only aggregations for the given period.

    Returns a plain dict the Markdown/HTML renderers both consume, so the two
    output formats can never drift.
    """
    _db_init()
    cfg = _PERIODS[period]
    days = cfg["days"]
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - days * 86_400_000

    total = {"sessions": 0, "in": 0, "out": 0, "cache_read": 0,
             "cache_creation": 0, "tokens": 0, "usd": 0.0}
    daily: dict[str, dict[str, Any]] = {}
    projects: dict[str, dict[str, Any]] = {}
    models: dict[str, dict[str, Any]] = {}
    top_sessions: list[dict[str, Any]] = []

    with _db() as c:
        rows = c.execute(
            "SELECT session_id, project, cwd, model, started_at, "
            "       input_tokens, output_tokens, cache_read_tokens, "
            "       cache_creation_tokens, total_tokens, first_user_prompt, score "
            "FROM sessions "
            "WHERE started_at IS NOT NULL AND started_at >= ? "
            "ORDER BY started_at DESC",
            (cutoff_ms,),
        ).fetchall()

        for r in rows:
            ti = int(r["input_tokens"] or 0)
            to = int(r["output_tokens"] or 0)
            cr = int(r["cache_read_tokens"] or 0)
            cc = int(r["cache_creation_tokens"] or 0)
            tt = int(r["total_tokens"] or 0) or (ti + to + cr + cc)
            model = _clean_model(r["model"])
            usd = _estimate(r["model"] or "", ti, to)

            total["sessions"] += 1
            total["in"] += ti
            total["out"] += to
            total["cache_read"] += cr
            total["cache_creation"] += cc
            total["tokens"] += tt
            total["usd"] += usd

            # daily bucket (local date of started_at)
            try:
                day = _dt.datetime.fromtimestamp(int(r["started_at"]) / 1000).date().isoformat()
            except Exception:
                day = "?"
            d = daily.setdefault(day, {"day": day, "sessions": 0, "tokens": 0, "usd": 0.0})
            d["sessions"] += 1
            d["tokens"] += tt
            d["usd"] += usd

            # by project
            pname = (r["project"] or r["cwd"] or "(unknown)").strip() or "(unknown)"
            pb = projects.setdefault(pname, {"project": pname, "sessions": 0, "tokens": 0, "usd": 0.0})
            pb["sessions"] += 1
            pb["tokens"] += tt
            pb["usd"] += usd

            # by model
            mb = models.setdefault(model, {"model": model, "sessions": 0,
                                           "in": 0, "out": 0, "tokens": 0, "usd": 0.0})
            mb["sessions"] += 1
            mb["in"] += ti
            mb["out"] += to
            mb["tokens"] += tt
            mb["usd"] += usd

            top_sessions.append({
                "sessionId": r["session_id"],
                "project": pname,
                "model": model,
                "tokens": tt,
                "usd": usd,
                "score": int(r["score"] or 0),
                "startedAt": int(r["started_at"] or 0),
                "prompt": (r["first_user_prompt"] or "").strip(),
            })

    # round currency once at the end
    total["usd"] = round(total["usd"], 4)
    daily_list = sorted(daily.values(), key=lambda x: x["day"])
    for d in daily_list:
        d["usd"] = round(d["usd"], 4)
    proj_list = sorted(projects.values(), key=lambda x: x["usd"], reverse=True)
    for p in proj_list:
        p["usd"] = round(p["usd"], 4)
    model_list = sorted(models.values(), key=lambda x: x["usd"], reverse=True)
    for m in model_list:
        m["usd"] = round(m["usd"], 4)
    top_sessions.sort(key=lambda s: s["tokens"], reverse=True)
    for s in top_sessions:
        s["usd"] = round(s["usd"], 4)

    return {
        "period": period,
        "labelKo": cfg["labelKo"],
        "labelEn": cfg["labelEn"],
        "days": days,
        "generatedAt": now_ms,
        "rangeFrom": cutoff_ms,
        "rangeTo": now_ms,
        "total": total,
        "daily": daily_list,
        "projects": proj_list[:15],
        "models": model_list,
        "topSessions": top_sessions[:15],
        "rateCard": _priced_models(),
    }


# ── Markdown rendering ───────────────────────────────────────────────────────
def _fmt_ts(ms: int) -> str:
    try:
        return _dt.datetime.fromtimestamp(int(ms) / 1000).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"


def _md(data: dict[str, Any]) -> str:
    t = data["total"]
    lines: list[str] = []
    a = lines.append

    a(f"# 사용량 리포트 — {data['labelKo']}")
    a("")
    a(f"- **생성 시각**: {_fmt_ts(data['generatedAt'])}")
    a(f"- **기간**: {_fmt_ts(data['rangeFrom'])} ~ {_fmt_ts(data['rangeTo'])} ({data['days']}일)")
    a(f"- **데이터 출처**: `~/.claude-dashboard.db` sessions 인덱스 (읽기 전용)")
    a(f"- **비용 추정 요금표**: {data['rateCard']}")
    a("")
    a("> 비용은 입력/출력 토큰 × 모델 요금으로 **추정**한 값입니다. 캐시 토큰은 합계에는 포함하지만 비용 추정에는 별도 단가를 적용하지 않습니다.")
    a("")

    a("## 기간 합계")
    a("")
    a("| 항목 | 값 |")
    a("|---|---|")
    a(f"| 세션 수 | {t['sessions']:,} |")
    a(f"| 입력 토큰 | {t['in']:,} |")
    a(f"| 출력 토큰 | {t['out']:,} |")
    a(f"| 캐시 읽기 토큰 | {t['cache_read']:,} |")
    a(f"| 캐시 생성 토큰 | {t['cache_creation']:,} |")
    a(f"| 총 토큰 | {t['tokens']:,} |")
    a(f"| 추정 비용 | {_usd(t['usd'])} |")
    a("")

    a("## 일별 추이")
    a("")
    if data["daily"]:
        a("| 날짜 | 세션 | 토큰 | 추정 비용 |")
        a("|---|---:|---:|---:|")
        for d in data["daily"]:
            a(f"| {d['day']} | {d['sessions']:,} | {d['tokens']:,} | {_usd(d['usd'])} |")
    else:
        a("_해당 기간에 기록된 세션이 없습니다._")
    a("")

    a("## 상위 프로젝트")
    a("")
    if data["projects"]:
        a("| 프로젝트 | 세션 | 토큰 | 추정 비용 |")
        a("|---|---:|---:|---:|")
        for p in data["projects"]:
            a(f"| {p['project']} | {p['sessions']:,} | {p['tokens']:,} | {_usd(p['usd'])} |")
    else:
        a("_데이터 없음._")
    a("")

    a("## 모델별 분포")
    a("")
    if data["models"]:
        a("| 모델 | 세션 | 입력 | 출력 | 총 토큰 | 추정 비용 |")
        a("|---|---:|---:|---:|---:|---:|")
        for m in data["models"]:
            a(f"| {m['model']} | {m['sessions']:,} | {m['in']:,} | {m['out']:,} | {m['tokens']:,} | {_usd(m['usd'])} |")
    else:
        a("_데이터 없음._")
    a("")

    a("## 상위 세션 (토큰 기준)")
    a("")
    if data["topSessions"]:
        a("| 시작 | 프로젝트 | 모델 | 토큰 | 추정 비용 | 점수 | 첫 프롬프트 |")
        a("|---|---|---|---:|---:|---:|---|")
        for s in data["topSessions"]:
            prompt = s["prompt"].replace("|", "\\|").replace("\n", " ")[:80]
            a(f"| {_fmt_ts(s['startedAt'])} | {s['project']} | {s['model']} | "
              f"{s['tokens']:,} | {_usd(s['usd'])} | {s['score']} | {prompt} |")
    else:
        a("_데이터 없음._")
    a("")

    a("---")
    a("")
    a(f"_{_PDF_NOTE}_")
    a("")
    return "\n".join(lines)


# ── HTML rendering (self-contained, printable) ───────────────────────────────
def _h(s: Any) -> str:
    return _html.escape(str(s if s is not None else ""))


def _rows(headers: list[str], aligns: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th style=\"text-align:{a}\">{_h(hd)}</th>" for hd, a in zip(headers, aligns))
    if not rows:
        body = f"<tr><td colspan=\"{len(headers)}\" class=\"empty\">데이터 없음</td></tr>"
    else:
        body = "".join(
            "<tr>" + "".join(
                f"<td style=\"text-align:{a}\">{cell}</td>" for cell, a in zip(r, aligns)
            ) + "</tr>"
            for r in rows
        )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def _html_doc(data: dict[str, Any]) -> str:
    t = data["total"]

    daily_rows = [[d["day"], f"{d['sessions']:,}", f"{d['tokens']:,}", _usd(d["usd"])]
                  for d in data["daily"]]
    proj_rows = [[_h(p["project"]), f"{p['sessions']:,}", f"{p['tokens']:,}", _usd(p["usd"])]
                 for p in data["projects"]]
    model_rows = [[_h(m["model"]), f"{m['sessions']:,}", f"{m['in']:,}", f"{m['out']:,}",
                   f"{m['tokens']:,}", _usd(m["usd"])]
                  for m in data["models"]]
    sess_rows = [[
        _fmt_ts(s["startedAt"]), _h(s["project"]), _h(s["model"]),
        f"{s['tokens']:,}", _usd(s["usd"]), str(s["score"]),
        _h(s["prompt"][:90]),
    ] for s in data["topSessions"]]

    # Simple inline bar chart for daily trend (no external Chart.js — must be
    # self-contained for save/share). Bars are scaled to the max daily token.
    max_tok = max((d["tokens"] for d in data["daily"]), default=0) or 1
    bars = "".join(
        f"<div class=\"bar-row\"><span class=\"bar-label\">{_h(d['day'][5:])}</span>"
        f"<span class=\"bar-track\"><span class=\"bar-fill\" "
        f"style=\"width:{max(2, round(d['tokens'] / max_tok * 100))}%\"></span></span>"
        f"<span class=\"bar-val\">{_tokens(d['tokens'])} · {_usd(d['usd'])}</span></div>"
        for d in data["daily"]
    ) or "<p class=\"empty\">해당 기간에 기록된 세션이 없습니다.</p>"

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>사용량 리포트 — {_h(data['labelKo'])}</title>
<style>
  :root {{ --fg:#1a1a1a; --mute:#666; --line:#e3e3e3; --accent:#d97757; --bg:#fff; --soft:#faf8f6; }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; padding:0; background:var(--bg); color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
    font-size:15px; line-height:1.55; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .wrap {{ max-width:920px; margin:0 auto; padding:2rem 1.25rem 4rem; }}
  header h1 {{ font-size:1.6rem; margin:0 0 .25rem; }}
  header .sub {{ color:var(--mute); font-size:.85rem; margin:0; }}
  .meta {{ background:var(--soft); border:1px solid var(--line); border-radius:10px;
    padding:.85rem 1rem; margin:1.25rem 0; font-size:.82rem; color:var(--mute); }}
  .meta b {{ color:var(--fg); }}
  .note {{ border-left:3px solid var(--accent); padding:.5rem .8rem; margin:1rem 0;
    background:#fdf3ee; color:#7a3d28; font-size:.82rem; border-radius:0 6px 6px 0; }}
  h2 {{ font-size:1.1rem; margin:2rem 0 .6rem; padding-bottom:.3rem; border-bottom:2px solid var(--line); }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:.75rem; margin:.5rem 0 0; }}
  .card {{ border:1px solid var(--line); border-radius:10px; padding:.85rem 1rem; }}
  .card .k {{ font-size:.72rem; color:var(--mute); text-transform:uppercase; letter-spacing:.04em; }}
  .card .v {{ font-size:1.25rem; font-weight:700; margin-top:.2rem; }}
  .card.accent .v {{ color:var(--accent); }}
  table {{ width:100%; border-collapse:collapse; margin:.4rem 0 0; font-size:.84rem; }}
  th,td {{ padding:.45rem .55rem; border-bottom:1px solid var(--line); }}
  th {{ color:var(--mute); font-weight:600; font-size:.74rem; text-transform:uppercase; letter-spacing:.03em; }}
  td.empty {{ text-align:center; color:var(--mute); padding:1rem; }}
  .table-scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
  .chart {{ margin:.5rem 0 0; }}
  .bar-row {{ display:flex; align-items:center; gap:.6rem; margin:.25rem 0; font-size:.78rem; }}
  .bar-label {{ width:48px; color:var(--mute); flex:none; }}
  .bar-track {{ flex:1 1 auto; height:14px; background:var(--soft); border-radius:7px; overflow:hidden; border:1px solid var(--line); }}
  .bar-fill {{ display:block; height:100%; background:var(--accent); }}
  .bar-val {{ width:150px; text-align:right; flex:none; color:var(--mute); }}
  .empty {{ color:var(--mute); font-size:.85rem; }}
  footer {{ margin-top:2.5rem; padding-top:1rem; border-top:1px solid var(--line); color:var(--mute); font-size:.78rem; }}
  .print-btn {{ position:fixed; top:1rem; right:1rem; background:var(--accent); color:#fff; border:0;
    border-radius:8px; padding:.6rem 1rem; font-size:.85rem; cursor:pointer; min-height:44px; box-shadow:0 2px 8px rgba(0,0,0,.15); }}
  @media (max-width:560px) {{ .bar-val {{ width:96px; }} .wrap {{ padding:1.25rem .85rem 3rem; }} }}
  @media print {{
    .print-btn {{ display:none; }}
    .wrap {{ max-width:none; padding:0; }}
    h2 {{ page-break-after:avoid; }}
    table, .chart {{ page-break-inside:avoid; }}
    body {{ font-size:11pt; }}
  }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">인쇄 / PDF로 저장</button>
<div class="wrap">
  <header>
    <h1>사용량 리포트 — {_h(data['labelKo'])}</h1>
    <p class="sub">{_fmt_ts(data['rangeFrom'])} ~ {_fmt_ts(data['rangeTo'])} · {data['days']}일 · 생성 {_fmt_ts(data['generatedAt'])}</p>
  </header>

  <div class="meta">
    <b>데이터 출처</b> ~/.claude-dashboard.db sessions 인덱스 (읽기 전용) ·
    <b>요금표</b> {_h(data['rateCard'])}
  </div>
  <div class="note">{_h(_PDF_NOTE)}</div>

  <h2>기간 합계</h2>
  <div class="cards">
    <div class="card"><div class="k">세션</div><div class="v">{t['sessions']:,}</div></div>
    <div class="card"><div class="k">총 토큰</div><div class="v">{t['tokens']:,}</div></div>
    <div class="card accent"><div class="k">추정 비용</div><div class="v">{_usd(t['usd'])}</div></div>
    <div class="card"><div class="k">입력 / 출력</div><div class="v" style="font-size:1rem">{t['in']:,} / {t['out']:,}</div></div>
    <div class="card"><div class="k">캐시 읽기 / 생성</div><div class="v" style="font-size:1rem">{t['cache_read']:,} / {t['cache_creation']:,}</div></div>
  </div>

  <h2>일별 추이</h2>
  <div class="chart">{bars}</div>
  <div class="table-scroll">
  {_rows(["날짜", "세션", "토큰", "추정 비용"], ["left", "right", "right", "right"], daily_rows)}
  </div>

  <h2>상위 프로젝트</h2>
  <div class="table-scroll">
  {_rows(["프로젝트", "세션", "토큰", "추정 비용"], ["left", "right", "right", "right"], proj_rows)}
  </div>

  <h2>모델별 분포</h2>
  <div class="table-scroll">
  {_rows(["모델", "세션", "입력", "출력", "총 토큰", "추정 비용"],
         ["left", "right", "right", "right", "right", "right"], model_rows)}
  </div>

  <h2>상위 세션 (토큰 기준)</h2>
  <div class="table-scroll">
  {_rows(["시작", "프로젝트", "모델", "토큰", "추정 비용", "점수", "첫 프롬프트"],
         ["left", "left", "left", "right", "right", "right", "left"], sess_rows)}
  </div>

  <footer>
    LazyClaude · 비용은 토큰 × 모델 요금 추정값입니다. 캐시 토큰은 합계 포함, 비용 추정 별도 단가 미적용.<br>
    {_h(_PDF_NOTE)}
  </footer>
</div>
</body>
</html>"""


# ── public handlers ──────────────────────────────────────────────────────────
def api_report_generate(query: dict | None = None) -> dict:
    """GET /api/report/generate?period=week|month → Markdown report.

    Returns JSON: {ok, period, markdown, total, meta}. The frontend renders a
    preview, offers copy-to-clipboard, and a link to the printable HTML.
    """
    try:
        period = _norm_period(query)
        data = _gather(period)
        return {
            "ok": True,
            "period": period,
            "label": data["labelKo"],
            "markdown": _md(data),
            "total": data["total"],
            "daily": data["daily"],
            "projects": data["projects"],
            "models": data["models"],
            "topSessions": data["topSessions"],
            "generatedAt": data["generatedAt"],
            "meta": {
                "rateCard": data["rateCard"],
                "source": "~/.claude-dashboard.db sessions (read-only)",
                "pdfNote": _PDF_NOTE,
                "canGeneratePdf": False,
            },
        }
    except Exception as e:
        log.warning("report generate failed: %s", e)
        return {"ok": False, "error": str(e)}


def api_report_html(query: dict | None = None) -> dict:
    """GET /api/report/html?period=week|month → self-contained printable HTML.

    NOTE on transport: the shared GET dispatcher in server/routes.py wraps
    every handler's return value in ``_send_json``. There is no raw-text path
    for arbitrary handlers, and this module must not edit routes.py. So this
    handler returns JSON ``{ok, html, contentType}`` and the frontend opens a
    new tab populated from ``html`` (document.write / Blob URL). The page is
    fully self-contained (inline CSS only) so it saves/shares/prints standalone.

    If the integrator later adds a raw-HTML dispatch branch for this path, the
    ``html`` field is exactly the bytes to write with ``Content-Type:
    text/html; charset=utf-8`` — see ``contentType`` below.
    """
    try:
        period = _norm_period(query)
        data = _gather(period)
        return {
            "ok": True,
            "period": period,
            "contentType": "text/html; charset=utf-8",
            "html": _html_doc(data),
        }
    except Exception as e:
        log.warning("report html failed: %s", e)
        return {"ok": False, "error": str(e)}
