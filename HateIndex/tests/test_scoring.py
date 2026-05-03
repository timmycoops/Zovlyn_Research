"""Starter tests for scoring math. Add more as logic grows."""
from __future__ import annotations

import numpy as np
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.compute_scores import time_series_z, cross_sectional_z
from scripts.compute_rrg import compute_rrg_pair, quadrant_label


def _weekly_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2020-01-03", periods=n, freq="W-FRI", tz="UTC")


def test_time_series_z_returns_zero_for_constant():
    s = pd.Series([5.0] * 200)
    z = time_series_z(s)
    # All non-NaN values should be zero (or NaN where std=0)
    assert (z.dropna().abs() < 1e-9).all() or z.dropna().empty


def test_time_series_z_extreme_low_negative():
    s = pd.Series(np.concatenate([np.ones(200) * 100, [50.0]]))
    z = time_series_z(s)
    assert z.iloc[-1] < 0


def test_cross_sectional_z_balances_to_zero():
    panel = pd.DataFrame({
        "date": [pd.Timestamp("2025-01-03", tz="UTC")] * 4,
        "commodity": ["A", "B", "C", "D"],
        "v": [1.0, 2.0, 3.0, 4.0],
    })
    z = cross_sectional_z(panel, "v")
    assert abs(z.mean()) < 1e-9


def test_quadrant_labels():
    assert quadrant_label(101, 101) == "Leading"
    assert quadrant_label(99, 101)  == "Improving"
    assert quadrant_label(99, 99)   == "Lagging"
    assert quadrant_label(101, 99)  == "Weakening"
    assert quadrant_label(np.nan, 100) == "N/A"


def test_rrg_at_benchmark_equals_100():
    """If the commodity tracks the benchmark exactly, RS-Ratio should hover at 100."""
    idx = _weekly_index(50)
    bench = pd.Series(np.linspace(100, 120, 50), index=idx)
    sym = bench.copy()
    rs_ratio, rs_mom = compute_rrg_pair(sym, bench)
    # The smoothed values once warmed up should sit very close to 100
    settled = rs_ratio.dropna().tail(20)
    assert (settled.between(99, 101)).all(), f"got {settled.values}"
