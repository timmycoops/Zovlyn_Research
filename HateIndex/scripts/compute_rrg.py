"""
Compute JdK RS-Ratio and RS-Momentum per commodity vs benchmark.

Reads:  data/raw/prices.parquet
Writes: data/processed/rrg.parquet (long format: date, commodity, rs_ratio, rs_momentum, quadrant)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

TICKER_MAP: dict[str, str] = {
    "Lithium": "LIT", "Uranium": "URA", "Copper": "COPX", "Gold": "GLD",
    "Silver": "SLV", "Rare Earths": "REMX", "Crude Oil": "USO", "Nat Gas": "UNG",
    "PGMs": "PPLT", "Iron Ore": "IRON.AX", "Thermal Coal": "BTU", "Nickel": "PICK",
}
BENCHMARK = "^AXJO"

WINDOW = 10
SMOOTH = 3
SCALE = 10   # JdK convention: multiply normalised deviation by 10 so values land in ~[85, 115]


def _zscore(s: pd.Series, window: int) -> pd.Series:
    return (s - s.rolling(window).mean()) / s.rolling(window).std()


def compute_rrg_pair(prices: pd.Series, benchmark: pd.Series,
                     window: int = WINDOW, smooth: int = SMOOTH, scale: int = SCALE
                     ) -> tuple[pd.Series, pd.Series]:
    """
    JdK RS-Ratio + RS-Momentum (de Kempenaer convention).

    rs_ratio = 100 + scale * z(rs, window)
    rs_mom   = 100 + scale * z(rs_ratio, window)

    The *scale* multiplier (default 10) spreads the values into the conventional
    [~85, ~115] range, so a standard RRG chart with [85, 115] axes frames the data
    and the quadrants (centred at 100,100) are visually meaningful.
    """
    aligned_bench = benchmark.reindex(prices.index).ffill()
    rs = 100 * prices / aligned_bench
    rs_ratio_raw = 100 + scale * _zscore(rs, window)
    rs_mom_raw = 100 + scale * _zscore(rs_ratio_raw, window)
    return rs_ratio_raw.rolling(smooth).mean(), rs_mom_raw.rolling(smooth).mean()


def quadrant_label(rs_ratio: float, rs_mom: float) -> str:
    if pd.isna(rs_ratio) or pd.isna(rs_mom):
        return "N/A"
    if rs_ratio >= 100 and rs_mom >= 100:
        return "Leading"
    if rs_ratio < 100 and rs_mom >= 100:
        return "Improving"
    if rs_ratio < 100 and rs_mom < 100:
        return "Lagging"
    return "Weakening"


def main() -> int:
    prices_path = RAW_DIR / "prices.parquet"
    if not prices_path.exists():
        log.error("Missing %s -- run ingest_prices.py first", prices_path)
        return 1

    prices = pd.read_parquet(prices_path)
    prices["date"] = pd.to_datetime(prices["date"], utc=True)

    bench = (
        prices[prices["ticker"] == BENCHMARK]
        .set_index("date")["close"]
        .sort_index()
    )
    if bench.empty:
        log.error("No benchmark data for %s", BENCHMARK)
        return 1

    rows: list[pd.DataFrame] = []
    for commodity, ticker in TICKER_MAP.items():
        sub = prices[prices["ticker"] == ticker].set_index("date")["close"].sort_index()
        if sub.empty:
            log.warning("No price series for %s (%s); skipping", commodity, ticker)
            continue
        rs_ratio, rs_mom = compute_rrg_pair(sub, bench)
        df = pd.DataFrame({
            "date": rs_ratio.index,
            "commodity": commodity,
            "rs_ratio": rs_ratio.values,
            "rs_momentum": rs_mom.values,
        })
        df["quadrant"] = [quadrant_label(r, m) for r, m in zip(df["rs_ratio"], df["rs_momentum"])]
        rows.append(df)

    out = pd.concat(rows, ignore_index=True).dropna(subset=["rs_ratio", "rs_momentum"])
    out = out.sort_values(["commodity", "date"]).reset_index(drop=True)

    out_path = PROC_DIR / "rrg.parquet"
    out.to_parquet(out_path, index=False)
    log.info("Wrote %d rows for %d commodities -> %s",
             len(out), out["commodity"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
