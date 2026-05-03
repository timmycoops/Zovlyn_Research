"""Payload-shape assertions for the augmented data.json output."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import build_site


@pytest.fixture
def fake_data(tmp_path, monkeypatch):
    """Wire build_site to read fixture parquets/JSON from tmp_path."""
    proc = tmp_path / "processed"; proc.mkdir(parents=True)
    raw = tmp_path / "raw"; raw.mkdir(parents=True)
    static = tmp_path / "static"; static.mkdir(parents=True)
    docs = tmp_path / "docs"; docs.mkdir(parents=True)

    monkeypatch.setattr(build_site, "PROC_DIR", proc)
    monkeypatch.setattr(build_site, "DOCS_DIR", docs)
    monkeypatch.setattr(build_site, "RAW_DIR", raw)
    monkeypatch.setattr(build_site, "STATIC_DIR", static)

    dates = pd.date_range("2024-04-26", periods=104, freq="W-FRI", tz="UTC")
    rows = []
    for c, t in build_site.TICKER_MAP.items():
        for i, d in enumerate(dates):
            rows.append({
                "date": d, "commodity": c,
                "score": float(i % 7 - 3),
                "drawdown": -0.20, "z_drawdown": 1.2,
                "rel_mom": -0.05, "z_momentum": 0.4,
                "z_positioning": None,
            })
    pd.DataFrame(rows).to_parquet(proc / "hate_scores.parquet", index=False)

    rrg_rows = []
    for c in build_site.TICKER_MAP:
        for i, d in enumerate(dates):
            rrg_rows.append({
                "date": d, "commodity": c,
                "rs_ratio": 100 + (i % 5),
                "rs_momentum": 100 - (i % 3),
                "quadrant": "Lagging",
            })
    pd.DataFrame(rrg_rows).to_parquet(proc / "rrg.parquet", index=False)

    cj = {c: {"members": [{"ticker": "FAKE", "name": "Fake Co",
                            "exchange": "NYSE", "role": "Pure-play"}]}
          for c in build_site.TICKER_MAP}
    (static / "constituents.json").write_text(json.dumps(cj))

    cp = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-17", "2026-04-24"], utc=True),
        "ticker": ["FAKE", "FAKE"],
        "close":  [100.0, 102.0],
    })
    cp.to_parquet(raw / "constituents_prices.parquet", index=False)
    return tmp_path


def test_payload_includes_commentary_for_every_commodity(fake_data):
    payload = build_site.build()
    for c in payload["commodities"]:
        assert "commentary" in c, f"{c['name']} missing commentary"
        assert set(c["commentary"]) == {"headline", "components", "rotation"}


def test_payload_includes_constituents_for_every_commodity(fake_data):
    payload = build_site.build()
    for c in payload["commodities"]:
        assert "constituents" in c
        assert isinstance(c["constituents"], list)
        if c["constituents"]:
            row = c["constituents"][0]
            assert set(row.keys()) >= {"ticker", "name", "exchange", "role",
                                       "last_close", "wow_pct", "stale"}


def test_constituents_wow_pct_computed(fake_data):
    payload = build_site.build()
    sample = payload["commodities"][0]["constituents"][0]
    assert sample["last_close"] == 102.0
    # (102 - 100) / 100 * 100 = 2.0%
    assert abs(sample["wow_pct"] - 2.0) < 0.01
    assert sample["stale"] is False
