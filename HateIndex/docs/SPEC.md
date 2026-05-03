# Commodity Hate Index — Technical Specification

## 1. Universe

12 commodities, each represented by a primary ETF for price data. ASX-listed alternatives noted where the US ETF is thin or where Tim wants AU exposure for trading.

| Commodity      | Primary ticker | Alt / AU exposure         | Notes                                      |
|----------------|----------------|---------------------------|--------------------------------------------|
| Lithium        | `LIT`          | `ATM.AX`, `PLS.AX`        | Tim holds adjacent positions               |
| Uranium        | `URA`          | `URNM`, `BOE.AX`          |                                            |
| Copper         | `COPX`         | `CPER`, `SFR.AX`          |                                            |
| Gold           | `GLD`          | `GDX` (miners), `NST.AX`  |                                            |
| Silver         | `SLV`          | `SIL` (miners)            |                                            |
| Rare Earths    | `REMX`         | `LYC.AX`                  |                                            |
| Crude Oil      | `USO`          | `WPL.AX`                  | Use front-month proxy                      |
| Natural Gas    | `UNG`          | —                         | High contango, treat carefully             |
| PGMs           | `PPLT`         | `PALL`                    | Platinum primary, palladium secondary      |
| Iron Ore       | `IRON.AX`      | `FMG.AX`                  | No clean US ETF                            |
| Thermal Coal   | `BTU`          | `WHC.AX`, `NHC.AX`        | KOL ETF was delisted 2020                  |
| Nickel         | `PICK`         | `NIC.AX`                  | PICK is broad metals proxy, imperfect      |

**Benchmark**: `^AXJO` (ASX 200) for RRG. Switchable to `DBC` (Bloomberg Commodity Index ETF) via config — useful for sector-relative vs broad-equity-relative views.

## 2. Hate Score components

Six components. **Phase 2 implements only the first three** (drawdown, momentum, positioning). Add the others in Phase 7, one per session.

For each component, compute a **dual z-score** per commodity per week:

```
z_ts(c, t)    = (x(c, t) - rolling_mean(x(c), 10y)) / rolling_std(x(c), 10y)
z_xs(c, t)    = (x(c, t) - mean(x(*, t))) / std(x(*, t))      # across all commodities at time t
z(c, t)       = 0.6 * z_ts + 0.4 * z_xs
```

Sign-flip if needed so **higher = more hated**.

### 2.1 Drawdown
```
x = (price / rolling_max(price, 5y)) - 1     # always ≤ 0
```
Sign-flip on the z-score (more negative drawdown → higher hate z).

### 2.2 Relative momentum
```
x = trailing_12m_return(commodity_ETF) - trailing_12m_return(^AXJO)
```
Sign-flip.

### 2.3 CFTC positioning
For each CFTC contract mapped to a commodity (see `scripts/ingest_cftc.py` mapping table):
```
x = managed_money_net_long / total_open_interest    # bounded roughly [-1, 1]
```
Sign-flip. Lag by 1 week to respect release timing.

### 2.4 Flow

Aggregates stock-level flow signals up to commodity level via a curated
ASX universe (`scripts/_universe.py` `STOCK_UNIVERSE`).

**Sub-component 1 — Short interest (live, Phase 7a):**

```
short_pct(stock, t)         = ASIC reported short %
short_pct_commodity(c, t)   = mean across stocks in c
z_short(c, t)               = dual_z(short_pct_commodity)   # NO sign-flip
```

Sign convention: high `short_pct` = bearish positioning = HIGH hate.

**Sub-component 2 — Block crossings (Phase 7a.5, deferred):**

```
block_value(stock, t)       = ASX TRF block crossings $ value (weekly sum)
block_value_commodity(c, t) = mean across stocks in c
z_blocks(c, t)              = -dual_z(block_value_commodity)   # SIGN-FLIPPED
```

Sign convention: high block volume = institutional accumulation = LOW hate.
**Status:** the ASX block-crossings URL is JS-rendered (returns 302 to a
generic page). Pending an URL hunt or a switch to Cboe Australia reports.

**Composite flow component:**

```
z_flow_composite = mean(z_short, z_blocks, ...)
```

In Phase 7a (current), `z_flow_composite = z_short` since blocks are deferred.

**Window:** flow z-scores use a 3-year (156-week) rolling window with a
26-week warmup, vs the 10-year/52-week window of price-based components.
Rationale: flow signals are noisier and more affected by structural market
changes (algos, regulations) — recent context is more informative.

**Sources:**

| Source | URL | Cadence | Lag |
|---|---|---|---|
| ASIC short positions | `download.asic.gov.au/short-selling/RR{YYYYMMDD}-001-SSDailyAggShortPos.csv` | Daily (Mon-Fri) | T+4 business days |
| ASX block crossings | *pending verification* | Daily | T+1 |

**Backtest implications:** when Phase 6 backtest is implemented, the flow
component must respect the T+4 lag on ASIC data. Concretely: at week T, the
most recent ASIC observation available is for week T-1.

**Output schema additions:**

In `docs/data.json` per commodity:

```json
{
  "components": {
    "drawdown":    2.4,
    "momentum":    2.1,
    "positioning": 1.7,
    "flows":       1.6,        // = z_flow_composite (currently = z_short)
    "valuation":   null,
    "sentiment":   null
  },
  "flow_breakdown": {
    "z_short":  1.9,
    "z_blocks": null
  }
}
```

### 2.5 Valuation (Phase 7)
Skip until a clean source is found. Damodaran's annual sector multiples are usable but coarse.

### 2.6 Sentiment (Phase 7)
GDELT 2.0 GKG, BigQuery free tier:
```sql
SELECT DATE(date), AVG(tone)
FROM `gdelt-bq.gdeltv2.gkg`
WHERE themes LIKE '%MINING_LITHIUM%'   -- per commodity
  AND date BETWEEN ... AND ...
```
90-day rolling average tone per commodity. Sign-flip (low tone → high hate).

### Composite

```
hate_score(c, t) = sum over k of w_k * z_k(c, t)
```

Equal weights to start (`w_k = 1` for all k). After ~2 years of live data, refit weights against forward 12m returns if desired.

## 3. RRG (Relative Rotation Graph)

Per de Kempenaer's published method, weekly bars vs benchmark:

```python
SCALE = 10  # multiplier so values land in the conventional ~[85, 115] window

def _z(s, window):
    return (s - s.rolling(window).mean()) / s.rolling(window).std()

def rrg(prices, benchmark, window=10, smooth=3, scale=SCALE):
    rs = 100 * prices / benchmark
    rs_ratio = 100 + scale * _z(rs, window)
    rs_mom   = 100 + scale * _z(rs_ratio, window)
    return rs_ratio.rolling(smooth).mean(), rs_mom.rolling(smooth).mean()
```

The `scale=10` multiplier matches the Bloomberg/Stockcharts convention so RRG charts
plotted on conventional `[85, 115]` axes frame the data correctly. Both axes are
z-score-normalised (the momentum axis is z(rs_ratio), not pct_change of it), so the
two axes share comparable scale and the quadrant boundaries at (100, 100) are
visually meaningful.

Quadrants (centred at 100, 100):

| RS-Ratio | RS-Momentum | Quadrant   |
|----------|-------------|------------|
| ≥ 100    | ≥ 100       | Leading    |
| < 100    | ≥ 100       | Improving  |
| < 100    | < 100       | Lagging    |
| ≥ 100    | < 100       | Weakening  |

The dashboard tail is the **last 6 weeks**. The "rotation status" string is `{quadrant_at_t-5}→{quadrant_at_t}`, or just `{quadrant}` if unchanged.

## 4. Signal definition

A commodity is **flagged** in a given week iff:

```
hate_score >= 4
AND last quadrant transition was into Improving OR into Leading
AND that transition occurred within the last 4 weeks
```

The 4-week persistence window prevents one-bar noise from triggering a flag.

## 5. Output contract — `docs/data.json`

The dashboard reads ONLY this file. Schema:

```json
{
  "as_of": "2026-04-25",
  "build": 142,
  "benchmark": "^AXJO",
  "is_stale": false,
  "age_days": 3,
  "commodities": [
    {
      "name": "Lithium",
      "ticker": "LIT",
      "score": 12.20,
      "components": {
        "drawdown": 2.4,
        "momentum": 2.1,
        "positioning": 1.7,
        "flows": 2.3,
        "valuation": 1.9,
        "sentiment": 1.8
      },
      "rrg_tail": [[94.0, 95.0], [95.0, 98.0], [96.0, 101.0], [98.0, 103.0], [100.0, 104.5], [101.8, 104.0]],
      "status": "Lagging→Leading",
      "just_entered": true,
      "score_history": [
        {"date": "2024-04-27", "score": 8.1},
        {"date": "2024-05-04", "score": 8.3}
      ]
    }
  ],
  "flagged": ["Lithium"]
}
```

Notes:
- `score_history` is the trailing 104 weeks (2 years).
- `rrg_tail` is exactly 6 entries.
- `components` includes all six keys; missing components have value `null` until Phase 7.
- `as_of` is the date of the most recent Friday close used.
- `is_stale` is `true` when `as_of` is older than 10 days (set in `build_site.STALE_THRESHOLD_DAYS`). The dashboard can use this to warn the user that the cron may have failed.
- `age_days` is the number of days between `as_of` and build time, for reference.

## 6. Backtest (Phase 6 — live)

The backtest is its own pipeline (`scripts/backtest.py`, `make backtest`), NOT
chained into `make refresh`. Triggered manually or on a separate slower cron.

Three layers, two output JSONs:

### 6.1 Layer A — Per-component calibration

For each component `k ∈ {drawdown, momentum, positioning, flows}` and each
horizon `h ∈ {4, 13, 26, 52}` weeks:

1. Take every (commodity, week) observation where `z_k` is defined.
2. Bucket into deciles by `z_k`.
3. Compute the mean forward return of the commodity's primary ticker over
   horizon `h`, anchored at week T+1 (one week after observation; reflects the
   "act on Monday after Friday signal" constraint).

A component is "worth tracking" if mean returns are roughly monotonically
increasing in decile, with sample sizes large enough that the spread isn't
noise. A flat or non-monotonic calibration is the actionable result — it tells
us to retire that component, not "fail" the backtest.

### 6.2 Layer B — Composite calibration

Same decile exercise on the summed `score` column. The composite earns its
place if its absolute decile spread at 26w AND 52w meets or exceeds the best
single component's. If a single component dominates, the composite is
decoration. The verdict block (`composite.beats_best_component`) records
this.

### 6.3 Layer C — Signal P&L with controls

**Treatment** — every (commodity, week) where:
- `score >= 4` AND
- last quadrant transition was into Improving or Leading AND
- that transition occurred within the last 4 weeks.

**Controls:**
- **hated_not_rotating**: `score >= 4` but no recent rotation transition.
- **rotating_not_hated**: just-entered Improving/Leading but `score < 4`.
- **inverse**: `score <= -4` (sanity check that the index has direction).
- **random_bootstrap**: 1000 block-bootstrap samples (block_size=4 to preserve
  serial correlation), sample_size matched to the treatment group size or 20
  whichever is larger.

For each group, at horizons 4w / 13w / 26w / 52w: hit rate, mean, median,
Sharpe (annualised √52 multiplier), n. The treatment also produces an
event-by-event detail list and an equal-weight equity curve vs `^AXJO`.

The `verdict` block in `backtest.json` says, honestly, which horizons the
treatment beat the random-bootstrap 95% CI on, and which it failed.

### 6.4 Outputs

- `docs/backtest_components.json` — Layers A + B
- `docs/backtest.json` — Layer C

Both are committed to the repo when `make backtest` runs, and consumed by the
dashboard FIG 05 panel via `fetch('./backtest_components.json')` and
`fetch('./backtest.json')`.

### 6.5 Point-in-time correctness

- Forward returns anchor at T+1, end at T+1+h.
- CFTC positioning is already lagged 1 week at scoring time.
- ASIC short-sales are released T+4 business days; the cron pulls with that
  cut applied so the parquet is point-in-time clean.
- Survivorship: tracked tickers in `prices.parquet` only — backtest events on
  truly delisted tickers truncate at the last available date rather than
  vanishing. (Maintain `data/raw/delisted.csv` if the universe ever evolves
  significantly.)

### 6.6 Tests

`tests/test_returns.py` covers the pure helpers (`forward_return` T+1 anchor
regression, decile bucketing, block bootstrap, monotonicity).
`tests/test_backtest.py` covers the orchestration (calibration shape,
composite presence, treatment exclusion of inverse signals, random-baseline
shape, schema check).

## 7. Refresh schedule

Weekly cron, Saturday 08:00 AEST = Friday 22:00 UTC. CFTC drops Friday 15:30 ET (~20:30 UTC), so 22:00 UTC gives a 90-minute buffer.

```cron
0 22 * * 5
```

The full pipeline (ingest → constituents → flows → score → RRG → site) should
complete in under 60 seconds on a standard GitHub Actions runner. The backtest
is **not** in this chain — it runs separately via `make backtest` (manual or
slower cron).
