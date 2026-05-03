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


def test_time_series_z_uses_3y_window_with_26w_warmup():
    """Flow z should warm up at 26 weeks (min_periods), not 52 weeks like
    the price-based components."""
    s = pd.Series([1.0] * 26 + [10.0])
    z = time_series_z(s)
    assert not pd.isna(z.iloc[26])


def test_short_interest_higher_means_more_hated():
    """Sign-convention regression: higher short_pct must produce a higher
    z_short. The compute_flows pipeline does NOT sign-flip the short signal."""
    panel = pd.concat([
        pd.DataFrame({
            "date": pd.date_range("2024-01-05", periods=30, freq="W-FRI", tz="UTC"),
            "commodity": ["Lithium"] * 30,
            "short_pct": [3.0] * 29 + [9.0],
        }),
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
