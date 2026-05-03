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
        for m in entry.get("members", []):
            seen.add(m["ticker"])
    return sorted(seen)


def build_long_frame(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    out = pd.concat(non_empty, ignore_index=True).dropna(subset=["close"])
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
