"""
Hate Index backtest orchestration.

Layer A: per-component calibration (mean forward return by decile).
Layer B: composite calibration (Task 4).
Layer C: signal P&L with controls (Task 5).

Reads:
    data/raw/prices.parquet
    data/processed/hate_scores.parquet
    data/processed/rrg.parquet           (Task 5)
Writes:
    docs/backtest_components.json   (Layers A + B)
    docs/backtest.json              (Layer C)
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from scripts._returns import (
    block_bootstrap_means,
    decile_bucket,
    forward_return,
    is_monotonic_increasing,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"

TICKER_MAP: dict[str, str] = {
    "Lithium": "LIT", "Uranium": "URA", "Copper": "COPX", "Gold": "GLD",
    "Silver": "SLV", "Rare Earths": "REMX", "Crude Oil": "USO", "Nat Gas": "UNG",
    "PGMs": "PPLT", "Iron Ore": "IRON.AX", "Thermal Coal": "BTU", "Nickel": "PICK",
}

DEFAULT_HORIZONS = (4, 13, 26, 52)
COMPONENT_COL_PREFIX = "z_"
COMPONENTS = ("drawdown", "momentum", "positioning", "flows")


def _load_scores() -> pd.DataFrame:
    p = PROC_DIR / "hate_scores.parquet"
    if not p.exists():
        raise FileNotFoundError(f"missing {p}; run compute_scores first")
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df


def _load_prices() -> pd.DataFrame:
    p = RAW_DIR / "prices.parquet"
    if not p.exists():
        raise FileNotFoundError(f"missing {p}; run ingest_prices first")
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df


def _align_to_price_grid(score_dates: pd.Series, ticker_prices: pd.DataFrame) -> pd.Series:
    """Map each score observation date to the most recent price-bar date on or before it.

    Scores are stamped to Friday close; the price parquet is stamped to weekly
    Mondays (the start of the same week). For point-in-time correctness we map
    a Friday observation back to that week's Monday bar — `forward_return` then
    anchors at the *next* Monday, i.e. the Monday after the Friday signal.
    """
    left_dates = pd.to_datetime(pd.Series(score_dates.values), utc=True)
    left = pd.DataFrame({"date": left_dates, "_orig_idx": np.arange(len(left_dates))})
    left = left.sort_values("date").reset_index(drop=True)
    right_dates = pd.to_datetime(pd.Series(ticker_prices["date"].values), utc=True)
    right = pd.DataFrame({"date": right_dates, "_aligned": right_dates})
    right = right.sort_values("date").reset_index(drop=True)
    merged = pd.merge_asof(left, right, on="date", direction="backward")
    # Reorder back to original score order.
    merged = merged.sort_values("_orig_idx").reset_index(drop=True)
    out = pd.Series(merged["_aligned"], index=merged.index)
    out.index = score_dates.index
    return out


def _attach_forward_returns(scores: pd.DataFrame, prices: pd.DataFrame,
                            ticker_map: dict[str, str], horizons: Iterable[int]) -> pd.DataFrame:
    """Add fwd_<h>w columns to scores via point-in-time forward_return.

    Score dates (Friday close) are mapped to the most recent price bar on or
    before that date (typically the same week's Monday) so that the exact-match
    lookup inside `forward_return` resolves correctly.
    """
    out = scores.copy()
    for h in horizons:
        out[f"fwd_{h}w"] = np.nan
    for commodity, ticker in ticker_map.items():
        sub_idx = out["commodity"] == commodity
        sub = out[sub_idx]
        if sub.empty:
            continue
        ticker_prices = prices[prices["ticker"] == ticker]
        if ticker_prices.empty:
            continue
        aligned_dates = _align_to_price_grid(sub["date"], ticker_prices)
        for h in horizons:
            col = f"fwd_{h}w"
            out.loc[sub_idx, col] = aligned_dates.apply(
                lambda d: forward_return(prices, ticker, d, h)
                if pd.notna(d) else float("nan")
            ).values
    return out


def compute_component_calibration(component_col: str,
                                  horizons: Iterable[int] = DEFAULT_HORIZONS) -> dict:
    """Decile calibration for a single z_* column across the requested horizons."""
    scores = _load_scores()
    prices = _load_prices()
    df = _attach_forward_returns(scores, prices, TICKER_MAP, horizons)

    df = df[df[component_col].notna()].copy()
    df["decile"] = decile_bucket(df[component_col])
    df = df[df["decile"].notna()]

    rows: list[dict] = []
    spread: dict[str, float | None] = {}
    monotonic: dict[str, bool] = {}
    for h in horizons:
        col = f"fwd_{h}w"
        sub = df[df[col].notna()]
        per_dec = (
            sub.groupby("decile")[col]
            .agg(["mean", "median", "count"])
            .reindex(range(1, 11))
        )
        for dec, r in per_dec.iterrows():
            rows.append({
                "horizon_w": int(h),
                "decile": int(dec),
                "mean_return": None if pd.isna(r["mean"]) else round(float(r["mean"]), 4),
                "median_return": None if pd.isna(r["median"]) else round(float(r["median"]), 4),
                "n": int(0 if pd.isna(r["count"]) else r["count"]),
            })
        means = per_dec["mean"].dropna().tolist()
        if len(means) >= 8:
            spread[f"{h}w"] = round(float(means[-1] - means[0]), 4)
            monotonic[f"{h}w"] = is_monotonic_increasing(means, tolerance=0.15)
        else:
            spread[f"{h}w"] = None
            monotonic[f"{h}w"] = False

    return {
        "calibration": rows,
        "spread_top_minus_bottom": spread,
        "monotonic": monotonic,
        "n_total": int(len(df)),
    }


def build_components_payload(horizons: Iterable[int] = DEFAULT_HORIZONS) -> dict:
    """Layer A: per-component calibration for all four components."""
    out_components: dict[str, dict] = {}
    for c in COMPONENTS:
        col = COMPONENT_COL_PREFIX + c
        try:
            out_components[c] = compute_component_calibration(col, horizons=horizons)
        except KeyError:
            log.warning("Column %s not in scores; skipping component %s", col, c)
            out_components[c] = {"calibration": [], "spread_top_minus_bottom": {},
                                 "monotonic": {}, "n_total": 0}
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "build": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M"),
        "horizons_weeks": list(horizons),
        "components": out_components,
        "composite": None,   # filled in by Task 4
    }


def main(write_components: bool = True, write_signal: bool = True) -> int:
    if write_components:
        payload = build_components_payload()
        out = DOCS_DIR / "backtest_components.json"
        out.write_text(json.dumps(payload, indent=2))
        log.info("Wrote %s", out)
    if write_signal:
        log.info("Layer C signal-payload writing is implemented in Task 5; skipping.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
