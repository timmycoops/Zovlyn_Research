# Hate Index Backtest — Design

| Field | Value |
| --- | --- |
| Date | 2026-05-04 |
| Author | Tim Cooper (with Claude) |
| Status | Approved — ready for implementation plan |
| Scope | HateIndex backtest module + dashboard tab. Phase 6 of the existing SPEC. |

## 1. Background

The Hate Index produces four component z-scores per commodity per week (drawdown, momentum, positioning, flows) and a composite. A signal fires when the composite ≥ 4 AND the commodity has just entered Improving / Leading on the rotation graph within the last 4 weeks. None of this has been validated. Without a backtest, we can't tell which components actually predict forward returns, whether combining them adds value, or whether the rotation overlay is pulling weight or hurting. This spec lays out a three-layer backtest framework and a dashboard tab to surface the results.

## 2. Goals

- Answer "is each component worth tracking?" with honest per-component calibration: do top-decile observations genuinely outperform bottom-decile across multiple horizons.
- Answer "does combining components beat the best single component?" via composite calibration.
- Answer "does the signal generate alpha vs honest controls?" via the existing SPEC § 6 P&L backtest, extended with random-baseline and ablation controls.
- Surface all of this on the dashboard so a reader can audit any single component's calibration, the signal's equity curve, and the hit rate by horizon — without leaving the page.
- Stay point-in-time correct: at week T the backtest can use only data available at week T, including CFTC's T+4 lag and ASIC's T+4 lag.

## 3. Non-goals

- No live signal alerts, paper trading, or order generation.
- No Monte Carlo / parameter sensitivity sweep beyond the few controls listed below. (Hyperparameter tuning is later.)
- No new data sources beyond what already feeds `data.json` (yfinance + CFTC + ASIC).
- No frontend framework change. Dashboard stays single-file React via CDN.
- No multi-asset portfolio construction. Per-commodity returns only.

## 4. Three-layer backtest framework

### 4.1 Layer A — Per-component calibration

For each component `k ∈ {drawdown, momentum, positioning, flows}` and each horizon `h ∈ {4w, 13w, 26w, 52w}`:

1. Take every (commodity, week) observation where `z_k` is defined.
2. Bucket into deciles by `z_k`.
3. Compute the mean forward return of the commodity's primary ticker over horizon `h`, starting from week T+1 (one week after the observation, to respect the data-publish lag and avoid look-ahead).
4. Output: `{component, horizon, decile, mean_return, n_obs}`.

**The component is "worth tracking" if** mean returns are roughly monotonically increasing in decile (top decile beats bottom decile) for at least one horizon, with sample sizes large enough that the spread isn't noise (rule of thumb: bottom-vs-top spread > 2× the per-decile standard error).

A flat or non-monotonic calibration is the actionable result — it tells us to retire that component, not "fail" the backtest.

### 4.2 Layer B — Composite calibration

Same decile exercise on the summed `hate_score` (with whatever components are non-null at each (c, t)). Same horizons. The composite earns its place if its decile spread is at least as wide as the best single component's. If a single component dominates, the composite is decoration.

### 4.3 Layer C — Signal P&L with controls

The SPEC § 6 design, slightly extended:

**Treatment** — every (commodity, week) where:
- `hate_score >= 4` AND
- last quadrant transition was into Improving or Leading AND
- that transition occurred within the last 4 weeks.

**Controls** — same forward-return computation, on each of:
- **Hated-not-rotating**: `hate_score >= 4` but no recent rotation transition.
- **Rotating-not-hated**: just-entered Improving/Leading but `hate_score < 4`.
- **Random**: uniform-random (commodity, week) — bootstrap 1000 samples to get the null distribution of any horizon's mean return.
- **Inverse**: `hate_score <= -4` (the universe's *liked* names) — sanity check that the index has direction.

For each treatment + control:
- Hit rate at +4w / +13w / +26w / +52w (% of trades positive)
- Mean, median, Sharpe ratio of forward returns
- Mean return relative to benchmark (^AXJO)
- Equity curve (compounded average of next-week return across all flagged commodities, weekly rebalance)

The signal is "worth shipping" if treatment beats all controls on at least the 26w and 52w horizons by a margin larger than the random-bootstrap 95% CI.

## 5. Architecture

### 5.1 Files

**New:**
- `HateIndex/scripts/backtest.py` — orchestration. Reads `prices.parquet`, `hate_scores.parquet`, `rrg.parquet`, `flow_scores.parquet`. Writes two JSONs: `docs/backtest.json` (Layer C) and `docs/backtest_components.json` (Layers A + B).
- `HateIndex/scripts/_returns.py` — pure helpers: `forward_return(prices, ticker, t, horizon_weeks)`, `weekly_friday_resample`, `decile_bucket`. Importable from backtest.py and easy to test.
- `HateIndex/tests/test_backtest.py` — calibration math, point-in-time correctness, control sample sizing, schema shape.

**Modified:**
- `HateIndex/scripts/ingest_short_sales.py` — extend default `--days` to 1825 (5 years) so the flow component has enough history for Layer A. Also add a `--since YYYY-MM-DD` argument for explicit one-shot backfills.
- `HateIndex/scripts/build_site.py` — *no change*. The two backtest JSONs are emitted directly by `backtest.py`, not folded into `data.json`. Keeps `data.json` lean for the live dashboard view; backtest tab fetches its own data.
- `HateIndex/Makefile` — `backtest` target wired into a separate phony chain (`make backtest`), NOT into `make refresh`. Backtest is expensive; we don't want it to run every weekly cron. Trigger manually or on a separate, slower cron.
- `.github/workflows/weekly.yml` — *no change*. (Optional later: a separate `monthly.yml` that runs the backtest on the 1st of each month.)
- `HateIndex/docs/index.html` — new `BacktestPanel` component rendering FIG 05 below FIG 04.
- `HateIndex/docs/SPEC.md` § 6 — replaced with this spec's contents.
- `HateIndex/CLAUDE.md` — phase tracker: Phase 6 complete after this lands.

### 5.2 Data flow

```
prices.parquet         ─┐
hate_scores.parquet    ─├──→ backtest.py ─→ docs/backtest.json
rrg.parquet            ─┤                ─→ docs/backtest_components.json
flow_scores.parquet    ─┘
```

Both JSONs are committed to the repo by the cron / manual trigger so the dashboard can fetch them statically.

### 5.3 Point-in-time correctness

Critical invariants enforced by `backtest.py`:

- **No look-ahead.** Forward-return columns and current-state columns must never coexist in the same DataFrame without explicit lag. The same rule the existing `compute_scores.py` already follows.
- **CFTC is lagged 1 week** at the score-computation step (already done by `compute_scores.compute_positioning`). When backtesting, the score read at week T already reflects CFTC at week T-1.
- **ASIC short sales are lagged T+4 business days** (~1 week). When backtesting Layer A on flows, the flow z-score read at week T already reflects ASIC at week T-1. Currently the cron pulls ASIC with the T+4 cut applied (`today - timedelta(days=4)`), so the parquet itself is point-in-time clean. Backtest just reads the parquet without any further lag.
- **Forward returns** are computed on the commodity's primary ticker (e.g. `LIT` for Lithium), starting from the Friday close of week T+1, ending at the Friday close of week T+1+h. Using T+1 (not T) gives one week's headroom for "you observed the score on Friday, you can only act on it Monday".
- **Survivorship.** `prices.parquet` only contains tickers we actively pull, so a delisted ticker (e.g. `IRON.AX` if it goes flat) loses history. For backtest honesty: maintain a small `data/raw/delisted.csv` listing tickers that disappeared, with their last trading date, so backtest events on those tickers truncate cleanly rather than disappearing. Initial seed empty; populate as the cron flags failures.

## 6. Output schemas

### 6.1 `docs/backtest_components.json` (Layers A + B)

```json
{
  "as_of": "2026-05-04",
  "build": "20260504-1530",
  "horizons_weeks": [4, 13, 26, 52],
  "components": {
    "drawdown": {
      "calibration": [
        {"horizon_w": 4,  "decile": 1,  "mean_return": -0.012, "median_return": -0.008, "n": 142},
        {"horizon_w": 4,  "decile": 10, "mean_return":  0.018, "median_return":  0.011, "n": 138},
        ...
      ],
      "spread_top_minus_bottom": {"4w": 0.030, "13w": 0.071, "26w": 0.112, "52w": 0.184},
      "monotonic": {"4w": true, "13w": true, "26w": true, "52w": false},
      "n_total": 4720
    },
    "momentum":    { ... },
    "positioning": { ... },
    "flows":       { ... }
  },
  "composite": {
    "calibration": [...],
    "spread_top_minus_bottom": {...},
    "monotonic": {...},
    "n_total": 4720,
    "best_horizon": "26w",
    "beats_best_component": true
  }
}
```

### 6.2 `docs/backtest.json` (Layer C — SPEC § 6 contract, extended)

```json
{
  "as_of": "2026-05-04",
  "n_events": 47,
  "horizons": {
    "4":  {"mean": 0.018, "median": 0.012, "hit_rate": 0.55, "sharpe": 0.4, "vs_bench": 0.011},
    "13": {"mean": 0.072, "median": 0.054, "hit_rate": 0.62, "sharpe": 0.7, "vs_bench": 0.043},
    "26": {"mean": 0.144, "median": 0.098, "hit_rate": 0.66, "sharpe": 0.9, "vs_bench": 0.087},
    "52": {"mean": 0.232, "median": 0.181, "hit_rate": 0.70, "sharpe": 1.1, "vs_bench": 0.142}
  },
  "events": [
    {"date": "2020-03-23", "commodity": "Crude Oil", "score": 9.8,
     "fwd_4w": 0.21, "fwd_13w": 0.43, "fwd_26w": 0.81, "fwd_52w": 1.34}
  ],
  "controls": {
    "hated_not_rotating":  { "horizons": { "4": {...}, "13": {...}, "26": {...}, "52": {...} }, "n_events": 312 },
    "rotating_not_hated":  { "horizons": {...}, "n_events": 198 },
    "inverse":             { "horizons": {...}, "n_events": 89 },
    "random_bootstrap": {
      "n_samples": 1000,
      "samples_per_run": 47,
      "horizons": {
        "4":  {"mean_p2.5": -0.005, "mean_p50": 0.002, "mean_p97.5": 0.009},
        "13": {"mean_p2.5": -0.012, "mean_p50": 0.005, "mean_p97.5": 0.022},
        "26": {"mean_p2.5": -0.020, "mean_p50": 0.010, "mean_p97.5": 0.040},
        "52": {"mean_p2.5": -0.035, "mean_p50": 0.020, "mean_p97.5": 0.075}
      }
    }
  },
  "calibration": [
    {"score_decile": 1, "mean_fwd_26w": -0.04, "n": 142},
    {"score_decile": 10, "mean_fwd_26w": 0.18, "n": 138}
  ],
  "equity_curve": [
    {"date": "2016-01-08", "strategy": 1.00, "benchmark": 1.00},
    {"date": "2016-01-15", "strategy": 1.012, "benchmark": 1.005}
  ],
  "verdict": {
    "beats_random_at_26w": true,
    "beats_random_at_52w": true,
    "beats_benchmark_at_52w": true,
    "summary": "Treatment beats both controls and random bootstrap at 26w/52w; at 4w/13w the lift is inside the random-bootstrap 95% CI and should not be acted on."
  }
}
```

The `verdict` block is computed from the controls and is the headline number that drives the dashboard's "should I trust this?" callout.

## 7. ASIC history extension

`ingest_short_sales.py` currently defaults to 365 days. For the flow-component Layer A backtest to have any signal-to-noise, we need at least 3 years (the same window the score's `time_series_z` already uses). The script's `--days` arg is the only knob; we'll trigger a one-time backfill:

```
python -m scripts.ingest_short_sales --days 1825
```

~1300 business days × 0.4s polite delay ≈ **9 minutes**, one-time. The existing dedupe-by-date logic in the script means subsequent cron runs only fetch the missing recent dates, so this is a paid-once cost.

If the ASIC archive goes back further than 5 years (it does — the URL pattern is stable), the ceiling is whatever's useful given evolving short-disclosure rules circa ~2015.

## 8. Dashboard — FIG 05

A new panel below FIG 04 (the weekly signal block), titled `FIG 05 · BACKTEST · DOES THIS WORK?`. Three sub-views, switchable via small tab links at the panel header:

1. **Per-component calibration** (default view). One small chart per component (drawdown, momentum, positioning, flows), each showing decile (1-10) on x and mean forward return on y, with one line per horizon. A small green tick / red cross icon next to each component's title indicating monotonicity at the 26w horizon.
2. **Composite calibration**. Single larger version of the same chart for the composite hate score.
3. **Signal P&L**. Equity curve (treatment vs benchmark vs random-bootstrap median + 95% CI ribbon), hit-rate-by-horizon table, the verdict callout.

Reads from the two new JSON files via `fetch('./backtest.json')` and `fetch('./backtest_components.json')` on mount. Falls back to a small "backtest not yet generated" message if the files are missing — same defensive pattern as the live `data.json` loader.

The panel is collapsible (default-expanded). Default state when files are missing: collapsed with a "run `make backtest`" hint.

## 9. Tests

`tests/test_backtest.py` — table-driven unit tests:

- `test_forward_return_uses_t_plus_1_anchor` — forward return for week T uses prices at T+1 and T+1+h, not T and T+h. Regression for the look-ahead trap.
- `test_decile_bucket_assigns_evenly` — 1000 random observations bucketed should have ~100 per decile.
- `test_calibration_monotonic_detector_flags_flat_series` — a calibration with no decile spread is correctly flagged as non-monotonic.
- `test_random_bootstrap_returns_correct_percentiles` — synthetic input → known output.
- `test_payload_schema_matches_spec` — the emitted JSONs validate against the schemas in §§ 6.1, 6.2 (use a fixture).
- `test_treatment_excludes_inverse_signals` — a (c, t) with `hate_score == -5` cannot be in the treatment group regardless of rotation.

No browser tests for the dashboard tab — manual `make serve` smoke as with FIG 03.5.

## 10. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Look-ahead bias creeps in unnoticed | Single point-in-time helper `forward_return(prices, ticker, t, horizon_weeks)` that explicitly anchors at T+1; tested. |
| Sample sizes too small for some components/horizons | Surface `n` per decile in the JSON and on the chart; readers can ignore noisy buckets. Add a minimum-n threshold below which the spread isn't reported. |
| Survivorship bias from delisted tickers | Maintain `data/raw/delisted.csv`; backtest events truncate at the delisting date rather than vanishing. Empty initial; populated from cron warnings over time. |
| Cherry-picking horizon | Verdict block is computed against multiple horizons, not just the prettiest one. The headline message is honest about which horizons fail. |
| ASIC history extension is slow | One-time 9-min cost. Subsequent runs are incremental. |
| Backtest runs every cron and slows the weekly refresh | `make backtest` is its own target, NOT chained into `make refresh`. Triggered manually or via a separate monthly cron. |
| Random bootstrap is misleading if returns are autocorrelated | Use **block bootstrap** with 4-week blocks instead of point-resampling. Documented in `_returns.py`. |
| Benchmark is the wrong reference for some commodities | Compute `vs_bench` against `^AXJO` (current) and additionally surface `vs_buy_and_hold` of the commodity's own primary ticker, so a flagged trade is compared against just owning the commodity all along. |

## 11. Out of scope (recap)

- No live signal alerts, no order generation, no portfolio construction, no Monte Carlo sweep beyond the random-bootstrap baseline, no ETF-shares-outstanding backtest (Phase 7b not yet shipped), no GDELT sentiment backtest (Phase 7c).

## 12. Definition of done

- `make backtest` produces `docs/backtest.json` and `docs/backtest_components.json` matching the schemas in §§ 6.1 and 6.2.
- Per-component calibration is visible on the dashboard FIG 05 with a clear visual indication of which components have monotonic decile spread at 26w / 52w.
- Composite calibration is visible and labelled with whether it beats the best single component.
- Signal P&L view shows treatment vs hated-not-rotating vs rotating-not-hated vs inverse vs random-bootstrap, with a single-sentence verdict that's honest about which horizons fail.
- ASIC history is extended to 5 years. The flow-component backtest at Layer A is therefore real (not gated on insufficient history).
- All new tests green; all existing tests green.
- Backtest is NOT in the weekly refresh chain. It's manually triggered or on a separate slower cron.
- `docs/SPEC.md` § 6 is replaced with this spec; CLAUDE.md phase tracker marks Phase 6 done.
