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

SIGNAL_THRESHOLD = 4.0
ROTATION_WINDOW_WEEKS = 4
TARGET_QUADRANTS = ("Improving", "Leading")


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


def compute_composite_calibration(horizons: Iterable[int] = DEFAULT_HORIZONS) -> dict:
    """Decile calibration for the summed `score` column (composite hate)."""
    return compute_component_calibration("score", horizons=horizons)


def _summarise_composite_vs_components(components_payload: dict, composite_payload: dict) -> dict:
    """Compute the 'beats best single component' verdict and pick the
    horizon where the composite has the widest decile spread."""
    spreads_composite = composite_payload.get("spread_top_minus_bottom", {})
    horizons_w = list(spreads_composite.keys())
    component_spreads_by_horizon = {h: 0.0 for h in horizons_w}
    for c, block in components_payload.items():
        for h, s in block.get("spread_top_minus_bottom", {}).items():
            if s is not None and abs(s) > abs(component_spreads_by_horizon.get(h, 0.0)):
                component_spreads_by_horizon[h] = s
    # Composite "beats" if its absolute spread at 26w AND 52w is >= max single-component absolute spread
    beats = False
    s26 = spreads_composite.get("26w")
    s52 = spreads_composite.get("52w")
    if s26 is not None and s52 is not None:
        beats = (
            abs(s26) >= abs(component_spreads_by_horizon.get("26w", 0.0))
            and abs(s52) >= abs(component_spreads_by_horizon.get("52w", 0.0))
        )
    valid = {h: s for h, s in spreads_composite.items() if s is not None}
    best_horizon = max(valid.items(), key=lambda kv: abs(kv[1]))[0] if valid else None
    return {
        **composite_payload,
        "best_horizon": best_horizon,
        "beats_best_component": beats,
    }


def _load_rrg() -> pd.DataFrame:
    p = PROC_DIR / "rrg.parquet"
    if not p.exists():
        raise FileNotFoundError(f"missing {p}; run compute_rrg first")
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df


def _is_treatment(scores_sub: pd.DataFrame, rrg: pd.DataFrame) -> pd.Series:
    """composite >= SIGNAL_THRESHOLD AND just-entered Improving/Leading within ROTATION_WINDOW_WEEKS."""
    out = pd.Series(False, index=scores_sub.index)
    for i, row in scores_sub.iterrows():
        if not (pd.notna(row.get("score")) and row["score"] >= SIGNAL_THRESHOLD):
            continue
        sub = rrg[(rrg["commodity"] == row["commodity"]) &
                  (rrg["date"] <= row["date"])].sort_values("date").tail(ROTATION_WINDOW_WEEKS + 1)
        if len(sub) < 2:
            continue
        last_q = sub.iloc[-1]["quadrant"]
        prev_qs = sub.iloc[:-1]["quadrant"].tolist()
        if last_q in TARGET_QUADRANTS and any(q != last_q for q in prev_qs):
            out.loc[i] = True
    return out


def _is_hated_not_rotating(scores_sub: pd.DataFrame, rrg: pd.DataFrame) -> pd.Series:
    treated = _is_treatment(scores_sub, rrg)
    hated = scores_sub["score"] >= SIGNAL_THRESHOLD
    return hated & ~treated


def _is_rotating_not_hated(scores_sub: pd.DataFrame, rrg: pd.DataFrame) -> pd.Series:
    out = pd.Series(False, index=scores_sub.index)
    for i, row in scores_sub.iterrows():
        if pd.notna(row.get("score")) and row["score"] >= SIGNAL_THRESHOLD:
            continue
        sub = rrg[(rrg["commodity"] == row["commodity"]) &
                  (rrg["date"] <= row["date"])].sort_values("date").tail(ROTATION_WINDOW_WEEKS + 1)
        if len(sub) < 2:
            continue
        last_q = sub.iloc[-1]["quadrant"]
        prev_qs = sub.iloc[:-1]["quadrant"].tolist()
        if last_q in TARGET_QUADRANTS and any(q != last_q for q in prev_qs):
            out.loc[i] = True
    return out


def _is_inverse(scores_sub: pd.DataFrame) -> pd.Series:
    return scores_sub["score"] <= -SIGNAL_THRESHOLD


def _summary_stats(returns: pd.Series) -> dict:
    r = returns.dropna()
    if r.empty:
        return {"mean": None, "median": None, "hit_rate": None, "sharpe": None, "n": 0}
    sharpe = float(r.mean() / r.std() * np.sqrt(52)) if r.std() > 0 else None
    return {
        "mean":     round(float(r.mean()), 4),
        "median":   round(float(r.median()), 4),
        "hit_rate": round(float((r > 0).mean()), 4),
        "sharpe":   None if sharpe is None else round(sharpe, 2),
        "n":        int(len(r)),
    }


def compute_random_baseline(df_with_returns: pd.DataFrame,
                            n_samples: int = 1000, sample_size: int = 50,
                            horizons: Iterable[int] = DEFAULT_HORIZONS) -> dict:
    out_horizons: dict[str, dict] = {}
    for h in horizons:
        col = f"fwd_{h}w"
        means = block_bootstrap_means(df_with_returns[col], n_samples=n_samples,
                                      sample_size=sample_size, block_size=4, seed=42)
        out_horizons[str(h)] = {
            "mean_p2.5":  round(float(np.percentile(means, 2.5)), 4),
            "mean_p50":   round(float(np.percentile(means, 50)),  4),
            "mean_p97.5": round(float(np.percentile(means, 97.5)), 4),
        }
    return {"n_samples": n_samples, "samples_per_run": sample_size, "horizons": out_horizons}


def _equity_curve(events: pd.DataFrame, scores: pd.DataFrame, prices: pd.DataFrame) -> list[dict]:
    """Naive equity curve: at each week with a flagged event, equal-weight
    the next-week returns of the flagged commodities. Compare against benchmark."""
    if events.empty:
        return []
    events = events.copy()
    events["fwd_1w"] = events.apply(
        lambda r: forward_return(prices, TICKER_MAP[r["commodity"]], r["date"], 1), axis=1)
    weekly = events.groupby("date")["fwd_1w"].mean()
    bench_prices = prices[prices["ticker"] == "^AXJO"].set_index("date")["close"].sort_index()
    if bench_prices.empty:
        bench_weekly = pd.Series(0.0, index=weekly.index)
    else:
        bench_weekly = bench_prices.pct_change().reindex(weekly.index).fillna(0.0)
    strategy_curve = (1 + weekly.fillna(0.0)).cumprod()
    benchmark_curve = (1 + bench_weekly).cumprod()
    return [
        {"date": d.strftime("%Y-%m-%d"),
         "strategy":  round(float(s), 4),
         "benchmark": round(float(b), 4)}
        for d, s, b in zip(strategy_curve.index, strategy_curve, benchmark_curve)
    ]


def build_signal_payload(horizons: Iterable[int] = DEFAULT_HORIZONS) -> dict:
    scores = _load_scores()
    prices = _load_prices()
    rrg = _load_rrg()
    df = _attach_forward_returns(scores, prices, TICKER_MAP, horizons)

    treat_mask = _is_treatment(df, rrg)
    hnr_mask   = _is_hated_not_rotating(df, rrg)
    rnh_mask   = _is_rotating_not_hated(df, rrg)
    inv_mask   = _is_inverse(df)

    treatment = df[treat_mask]
    horizons_block = {str(h): _summary_stats(treatment[f"fwd_{h}w"]) for h in horizons}

    events = [
        {"date": r["date"].strftime("%Y-%m-%d"), "commodity": r["commodity"],
         "score": round(float(r["score"]), 2),
         **{f"fwd_{h}w": (None if pd.isna(r[f"fwd_{h}w"]) else round(float(r[f"fwd_{h}w"]), 4)) for h in horizons}}
        for _, r in treatment.iterrows()
    ]

    sample_size = max(20, int(treat_mask.sum()))
    controls = {
        "hated_not_rotating": {
            "horizons": {str(h): _summary_stats(df[hnr_mask][f"fwd_{h}w"]) for h in horizons},
            "n_events": int(hnr_mask.sum()),
        },
        "rotating_not_hated": {
            "horizons": {str(h): _summary_stats(df[rnh_mask][f"fwd_{h}w"]) for h in horizons},
            "n_events": int(rnh_mask.sum()),
        },
        "inverse": {
            "horizons": {str(h): _summary_stats(df[inv_mask][f"fwd_{h}w"]) for h in horizons},
            "n_events": int(inv_mask.sum()),
        },
        "random_bootstrap": compute_random_baseline(df, horizons=horizons, sample_size=sample_size),
    }

    rb = controls["random_bootstrap"]["horizons"]
    beats: dict[str, bool] = {}
    for h in horizons:
        h_s = str(h)
        t_mean = horizons_block[h_s]["mean"]
        cap = rb[h_s]["mean_p97.5"]
        beats[h_s] = (t_mean is not None and cap is not None and t_mean > cap)
    pos = [h for h, b in beats.items() if b]
    neg = [h for h, b in beats.items() if not b]
    parts = []
    if pos: parts.append("Treatment beats random-bootstrap 95% CI at " + ", ".join(f"{h}w" for h in pos))
    if neg: parts.append("fails at " + ", ".join(f"{h}w" for h in neg))
    summary = "; ".join(parts) if parts else "Insufficient events to render a verdict."

    eq = _equity_curve(treatment, scores, prices)

    composite_26 = compute_composite_calibration(horizons=(26,))["calibration"]

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "n_events": int(treat_mask.sum()),
        "horizons": horizons_block,
        "events": events,
        "controls": controls,
        "calibration": [
            {"score_decile": int(rec["decile"]), "mean_fwd_26w": rec["mean_return"], "n": rec["n"]}
            for rec in composite_26
        ],
        "equity_curve": eq,
        "verdict": {
            "beats_random_at_26w": beats.get("26", False),
            "beats_random_at_52w": beats.get("52", False),
            "beats_benchmark_at_52w": (eq and eq[-1]["strategy"] > eq[-1]["benchmark"]) if eq else False,
            "summary": summary,
        },
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
    composite_raw = compute_composite_calibration(horizons=horizons)
    composite = _summarise_composite_vs_components(out_components, composite_raw)
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "build": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M"),
        "horizons_weeks": list(horizons),
        "components": out_components,
        "composite": composite,
    }


def main(write_components: bool = True, write_signal: bool = True) -> int:
    if write_components:
        payload = build_components_payload()
        out = DOCS_DIR / "backtest_components.json"
        out.write_text(json.dumps(payload, indent=2))
        log.info("Wrote %s", out)
    if write_signal:
        try:
            payload = build_signal_payload()
        except FileNotFoundError as e:
            log.warning("Skipping signal payload: %s", e)
            return 0
        out = DOCS_DIR / "backtest.json"
        out.write_text(json.dumps(payload, indent=2))
        log.info("Wrote %s (n_events=%d)", out, payload["n_events"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
