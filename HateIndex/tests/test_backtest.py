"""Tests for the backtest orchestration."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import backtest as bt


@pytest.fixture
def fake_parquets(tmp_path, monkeypatch):
    """Tiny fixture: 4 commodities x 200 weeks of synthetic prices + scores."""
    raw = tmp_path / "raw"; raw.mkdir(parents=True)
    proc = tmp_path / "processed"; proc.mkdir(parents=True)
    docs = tmp_path / "docs"; docs.mkdir(parents=True)

    monkeypatch.setattr(bt, "RAW_DIR", raw)
    monkeypatch.setattr(bt, "PROC_DIR", proc)
    monkeypatch.setattr(bt, "DOCS_DIR", docs)

    rng = np.random.default_rng(0)
    dates = pd.date_range("2022-01-07", periods=200, freq="W-FRI", tz="UTC")
    commodities = ["A", "B", "C", "D"]
    tickers = {"A": "TA", "B": "TB", "C": "TC", "D": "TD"}

    price_rows = []
    for c, t in tickers.items():
        prices = 100 * (1 + rng.normal(0.001, 0.02, 200)).cumprod()
        for d, p in zip(dates, prices):
            price_rows.append({"date": d, "ticker": t, "close": float(p)})
    pd.DataFrame(price_rows).to_parquet(raw / "prices.parquet", index=False)

    score_rows = []
    for c in commodities:
        for d in dates:
            score_rows.append({
                "date": d, "commodity": c,
                "score": float(rng.normal(0, 2)),
                "z_drawdown": float(rng.normal(0, 1)),
                "z_momentum": float(rng.normal(0, 1)),
                "z_positioning": float(rng.normal(0, 1)),
                "z_flows": float(rng.normal(0, 1)),
            })
    pd.DataFrame(score_rows).to_parquet(proc / "hate_scores.parquet", index=False)

    monkeypatch.setattr(bt, "TICKER_MAP", tickers)
    return tmp_path


def test_compute_component_calibration_returns_decile_table(fake_parquets):
    payload = bt.compute_component_calibration("z_drawdown", horizons=(4, 13, 26))
    assert "calibration" in payload
    assert "spread_top_minus_bottom" in payload
    assert "monotonic" in payload
    assert "n_total" in payload
    by_h = {h: [r for r in payload["calibration"] if r["horizon_w"] == h] for h in (4, 13, 26)}
    for h, rows in by_h.items():
        assert len(rows) == 10
        deciles = sorted(r["decile"] for r in rows)
        assert deciles == list(range(1, 11))
        assert all("mean_return" in r and "n" in r for r in rows)


def test_components_payload_includes_all_four_components(fake_parquets):
    payload = bt.build_components_payload(horizons=(4, 13))
    assert set(payload["components"].keys()) == {"drawdown", "momentum", "positioning", "flows"}
    for c, block in payload["components"].items():
        assert "calibration" in block
        assert "spread_top_minus_bottom" in block


def test_calibration_n_per_decile_is_balanced(fake_parquets):
    payload = bt.compute_component_calibration("z_drawdown", horizons=(13,))
    rows = [r for r in payload["calibration"] if r["horizon_w"] == 13]
    ns = [r["n"] for r in rows]
    assert min(ns) >= 60
    assert max(ns) <= 100


def test_main_writes_backtest_components_json(fake_parquets, tmp_path):
    rc = bt.main(write_components=True, write_signal=False)
    assert rc == 0
    out = json.loads((bt.DOCS_DIR / "backtest_components.json").read_text())
    assert "components" in out
    assert "as_of" in out
    assert out["horizons_weeks"] == [4, 13, 26, 52]


def test_composite_calibration_present(fake_parquets):
    payload = bt.build_components_payload(horizons=(13,))
    comp = payload["composite"]
    assert comp is not None
    assert "calibration" in comp
    assert "best_horizon" in comp
    assert "beats_best_component" in comp


def test_composite_beats_best_component_is_boolean(fake_parquets):
    payload = bt.build_components_payload()
    assert isinstance(payload["composite"]["beats_best_component"], bool)
