"""Canonical mapping of commodities to representative ASX-listed equities.

This is the source of truth for the FLOW components (ASIC short positions,
later block crossings, later ETF flows). It is intentionally separate from
data/static/constituents.json — that file curates the dashboard's
"companies on the desk" view (mixed exchanges + ETFs), whereas this dict
is the ASX subset used to roll per-stock daily flow signals up to the
commodity level.

Tickers can appear in multiple commodities (e.g. IGO is both lithium-
adjacent and nickel; STO is both crude oil and natural gas).
"""
from __future__ import annotations


STOCK_UNIVERSE: dict[str, list[str]] = {
    "Lithium":      ["PLS", "MIN", "LTR", "IGO", "ATM", "AKE", "WR1"],
    "Uranium":      ["PDN", "BOE", "DYL", "PEN", "LOT", "DEV"],
    "Copper":       ["SFR", "29M", "AIS", "CAY", "C29", "AZS"],
    "Gold":         ["NST", "EVN", "NEM", "RRL", "RMS", "GMD", "WGX"],
    "Silver":       ["AYM", "ADV", "SVL", "MKR"],
    "Rare Earths":  ["LYC", "ILU", "HAS", "ARU", "VML"],
    "Crude Oil":    ["WDS", "STO", "BPT", "KAR", "COE"],
    "Nat Gas":      ["STO", "BPT", "ORG", "AOG"],
    "PGMs":         ["CHN"],
    "Iron Ore":     ["BHP", "RIO", "FMG", "CIA", "MIN", "MGX", "GRR"],
    "Thermal Coal": ["WHC", "NHC", "YAL", "CRN", "TER"],
    "Nickel":       ["NIC", "IGO", "WSA", "MCR", "PAN"],
}


def all_tickers(universe: dict[str, list[str]] = STOCK_UNIVERSE) -> set[str]:
    """Unique set of tickers across the universe."""
    out: set[str] = set()
    for tickers in universe.values():
        out.update(tickers)
    return out


def ticker_to_commodities(universe: dict[str, list[str]] = STOCK_UNIVERSE) -> dict[str, list[str]]:
    """Reverse map: ticker → list of commodities it belongs to."""
    out: dict[str, list[str]] = {}
    for commodity, tickers in universe.items():
        for t in tickers:
            out.setdefault(t, []).append(commodity)
    return out
