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

### 2.4 ETF flows (Phase 7)
```
shares_out_change = shares_outstanding_t - shares_outstanding_(t-26w)
flow_proxy = shares_out_change * avg_price / aum_(t-26w)
```
Sign-flip. yfinance has `sharesOutstanding` history.

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
def rrg(prices: pd.Series, benchmark: pd.Series, window: int = 10, smooth: int = 3):
    rs = 100 * prices / benchmark
    rs_ratio = 100 + ((rs - rs.rolling(window).mean())
                      / rs.rolling(window).std())
    rs_mom = 100 + rs_ratio.pct_change() * 100
    return rs_ratio.rolling(smooth).mean(), rs_mom.rolling(smooth).mean()
```

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

## 6. Backtest spec (Phase 6)

Generate a historical signal series: at every week t in the last 10 years, evaluate the signal rule. For each flagged event, compute forward returns at +4w, +13w, +26w, +52w using the commodity's primary ticker.

Outputs to `docs/backtest.json`:

```json
{
  "as_of": "2026-04-25",
  "n_events": 47,
  "horizons": {
    "4":  {"mean": 0.018, "median": 0.012, "hit_rate": 0.55, "sharpe": 0.4, "vs_bench": 0.011},
    "13": {"mean": 0.072, "median": 0.054, "hit_rate": 0.62, "sharpe": 0.7, "vs_bench": 0.043},
    "26": {"mean": 0.144, "median": 0.098, "hit_rate": 0.66, "sharpe": 0.9, "vs_bench": 0.087},
    "52": {"mean": 0.232, "median": 0.181, "hit_rate": 0.70, "sharpe": 1.1, "vs_bench": 0.142}
  },
  "events": [
    {"date": "2020-03-23", "commodity": "Crude Oil", "score": 9.8, "fwd_4w": 0.21, "fwd_13w": 0.43, "fwd_26w": 0.81, "fwd_52w": 1.34}
  ],
  "calibration": [
    {"score_decile": 1, "mean_fwd_26w": -0.04, "n": 142},
    {"score_decile": 10, "mean_fwd_26w": 0.18, "n": 138}
  ],
  "equity_curve": [
    {"date": "2016-01-08", "strategy": 1.00, "benchmark": 1.00}
  ]
}
```

Controls (must also be computed for honesty):
- Same statistics for the benchmark over identical weeks
- Hated-but-not-rotating
- Rotating-but-not-hated
- Random-time-random-commodity baseline (1000 bootstrap samples)

Survivorship: use point-in-time tickers. Maintain a small `data/raw/delisted.csv` for tickers that no longer exist (e.g. KOL).

## 7. Refresh schedule

Weekly cron, Saturday 08:00 AEST = Friday 22:00 UTC. CFTC drops Friday 15:30 ET (~20:30 UTC), so 22:00 UTC gives a 90-minute buffer.

```cron
0 22 * * 5
```

The full pipeline (ingest → score → RRG → site → backtest) should complete in under 60 seconds on a standard GitHub Actions runner.
