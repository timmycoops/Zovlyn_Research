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
