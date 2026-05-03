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
