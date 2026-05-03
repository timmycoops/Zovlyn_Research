"""
Pull weekly close prices for the commodity universe + benchmark and store as parquet.

Run: python scripts/ingest_prices.py
Output: data/raw/prices.parquet  (long format: date, ticker, close)
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scripts._yf_retry import fetch_with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

UNIVERSE: list[tuple[str, list[str]]] = [
    ("Lithium",      ["LIT"]),
    ("Uranium",      ["URA"]),
    ("Copper",       ["COPX"]),
    ("Gold",         ["GLD"]),
    ("Silver",       ["SLV"]),
    ("Rare Earths",  ["REMX"]),
    ("Crude Oil",    ["USO"]),
    ("Nat Gas",      ["UNG"]),
    ("PGMs",         ["PPLT"]),
    ("Iron Ore",     ["IRON.AX", "FMG.AX"]),  # IRON.AX flaky; SPEC alt is FMG.AX
    ("Thermal Coal", ["BTU"]),
    ("Nickel",       ["PICK"]),
]
BENCHMARK = "^AXJO"
HISTORY_PERIOD = "10y"


def fetch(ticker: str) -> pd.DataFrame:
    return fetch_with_retry(ticker, period=HISTORY_PERIOD, interval="1wk")


def fetch_with_fallbacks(tickers: list[str]) -> tuple[pd.DataFrame, str | None]:
    """Try each ticker in order; return (frame, ticker_used) on first success."""
    for tkr in tickers:
        df = fetch(tkr)
        if not df.empty:
            return df, tkr
    return pd.DataFrame(columns=["date", "ticker", "close"]), None


def main() -> int:
    frames: list[pd.DataFrame] = []
    for _name, fallbacks in UNIVERSE:
        primary = fallbacks[0]
        df, used = fetch_with_fallbacks(fallbacks)
        if used is None:
            log.error("All fallbacks failed for %s: %s", _name, fallbacks)
            continue
        if used != primary:
            log.warning("Using fallback %s for %s (primary %s failed)", used, _name, primary)
            df = df.assign(ticker=primary)  # store under canonical ticker
        frames.append(df)

    bench_df = fetch(BENCHMARK)
    if not bench_df.empty:
        frames.append(bench_df)
    else:
        log.error("Benchmark %s failed to fetch", BENCHMARK)

    if not frames:
        log.error("No data fetched; aborting")
        return 1

    combined = pd.concat(frames, ignore_index=True).dropna(subset=["close"])
    combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)

    expected = {fallbacks[0] for _n, fallbacks in UNIVERSE} | {BENCHMARK}
    got = set(combined["ticker"].unique())
    missing = expected - got
    if missing:
        log.error("Missing tickers entirely after retries: %s", sorted(missing))
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=14)
    stale = []
    for tkr in got:
        latest = combined.loc[combined["ticker"] == tkr, "date"].max()
        if latest < cutoff:
            stale.append((tkr, str(latest.date())))
    if stale:
        log.warning("Stale tickers (latest > 14d ago): %s", stale)

    out_path = RAW_DIR / "prices.parquet"
    combined.to_parquet(out_path, index=False)
    log.info("Wrote %d rows across %d tickers -> %s",
             len(combined), combined["ticker"].nunique(), out_path)

    manifest = pd.DataFrame([{
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "n_tickers": combined["ticker"].nunique(),
        "n_rows": len(combined),
        "earliest": str(combined["date"].min()),
        "latest": str(combined["date"].max()),
    }])
    manifest.to_parquet(RAW_DIR / "prices_manifest.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
