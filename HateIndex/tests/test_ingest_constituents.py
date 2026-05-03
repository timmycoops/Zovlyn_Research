"""Tests for the constituents ingest script."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.ingest_constituents import collect_unique_tickers, build_long_frame


def test_collect_unique_tickers_dedupes_across_commodities(tmp_path: Path):
    cj = {
        "A": {"members": [{"ticker": "X"}, {"ticker": "Y"}]},
        "B": {"members": [{"ticker": "Y"}, {"ticker": "Z"}]},
    }
    p = tmp_path / "constituents.json"
    p.write_text(json.dumps(cj))
    assert sorted(collect_unique_tickers(p)) == ["X", "Y", "Z"]


def test_build_long_frame_concatenates_per_ticker_frames():
    f1 = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-17", "2026-04-24"], utc=True),
        "ticker": ["X", "X"],
        "close": [100.0, 102.0],
    })
    f2 = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-24"], utc=True),
        "ticker": ["Y"],
        "close": [50.0],
    })
    out = build_long_frame([f1, f2])
    assert list(out["ticker"]) == ["X", "X", "Y"]   # sort order: ticker, date
    assert list(out.columns) == ["date", "ticker", "close"]
    assert list(out["close"]) == [100.0, 102.0, 50.0]


def test_build_long_frame_empty_inputs_return_canonical_empty():
    out = build_long_frame([])
    assert out.empty
    assert list(out.columns) == ["date", "ticker", "close"]
    out2 = build_long_frame([pd.DataFrame()])
    assert out2.empty
    assert list(out2.columns) == ["date", "ticker", "close"]


def test_build_long_frame_drops_nan_close_rows():
    f = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-17", "2026-04-24"], utc=True),
        "ticker": ["X", "X"],
        "close": [100.0, float("nan")],
    })
    out = build_long_frame([f])
    assert len(out) == 1
    assert out.iloc[0]["close"] == 100.0
