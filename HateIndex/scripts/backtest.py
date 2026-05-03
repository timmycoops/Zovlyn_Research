"""
Phase 6 — Historical backtest of the Hate-and-Rotating signal.

This is a STUB. The structure is laid out below; fill in the TODOs.

Reads:
    data/processed/hate_scores.parquet
    data/processed/rrg.parquet
    data/raw/prices.parquet         (for forward returns)

Writes:
    docs/backtest.json              (consumed by a future dashboard tab)

See docs/SPEC.md § 6 for output schema and methodology requirements.

Critical correctness rules:
- Forward returns are computed AFTER the signal is generated. Never let
  forward-return columns and current-state columns coexist in the same frame
  during signal generation.
- Survivorship: maintain data/raw/delisted.csv and include in the universe
  for backtest weeks where the ticker was still trading.
- Bootstrap CIs around all reported statistics — small N.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
DOCS_DIR = ROOT / "docs"

HORIZONS_WEEKS = [4, 13, 26, 52]
SIGNAL_THRESHOLD = 4.0
PERSISTENCE_WEEKS = 4   # signal must be active for N weeks before flagging


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scores = pd.read_parquet(PROC_DIR / "hate_scores.parquet")
    rrg = pd.read_parquet(PROC_DIR / "rrg.parquet")
    prices = pd.read_parquet(RAW_DIR / "prices.parquet")
    for df in (scores, rrg, prices):
        df["date"] = pd.to_datetime(df["date"], utc=True)
    return scores, rrg, prices


def compute_forward_returns(prices: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """For each (ticker, date), forward total return at each horizon (weeks)."""
    # TODO: pivot prices to wide, compute ticker.shift(-h) / ticker - 1
    raise NotImplementedError("Phase 6")


def generate_signals(scores: pd.DataFrame, rrg: pd.DataFrame) -> pd.DataFrame:
    """
    Return long-format frame with columns (date, commodity, score, status, flag_active).
    flag_active = True iff score >= SIGNAL_THRESHOLD AND quadrant just entered Improving/Leading
                  AND the entry persisted for PERSISTENCE_WEEKS.
    """
    # TODO: merge scores+rrg on (date, commodity), compute rolling quadrant transitions,
    #       apply thresholds, return frame.
    raise NotImplementedError("Phase 6")


def compute_event_returns(signals: pd.DataFrame, fwd: pd.DataFrame) -> pd.DataFrame:
    """For each flagged event, attach forward returns at all horizons."""
    raise NotImplementedError("Phase 6")


def aggregate(events: pd.DataFrame, horizons: list[int]) -> dict:
    """Hit rate, mean, median, Sharpe, vs-benchmark per horizon."""
    raise NotImplementedError("Phase 6")


def calibration_buckets(signals: pd.DataFrame, fwd: pd.DataFrame, horizon: int = 26) -> list[dict]:
    """Decile-bin scores; report mean forward return per decile. Monotonic = signal works."""
    raise NotImplementedError("Phase 6")


def equity_curve(signals: pd.DataFrame, fwd: pd.DataFrame) -> list[dict]:
    """Compound returns of equal-weight basket of currently-flagged commodities, weekly."""
    raise NotImplementedError("Phase 6")


def main() -> int:
    log.warning("backtest.py is a stub — Phase 6 implementation pending")
    payload = {
        "as_of": None,
        "n_events": 0,
        "horizons": {},
        "events": [],
        "calibration": [],
        "equity_curve": [],
        "_status": "phase 6 not yet implemented",
    }
    out = DOCS_DIR / "backtest.json"
    out.write_text(json.dumps(payload, indent=2))
    log.info("Wrote stub %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
