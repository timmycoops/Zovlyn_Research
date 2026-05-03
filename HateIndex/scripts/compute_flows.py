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

TS_WINDOW_WEEKS = 156
TS_MIN_PERIODS = 26


def time_series_z(series: pd.Series, window_weeks: int = TS_WINDOW_WEEKS,
                  min_periods: int = TS_MIN_PERIODS) -> pd.Series:
    rm = series.rolling(window_weeks, min_periods=min_periods).mean()
    rs = series.rolling(window_weeks, min_periods=min_periods).std()
    # A constant rolling window has zero std → treat as zero z-score (no
    # time-series signal yet) rather than letting NaN poison dual_z.
    z = (series - rm) / rs.replace(0, pd.NA)
    return z.where(~rs.eq(0), 0.0)


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
    out["z_flow_composite"] = out["z_short"]
    out = out.dropna(subset=["z_flow_composite"]).sort_values(["date", "commodity"])

    out_path = PROC_DIR / "flow_scores.parquet"
    out.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d commodities → %s",
             len(out), out["commodity"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
