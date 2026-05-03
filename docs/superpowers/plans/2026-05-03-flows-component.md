# Flows Component (Phase 7a) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder `flows` component in the Hate Score with a real signal derived from ASIC daily aggregated short positions, aggregated to commodity level via a curated ASX stock universe.

**Architecture:** New `_universe.py` module holds the canonical `STOCK_UNIVERSE` mapping (commodity → list of ASX tickers); `ingest_short_sales.py` pulls the daily ASIC CSV and writes `data/raw/short_sales.parquet`; `compute_flows.py` resamples to weekly Friday closes, aggregates per ticker to per commodity (a ticker can belong to multiple commodities), produces a per-commodity `z_short` z-score, and emits `data/processed/flow_scores.parquet`. `compute_scores.py` joins the flow z into the master composite. `build_site.py` surfaces `z_flows` in `components.flows` and exposes `flow_breakdown.z_short` for drill-down.

**Tech Stack:** Python 3.12, pandas, pyarrow, requests, pytest. Source bundle: `HateIndex/hate-index-flows/` (will be deleted after integration).

**Scope decisions baked in:**
- **Shorts only.** Block crossings are deferred (URL is unverified — JS-rendered, returns 302). The compute_flows pipeline already handles a missing block-crossings parquet gracefully, so this is a one-flag scope choice today and an additive change later.
- **Shared universe module from day one.** The bundle's three duplicated `STOCK_UNIVERSE` dicts get extracted into `scripts/_universe.py` upfront so the dict has one source of truth.
- **Bundle gets cleaned up at the end.** `hate-index-flows/` folder, `.zip`, and any `:Zone.Identifier` files are removed; the spec content folds into `docs/SPEC.md`.

---

## File Map

**New files:**
- `HateIndex/scripts/_universe.py` — single source of truth for `STOCK_UNIVERSE` and helpers (`all_tickers`, `ticker_to_commodities`)
- `HateIndex/scripts/ingest_short_sales.py` — daily ASIC CSV → `data/raw/short_sales.parquet`
- `HateIndex/scripts/compute_flows.py` — weekly aggregation → `data/processed/flow_scores.parquet`
- `HateIndex/tests/test_universe.py` — universe + reverse-map tests (~3)
- `HateIndex/tests/test_flows.py` — aggregation + z + sign-convention tests (~6)
- `HateIndex/tests/test_ingest_short_sales.py` — URL builder + CSV-parse-mock tests (~3)

**Modified files:**
- `HateIndex/scripts/compute_scores.py` — read `flow_scores.parquet`, merge into composite
- `HateIndex/scripts/build_site.py` — surface `z_flows` in `components.flows` and emit `flow_breakdown` sub-block
- `HateIndex/Makefile` — `flows` target; thread into `refresh`
- `.github/workflows/weekly.yml` — new "Ingest ASIC short sales" + "Compute flows" steps with `continue-on-error: true`
- `HateIndex/docs/SPEC.md` — replace § 2.4 placeholder with the flow-component spec
- `HateIndex/CLAUDE.md` — phase tracker: Phase 7a done, Phase 7a.5 (block crossings), 7b, 7c, 7d remaining

**Deleted at end:**
- `HateIndex/hate-index-flows/` (whole folder + zip + Zone.Identifier files)

---

## Phase 1 — Universe + ingest + compute (TDD)

### Task 1: Shared `_universe.py`

**Files:**
- Create: `HateIndex/scripts/_universe.py`
- Create: `HateIndex/tests/test_universe.py`

The universe stays ASX-only because ASIC is the data source. This is **separate from** `data/static/constituents.json` (which is the dashboard's "companies on the desk" curation, mixed exchanges + ETFs). Different purpose, different shape — keep them apart.

- [ ] **Step 1: Write the failing tests**

```python
# HateIndex/tests/test_universe.py
"""Tests for the shared ASX stock universe used by the flow components."""
from __future__ import annotations

from scripts._universe import STOCK_UNIVERSE, all_tickers, ticker_to_commodities


def test_universe_has_twelve_commodities():
    expected = {"Lithium", "Uranium", "Copper", "Gold", "Silver", "Rare Earths",
                "Crude Oil", "Nat Gas", "PGMs", "Iron Ore", "Thermal Coal", "Nickel"}
    assert set(STOCK_UNIVERSE.keys()) == expected


def test_all_tickers_dedupes_dual_membership():
    """IGO appears in both Lithium and Nickel; STO in Crude Oil and Nat Gas.
    all_tickers() returns the *unique* set, not the bag."""
    universe = STOCK_UNIVERSE
    bag_size = sum(len(v) for v in universe.values())
    unique = all_tickers()
    assert len(unique) < bag_size
    assert "IGO" in unique
    assert "STO" in unique


def test_ticker_to_commodities_reverse_map():
    rev = ticker_to_commodities(STOCK_UNIVERSE)
    assert "Lithium" in rev["IGO"]
    assert "Nickel"  in rev["IGO"]
    assert "Crude Oil" in rev["STO"]
    assert "Nat Gas"   in rev["STO"]
```

- [ ] **Step 2: Run to verify FAIL**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/pytest tests/test_universe.py -v
```

Expected: 3 errors (`ModuleNotFoundError: scripts._universe`).

- [ ] **Step 3: Implement the module**

```python
# HateIndex/scripts/_universe.py
"""Canonical mapping of commodities to representative ASX-listed equities.

This is the source of truth for the FLOW components (ASIC short positions,
later block crossings, later ETF flows). It is intentionally separate from
data/static/constituents.json — that file curates the dashboard's
"companies on the desk" view (mixed exchanges + ETFs), whereas this dict
is the ASX subset used to roll per-stock daily flow signals up to the
commodity level.

Tickers can appear in multiple commodities (e.g. IGO is both lithium-
adjacent and nickel; STO is both crude oil and natural gas).
"""
from __future__ import annotations


STOCK_UNIVERSE: dict[str, list[str]] = {
    "Lithium":      ["PLS", "MIN", "LTR", "IGO", "ATM", "AKE", "WR1"],
    "Uranium":      ["PDN", "BOE", "DYL", "PEN", "LOT", "DEV"],
    "Copper":       ["SFR", "29M", "AIS", "CAY", "C29", "AZS"],
    "Gold":         ["NST", "EVN", "NEM", "RRL", "RMS", "GMD", "WGX"],
    "Silver":       ["AYM", "ADV", "SVL", "MKR"],
    "Rare Earths":  ["LYC", "ILU", "HAS", "ARU", "VML"],
    "Crude Oil":    ["WDS", "STO", "BPT", "KAR", "COE"],
    "Nat Gas":      ["STO", "BPT", "ORG", "AOG"],
    "PGMs":         ["CHN"],
    "Iron Ore":     ["BHP", "RIO", "FMG", "CIA", "MIN", "MGX", "GRR"],
    "Thermal Coal": ["WHC", "NHC", "YAL", "CRN", "TER"],
    "Nickel":       ["NIC", "IGO", "WSA", "MCR", "PAN"],
}


def all_tickers(universe: dict[str, list[str]] = STOCK_UNIVERSE) -> set[str]:
    """Unique set of tickers across the universe."""
    out: set[str] = set()
    for tickers in universe.values():
        out.update(tickers)
    return out


def ticker_to_commodities(universe: dict[str, list[str]] = STOCK_UNIVERSE) -> dict[str, list[str]]:
    """Reverse map: ticker → list of commodities it belongs to."""
    out: dict[str, list[str]] = {}
    for commodity, tickers in universe.items():
        for t in tickers:
            out.setdefault(t, []).append(commodity)
    return out
```

- [ ] **Step 4: Run to verify PASS**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/pytest tests/test_universe.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git add HateIndex/scripts/_universe.py HateIndex/tests/test_universe.py
git -c user.name="Tim Cooper" -c user.email="tim.cooper@zovlyn.com" commit -m "feat: shared ASX stock universe for flow components"
```

---

### Task 2: `ingest_short_sales.py`

**Files:**
- Create: `HateIndex/scripts/ingest_short_sales.py`
- Create: `HateIndex/tests/test_ingest_short_sales.py`

The bundle ships a near-complete script. Key adaptations:
- Import `STOCK_UNIVERSE` and `all_tickers` from `_universe`; do not duplicate.
- Default `--days 730` (≈2 years for a forward backtest window).
- Source URL is verified working: `https://download.asic.gov.au/short-selling/RR{YYYYMMDD}-001-SSDailyAggShortPos.csv`.

- [ ] **Step 1: Write the failing tests**

```python
# HateIndex/tests/test_ingest_short_sales.py
"""Tests for the short-sales ingest helpers."""
from __future__ import annotations

from datetime import date

from scripts.ingest_short_sales import URL_TEMPLATE, business_days


def test_url_template_formats_yyyymmdd():
    url = URL_TEMPLATE.format(ymd="20260424")
    assert "RR20260424-001-SSDailyAggShortPos.csv" in url


def test_business_days_excludes_weekends():
    # 2026-04-25 = Saturday, 2026-04-26 = Sunday
    days = business_days(date(2026, 4, 24), date(2026, 4, 27))
    assert date(2026, 4, 24) in days   # Friday
    assert date(2026, 4, 25) not in days
    assert date(2026, 4, 26) not in days
    assert date(2026, 4, 27) in days   # Monday
    assert len(days) == 2


def test_business_days_inclusive_endpoints():
    days = business_days(date(2026, 4, 20), date(2026, 4, 24))  # Mon..Fri
    assert len(days) == 5
```

- [ ] **Step 2: Run to verify FAIL**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/pytest tests/test_ingest_short_sales.py -v
```

Expected: errors with `ModuleNotFoundError: scripts.ingest_short_sales`.

- [ ] **Step 3: Implement the script** (adapted from `hate-index-flows/scripts/ingest_short_sales.py`)

```python
# HateIndex/scripts/ingest_short_sales.py
"""
Pull ASIC daily aggregated short positions for the ASX universe.

Source: https://download.asic.gov.au/short-selling/RR{YYYYMMDD}-001-SSDailyAggShortPos.csv
Release: T+4 business days. Friday's data appears the following Thursday.

Run: python -m scripts.ingest_short_sales [--days 730]
Output: data/raw/short_sales.parquet
        long format: date, ticker, short_positions, total_in_issue, short_pct
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from scripts._universe import STOCK_UNIVERSE, all_tickers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

URL_TEMPLATE = "https://download.asic.gov.au/short-selling/RR{ymd}-001-SSDailyAggShortPos.csv"
USER_AGENT = "Mozilla/5.0 (compatible; ZovlynHateIndex/1.0)"
REQUEST_DELAY_S = 0.4   # be polite


def business_days(start: date, end: date) -> list[date]:
    """Mon-Fri between start and end inclusive. ASIC publishes Mon-Fri excluding
    public holidays; downloads on holidays will 404 and we tolerate."""
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def fetch_one(d: date, session: requests.Session) -> pd.DataFrame | None:
    url = URL_TEMPLATE.format(ymd=d.strftime("%Y%m%d"))
    try:
        r = session.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as e:
        log.warning("Network error for %s: %s", d.isoformat(), e)
        return None

    if r.status_code == 404:
        log.debug("No file for %s (holiday or T+4 not yet released)", d)
        return None
    if r.status_code != 200:
        log.warning("HTTP %d for %s", r.status_code, url)
        return None

    try:
        df = pd.read_csv(io.BytesIO(r.content), encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(r.content), encoding="latin-1")

    rename = {
        "Product Code": "ticker",
        "Reported Short Positions": "short_positions",
        "Total Product in Issue": "total_in_issue",
        "% of Total Product in Issue Reported as Short Positions": "short_pct",
    }
    missing = [c for c in rename if c not in df.columns]
    if missing:
        log.warning("Unexpected columns in %s; missing %s", url, missing)
        return None

    out = df[list(rename)].rename(columns=rename).copy()
    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    out["short_positions"] = pd.to_numeric(out["short_positions"], errors="coerce")
    out["total_in_issue"]  = pd.to_numeric(out["total_in_issue"],  errors="coerce")
    out["short_pct"]       = pd.to_numeric(out["short_pct"],       errors="coerce")
    out["date"] = pd.Timestamp(d, tz="UTC")
    return out[["date", "ticker", "short_positions", "total_in_issue", "short_pct"]]


def existing_dates(path: Path) -> set[date]:
    if not path.exists():
        return set()
    df = pd.read_parquet(path, columns=["date"])
    return set(pd.to_datetime(df["date"]).dt.date.unique())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=730,
                        help="Days of history to ensure on disk (default 730)")
    parser.add_argument("--full", action="store_true",
                        help="Pull --days fresh, ignoring existing parquet")
    args = parser.parse_args()

    out_path = RAW_DIR / "short_sales.parquet"
    universe = all_tickers()
    log.info("Universe: %d unique tickers across %d commodities",
             len(universe), len(STOCK_UNIVERSE))

    today = datetime.now(timezone.utc).date()
    earliest = today - timedelta(days=args.days)
    target_dates = business_days(earliest, today - timedelta(days=4))  # T+4

    have = set() if args.full else existing_dates(out_path)
    todo = [d for d in target_dates if d not in have]
    log.info("Need %d dates (already have %d, target window %d)",
             len(todo), len(have), len(target_dates))

    if not todo:
        log.info("Nothing to do; parquet already current")
        return 0

    session = requests.Session()
    frames: list[pd.DataFrame] = []
    fetched = 0
    for d in todo:
        df = fetch_one(d, session)
        if df is not None:
            df = df[df["ticker"].isin(universe)]
            if not df.empty:
                frames.append(df)
                fetched += 1
        time.sleep(REQUEST_DELAY_S)

    if not frames:
        log.warning("No new data fetched")
        return 0 if have else 1

    new_data = pd.concat(frames, ignore_index=True)
    log.info("Fetched %d new days, %d rows", fetched, len(new_data))

    if out_path.exists() and not args.full:
        existing = pd.read_parquet(out_path)
        combined = (
            pd.concat([existing, new_data], ignore_index=True)
            .drop_duplicates(subset=["date", "ticker"], keep="last")
        )
    else:
        combined = new_data

    combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)
    combined.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d tickers → %s",
             len(combined), combined["ticker"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run unit tests to verify PASS**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/pytest tests/test_ingest_short_sales.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Smoke-run against real ASIC**

Pull a small slice (last 30 days) to confirm the URL works and the schema parses:

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/python -m scripts.ingest_short_sales --days 30 2>&1 | tail -10
```

Expected: ~15-20 days of data successfully fetched (some days will 404 — Australian holidays). Final log line: `Wrote N rows for M tickers → .../short_sales.parquet` where M is around 50-70 (the universe is ~60 tickers; some may have no recent short data).

If you see 0 rows or a ModuleNotFoundError, stop and investigate.

- [ ] **Step 6: Pull full 2-year history**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/python -m scripts.ingest_short_sales --days 730 2>&1 | tail -10
```

Expected: ~500 business days fetched. Takes ~5 min (0.4s polite delay × 500 dates).

- [ ] **Step 7: Commit**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git add HateIndex/scripts/ingest_short_sales.py HateIndex/tests/test_ingest_short_sales.py HateIndex/data/raw/short_sales.parquet
git -c user.name="Tim Cooper" -c user.email="tim.cooper@zovlyn.com" commit -m "feat: ingest_short_sales pulls ASIC daily aggregated shorts"
```

---

### Task 3: `compute_flows.py`

**Files:**
- Create: `HateIndex/scripts/compute_flows.py`
- Create: `HateIndex/tests/test_flows.py`

Adapted from the bundle. Key changes:
- Import `STOCK_UNIVERSE` and `ticker_to_commodities` from `_universe`.
- Drop block-crossings code path (deferred). The `z_flow_composite` is just `z_short` for this phase.
- Mean instead of weighted-by-inverse-universe-size aggregation (the bundle's docstring suggests inverse weighting but the code uses `.mean()`; the spec also says mean — keep mean).
- Sign convention: high `short_pct` = bearish positioning = HIGH hate. **No flip.**

- [ ] **Step 1: Write the failing tests**

```python
# HateIndex/tests/test_flows.py
"""Tests for compute_flows.py — aggregation + z + sign convention."""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.compute_flows import aggregate_to_commodity, time_series_z, dual_z
from scripts._universe import STOCK_UNIVERSE, ticker_to_commodities


def _weekly_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-05", periods=n, freq="W-FRI", tz="UTC")


def test_reverse_map_includes_dual_membership():
    rev = ticker_to_commodities(STOCK_UNIVERSE)
    assert "Lithium" in rev["IGO"]
    assert "Nickel"  in rev["IGO"]


def test_aggregate_averages_across_tickers():
    idx = _weekly_index(3)
    weekly = pd.DataFrame({
        "date": list(idx) * 2,
        "ticker": ["PLS"] * 3 + ["MIN"] * 3,
        "short_pct": [10.0, 12.0, 14.0, 5.0, 7.0, 9.0],
    })
    rev = ticker_to_commodities({"Lithium": ["PLS", "MIN"]})
    out = aggregate_to_commodity(weekly, "short_pct", rev).sort_values("date").reset_index(drop=True)
    assert len(out) == 3
    np.testing.assert_allclose(out["short_pct"].tolist(), [7.5, 9.5, 11.5])


def test_aggregate_dual_membership_appears_in_both_commodities():
    idx = _weekly_index(2)
    weekly = pd.DataFrame({
        "date": list(idx),
        "ticker": ["IGO"] * 2,
        "short_pct": [3.0, 4.0],
    })
    rev = {"IGO": ["Lithium", "Nickel"]}
    out = aggregate_to_commodity(weekly, "short_pct", rev)
    assert set(out["commodity"].unique()) == {"Lithium", "Nickel"}
    assert len(out) == 4


def test_aggregate_drops_unknown_tickers():
    idx = _weekly_index(2)
    weekly = pd.DataFrame({
        "date": list(idx) * 2,
        "ticker": ["PLS"] * 2 + ["XYZ"] * 2,
        "short_pct": [10.0, 11.0, 99.0, 99.0],
    })
    rev = {"PLS": ["Lithium"]}
    out = aggregate_to_commodity(weekly, "short_pct", rev)
    assert (out["short_pct"] != 99.0).all()


def test_time_series_z_uses_3y_window_not_10y():
    """Flow z should warm up at 26 weeks (min_periods), not 52 weeks like
    the price-based components."""
    s = pd.Series([1.0] * 30 + [10.0])
    z = time_series_z(s)
    # At index 30 we have 31 observations; min_periods=26 → z is computed
    assert not pd.isna(z.iloc[30])


def test_short_interest_higher_means_more_hated():
    """Sign-convention regression: higher short_pct must produce a higher
    z_short. The compute_flows pipeline does NOT sign-flip the short signal."""
    panel = pd.DataFrame({
        "date": pd.date_range("2024-01-05", periods=30, freq="W-FRI", tz="UTC"),
        "commodity": ["Lithium"] * 30,
        "short_pct": [3.0] * 29 + [9.0],   # spike on the last week
    })
    panel = pd.concat([
        panel,
        pd.DataFrame({
            "date": pd.date_range("2024-01-05", periods=30, freq="W-FRI", tz="UTC"),
            "commodity": ["Gold"] * 30,
            "short_pct": [3.0] * 30,
        }),
    ], ignore_index=True)
    z = dual_z(panel, "short_pct")
    panel["z"] = z
    last_lithium = panel[(panel["commodity"] == "Lithium")].iloc[-1]["z"]
    last_gold    = panel[(panel["commodity"] == "Gold")].iloc[-1]["z"]
    assert last_lithium > last_gold, "high short_pct must produce higher z_short"
```

- [ ] **Step 2: Run to verify FAIL**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/pytest tests/test_flows.py -v
```

Expected: errors with `ModuleNotFoundError: scripts.compute_flows`.

- [ ] **Step 3: Implement the script**

```python
# HateIndex/scripts/compute_flows.py
"""
Compute the FLOW component of the Hate Score.

Aggregates stock-level flow data (ASIC short positions; later: block crossings,
ETF shares-outstanding) up to commodity level via STOCK_UNIVERSE, then produces
a per-commodity weekly z-score.

The intuition: a commodity is "flow-hated" when, across its representative ASX
equities, short interest is elevated.

Reads:  data/raw/short_sales.parquet
Writes: data/processed/flow_scores.parquet
        long format: date, commodity, z_short, z_flow_composite

`z_flow_composite` = `z_short` for this phase. When block crossings or ETF
flows arrive, this becomes a mean across sub-component z-scores.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

from scripts._universe import STOCK_UNIVERSE, ticker_to_commodities

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

# Window choice: flow signals are noisier than price-based ones and benefit
# from a tighter window. 3 years (156 weeks) with a 26-week warmup.
TS_WINDOW_WEEKS = 156
TS_MIN_PERIODS = 26


def time_series_z(series: pd.Series, window_weeks: int = TS_WINDOW_WEEKS,
                  min_periods: int = TS_MIN_PERIODS) -> pd.Series:
    rm = series.rolling(window_weeks, min_periods=min_periods).mean()
    rs = series.rolling(window_weeks, min_periods=min_periods).std()
    return (series - rm) / rs


def cross_sectional_z(panel: pd.DataFrame, value_col: str) -> pd.Series:
    g = panel.groupby("date")[value_col]
    return (panel[value_col] - g.transform("mean")) / g.transform("std")


def dual_z(panel: pd.DataFrame, value_col: str, ts_weight: float = 0.6) -> pd.Series:
    ts_z = panel.groupby("commodity")[value_col].transform(lambda s: time_series_z(s))
    xs_z = cross_sectional_z(panel, value_col)
    return ts_weight * ts_z + (1 - ts_weight) * xs_z


def to_weekly_per_ticker(df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """Resample daily ticker data to weekly Friday frequency (mean within week)."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], utc=True)
    out = out.set_index("date").groupby("ticker")[value_cols].resample("W-FRI").mean()
    return out.reset_index()


def aggregate_to_commodity(weekly: pd.DataFrame, value_col: str,
                           reverse_map: dict[str, list[str]]) -> pd.DataFrame:
    """Average across tickers in each commodity bucket. A ticker that belongs
    to multiple commodities contributes to each."""
    rows: list[pd.DataFrame] = []
    for ticker in weekly["ticker"].unique():
        if ticker not in reverse_map:
            continue
        sub = weekly[weekly["ticker"] == ticker][["date", value_col]].copy()
        for commodity in reverse_map[ticker]:
            rows.append(sub.assign(commodity=commodity))
    if not rows:
        return pd.DataFrame(columns=["date", "commodity", value_col])
    long = pd.concat(rows, ignore_index=True)
    return long.groupby(["date", "commodity"], as_index=False)[value_col].mean()


def main() -> int:
    short_path = RAW_DIR / "short_sales.parquet"
    if not short_path.exists():
        log.error("Missing %s — run ingest_short_sales first", short_path)
        return 1

    rev = ticker_to_commodities(STOCK_UNIVERSE)

    shorts_daily = pd.read_parquet(short_path)
    shorts_weekly = to_weekly_per_ticker(shorts_daily, ["short_pct"])
    shorts_commodity = aggregate_to_commodity(shorts_weekly, "short_pct", rev)
    shorts_commodity = shorts_commodity.sort_values(["commodity", "date"])
    # Sign convention: high short_pct = bearish = HIGH hate. NO sign-flip.
    shorts_commodity["z_short"] = dual_z(shorts_commodity, "short_pct")

    out = shorts_commodity[["date", "commodity", "z_short"]].copy()
    # Composite = mean across sub-components. With shorts only, that's just z_short.
    out["z_flow_composite"] = out["z_short"]
    out = out.dropna(subset=["z_flow_composite"]).sort_values(["date", "commodity"])

    out_path = PROC_DIR / "flow_scores.parquet"
    out.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d commodities → %s",
             len(out), out["commodity"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests + smoke**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/pytest tests/test_flows.py -v
.venv/bin/python -m scripts.compute_flows 2>&1 | tail -3
```

Expected: 6 tests passed; smoke run writes `flow_scores.parquet` with 12 commodities.

Sanity check the output:

```
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/processed/flow_scores.parquet')
print('shape:', df.shape)
print('commodities:', df['commodity'].nunique())
print('date range:', df['date'].min(), '→', df['date'].max())
print('z_short summary:'); print(df.groupby('commodity')['z_short'].describe()[['count','mean','min','max']].round(2))
"
```

- [ ] **Step 5: Commit**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git add HateIndex/scripts/compute_flows.py HateIndex/tests/test_flows.py HateIndex/data/processed/flow_scores.parquet
git -c user.name="Tim Cooper" -c user.email="tim.cooper@zovlyn.com" commit -m "feat: compute_flows produces z_short / z_flow_composite per commodity"
```

---

### Task 4: Wire flows into `compute_scores.py` + `build_site.py`

**Files:**
- Modify: `HateIndex/scripts/compute_scores.py` — read `flow_scores.parquet`, merge into composite
- Modify: `HateIndex/scripts/build_site.py` — surface `z_flows` in `components.flows` + emit `flow_breakdown`

- [ ] **Step 1: Edit compute_scores.py**

Read the file first to find the right insertion points:

```
grep -n "def main\|positioning = compute_positioning\|merged = merged.merge" HateIndex/scripts/compute_scores.py
```

At the top with the existing constants, add:

```python
FLOW_PATH = ROOT / "data" / "processed" / "flow_scores.parquet"
```

In `main()`, find the block that loads CFTC and computes positioning. AFTER that block and BEFORE the `keys = ["date", "commodity"]` merge line, add:

```python
    if FLOW_PATH.exists():
        flows = pd.read_parquet(FLOW_PATH)[["date", "commodity", "z_flow_composite"]]
        flows = flows.rename(columns={"z_flow_composite": "z_flows"})
        flows["date"] = pd.to_datetime(flows["date"], utc=True)
    else:
        log.info("No flow_scores.parquet; flows component will be NaN")
        flows = pd.DataFrame(columns=["date", "commodity", "z_flows"])
```

Then in the merge chain, find:

```python
    merged = drawdown.merge(momentum, on=keys, how="outer")
    merged = merged.merge(positioning, on=keys, how="outer")
```

and append:

```python
    merged = merged.merge(flows, on=keys, how="outer")
```

The composite-score line `merged["score"] = merged[z_cols].sum(axis=1, min_count=1)` already auto-includes any column starting with `z_` so the new component participates without further changes.

- [ ] **Step 2: Edit build_site.py**

Find the components dict construction in `build()`:

```
grep -n "components = {" HateIndex/scripts/build_site.py
```

Change:

```python
            "flows":       None,
```

to:

```python
            "flows":       nullable(latest.get("z_flows")),
```

For the drill-down: just below the `components` dict, add a `flow_breakdown` block (read from the same `flow_scores.parquet`):

```python
        flow_breakdown_block = {
            "z_short":  nullable(latest.get("z_short") if "z_short" in latest else None),
            "z_blocks": None,   # Phase 7a.5
        }
```

Then in the `commodities_payload.append({...})` dict literal, add:

```python
            "flow_breakdown": flow_breakdown_block,
```

To make `latest.get("z_short")` resolve, the merged scores frame in `compute_scores.py` needs to retain `z_short`. Currently `compute_scores.py` only pulls `z_flow_composite` (renamed to `z_flows`). Update that step to also pull `z_short`:

```python
    if FLOW_PATH.exists():
        flows = pd.read_parquet(FLOW_PATH)[["date", "commodity", "z_short", "z_flow_composite"]]
        flows = flows.rename(columns={"z_flow_composite": "z_flows"})
        flows["date"] = pd.to_datetime(flows["date"], utc=True)
    else:
        log.info("No flow_scores.parquet; flows component will be NaN")
        flows = pd.DataFrame(columns=["date", "commodity", "z_short", "z_flows"])
```

The score composite `merged[z_cols].sum(...)` will pick up BOTH `z_short` AND `z_flows` and double-count. Fix: rename `z_flow_composite` → `z_flows` and DROP `z_short` from the z_cols-summed list, OR exclude it explicitly. Cleanest: in `compute_scores.py`, after computing `score`, materialise `z_short` as a non-`z_`-prefixed name for `build_site` consumption:

```python
    merged = merged.merge(flows, on=keys, how="outer")

    # The composite line counts all columns starting with "z_". The z_short
    # sub-component is already inside z_flows; rename it so the composite
    # doesn't double-count, but keep the value reachable for build_site.
    if "z_short" in merged.columns:
        merged = merged.rename(columns={"z_short": "sub_z_short"})
```

Then in `build_site.py`:

```python
        flow_breakdown_block = {
            "z_short":  nullable(latest.get("sub_z_short")),
            "z_blocks": None,
        }
```

- [ ] **Step 3: Re-run the full pipeline + test suite**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && .venv/bin/python -m scripts.compute_scores 2>&1 | tail -3
.venv/bin/python -m scripts.build_site 2>&1 | tail -3
.venv/bin/pytest tests/ -v 2>&1 | tail -5
```

Expected: pipeline writes parquet + data.json; full test suite passes.

Sanity check `data.json`:

```
.venv/bin/python -c "
import json
d = json.load(open('docs/data.json'))
c = d['commodities'][0]
print('flows component:', c['components']['flows'])
print('flow_breakdown:', c.get('flow_breakdown'))
"
```

- [ ] **Step 4: Commit**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git add HateIndex/scripts/compute_scores.py HateIndex/scripts/build_site.py HateIndex/data/processed/hate_scores.parquet HateIndex/docs/data.json
git -c user.name="Tim Cooper" -c user.email="tim.cooper@zovlyn.com" commit -m "feat: wire z_flows into composite + surface flow_breakdown in data.json"
```

---

### Task 5: Wire Makefile + workflow

**Files:**
- Modify: `HateIndex/Makefile`
- Modify: `.github/workflows/weekly.yml`

- [ ] **Step 1: Update Makefile**

Add `flows` to `.PHONY` and the help block, and chain it into `refresh`:

```makefile
.PHONY: help install ingest constituents flows score rrg site backtest refresh test serve clean
```

In the `help:` block:

```makefile
	@echo "  flows     - pull ASIC short sales and compute flow z-scores"
```

Add target:

```makefile
flows:
	$(PYTHON) -m scripts.ingest_short_sales
	$(PYTHON) -m scripts.compute_flows
```

Update `refresh`:

```makefile
refresh: ingest constituents flows score rrg site
```

(`flows` runs after constituents so the ASIC fetch and constituent fetch can interleave with the price fetch in the future, but for now `flows` doesn't depend on `score`/`rrg`/`site` — it must complete before `score` so the merge picks it up.)

- [ ] **Step 2: Update .github/workflows/weekly.yml**

Read the existing workflow:

```
grep -n "Pull constituents\|Compute hate scores" .github/workflows/weekly.yml
```

After the `Pull constituents` step and BEFORE `Compute hate scores`, insert:

```yaml
      - name: Ingest ASIC short sales
        run: python -m scripts.ingest_short_sales
        continue-on-error: true   # ASIC fetch failures should not fail the cron

      - name: Compute flows
        run: python -m scripts.compute_flows
        continue-on-error: true
```

- [ ] **Step 3: Verify make refresh works end-to-end**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && make refresh 2>&1 | tail -10
```

Expected: completes with "Pipeline refresh complete." Includes log lines for short-sales ingest and flow compute.

- [ ] **Step 4: Commit**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git add HateIndex/Makefile .github/workflows/weekly.yml
git -c user.name="Tim Cooper" -c user.email="tim.cooper@zovlyn.com" commit -m "chore: wire flows into Makefile + weekly cron"
```

---

### Task 6: Spec, CLAUDE.md, cleanup

**Files:**
- Modify: `HateIndex/docs/SPEC.md` — replace § 2.4 with the flow-component spec
- Modify: `HateIndex/CLAUDE.md` — phase tracker update
- Delete: `HateIndex/hate-index-flows/` (whole folder)

- [ ] **Step 1: Update SPEC.md**

Read `HateIndex/docs/SPEC.md` and find the existing "2.4 ETF flows (Phase 7)" section. Replace it with the content from `HateIndex/hate-index-flows/hate-index-flows/docs/SPEC_FLOWS.md`, retitling the heading to `### 2.4 Flow`. Adapt for v1 scope — block crossings is documented as **deferred to Phase 7a.5** with a note about the URL hunt; only `z_short` is described as live.

- [ ] **Step 2: Update CLAUDE.md phase tracker**

Find the "Phase plan" section. Replace the existing Phase 7 line:

```
- [ ] **Phase 7 — Add components.** ETF flows, sentiment (GDELT), valuation. One per session.
```

with:

```
- [x] **Phase 7a — Flow component (ASIC short sales).** Live.
- [ ] **Phase 7a.5 — Block crossings sub-component.** Awaiting URL hunt.
- [ ] **Phase 7b — ETF shares-outstanding (yfinance).** Estimated 80 LOC.
- [ ] **Phase 7c — Sentiment (GDELT).** Free tier, BigQuery.
- [ ] **Phase 7d — Valuation.** Skip until clean source.
```

Update **CURRENT PHASE** if it's still pinned to an older value. Set to `7a.5 / 7b` (next work).

- [ ] **Step 3: Delete the bundle folder and zip**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
rm -rf HateIndex/hate-index-flows HateIndex/hate-index-flows.zip
```

The `:Zone.Identifier` files inside that folder go with it. `.gitignore` already covers any new ones from future copy-pastes.

- [ ] **Step 4: Final test pass**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && make test 2>&1 | tail -5
```

Expected: ~43 passed (33 prior + ~10 new).

- [ ] **Step 5: Commit**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git add HateIndex/docs/SPEC.md HateIndex/CLAUDE.md
git rm -r HateIndex/hate-index-flows HateIndex/hate-index-flows.zip 2>/dev/null || true
git add -u
git -c user.name="Tim Cooper" -c user.email="tim.cooper@zovlyn.com" commit -m "docs: fold flow spec into SPEC.md, update phase tracker, remove bundle"
```

---

### Task 7: End-to-end smoke + push

- [ ] **Step 1: Cold pipeline run**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows/HateIndex && make clean && make refresh 2>&1 | tail -15
```

Expected: completes cleanly. Includes log lines for prices, cftc, constituents, short_sales, flows, scores, rrg, build_site.

- [ ] **Step 2: Verify data.json includes flows**

```
.venv/bin/python -c "
import json
d = json.load(open('docs/data.json'))
print(f'{c[\"name\"]:14s} flows={c[\"components\"][\"flows\"]}  z_short={c[\"flow_breakdown\"][\"z_short\"] if c.get(\"flow_breakdown\") else None}' for c in d['commodities'])
" 2>&1 || true
.venv/bin/python -c "
import json
d = json.load(open('docs/data.json'))
for c in d['commodities']:
    fb = c.get('flow_breakdown') or {}
    print(f'{c[\"name\"]:14s} flows={c[\"components\"][\"flows\"]}  z_short={fb.get(\"z_short\")}')
"
```

Expected: `flows` is a real number (not None) for every commodity, `z_short` matches.

- [ ] **Step 3: Visual smoke (optional)**

```
make serve
```

Open dashboard, click any commodity, confirm `flows` bar in `ComponentBars` is now a real bar (no longer ghosted "phase 7"). The `flow_breakdown.z_short` is in the JSON for future drill-down — current panel doesn't render it yet.

- [ ] **Step 4: Push**

```
cd /home/coops/ZovlynResearch/.worktrees/feat-flows
git push -u origin feat/flows-component 2>&1 | tail -5
```

- [ ] **Step 5: Merge to main**

```
cd /home/coops/ZovlynResearch
git merge feat/flows-component --ff-only
git push
git worktree remove .worktrees/feat-flows
git branch -d feat/flows-component
git push origin --delete feat/flows-component
```

---

## Definition of done

- A reader looks at the Hate Index dashboard and sees `flows` as a non-null bar in the component breakdown for every commodity.
- `make refresh` produces a `data.json` where every commodity has `components.flows` as a real number.
- All new tests green; all existing tests green.
- The bundle folder and zip are gone; `docs/SPEC.md` § 2.4 is the canonical spec.
- Branch merged, pushed, worktree cleaned up.
