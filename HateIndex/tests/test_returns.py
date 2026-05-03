"""Tests for the pure return / bucketing / bootstrap helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts._returns import (
    forward_return, decile_bucket, block_bootstrap_means, is_monotonic_increasing,
)


def _weekly_close_series(n: int, start_price: float = 100.0, weekly_drift: float = 0.005) -> pd.DataFrame:
    """Build a long-format prices frame for a single ticker, weekly Friday."""
    dates = pd.date_range("2020-01-03", periods=n, freq="W-FRI", tz="UTC")
    close = start_price * (1 + weekly_drift) ** np.arange(n)
    return pd.DataFrame({"date": dates, "ticker": "FAKE", "close": close})


def test_forward_return_uses_t_plus_1_anchor():
    """Forward return for week T must use prices at T+1 and T+1+h, NOT T and T+h.
    This is the look-ahead-prevention regression."""
    prices = _weekly_close_series(30, start_price=100.0, weekly_drift=0.01)
    r = forward_return(prices, "FAKE", t=prices.iloc[5]["date"], horizon_weeks=4)
    expected = prices.iloc[10]["close"] / prices.iloc[6]["close"] - 1
    assert abs(r - expected) < 1e-12


def test_forward_return_returns_nan_when_history_short():
    prices = _weekly_close_series(10)
    r = forward_return(prices, "FAKE", t=prices.iloc[8]["date"], horizon_weeks=4)
    assert pd.isna(r)


def test_decile_bucket_assigns_evenly():
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(size=1000))
    deciles = decile_bucket(s)
    counts = deciles.value_counts().sort_index()
    assert (counts >= 95).all()
    assert (counts <= 105).all()
    assert set(deciles.unique()) == set(range(1, 11))


def test_decile_bucket_handles_nan():
    s = pd.Series([1.0, 2.0, np.nan, 4.0])
    deciles = decile_bucket(s)
    assert pd.isna(deciles.iloc[2])
    assert deciles.dropna().notna().all()


def test_block_bootstrap_means_returns_n_samples():
    rng = np.random.default_rng(0)
    series = pd.Series(rng.normal(0, 1, 200))
    out = block_bootstrap_means(series, n_samples=100, sample_size=20, block_size=4, seed=42)
    assert len(out) == 100
    assert abs(out.mean()) < 0.3


def test_block_bootstrap_preserves_local_correlation():
    """If we bootstrap with block_size=1 (i.i.d. resample), an autocorrelated
    series collapses to its overall mean. With block_size>=4, blocks of
    autocorrelated values move together so the bootstrap distribution is wider."""
    rng = np.random.default_rng(1)
    raw = rng.normal(0, 1, 500)
    autocorrelated = pd.Series(np.cumsum(raw) * 0.1)
    iid_means = block_bootstrap_means(autocorrelated, n_samples=200, sample_size=20, block_size=1, seed=1)
    block_means = block_bootstrap_means(autocorrelated, n_samples=200, sample_size=20, block_size=4, seed=1)
    assert block_means.var() >= iid_means.var() * 0.5


def test_is_monotonic_increasing_with_tolerance():
    assert is_monotonic_increasing([1, 2, 3, 4, 5])
    assert is_monotonic_increasing([1, 2, 1.95, 4, 5], tolerance=0.1)
    assert not is_monotonic_increasing([1, 5, 3, 4, 2])
    assert not is_monotonic_increasing([5, 4, 3, 2, 1])
