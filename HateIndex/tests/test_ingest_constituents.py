"""Tests for the constituents ingest script."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

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
    assert set(out["ticker"]) == {"X", "Y"}
    assert len(out) == 3
    assert list(out.columns) == ["date", "ticker", "close"]
