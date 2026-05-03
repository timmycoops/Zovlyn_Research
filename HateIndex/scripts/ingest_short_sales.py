"""
Pull ASIC daily aggregated short positions for the ASX universe.

Source: https://download.asic.gov.au/short-selling/RR{YYYYMMDD}-001-SSDailyAggShortPos.csv
Release: T+4 business days. Friday's data appears the following Thursday.

Run: python -m scripts.ingest_short_sales [--days 365]
Output: data/raw/short_sales.parquet
        long format: date, ticker, short_positions, total_in_issue, short_pct
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from scripts._universe import STOCK_UNIVERSE, all_tickers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

URL_TEMPLATE = "https://download.asic.gov.au/short-selling/RR{ymd}-001-SSDailyAggShortPos.csv"
USER_AGENT = "Mozilla/5.0 (compatible; ZovlynHateIndex/1.0)"
REQUEST_DELAY_S = 0.4


def business_days(start: date, end: date) -> list[date]:
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def fetch_one(d: date, session: requests.Session) -> pd.DataFrame | None:
    url = URL_TEMPLATE.format(ymd=d.strftime("%Y%m%d"))
    try:
        r = session.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as e:
        log.warning("Network error for %s: %s", d.isoformat(), e)
        return None

    if r.status_code == 404:
        log.debug("No file for %s (holiday or T+4 not yet released)", d)
        return None
    if r.status_code != 200:
        log.warning("HTTP %d for %s", r.status_code, url)
        return None

    try:
        df = pd.read_csv(io.BytesIO(r.content), encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(r.content), encoding="latin-1")

    rename = {
        "Product Code": "ticker",
        "Reported Short Positions": "short_positions",
        "Total Product in Issue": "total_in_issue",
        "% of Total Product in Issue Reported as Short Positions": "short_pct",
    }
    missing = [c for c in rename if c not in df.columns]
    if missing:
        log.warning("Unexpected columns in %s; missing %s", url, missing)
        return None

    out = df[list(rename)].rename(columns=rename).copy()
    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    out["short_positions"] = pd.to_numeric(out["short_positions"], errors="coerce")
    out["total_in_issue"]  = pd.to_numeric(out["total_in_issue"],  errors="coerce")
    out["short_pct"]       = pd.to_numeric(out["short_pct"],       errors="coerce")
    out["date"] = pd.Timestamp(d, tz="UTC")
    return out[["date", "ticker", "short_positions", "total_in_issue", "short_pct"]]


def existing_dates(path: Path) -> set[date]:
    if not path.exists():
        return set()
    df = pd.read_parquet(path, columns=["date"])
    return set(pd.to_datetime(df["date"]).dt.date.unique())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    out_path = RAW_DIR / "short_sales.parquet"
    universe = all_tickers()
    log.info("Universe: %d unique tickers across %d commodities",
             len(universe), len(STOCK_UNIVERSE))

    today = datetime.now(timezone.utc).date()
    earliest = today - timedelta(days=args.days)
    target_dates = business_days(earliest, today - timedelta(days=4))

    have = set() if args.full else existing_dates(out_path)
    todo = [d for d in target_dates if d not in have]
    log.info("Need %d dates (already have %d, target window %d)",
             len(todo), len(have), len(target_dates))

    if not todo:
        log.info("Nothing to do; parquet already current")
        return 0

    session = requests.Session()
    frames: list[pd.DataFrame] = []
    fetched = 0
    for d in todo:
        df = fetch_one(d, session)
        if df is not None:
            df = df[df["ticker"].isin(universe)]
            if not df.empty:
                frames.append(df)
                fetched += 1
        time.sleep(REQUEST_DELAY_S)

    if not frames:
        log.warning("No new data fetched")
        return 0 if have else 1

    new_data = pd.concat(frames, ignore_index=True)
    log.info("Fetched %d new days, %d rows", fetched, len(new_data))

    if out_path.exists() and not args.full:
        existing = pd.read_parquet(out_path)
        combined = (
            pd.concat([existing, new_data], ignore_index=True)
            .drop_duplicates(subset=["date", "ticker"], keep="last")
        )
    else:
        combined = new_data

    combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)
    combined.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d tickers → %s",
             len(combined), combined["ticker"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
