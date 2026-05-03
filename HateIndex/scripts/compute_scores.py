"""
Compute the composite Hate Score per commodity per week.

Reads:  data/raw/prices.parquet, data/raw/cftc.parquet
Writes: data/processed/hate_scores.parquet  (long format with one row per commodity per week)

Phase 2 implements three components: drawdown, relative momentum, CFTC positioning.
Phase 7 will add: ETF flows, valuation, sentiment.

All math is point-in-time correct: at week T, only data available at week T is used.
The CFTC frame is lagged by one week to respect Friday-afternoon release timing.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)
FLOW_PATH = ROOT / "data" / "processed" / "flow_scores.parquet"

# Same as ingest_prices.UNIVERSE — kept here too so this script can run independently
TICKER_MAP: dict[str, str] = {
    "Lithium": "LIT", "Uranium": "URA", "Copper": "COPX", "Gold": "GLD",
    "Silver": "SLV", "Rare Earths": "REMX", "Crude Oil": "USO", "Nat Gas": "UNG",
    "PGMs": "PPLT", "Iron Ore": "IRON.AX", "Thermal Coal": "BTU", "Nickel": "PICK",
}
BENCHMARK = "^AXJO"

# ── z-score helpers ────────────────────────────────────────────────────────

def time_series_z(series: pd.Series, window_weeks: int = 520) -> pd.Series:
    """Rolling 10-year (520-week) z-score, point-in-time correct."""
    rolling_mean = series.rolling(window_weeks, min_periods=52).mean()
    rolling_std  = series.rolling(window_weeks, min_periods=52).std()
    return (series - rolling_mean) / rolling_std


def cross_sectional_z(panel: pd.DataFrame, value_col: str) -> pd.Series:
    """For each date, z-score across commodities at that date."""
    grouped = panel.groupby("date")[value_col]
    means = grouped.transform("mean")
    stds  = grouped.transform("std")
    return (panel[value_col] - means) / stds


def dual_z(panel: pd.DataFrame, value_col: str, ts_weight: float = 0.6) -> pd.Series:
    """60% time-series z + 40% cross-sectional z."""
    ts_z = (
        panel.groupby("commodity")[value_col]
        .transform(lambda s: time_series_z(s))
    )
    xs_z = cross_sectional_z(panel, value_col)
    return ts_weight * ts_z + (1 - ts_weight) * xs_z


# ── component computations ─────────────────────────────────────────────────

def compute_drawdown(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Drawdown from 5-year rolling max; sign-flipped so deeper drawdown = higher hate."""
    out = prices_long.copy()
    out["rolling_max_5y"] = (
        out.groupby("commodity")["close"]
        .transform(lambda s: s.rolling(260, min_periods=52).max())
    )
    out["drawdown"] = (out["close"] / out["rolling_max_5y"]) - 1.0
    out["z_drawdown"] = -dual_z(out, "drawdown")  # sign-flip
    return out[["date", "commodity", "drawdown", "z_drawdown"]]


def compute_momentum(prices_long: pd.DataFrame, bench_series: pd.Series) -> pd.DataFrame:
    """12-month return minus 12-month benchmark return; sign-flipped."""
    out = prices_long.copy()
    out["ret_12m"] = (
        out.groupby("commodity")["close"]
        .transform(lambda s: s.pct_change(52))
    )
    bench_ret = bench_series.pct_change(52).rename("bench_ret_12m")
    out = out.merge(bench_ret, left_on="date", right_index=True, how="left")
    out["rel_mom"] = out["ret_12m"] - out["bench_ret_12m"]
    out["z_momentum"] = -dual_z(out, "rel_mom")
    return out[["date", "commodity", "rel_mom", "z_momentum"]]


def compute_positioning(cftc: pd.DataFrame) -> pd.DataFrame:
    """Managed money net long as % of OI, lagged 1 week, sign-flipped."""
    cftc = cftc.copy().sort_values(["commodity", "date"])
    cftc["mm_net_pct_oi_lag1"] = (
        cftc.groupby("commodity")["mm_net_pct_oi"].shift(1)
    )
    cftc["z_positioning"] = -dual_z(cftc, "mm_net_pct_oi_lag1")
    return cftc[["date", "commodity", "mm_net_pct_oi", "z_positioning"]]


# ── orchestration ──────────────────────────────────────────────────────────

def to_long_with_commodity_names(prices: pd.DataFrame) -> pd.DataFrame:
    inv = {v: k for k, v in TICKER_MAP.items()}
    out = prices[prices["ticker"].isin(inv)].copy()
    out["commodity"] = out["ticker"].map(inv)
    return out[["date", "commodity", "close"]]


def align_to_weekly_calendar(*frames: pd.DataFrame) -> list[pd.DataFrame]:
    """Snap all date columns to Friday weeks so they join cleanly."""
    aligned = []
    for f in frames:
        f = f.copy()
        f["date"] = pd.to_datetime(f["date"], utc=True).dt.tz_convert("UTC")
        # snap to nearest Friday (weekday=4)
        f["date"] = f["date"] - pd.to_timedelta((f["date"].dt.weekday - 4) % 7, unit="D")
        f["date"] = f["date"].dt.normalize()
        aligned.append(f)
    return aligned


def main() -> int:
    prices_path = RAW_DIR / "prices.parquet"
    cftc_path = RAW_DIR / "cftc.parquet"
    if not prices_path.exists():
        log.error("Missing %s — run ingest_prices.py first", prices_path)
        return 1

    prices_raw = pd.read_parquet(prices_path)
    bench = (
        prices_raw[prices_raw["ticker"] == BENCHMARK]
        .set_index("date")["close"]
        .sort_index()
    )
    prices_long = to_long_with_commodity_names(prices_raw).sort_values(["commodity", "date"])

    # CFTC is optional in Phase 2 — if missing, skip positioning component
    if cftc_path.exists():
        cftc = pd.read_parquet(cftc_path)
        prices_long, cftc = align_to_weekly_calendar(prices_long, cftc)
        positioning = compute_positioning(cftc)
    else:
        log.warning("No cftc.parquet found; positioning component will be NaN")
        prices_long, = align_to_weekly_calendar(prices_long)
        positioning = pd.DataFrame(columns=["date", "commodity", "z_positioning"])

    if FLOW_PATH.exists():
        flows = pd.read_parquet(FLOW_PATH)[["date", "commodity", "z_short", "z_flow_composite"]]
        flows = flows.rename(columns={"z_flow_composite": "z_flows"})
        flows["date"] = pd.to_datetime(flows["date"], utc=True)
    else:
        log.info("No flow_scores.parquet; flows component will be NaN")
        flows = pd.DataFrame(columns=["date", "commodity", "z_short", "z_flows"])

    drawdown = compute_drawdown(prices_long)
    momentum = compute_momentum(prices_long, bench)

    # Merge components on (date, commodity)
    keys = ["date", "commodity"]
    merged = drawdown.merge(momentum, on=keys, how="outer")
    merged = merged.merge(positioning, on=keys, how="outer")
    merged = merged.merge(flows, on=keys, how="outer")

    # z_short is a sub-component already rolled into z_flows. Rename it so
    # the composite sum (which auto-includes every z_*) does not double-count.
    if "z_short" in merged.columns:
        merged = merged.rename(columns={"z_short": "sub_z_short"})

    # Composite — equal-weighted sum of available z-scores (NaN-safe)
    z_cols = [c for c in merged.columns if c.startswith("z_")]
    merged["score"] = merged[z_cols].sum(axis=1, min_count=1)

    # Drop rows where the composite is undefined (early in history)
    merged = merged.dropna(subset=["score"]).sort_values(["date", "commodity"])

    out_path = PROC_DIR / "hate_scores.parquet"
    merged.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d commodities → %s",
             len(merged), merged["commodity"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
