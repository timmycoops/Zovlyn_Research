"""Tests for the shared yfinance retry/backoff helper."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts._yf_retry import fetch_with_retry


def test_returns_normalised_long_frame_on_success(mocker):
    raw = pd.DataFrame(
        {"Close": [100.0, 102.0]},
        index=pd.to_datetime(["2026-04-17", "2026-04-24"]),
    )
    raw.index.name = "Date"
    mocker.patch("scripts._yf_retry.yf.download", return_value=raw)

    out = fetch_with_retry("FOO", period="1y", interval="1wk")

    assert list(out.columns) == ["date", "ticker", "close"]
    assert (out["ticker"] == "FOO").all()
    assert len(out) == 2
    assert out["date"].dt.tz is not None  # UTC-aware


def test_retries_on_empty_frame_then_succeeds(mocker):
    bad = pd.DataFrame()
    good = pd.DataFrame(
        {"Close": [50.0]},
        index=pd.to_datetime(["2026-04-24"]),
    )
    good.index.name = "Date"
    mocker.patch("scripts._yf_retry.yf.download", side_effect=[bad, good])
    mocker.patch("scripts._yf_retry.time.sleep")  # don't actually sleep

    out = fetch_with_retry("BAR", period="1y", interval="1wk", max_attempts=3)
    assert len(out) == 1


def test_returns_empty_frame_after_all_attempts_fail(mocker):
    mocker.patch("scripts._yf_retry.yf.download", return_value=pd.DataFrame())
    mocker.patch("scripts._yf_retry.time.sleep")

    out = fetch_with_retry("BAZ", period="1y", interval="1wk", max_attempts=2)
    assert out.empty
    assert list(out.columns) == ["date", "ticker", "close"]
