# Commodity Detail Drill-Down — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-page commodity detail panel to the Hate Index dashboard that shows a 104-week score history, current-week component breakdown, plain-English commentary, and a curated constituents table.

**Architecture:** Hand-curated `constituents.json` defines sector membership; a new ingest step pulls weekly prices for all member tickers via yfinance; `build_site.py` joins everything and emits a `commentary` block (templated narration) and a `constituents` block per commodity in `data.json`; the dashboard adds a `CommodityDetailPanel` between the existing FIG 03 (RRG) and FIG 04 (signals) that hydrates from the existing `selected` state.

**Tech Stack:** Python 3.12, pandas, pyarrow, yfinance, pytest. Single-file React (via CDN) for the dashboard, no build step. Spec: `docs/superpowers/specs/2026-05-03-commodity-detail-design.md`.

**Two-phase plan:**
- **Phase 1 (Tasks 1–6):** backend / pipeline — strict TDD where applicable, frequent commits.
- **Phase 2 (Tasks 7–12):** dashboard — manual browser verification (no JS test runner is in scope; adding one would violate the "single-file React via CDN" non-goal in the spec).

---

## File Map

**New files (Phase 1):**
- `HateIndex/scripts/_yf_retry.py` — shared yfinance retry/backoff helper
- `HateIndex/scripts/ingest_constituents.py` — pulls weekly prices for constituent tickers
- `HateIndex/scripts/narrate.py` — pure functions that turn z-scores + status into commentary strings
- `HateIndex/data/static/constituents.json` — committed, hand-curated sector membership
- `HateIndex/tests/test_narrate.py` — table-driven tests for narration bands
- `HateIndex/tests/test_build_site_payload.py` — payload-shape assertions for the augmented `data.json`

**Modified files (Phase 1):**
- `HateIndex/scripts/ingest_prices.py` — use shared retry helper
- `HateIndex/scripts/build_site.py` — inject `commentary` + `constituents` per commodity
- `HateIndex/Makefile` — new `constituents` target; `refresh` chain extended
- `.github/workflows/weekly.yml` — new "Pull constituents" step

**Modified file (Phase 2):**
- `HateIndex/docs/index.html` — add `CommodityDetailPanel` and three sub-components (`ScoreHistoryChart`, `ComponentBars`, `ConstituentsTable`); plug it into the existing `selected` state between FIG 03 and FIG 04.

---

## Phase 1 — Pipeline & narration (TDD)

### Task 1: Extract yfinance retry/backoff helper

**Files:**
- Create: `HateIndex/scripts/_yf_retry.py`
- Modify: `HateIndex/scripts/ingest_prices.py` (replace `_download_once` + `fetch` with imports)
- Test: `HateIndex/tests/test_yf_retry.py` (new)

The existing retry/backoff lives inline in `ingest_prices.py`. Two ingest scripts will need it (`ingest_prices.py` and `ingest_constituents.py`), so extract first to keep the second DRY.

- [ ] **Step 1: Write the failing test**

```python
# HateIndex/tests/test_yf_retry.py
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd HateIndex && .venv/bin/pytest tests/test_yf_retry.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts._yf_retry'`

- [ ] **Step 3: Implement the helper**

```python
# HateIndex/scripts/_yf_retry.py
"""Shared yfinance retry/backoff helper.

Used by ingest_prices.py and ingest_constituents.py. Returns a long-format
frame with columns [date, ticker, close], or an empty frame after retries
are exhausted.
"""
from __future__ import annotations

import logging
import time

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_BASE_SECONDS = 2


def _normalise(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = (
        df.reset_index()[["Date", "Close"]]
        .rename(columns={"Date": "date", "Close": "close"})
        .assign(ticker=ticker)
        [["date", "ticker", "close"]]
    )
    out["date"] = pd.to_datetime(out["date"], utc=True)
    return out


def fetch_with_retry(
    ticker: str,
    period: str,
    interval: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_base_seconds: int = DEFAULT_BACKOFF_BASE_SECONDS,
) -> pd.DataFrame:
    """Fetch one ticker with retry-with-backoff. Returns empty frame on total failure."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            log.info("Fetching %s (attempt %d/%d)", ticker, attempt, max_attempts)
            raw = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
            )
            if raw.empty:
                raise RuntimeError(f"empty frame returned for {ticker}")
            return _normalise(raw, ticker)
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                wait = backoff_base_seconds ** attempt
                log.warning("Attempt %d failed for %s (%s); retrying in %ds",
                            attempt, ticker, e, wait)
                time.sleep(wait)
    log.error("All %d attempts failed for %s: %s", max_attempts, ticker, last_err)
    return pd.DataFrame(columns=["date", "ticker", "close"])
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd HateIndex && .venv/bin/pytest tests/test_yf_retry.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Refactor `ingest_prices.py` to use the helper**

In `HateIndex/scripts/ingest_prices.py`, delete the local `_download_once` and `fetch` functions and the `MAX_ATTEMPTS`/`BACKOFF_BASE_SECONDS` constants, then replace with:

```python
from scripts._yf_retry import fetch_with_retry

def fetch(ticker: str) -> pd.DataFrame:
    return fetch_with_retry(ticker, period=HISTORY_PERIOD, interval="1wk")
```

Keep everything else in `ingest_prices.py` unchanged (the `fetch_with_fallbacks` function still calls `fetch`).

- [ ] **Step 6: Run the full test suite to make sure nothing regressed**

```bash
cd HateIndex && .venv/bin/pytest tests/ -v
```
Expected: 8 passed (5 existing + 3 new).

- [ ] **Step 7: Commit**

```bash
git add HateIndex/scripts/_yf_retry.py HateIndex/scripts/ingest_prices.py HateIndex/tests/test_yf_retry.py
git commit -m "refactor: extract yfinance retry/backoff into shared helper"
```

---

### Task 2: Seed `constituents.json`

**Files:**
- Create: `HateIndex/data/static/constituents.json`

This is a hand-curated data file. Tim must review the names before commit. There are no tests — it's a static fixture; downstream tasks validate that it loads.

- [ ] **Step 1: Create the file with seeded names**

```json
{
  "Lithium": {
    "members": [
      {"ticker": "ALB", "name": "Albemarle", "exchange": "NYSE", "role": "Major"},
      {"ticker": "SQM", "name": "SQM", "exchange": "NYSE", "role": "Major"},
      {"ticker": "PLS.AX", "name": "Pilbara Minerals", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "LTR.AX", "name": "Liontown Resources", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "MIN.AX", "name": "Mineral Resources", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "LAC", "name": "Lithium Americas", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "PMET.TO", "name": "Patriot Battery Metals", "exchange": "TSX", "role": "Pure-play"},
      {"ticker": "LIT", "name": "Global X Lithium ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Uranium": {
    "members": [
      {"ticker": "CCJ", "name": "Cameco", "exchange": "NYSE", "role": "Major"},
      {"ticker": "PDN.AX", "name": "Paladin Energy", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "BOE.AX", "name": "Boss Energy", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "DNN", "name": "Denison Mines", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "NXE", "name": "NexGen Energy", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "URA", "name": "Global X Uranium ETF", "exchange": "NYSE", "role": "ETF"},
      {"ticker": "URNM", "name": "Sprott Uranium Miners ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Copper": {
    "members": [
      {"ticker": "FCX", "name": "Freeport-McMoRan", "exchange": "NYSE", "role": "Major"},
      {"ticker": "BHP.AX", "name": "BHP Group", "exchange": "ASX", "role": "Major"},
      {"ticker": "RIO.AX", "name": "Rio Tinto", "exchange": "ASX", "role": "Major"},
      {"ticker": "SCCO", "name": "Southern Copper", "exchange": "NYSE", "role": "Major"},
      {"ticker": "SFR.AX", "name": "Sandfire Resources", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "29M.AX", "name": "29Metals", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "COPX", "name": "Global X Copper Miners ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Gold": {
    "members": [
      {"ticker": "NEM", "name": "Newmont", "exchange": "NYSE", "role": "Major"},
      {"ticker": "NST.AX", "name": "Northern Star Resources", "exchange": "ASX", "role": "Major"},
      {"ticker": "EVN.AX", "name": "Evolution Mining", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "GOLD", "name": "Barrick Gold", "exchange": "NYSE", "role": "Major"},
      {"ticker": "AEM", "name": "Agnico Eagle Mines", "exchange": "NYSE", "role": "Major"},
      {"ticker": "GLD", "name": "SPDR Gold Shares", "exchange": "NYSE", "role": "ETF"},
      {"ticker": "GDX", "name": "VanEck Gold Miners ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Silver": {
    "members": [
      {"ticker": "PAAS", "name": "Pan American Silver", "exchange": "NYSE", "role": "Major"},
      {"ticker": "FSM", "name": "Fortuna Silver Mines", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "AG", "name": "First Majestic Silver", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "SLV", "name": "iShares Silver Trust", "exchange": "NYSE", "role": "ETF"},
      {"ticker": "SIL", "name": "Global X Silver Miners ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Rare Earths": {
    "members": [
      {"ticker": "MP", "name": "MP Materials", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "LYC.AX", "name": "Lynas Rare Earths", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "ILU.AX", "name": "Iluka Resources", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "ARU.AX", "name": "Arafura Rare Earths", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "REMX", "name": "VanEck Rare Earth & Strategic Metals ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Crude Oil": {
    "members": [
      {"ticker": "XOM", "name": "ExxonMobil", "exchange": "NYSE", "role": "Major"},
      {"ticker": "CVX", "name": "Chevron", "exchange": "NYSE", "role": "Major"},
      {"ticker": "WDS.AX", "name": "Woodside Energy", "exchange": "ASX", "role": "Major"},
      {"ticker": "STO.AX", "name": "Santos", "exchange": "ASX", "role": "Major"},
      {"ticker": "OXY", "name": "Occidental Petroleum", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "USO", "name": "United States Oil Fund", "exchange": "NYSE", "role": "ETF"},
      {"ticker": "XLE", "name": "Energy Select Sector SPDR", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Nat Gas": {
    "members": [
      {"ticker": "EQT", "name": "EQT Corporation", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "AR", "name": "Antero Resources", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "RRC", "name": "Range Resources", "exchange": "NYSE", "role": "Pure-play"},
      {"ticker": "CHK", "name": "Chesapeake Energy", "exchange": "NASDAQ", "role": "Pure-play"},
      {"ticker": "UNG", "name": "United States Natural Gas Fund", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "PGMs": {
    "members": [
      {"ticker": "SBSW", "name": "Sibanye Stillwater", "exchange": "NYSE", "role": "Major"},
      {"ticker": "AAL.L", "name": "Anglo American Platinum (parent)", "exchange": "LSE", "role": "Major"},
      {"ticker": "IMPUY", "name": "Impala Platinum", "exchange": "OTC", "role": "Major"},
      {"ticker": "PPLT", "name": "Aberdeen Standard Physical Platinum Shares", "exchange": "NYSE", "role": "ETF"},
      {"ticker": "PALL", "name": "Aberdeen Standard Physical Palladium Shares", "exchange": "NYSE", "role": "ETF"}
    ]
  },
  "Iron Ore": {
    "members": [
      {"ticker": "FMG.AX", "name": "Fortescue", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "BHP.AX", "name": "BHP Group", "exchange": "ASX", "role": "Major"},
      {"ticker": "RIO.AX", "name": "Rio Tinto", "exchange": "ASX", "role": "Major"},
      {"ticker": "VALE", "name": "Vale", "exchange": "NYSE", "role": "Major"},
      {"ticker": "MGX.AX", "name": "Mount Gibson Iron", "exchange": "ASX", "role": "Junior"},
      {"ticker": "CIA.TO", "name": "Champion Iron", "exchange": "TSX", "role": "Pure-play"}
    ]
  },
  "Thermal Coal": {
    "members": [
      {"ticker": "BTU", "name": "Peabody Energy", "exchange": "NYSE", "role": "Major"},
      {"ticker": "WHC.AX", "name": "Whitehaven Coal", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "NHC.AX", "name": "New Hope Corporation", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "YAL.AX", "name": "Yancoal Australia", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "ARCH", "name": "Arch Resources", "exchange": "NYSE", "role": "Pure-play"}
    ]
  },
  "Nickel": {
    "members": [
      {"ticker": "VALE", "name": "Vale", "exchange": "NYSE", "role": "Major"},
      {"ticker": "NIC.AX", "name": "Nickel Industries", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "WSA.AX", "name": "Western Areas (delisted; placeholder)", "exchange": "ASX", "role": "Junior"},
      {"ticker": "IGO.AX", "name": "IGO Limited", "exchange": "ASX", "role": "Pure-play"},
      {"ticker": "PICK", "name": "iShares MSCI Global Metals & Mining Producers ETF", "exchange": "NYSE", "role": "ETF"}
    ]
  }
}
```

- [ ] **Step 2: Validate the JSON loads**

```bash
cd HateIndex && .venv/bin/python -c "import json; d = json.load(open('data/static/constituents.json')); print(f'{len(d)} commodities, {sum(len(v[\"members\"]) for v in d.values())} total tickers')"
```
Expected: `12 commodities, 76 total tickers` (give or take if Tim red-lines names).

- [ ] **Step 3: Tim reviews the list**

Tim opens `HateIndex/data/static/constituents.json` and either approves as-is or replaces specific entries. Particular things to check: WSA.AX is delisted (intentionally there as a placeholder so the cron-warning path gets exercised); IRON.AX is intentionally not present (Iron Ore uses FMG.AX as primary now); the PGM list mixes platinum and palladium proxies which is correct for a single commodity bucket.

- [ ] **Step 4: Commit**

```bash
git add HateIndex/data/static/constituents.json
git commit -m "data: seed constituents.json with curated sector membership"
```

---

### Task 3: Implement `ingest_constituents.py`

**Files:**
- Create: `HateIndex/scripts/ingest_constituents.py`
- Test: `HateIndex/tests/test_ingest_constituents.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# HateIndex/tests/test_ingest_constituents.py
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd HateIndex && .venv/bin/pytest tests/test_ingest_constituents.py -v
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the ingest script**

```python
# HateIndex/scripts/ingest_constituents.py
"""
Pull weekly close prices for all constituent tickers from constituents.json.

Run: python scripts/ingest_constituents.py
Output: data/raw/constituents_prices.parquet (long format: date, ticker, close)
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

from scripts._yf_retry import fetch_with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "data" / "static" / "constituents.json"
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PERIOD = "3mo"   # we only need the latest two weekly closes; pull a small buffer


def collect_unique_tickers(path: Path = STATIC) -> list[str]:
    cj = json.loads(path.read_text())
    seen: set[str] = set()
    for entry in cj.values():
        for m in entry["members"]:
            seen.add(m["ticker"])
    return sorted(seen)


def build_long_frame(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    out = pd.concat(non_empty, ignore_index=True)
    return out.sort_values(["ticker", "date"]).reset_index(drop=True)


def main() -> int:
    tickers = collect_unique_tickers()
    log.info("Pulling %d constituent tickers", len(tickers))
    frames: list[pd.DataFrame] = []
    failed: list[str] = []
    for t in tickers:
        df = fetch_with_retry(t, period=PERIOD, interval="1wk")
        if df.empty:
            failed.append(t)
        else:
            frames.append(df)

    combined = build_long_frame(frames)
    out_path = RAW_DIR / "constituents_prices.parquet"
    combined.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d tickers -> %s",
             len(combined), combined["ticker"].nunique(), out_path)
    if failed:
        log.warning("Tickers that failed all retries (edit constituents.json or accept stale): %s", failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd HateIndex && .venv/bin/pytest tests/test_ingest_constituents.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Smoke-run against real yfinance**

```bash
cd HateIndex && .venv/bin/python scripts/ingest_constituents.py 2>&1 | tail -10
```
Expected: log line `Wrote N rows for M tickers -> .../constituents_prices.parquet`. M should be ~70 (76 minus a few delisted/flaky names like WSA.AX). A `WARNING` line listing the failed tickers is expected and acceptable.

- [ ] **Step 6: Commit**

```bash
git add HateIndex/scripts/ingest_constituents.py HateIndex/tests/test_ingest_constituents.py HateIndex/data/raw/constituents_prices.parquet
git commit -m "feat: ingest_constituents pulls weekly closes for sector members"
```

---

### Task 4: Implement `narrate.py`

**Files:**
- Create: `HateIndex/scripts/narrate.py`
- Test: `HateIndex/tests/test_narrate.py`

Pure functions only — table-driven tests cover each band of each component plus null-handling.

- [ ] **Step 1: Write the failing tests**

```python
# HateIndex/tests/test_narrate.py
"""Table-driven tests for narration band helpers. Pure functions, no I/O."""
from __future__ import annotations

import pytest

from scripts.narrate import (
    drawdown_phrase,
    momentum_phrase,
    positioning_phrase,
    headline_phrase,
    rotation_phrase,
    build_commentary,
)


@pytest.mark.parametrize("z, dd, expect_substr", [
    (2.5, -0.42, "deeper drawdown than 95%"),
    (1.4, -0.28, "more depressed than two-thirds"),
    (0.1, -0.05, "normal historical range"),
    (-1.5, 0.10, "no drawdown signal"),
    (None, -0.20, None),
])
def test_drawdown_phrase_bands(z, dd, expect_substr):
    out = drawdown_phrase(z, dd)
    if expect_substr is None:
        assert out is None
    else:
        assert expect_substr in out


@pytest.mark.parametrize("z, expect_substr", [
    (2.0, "underperforming the benchmark"),
    (0.0, "tracking the benchmark"),
    (-1.5, "outperforming the benchmark"),
    (None, None),
])
def test_momentum_phrase_bands(z, expect_substr):
    out = momentum_phrase(z)
    if expect_substr is None:
        assert out is None
    else:
        assert expect_substr in out


def test_positioning_phrase_null_returns_none():
    assert positioning_phrase(None) is None


def test_positioning_phrase_negative_z_means_long():
    assert "long" in positioning_phrase(-1.5).lower()


def test_positioning_phrase_positive_z_means_short():
    assert "short" in positioning_phrase(1.5).lower()


def test_headline_phrase_includes_score_and_rank():
    out = headline_phrase("Lithium", -1.0, universe_scores=[1.9, 0.8, -1.0, -1.2])
    assert "Lithium" in out
    assert "-1.0" in out


def test_rotation_phrase_unchanged_status():
    assert "Lagging" in rotation_phrase("Lagging", just_entered=False)


def test_rotation_phrase_just_entered_leading_is_flagged():
    out = rotation_phrase("Lagging→Leading", just_entered=True)
    assert "fresh" in out.lower() or "rotated" in out.lower()


def test_build_commentary_returns_three_keys():
    out = build_commentary(
        name="Lithium",
        score=-1.0,
        universe_scores=[1.9, 0.8, -1.0, -1.2],
        components={"drawdown": 1.4, "momentum": 0.6, "positioning": None,
                    "flows": None, "valuation": None, "sentiment": None},
        drawdown_pct=-0.28,
        status="Lagging→Leading",
        just_entered=True,
    )
    assert set(out.keys()) == {"headline", "components", "rotation"}
    assert isinstance(out["components"], list)
    # null components produce explicit "not available" notes
    assert any("not available" in s.lower() for s in out["components"])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd HateIndex && .venv/bin/pytest tests/test_narrate.py -v
```
Expected: all FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `narrate.py`**

```python
# HateIndex/scripts/narrate.py
"""
Pure-function narration helpers.

Each component has a band-based template that turns a z-score into a sentence
in the project voice (numbers + comparison + caveat; no exclamation marks).
build_commentary() composes the three blocks the dashboard reads.
"""
from __future__ import annotations

from typing import Optional


def drawdown_phrase(z: Optional[float], drawdown_pct: float) -> Optional[str]:
    if z is None:
        return None
    abs_dd = abs(drawdown_pct) * 100
    if z >= 2:
        return f"Trading {abs_dd:.0f}% below 5-year max — deeper drawdown than 95% of historical weeks."
    if z >= 1:
        return f"Trading {abs_dd:.0f}% below 5-year max — more depressed than two-thirds of weeks."
    if z >= -1:
        return "Drawdown is in the normal historical range."
    return "Above its 5-year average — no drawdown signal."


def momentum_phrase(z: Optional[float]) -> Optional[str]:
    if z is None:
        return None
    if z >= 1:
        return "Underperforming the benchmark — relative momentum negative."
    if z <= -1:
        return "Outperforming the benchmark — relative momentum positive."
    return "Tracking the benchmark — no momentum signal."


def positioning_phrase(z: Optional[float]) -> Optional[str]:
    if z is None:
        return None
    if z >= 1:
        return "Managed money is short — extreme bearish positioning."
    if z <= -1:
        return "Managed money is long — extreme bullish positioning."
    return "Managed money positioning is neutral."


def headline_phrase(name: str, score: float, universe_scores: list[float]) -> str:
    sorted_desc = sorted(universe_scores, reverse=True)
    rank = sorted_desc.index(score) + 1 if score in sorted_desc else len(sorted_desc)
    n = len(sorted_desc)
    if rank <= n / 3:
        rank_label = "top third — the market hates this"
    elif rank <= 2 * n / 3:
        rank_label = "middle of the pack"
    else:
        rank_label = "bottom third — not yet hated"
    return f"{name} at {score:+.1f} sits in the {rank_label}."


def rotation_phrase(status: str, just_entered: bool) -> str:
    if just_entered and "Leading" in status:
        return f"{status}: rotated into Leading — fresh momentum, signal active."
    if just_entered and "Improving" in status:
        return f"{status}: rotated into Improving — early-stage rotation."
    if "→" in status:
        return f"{status}: rotation in progress."
    return f"{status}: unchanged this week."


def build_commentary(
    name: str,
    score: float,
    universe_scores: list[float],
    components: dict,
    drawdown_pct: float,
    status: str,
    just_entered: bool,
) -> dict:
    parts: list[str] = []
    dd = drawdown_phrase(components.get("drawdown"), drawdown_pct)
    mo = momentum_phrase(components.get("momentum"))
    po = positioning_phrase(components.get("positioning"))
    if dd: parts.append(dd)
    if mo: parts.append(mo)
    if po: parts.append(po)
    else:  parts.append("Positioning data not available — CFTC does not publish a managed-money series for this contract.")
    for k in ("flows", "valuation", "sentiment"):
        if components.get(k) is None:
            parts.append(f"{k.title()} component not yet implemented (Phase 7).")

    return {
        "headline":   headline_phrase(name, score, universe_scores),
        "components": parts,
        "rotation":   rotation_phrase(status, just_entered),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd HateIndex && .venv/bin/pytest tests/test_narrate.py -v
```
Expected: all 12+ tests passed.

- [ ] **Step 5: Commit**

```bash
git add HateIndex/scripts/narrate.py HateIndex/tests/test_narrate.py
git commit -m "feat: narrate.py — band-based templates for score commentary"
```

---

### Task 5: Augment `build_site.py` with `commentary` + `constituents`

**Files:**
- Modify: `HateIndex/scripts/build_site.py`
- Test: `HateIndex/tests/test_build_site_payload.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# HateIndex/tests/test_build_site_payload.py
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
        "date": pd.to_datetime(["2026-04-17", "2026-04-24"] * 1, utc=True),
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd HateIndex && .venv/bin/pytest tests/test_build_site_payload.py -v
```
Expected: FAIL — `commentary` key missing or `STATIC_DIR` not defined.

- [ ] **Step 3: Modify `build_site.py`**

Add at the top of the file, near the existing constants:

```python
STATIC_DIR = ROOT / "data" / "static"
```

Add new imports:

```python
from scripts.narrate import build_commentary
```

Add a helper near the existing `nullable` function:

```python
def _build_constituents(commodity: str, prices: pd.DataFrame, static: dict) -> list[dict]:
    """Join static member metadata with the latest 2 weekly closes per ticker."""
    members = static.get(commodity, {}).get("members", [])
    out: list[dict] = []
    for m in members:
        sub = prices[prices["ticker"] == m["ticker"]].sort_values("date")
        if len(sub) >= 2:
            prev, last = sub.iloc[-2]["close"], sub.iloc[-1]["close"]
            wow = (last - prev) / prev * 100 if prev else 0.0
            out.append({**m, "last_close": round(float(last), 2),
                              "wow_pct": round(float(wow), 2),
                              "stale": False})
        elif len(sub) == 1:
            out.append({**m, "last_close": round(float(sub.iloc[-1]["close"]), 2),
                              "wow_pct": None, "stale": True})
        else:
            out.append({**m, "last_close": None, "wow_pct": None, "stale": True})
    # ETFs to the bottom; pure-plays first, then majors, then juniors
    role_order = {"Pure-play": 0, "Major": 1, "Junior": 2, "ETF": 3}
    out.sort(key=lambda r: (role_order.get(r["role"], 9), r.get("name", "")))
    return out
```

In the `build()` function, after the existing `as_of` block and before the `for commodity in TICKER_MAP:` loop, load the static + constituent prices:

```python
    static_path = STATIC_DIR / "constituents.json"
    static_data = json.loads(static_path.read_text()) if static_path.exists() else {}

    cp_path = RAW_DIR / "constituents_prices.parquet"
    if cp_path.exists():
        constituent_prices = pd.read_parquet(cp_path)
        constituent_prices["date"] = pd.to_datetime(constituent_prices["date"], utc=True)
    else:
        constituent_prices = pd.DataFrame(columns=["date", "ticker", "close"])
```

Also add `RAW_DIR = ROOT / "data" / "raw"` at the top alongside `PROC_DIR` if not already there.

Inside the per-commodity loop, after computing `components` and just before `commodities_payload.append(...)`, add:

```python
        universe_scores = [
            float(scores[(scores["commodity"] == k) & (scores["date"] <= as_of)]
                  .sort_values("date").iloc[-1]["score"])
            for k in TICKER_MAP
            if not scores[(scores["commodity"] == k) & (scores["date"] <= as_of)].empty
        ]
        commentary = build_commentary(
            name=commodity,
            score=round(float(latest["score"]), 2),
            universe_scores=universe_scores,
            components=components,
            drawdown_pct=float(latest.get("drawdown") or 0.0),
            status=status,
            just_entered=bool(just_entered),
        )
        constituents = _build_constituents(commodity, constituent_prices, static_data)
```

Then extend the dict appended to `commodities_payload` with two new keys:

```python
            "commentary":   commentary,
            "constituents": constituents,
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd HateIndex && .venv/bin/pytest tests/test_build_site_payload.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Run the full pipeline against real data**

```bash
cd HateIndex && make refresh
```
Expected: ends with `Pipeline refresh complete.` and no errors. The new `data.json` should be larger (~6 MB) and contain `commentary` + `constituents` blocks.

Spot-check:

```bash
cd HateIndex && .venv/bin/python -c "
import json
d = json.load(open('docs/data.json'))
c = d['commodities'][0]
print('name:', c['name'])
print('commentary keys:', list(c['commentary'].keys()))
print('headline:', c['commentary']['headline'])
print('first constituent:', c['constituents'][0])
"
```

- [ ] **Step 6: Run the full test suite**

```bash
cd HateIndex && .venv/bin/pytest tests/ -v
```
Expected: all tests passed (5 existing + 3 yf_retry + 2 ingest_constituents + ~12 narrate + 3 payload = ~25 total).

- [ ] **Step 7: Commit**

```bash
git add HateIndex/scripts/build_site.py HateIndex/tests/test_build_site_payload.py HateIndex/docs/data.json HateIndex/data/raw/constituents_prices.parquet
git commit -m "feat: build_site emits commentary and constituents per commodity"
```

---

### Task 6: Wire into `Makefile` and the workflow

**Files:**
- Modify: `HateIndex/Makefile`
- Modify: `.github/workflows/weekly.yml`

- [ ] **Step 1: Update `HateIndex/Makefile`**

Add `constituents` to the `.PHONY` line and the help block, add a target, and insert it into the `refresh` chain:

Replace:
```makefile
.PHONY: help install ingest score rrg site backtest refresh test serve clean
```
with:
```makefile
.PHONY: help install ingest constituents score rrg site backtest refresh test serve clean
```

In the `help` block, add this line below the `ingest` line:
```makefile
	@echo "  constituents - pull weekly closes for sector constituents"
```

Add a new target near the others:
```makefile
constituents:
	$(PYTHON) scripts/ingest_constituents.py
```

Replace:
```makefile
refresh: ingest score rrg site
```
with:
```makefile
refresh: ingest constituents score rrg site
```

- [ ] **Step 2: Verify `make refresh` runs end-to-end with the new step in place**

```bash
cd HateIndex && make refresh
```
Expected: a `Pulling N constituent tickers` log line and no errors.

- [ ] **Step 3: Update `.github/workflows/weekly.yml`**

After the `Ingest CFTC` step (which has `continue-on-error: true`), insert:

```yaml
      - name: Pull constituents
        run: python scripts/ingest_constituents.py
        continue-on-error: true   # constituent fetch failures should not fail the cron
```

Update the `Commit refreshed data` step to also include the new parquet:

Replace:
```yaml
          git add HateIndex/data/ HateIndex/docs/data.json
```
with:
```yaml
          git add HateIndex/data/ HateIndex/docs/data.json
```
(no change actually needed — `HateIndex/data/` already covers `data/raw/constituents_prices.parquet`. Keep as-is. Just verify by inspection.)

- [ ] **Step 4: Commit**

```bash
git add HateIndex/Makefile .github/workflows/weekly.yml
git commit -m "chore: wire constituents ingest into Makefile + weekly cron"
```

---

## Phase 2 — Dashboard

Phase 2 modifies `HateIndex/docs/index.html` only. There is no JS test runner; verification is by `make serve` and visual inspection in a browser. Each task ends with a manual smoke test and a commit.

### Task 7: Add empty `CommodityDetailPanel` between FIG 03 and FIG 04

**Files:**
- Modify: `HateIndex/docs/index.html`

- [ ] **Step 1: Add the panel JSX between FIG 03 and FIG 04**

Find the existing block in `HateIndex/docs/index.html` that starts:

```jsx
      <div className="panel" style={{ padding: 22 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div className="mono" style={{ fontSize: 9, color: BRAND.textDim, letterSpacing: '0.15em' }}>FIG 04 · WEEKLY SIGNAL</div>
```

Immediately *before* that `<div className="panel"...>` (FIG 04), insert:

```jsx
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <div className="mono" style={{ fontSize: 9, color: BRAND.textDim, letterSpacing: '0.15em' }}>FIG 03.5 · COMMODITY DETAIL</div>
          <h2 className="display" style={{ fontSize: 22, fontWeight: 500, margin: '4px 0 0' }}>
            {selected || 'Pick a commodity'}
          </h2>
        </div>
        <CommodityDetailPanel data={data} selected={selected} setSelected={setSelected} />
      </div>
```

- [ ] **Step 2: Add the `CommodityDetailPanel` component definition**

Below the existing `RRGPanel` component definition, add:

```jsx
function CommodityDetailPanel({ data, selected, setSelected }) {
  const c = data.find(d => d.name === selected);
  if (!c) {
    return (
      <div style={{ padding: 24, color: BRAND.textDim, fontSize: 12, fontStyle: 'italic' }}>
        Hover the rotation map or click a row in the leaderboard to drill in.
      </div>
    );
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '7fr 5fr', gap: 18 }}>
      <div>
        {/* Score history + components — Tasks 8 & 9 */}
        <div style={{ height: 140, background: BRAND.panel, border: `1px solid ${BRAND.border}`, borderRadius: 4, marginBottom: 12, display: 'grid', placeItems: 'center', color: BRAND.textDim, fontSize: 11 }}>
          ScoreHistoryChart placeholder — Task 8
        </div>
        <div style={{ height: 120, background: BRAND.panel, border: `1px solid ${BRAND.border}`, borderRadius: 4, display: 'grid', placeItems: 'center', color: BRAND.textDim, fontSize: 11 }}>
          ComponentBars placeholder — Task 9
        </div>
      </div>
      <div>
        {/* Commentary + constituents — Tasks 10 & 11 */}
        <div style={{ marginBottom: 16, color: BRAND.textDim, fontSize: 11 }}>
          Commentary placeholder — Task 10
        </div>
        <div style={{ color: BRAND.textDim, fontSize: 11 }}>
          ConstituentsTable placeholder — Task 11
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire the leaderboard rows to set `selected`**

Find the leaderboard row click handler (search for `onClick={() => setSelected(`). It should already exist — confirm it does. If not, add `onClick={() => setSelected(d.name)}` to the leaderboard row's outer wrapper.

- [ ] **Step 4: Smoke-test in browser**

```bash
cd HateIndex && make serve
```

Open http://localhost:8000. Expected:
- A new "FIG 03.5 · COMMODITY DETAIL" panel appears between the rotation map and the weekly signal section.
- With nothing selected: shows the placeholder "Hover the rotation map or click a row in the leaderboard to drill in."
- Hover a tail in the RRG: panel header changes to that commodity, two grey placeholder boxes appear.
- Click a leaderboard row: same as hover but sticky.

- [ ] **Step 5: Commit**

```bash
git add HateIndex/docs/index.html
git commit -m "feat: scaffold CommodityDetailPanel between FIG 03 and FIG 04"
```

---

### Task 8: `ScoreHistoryChart`

**Files:**
- Modify: `HateIndex/docs/index.html`

- [ ] **Step 1: Add component definition below `RRGPanel`**

```jsx
function ScoreHistoryChart({ history, score }) {
  if (!history || history.length === 0) return null;
  const W = 700, H = 140, P = { top: 12, right: 12, bottom: 22, left: 36 };
  const cw = W - P.left - P.right, ch = H - P.top - P.bottom;
  const ys = history.map(h => h.score);
  const yMin = Math.min(-2, ...ys) - 0.5;
  const yMax = Math.max(10, ...ys) + 0.5;
  const xScale = i => P.left + (i / (history.length - 1)) * cw;
  const yScale = y => P.top + (1 - (y - yMin) / (yMax - yMin)) * ch;
  const path = history.map((h, i) => `${i === 0 ? 'M' : 'L'}${xScale(i)},${yScale(h.score)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {[4, 8].map(t => (
        <g key={t}>
          <line x1={P.left} y1={yScale(t)} x2={P.left + cw} y2={yScale(t)}
                stroke={t === 8 ? BRAND.orange : BRAND.pink} strokeOpacity={0.5}
                strokeDasharray="3 4" />
          <text x={P.left + cw + 4} y={yScale(t) + 3} fontSize={9} fill={BRAND.textDim}
                fontFamily="JetBrains Mono">{t === 8 ? 'capitulation' : 'hated'}</text>
        </g>
      ))}
      <line x1={P.left} y1={yScale(0)} x2={P.left + cw} y2={yScale(0)}
            stroke={BRAND.textMute} strokeOpacity={0.4} />
      <path d={path} fill="none" stroke={BRAND.green} strokeWidth={1.5} />
      <text x={P.left} y={H - 6} fontSize={9} fill={BRAND.textDim} fontFamily="JetBrains Mono">
        {history[0].date} → {history[history.length - 1].date}
      </text>
      <text x={P.left - 8} y={yScale(yMax) + 4} fontSize={9} fill={BRAND.textDim}
            fontFamily="JetBrains Mono" textAnchor="end">{yMax.toFixed(1)}</text>
      <text x={P.left - 8} y={yScale(yMin) + 4} fontSize={9} fill={BRAND.textDim}
            fontFamily="JetBrains Mono" textAnchor="end">{yMin.toFixed(1)}</text>
    </svg>
  );
}
```

- [ ] **Step 2: Replace the score-history placeholder in `CommodityDetailPanel`**

Replace this block:
```jsx
        <div style={{ height: 140, ...placeholder for ScoreHistoryChart... }}>
          ScoreHistoryChart placeholder — Task 8
        </div>
```
with:
```jsx
        <div style={{ marginBottom: 12 }}>
          <ScoreHistoryChart history={c.score_history} score={c.score} />
        </div>
```

- [ ] **Step 3: Smoke-test in browser**

`make serve`, then click various commodities. Expected:
- A green line traces the 104-week history.
- Two horizontal dashed reference lines (orange at 8, pink at 4) labelled "capitulation" / "hated".
- X-axis label shows the date range.
- Y-axis labels show the min/max bounds.

- [ ] **Step 4: Commit**

```bash
git add HateIndex/docs/index.html
git commit -m "feat: ScoreHistoryChart in the commodity detail panel"
```

---

### Task 9: `ComponentBars`

**Files:**
- Modify: `HateIndex/docs/index.html`

- [ ] **Step 1: Add component definition below `ScoreHistoryChart`**

```jsx
function ComponentBars({ components }) {
  const ORDER = ['drawdown', 'momentum', 'positioning', 'flows', 'valuation', 'sentiment'];
  const W = 700, H = 120, P = { top: 8, right: 60, bottom: 8, left: 100 };
  const rh = (H - P.top - P.bottom) / ORDER.length;
  const xRange = 3.5;  // bars span ±3.5 z-units
  const cx = P.left + (W - P.left - P.right) / 2;
  const xScale = z => cx + (z / xRange) * ((W - P.left - P.right) / 2);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      <line x1={cx} y1={P.top} x2={cx} y2={H - P.bottom} stroke={BRAND.textMute} strokeOpacity={0.4} />
      {ORDER.map((name, i) => {
        const z = components[name];
        const y = P.top + i * rh;
        const isNull = z === null || z === undefined;
        const barEnd = isNull ? cx : xScale(z);
        return (
          <g key={name}>
            <text x={P.left - 8} y={y + rh / 2 + 4} fontSize={11}
                  fill={isNull ? BRAND.textDim : BRAND.text}
                  fontFamily="JetBrains Mono" textAnchor="end">{name}</text>
            {isNull ? (
              <rect x={cx - 1} y={y + 4} width={2} height={rh - 8}
                    fill={BRAND.textDim} opacity={0.3} />
            ) : (
              <rect x={Math.min(cx, barEnd)} y={y + 4}
                    width={Math.abs(barEnd - cx)} height={rh - 8}
                    fill={z >= 0 ? BRAND.green : BRAND.red} opacity={0.85} />
            )}
            <text x={W - P.right + 4} y={y + rh / 2 + 4} fontSize={10}
                  fill={isNull ? BRAND.textDim : BRAND.text}
                  fontFamily="JetBrains Mono">
              {isNull ? 'phase 7' : (z >= 0 ? '+' : '') + z.toFixed(2)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

- [ ] **Step 2: Replace the component-bars placeholder in `CommodityDetailPanel`**

Replace:
```jsx
        <div style={{ height: 120, ...placeholder for ComponentBars... }}>
          ComponentBars placeholder — Task 9
        </div>
```
with:
```jsx
        <ComponentBars components={c.components} />
```

- [ ] **Step 3: Smoke-test**

`make serve`. Expected:
- 6 horizontal bars, one per component, with names on the left and z-score values on the right.
- `drawdown`, `momentum`, `positioning` have green/pink coloured bars depending on sign.
- `flows`, `valuation`, `sentiment` show as ghosted thin strokes labelled "phase 7".

- [ ] **Step 4: Commit**

```bash
git add HateIndex/docs/index.html
git commit -m "feat: ComponentBars in the commodity detail panel"
```

---

### Task 10: Commentary block

**Files:**
- Modify: `HateIndex/docs/index.html`

- [ ] **Step 1: Replace the commentary placeholder in `CommodityDetailPanel`**

Replace:
```jsx
        <div style={{ marginBottom: 16, color: BRAND.textDim, fontSize: 11 }}>
          Commentary placeholder — Task 10
        </div>
```
with:
```jsx
        <div style={{ marginBottom: 18 }}>
          <div className="mono" style={{ fontSize: 9, color: BRAND.textDim, letterSpacing: '0.15em', marginBottom: 6 }}>
            WHAT THE SCORE MEANS
          </div>
          <p style={{ fontSize: 13, fontWeight: 600, color: BRAND.text, lineHeight: 1.45, margin: '0 0 10px' }}>
            {c.commentary.headline}
          </p>
          <ul style={{ fontSize: 12, color: BRAND.textMute, lineHeight: 1.55, paddingLeft: 16, margin: '0 0 10px' }}>
            {c.commentary.components.map((line, i) => (
              <li key={i} style={{ marginBottom: 4 }}>{line}</li>
            ))}
          </ul>
          <p style={{ fontSize: 12, color: BRAND.text, lineHeight: 1.45, margin: 0, fontStyle: 'italic' }}>
            {c.commentary.rotation}
          </p>
        </div>
```

- [ ] **Step 2: Smoke-test**

`make serve`. Click various commodities. Expected:
- "WHAT THE SCORE MEANS" header in mono caps.
- Bold headline sentence (Lithium-specific framing of the score).
- Bullet list of component sentences (3–6 lines, including the "Phase 7" notes for null components).
- Italic rotation sentence.

- [ ] **Step 3: Commit**

```bash
git add HateIndex/docs/index.html
git commit -m "feat: commentary block in the commodity detail panel"
```

---

### Task 11: `ConstituentsTable`

**Files:**
- Modify: `HateIndex/docs/index.html`

- [ ] **Step 1: Add component definition**

```jsx
function ConstituentsTable({ rows }) {
  if (!rows || rows.length === 0) {
    return <div style={{ color: BRAND.textDim, fontSize: 11 }}>No constituents configured.</div>;
  }
  const fmtPx = v => v == null ? '—' : v.toFixed(2);
  const fmtPct = v => {
    if (v == null) return '—';
    const sign = v > 0 ? '+' : '';
    return `${sign}${v.toFixed(2)}%`;
  };
  const colorPct = v => v == null ? BRAND.textDim : v > 0 ? BRAND.green : v < 0 ? BRAND.red : BRAND.textMute;
  return (
    <div>
      <div className="mono" style={{ fontSize: 9, color: BRAND.textDim, letterSpacing: '0.15em', marginBottom: 8 }}>
        SECTOR · COMPANIES ON THE DESK
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: 'JetBrains Mono' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${BRAND.border}`, color: BRAND.textDim }}>
            <th style={{ textAlign: 'left',  padding: '4px 6px' }}>Ticker</th>
            <th style={{ textAlign: 'left',  padding: '4px 6px' }}>Name</th>
            <th style={{ textAlign: 'left',  padding: '4px 6px' }}>Role</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>Last</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>WoW</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.ticker} style={{ borderBottom: `1px solid ${BRAND.border}40` }}>
              <td style={{ padding: '5px 6px', color: BRAND.text, fontWeight: 600 }}>
                <a href={`https://finance.yahoo.com/quote/${encodeURIComponent(r.ticker)}`}
                   target="_blank" rel="noopener" style={{ color: 'inherit', textDecoration: 'none' }}>
                  {r.ticker}
                </a>
              </td>
              <td style={{ padding: '5px 6px', color: BRAND.textMute }}>{r.name}</td>
              <td style={{ padding: '5px 6px', color: BRAND.textDim, fontSize: 10 }}>
                {r.role}{r.stale ? ' · stale' : ''}
              </td>
              <td style={{ padding: '5px 6px', textAlign: 'right', color: BRAND.text }}>{fmtPx(r.last_close)}</td>
              <td style={{ padding: '5px 6px', textAlign: 'right', color: colorPct(r.wow_pct) }}>{fmtPct(r.wow_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Replace the constituents placeholder in `CommodityDetailPanel`**

Replace:
```jsx
        <div style={{ color: BRAND.textDim, fontSize: 11 }}>
          ConstituentsTable placeholder — Task 11
        </div>
```
with:
```jsx
        <ConstituentsTable rows={c.constituents} />
```

- [ ] **Step 3: Smoke-test**

`make serve`. Click various commodities. Expected:
- Header "SECTOR · COMPANIES ON THE DESK".
- Table with Ticker / Name / Role / Last / WoW columns.
- Pure-plays first (alphabetical), then majors, then juniors, ETFs at the bottom.
- Tickers click out to Yahoo Finance.
- Negative WoW% shown in pink, positive in accent green.
- Stale rows show "—" for price and a "stale" tag in the Role cell.

- [ ] **Step 4: Commit**

```bash
git add HateIndex/docs/index.html
git commit -m "feat: ConstituentsTable in the commodity detail panel"
```

---

### Task 12: End-to-end smoke test + final commit

**Files:** none.

- [ ] **Step 1: Run the full pipeline cold**

```bash
cd HateIndex && make clean && make refresh
```
Expected: completes in <60s with no errors. Logs include "Pulling N constituent tickers" and "Wrote .../docs/data.json".

- [ ] **Step 2: Run the full test suite**

```bash
cd HateIndex && .venv/bin/pytest tests/ -v
```
Expected: all tests pass (~25 total).

- [ ] **Step 3: Visual walk-through**

`make serve`. For each of: Nat Gas, Lithium, Iron Ore, PGMs, Crude Oil:
1. Click the leaderboard row.
2. Confirm the detail panel populates with header, score-history chart, component bars, commentary, and constituents.
3. Confirm at least one constituent ticker links out to Yahoo correctly.
4. Confirm null components ("phase 7") render as ghosted bars.

- [ ] **Step 4: If any defect found, file as a follow-up commit on the same branch — do not amend.**

- [ ] **Step 5: Push**

```bash
git push
```

---

## Definition of done (recap)

- A reader can land on the dashboard, click any commodity in the leaderboard or hover any tail in the RRG, and see a populated detail panel with chart, components, commentary, and constituents.
- `make refresh` produces a `data.json` containing `commentary` and `constituents` blocks for every commodity.
- All new tests green; all existing tests green.
- Branch pushed; ready for review.
