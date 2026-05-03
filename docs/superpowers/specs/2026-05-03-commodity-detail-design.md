# Commodity Detail Drill-Down — Design

| Field | Value |
| --- | --- |
| Date | 2026-05-03 |
| Author | Tim Cooper (with Claude) |
| Status | Approved — ready for implementation plan |
| Scope | HateIndex dashboard + pipeline (no changes outside `HateIndex/`) |

## 1. Background and intent

The Hate Index dashboard ranks 12 commodities by a composite hate score and overlays a JdK rotation graph. It works for someone who already knows what a hate score is. It does *not* explain itself to a reader who is seeing the dashboard for the first time, and it does not let a reader drill into a specific commodity to see (a) how its score has moved over time, (b) what each component is contributing this week, and (c) which companies they would actually trade to express a view.

This spec adds an in-page drill-down panel that does all three.

## 2. Goals

- Reader can click any commodity from the leaderboard, or hover any tail in the rotation graph, and see a detail panel for that commodity.
- The panel shows: a 104-week score history chart, a current-week component breakdown, plain-English commentary on what the score means right now, and a curated list of constituent companies with live weekly prices.
- All explanation is data-driven — the same template generates the right paragraph for any commodity at any score level. No hand-written per-commodity copy.
- One static, version-controlled JSON file (`HateIndex/data/static/constituents.json`) is the source of truth for sector membership.
- The weekly cron picks up constituent prices in the existing yfinance run; no new external dependency.

## 3. Non-goals

- No per-company fundamentals (P/E, market cap, position sizing, etc.).
- No ETF-holdings auto-pull — curated lists only.
- No build step or new front-end framework. The dashboard remains a single-file React-via-CDN page.
- No new data sources. yfinance + CFTC + (Phase 7) FRED/GDELT only.
- No routing or per-commodity URLs. Single dashboard page.

## 4. User flow

1. Reader lands on the dashboard. KPI cards, leaderboard, RRG, signal cards as today.
2. A new section between the RRG (FIG 03) and the signal cards (FIG 04) introduces "FIG 03.5 · COMMODITY DETAIL". When nothing is selected, the panel shows a faint placeholder: *"Hover the rotation map or click a row in the leaderboard to drill in."*
3. Reader hovers a tail in the RRG → panel populates with that commodity's detail. Hover off → panel reverts to placeholder (transient).
4. Reader clicks a row in the leaderboard → panel populates and stays populated until another commodity is clicked or the reader clicks an explicit "clear" affordance (sticky).
5. Inside the panel, the reader sees:
   - Header strip with name, ticker, current score, status string, as-of date.
   - Score-history chart with hated/capitulation reference lines.
   - Component breakdown bars.
   - Plain-English commentary (3 short paragraphs).
   - Constituents table with last close + week-on-week % change.

The same `selected` state in `HateIndexDashboard` already drives RRG dimming/highlighting; this spec extends its consumers, not its shape.

## 5. Architecture

### 5.1 Layout (panel internals)

A 12-column grid inside the panel:

- **Cols 1–7 — Data column.**
  - Header strip (single row).
  - Score-history sparkline, ~700×140 px. X-axis: weekly date. Y-axis: composite hate score. Horizontal reference lines at score=4 (hated threshold) and score=8 (capitulation threshold), with dashed style and a faint colour. Dots on weeks where the commodity was flagged. Tooltip on hover: date + score + per-component contribution for that week.
  - Component bar chart, ~700×120 px. One horizontal bar per component (drawdown, momentum, positioning, flows, valuation, sentiment). Each bar shows the latest week's z-score. Null components (Phase 7) render as ghosted bars labelled "phase 7" so readers see what's coming.

- **Cols 8–12 — Meaning column.**
  - "What the score means" — three short paragraphs generated from templates. See §7.
  - Sector — companies on the desk: a sortable table of constituents. Columns: ticker, name, exchange, role tag, last close, week's % change. Default sort: pure-plays first (alphabetical), then majors (alphabetical), ETF rows pinned at bottom. Tickers are external links to the relevant Yahoo Finance / ASX page.

The panel uses the existing `panel` and `mono`/`display` classes. No new CSS tokens. The chart palette stays inside the existing brand: accent green for the subject, red for downside reference lines, fg-2 for axes/grid.

### 5.2 Data flow

```
ingest_prices.py    ─→ prices.parquet         ─→ compute_scores.py ─→ hate_scores.parquet ─┐
                                               ─→ compute_rrg.py    ─→ rrg.parquet         ─┤
ingest_cftc.py      ─→ cftc.parquet           ─→ compute_scores.py                          ├─→ build_site.py ─→ docs/data.json
                                                                                            │
constituents.json (static) ─→ ingest_constituents.py ─→ constituents_prices.parquet ────────┤
constituents.json (static) ─────────────────────────────────────────────────────────────────┘
```

`ingest_constituents.py` is a new standalone script with its own yfinance call — it does not extend `ingest_prices.py`. `build_site.py` reads the static `constituents.json` directly (for member metadata) and the parquet (for prices), joins them, and emits a single `data.json` per the existing schema plus two new blocks per commodity (`commentary`, `constituents`).

### 5.3 Components added

- `scripts/ingest_constituents.py` — pulls weekly prices for every ticker referenced in `constituents.json`. Reuses `ingest_prices.py`'s retry/backoff helper. One batched yfinance call. Writes `data/raw/constituents_prices.parquet`.
- `scripts/narrate.py` — pure functions that turn z-scores and a commodity's metadata into the three commentary paragraphs. Importable from `build_site.py`.
- `data/static/constituents.json` — committed, hand-curated. Schema in §6.1.
- New panel + chart components in `docs/index.html` — `CommodityDetailPanel`, `ScoreHistoryChart`, `ComponentBars`, `ConstituentsTable`.

## 6. Data model

### 6.1 `HateIndex/data/static/constituents.json`

```json
{
  "Lithium": {
    "members": [
      {"ticker": "ALB",    "name": "Albemarle",          "exchange": "NYSE", "role": "Major"},
      {"ticker": "SQM",    "name": "SQM",                "exchange": "NYSE", "role": "Major"},
      {"ticker": "PLS.AX", "name": "Pilbara Minerals",   "exchange": "ASX",  "role": "Pure-play"},
      {"ticker": "LAC.TO", "name": "Lithium Americas",   "exchange": "TSX",  "role": "Pure-play"},
      {"ticker": "LIT",    "name": "Global X Lithium ETF","exchange": "NYSE","role": "ETF"}
    ]
  },
  "Uranium":      { "members": [/* … */] },
  "Copper":       { "members": [/* … */] },
  "Gold":         { "members": [/* … */] },
  "Silver":       { "members": [/* … */] },
  "Rare Earths":  { "members": [/* … */] },
  "Crude Oil":    { "members": [/* … */] },
  "Nat Gas":      { "members": [/* … */] },
  "PGMs":         { "members": [/* … */] },
  "Iron Ore":     { "members": [/* … */] },
  "Thermal Coal": { "members": [/* … */] },
  "Nickel":       { "members": [/* … */] }
}
```

Roles enumerated: `"Pure-play" | "Major" | "ETF" | "Junior"`. Targets: 6–10 names per commodity. Initial seeding done as part of implementation by Claude, reviewed and red-lined by Tim before merge.

### 6.2 `data.json` additions

Each entry in `commodities` gains two new keys:

```json
{
  "name": "Lithium",
  "ticker": "LIT",
  "score": -1.02,
  "components": { /* unchanged */ },
  "rrg_tail": [ /* unchanged */ ],
  "status": "Lagging→Leading",
  "just_entered": false,
  "score_history": [ /* unchanged */ ],

  "commentary": {
    "headline": "Lithium at -1.0 sits in the bottom third of the universe — the market does not yet think it's hated.",
    "components": [
      "Drawdown z = +1.4 → trading 28% below its 5-year max, more depressed than 8 in 10 historical weeks.",
      "Relative momentum z = +0.6 → underperforming the ASX 200, but only mildly.",
      "Positioning data not available for this commodity — CFTC does not publish a managed-money series for lithium contracts."
    ],
    "rotation": "Lagging → Leading: rotated through Improving 3 weeks ago — fresh momentum."
  },

  "constituents": [
    {"ticker": "ALB", "name": "Albemarle", "exchange": "NYSE", "role": "Major",
     "last_close": 92.34, "wow_pct": -1.06, "stale": false},
    {"ticker": "PLS.AX", "name": "Pilbara Minerals", "exchange": "ASX", "role": "Pure-play",
     "last_close": 3.45, "wow_pct": 2.10, "stale": false},
    {"ticker": "LIT", "name": "Global X Lithium ETF", "exchange": "NYSE", "role": "ETF",
     "last_close": 48.22, "wow_pct": -0.90, "stale": false}
  ]
}
```

`commentary.components` is a list of 3–6 short strings (one per non-null component plus optional "not available" notes for the Phase 7 components). The dashboard joins them with bullets or stacks them as paragraphs — that's a layout call, not a data call.

`stale: true` on a constituent row means the latest yfinance fetch failed; the row still renders but with `—` for price and a small "stale" tag.

## 7. Narration templates

A small library of band-based templates per component. Pure functions; no commodity-specific branches. Example skeleton:

```python
# narrate.py
def drawdown_phrase(z: float, drawdown_pct: float) -> str | None:
    abs_dd = abs(drawdown_pct) * 100
    if z is None:
        return None
    if z >= 2:
        return f"Trading {abs_dd:.0f}% below 5-year max — deeper drawdown than 95% of historical weeks."
    if z >= 1:
        return f"Trading {abs_dd:.0f}% below 5-year max — more depressed than two-thirds of weeks."
    if z >= -1:
        return "Drawdown is in the normal historical range."
    return "Above its 5-year average — no drawdown signal."
```

Same shape for `momentum_phrase`, `positioning_phrase`, plus a `headline_phrase(score, universe_scores)` and `rotation_phrase(status, just_entered)`.

Voice matches `CLAUDE.md`: numbers + comparison + caveat, no exclamation marks, no glossary, no hand-holding. The templates are written once, audited by Tim, then automatic.

## 8. Pipeline changes

### 8.1 New ingest step

`scripts/ingest_constituents.py`:

1. Read `data/static/constituents.json`. Build the union set of unique tickers across all commodities.
2. For each ticker, call yfinance for two weekly closes (current and prior). The retry/backoff helper currently inside `ingest_prices.py` is extracted into a new `scripts/_yf_retry.py` module (single function `fetch_with_retry(ticker, period, interval) -> DataFrame`) and imported from both ingest scripts.
3. Write `data/raw/constituents_prices.parquet` with columns `[ticker, date, close]`.
4. Log a warning per ticker that fails after 3 attempts so Tim sees them in cron output.

### 8.2 Build step augments `data.json`

`scripts/build_site.py`:

1. Read `constituents.json` and `constituents_prices.parquet`.
2. For each commodity, compute `last_close` and `wow_pct` for each member; mark `stale: true` if no data.
3. Generate `commentary` via `narrate.py` from the latest score + components + status.
4. Inject `constituents` and `commentary` blocks into each commodity entry.

### 8.3 Workflow / Makefile

- `Makefile`: new `constituents` target; `refresh` becomes `ingest score rrg constituents site`.
- `.github/workflows/weekly.yml`: add a "Pull constituents" step before "Build site". Same `continue-on-error: true` treatment as CFTC — a constituents fetch failure logs but does not fail the cron.

## 9. Tests

- `tests/test_narrate.py` — table-driven, ~12 cases covering each z-score band per component plus null cases.
- `tests/test_build_site_payload.py` — runs `build_site.build()` against minimal fixture parquets and asserts the resulting payload includes `commentary` (with the 3 keys) and `constituents` (a list with the expected fields) for each commodity.
- Existing tests (`test_scoring.py`) untouched.

## 10. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| yfinance breaks again | Existing retry/backoff. Constituents fetch is `continue-on-error` so the rest of the cron still publishes. Stale rows render with `—`. |
| Constituents JSON drifts from reality (delistings) | Cron warning logs, Tim edits one line in JSON. No code changes needed. |
| Initial seed quality | Tim reviews the seeded JSON before the first commit; round-trip in PR review. |
| Narration sounds robotic | Templates audited as a phase of implementation; each band's phrase tweaked once before merging. |
| Panel adds visual clutter | Default state is a faint placeholder; nothing renders until a commodity is selected. The dashboard's existing flow is unchanged for any reader who never clicks. |

## 11. Out of scope (recap)

- No per-company fundamentals; no holdings auto-pull; no new dashboard framework or build step; no new external data sources; no per-commodity URL routing; no per-commodity hand-written copy.

## 12. Definition of done

- A reader can land on the dashboard, click any commodity in the leaderboard or hover any tail in the RRG, and see a populated detail panel with chart, components, commentary, and constituents.
- `make refresh` produces a `data.json` containing `commentary` and `constituents` blocks for every commodity.
- All new tests green; all existing tests green.
- One commit, one PR. Spec doc and implementation in separate commits in the same branch.
