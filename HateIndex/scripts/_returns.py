"""
Pure helpers for the backtest module: forward returns with point-in-time
anchoring, decile bucketing, block bootstrap.

No I/O, no globals — designed to be unit-testable in isolation.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def forward_return(prices: pd.DataFrame, ticker: str,
                   t: pd.Timestamp, horizon_weeks: int) -> float:
    """
    Return the forward return on `ticker` from week T+1 to T+1+horizon_weeks.

    Anchoring at T+1 (rather than T) reflects the realistic constraint that
    a signal observed at the Friday close of week T can only be acted on the
    following Monday — i.e. you enter at the next week's close.

    `prices` is a long-format frame [date, ticker, close]. `t` is the
    observation date (typically a Friday close). Returns NaN if either
    anchor or end price is missing.
    """
    sub = prices[prices["ticker"] == ticker].sort_values("date").reset_index(drop=True)
    if sub.empty:
        return float("nan")
    matches = sub.index[sub["date"] == t]
    if len(matches) == 0:
        return float("nan")
    i = int(matches[0])
    anchor_idx = i + 1
    end_idx = i + 1 + horizon_weeks
    if end_idx >= len(sub):
        return float("nan")
    p0 = sub.iloc[anchor_idx]["close"]
    p1 = sub.iloc[end_idx]["close"]
    if not np.isfinite(p0) or not np.isfinite(p1) or p0 == 0:
        return float("nan")
    return float(p1 / p0 - 1.0)


def decile_bucket(values: pd.Series) -> pd.Series:
    """Assign each non-NaN value to a decile in [1, 10]. NaNs propagate."""
    out = pd.Series(np.nan, index=values.index, dtype="float64")
    non_null = values.dropna()
    if len(non_null) < 10:
        return out
    try:
        bins = pd.qcut(non_null, q=10, labels=False, duplicates="drop")
        out.loc[non_null.index] = bins.astype(float) + 1.0
    except ValueError:
        return out
    return out


def block_bootstrap_means(series: pd.Series, n_samples: int, sample_size: int,
                          block_size: int = 4, seed: int | None = None) -> pd.Series:
    """
    Bootstrap the sampling distribution of the mean using non-overlapping
    blocks. Returns a Series of length `n_samples`.
    """
    rng = np.random.default_rng(seed)
    arr = series.dropna().to_numpy()
    if len(arr) < sample_size:
        return pd.Series([np.nan] * n_samples)
    n_blocks = max(1, sample_size // block_size)
    means = np.empty(n_samples)
    for k in range(n_samples):
        starts = rng.integers(0, len(arr) - block_size + 1, size=n_blocks)
        chunks = [arr[s:s + block_size] for s in starts]
        sample = np.concatenate(chunks)[:sample_size]
        means[k] = sample.mean()
    return pd.Series(means)


def is_monotonic_increasing(values: Sequence[float], tolerance: float = 0.0) -> bool:
    """Return True if values are roughly monotonically increasing.

    `tolerance` is the maximum relative dip allowed between adjacent points
    (as a fraction of the total spread).
    """
    arr = np.asarray(values, dtype=float)
    if len(arr) < 2:
        return True
    spread = arr.max() - arr.min()
    if spread <= 0:
        return False
    diffs = np.diff(arr)
    allowed_dip = -tolerance * spread
    return bool((diffs >= allowed_dip).all())
