"""
Pull CFTC Commitments of Traders (Disaggregated) report and store as parquet.

The Disaggregated report categorises traders into:
- Producer/Merchant/Processor/User
- Swap Dealers
- Managed Money     ← this is what we want for capitulation signal
- Other Reportables
- Nonreportable Positions

Source: CFTC publishes weekly text/excel files. The combined annual ZIPs at
https://www.cftc.gov/dea/history/dea_disagg_xls_YYYY.zip are the cleanest bulk source.
For the latest week, the current-year file is updated each Friday afternoon ET.

This is a STARTER implementation. Phase 1 deliverable: working ingestion for
the 6 most relevant contracts. Add more in Phase 7 alongside extra components.

Run: python scripts/ingest_cftc.py
Output: data/raw/cftc.parquet  (long format: date, contract, mm_net_long, mm_net_pct_oi)
"""
from __future__ import annotations

import io
import logging
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Map our commodity name → CFTC "Market_and_Exchange_Names" substring(s).
# If multiple contracts cover one commodity (e.g. crude has WTI + Brent), aggregate.
# These are starter mappings — verify against actual CFTC names; adjust as needed.
CFTC_MAP: dict[str, list[str]] = {
    "Gold":      ["GOLD - COMMODITY EXCHANGE INC."],
    "Silver":    ["SILVER - COMMODITY EXCHANGE INC."],
    "Copper":    ["COPPER- #1 - COMMODITY EXCHANGE INC."],
    "Crude Oil": ["WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
                  "CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE"],
    "Nat Gas":   ["NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"],
    "Platinum":  ["PLATINUM - NEW YORK MERCANTILE EXCHANGE"],
    "Palladium": ["PALLADIUM - NEW YORK MERCANTILE EXCHANGE"],
    # Lithium, uranium, rare earths, iron ore, thermal coal, nickel:
    # CFTC has limited or no managed-money data. Use ETF flows as positioning proxy
    # for those (Phase 7).
}

YEARS_BACK = 10  # Phase 2 backtest needs at least 5; pull 10 to be safe.


def fetch_year(year: int) -> pd.DataFrame:
    url = f"https://www.cftc.gov/dea/history/dea_disagg_xls_{year}.zip"
    log.info("Downloading CFTC disaggregated report for %d", year)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        # The zip contains a single .xls file
        names = [n for n in z.namelist() if n.endswith(".xls") or n.endswith(".xlsx")]
        if not names:
            raise RuntimeError(f"No xls in zip for {year}")
        with z.open(names[0]) as f:
            df = pd.read_excel(f)
    return df


def normalise(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Extract the columns we need and aggregate by our commodity mapping."""
    # CFTC column names are long; use partial matches
    cols = df_raw.columns.tolist()
    def find(*needles: str) -> str:
        for c in cols:
            if all(n.lower() in c.lower() for n in needles):
                return c
        raise KeyError(f"None of {needles} matched any column")

    market_col = find("Market_and_Exchange_Names")
    date_col   = find("Report_Date")
    mm_long    = find("M_Money_Positions_Long_All")
    mm_short   = find("M_Money_Positions_Short_All")
    oi         = find("Open_Interest_All")

    out = pd.DataFrame({
        "date":     pd.to_datetime(df_raw[date_col], utc=True),
        "market":   df_raw[market_col].astype(str),
        "mm_long":  df_raw[mm_long],
        "mm_short": df_raw[mm_short],
        "oi":       df_raw[oi],
    })
    out["mm_net_long"] = out["mm_long"] - out["mm_short"]
    return out


def aggregate_to_universe(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    missing_in_recent: list[str] = []
    # The most recent report date in the dataset; we use this to spot CFTC
    # market-name renames silently nuking a commodity's positioning data.
    latest_date = raw["date"].max() if not raw.empty else None

    for commodity, market_keys in CFTC_MAP.items():
        sub = raw[raw["market"].isin(market_keys)]
        if sub.empty:
            log.warning("No rows for %s (markets %s) — check CFTC_MAP names",
                        commodity, market_keys)
            missing_in_recent.append(commodity)
            continue
        if latest_date is not None:
            recent = sub[sub["date"] == latest_date]
            if recent.empty:
                log.warning("%s has no data for the latest report date %s — "
                            "possible market rename", commodity, latest_date.date())
                missing_in_recent.append(commodity)

        agg = (
            sub.groupby("date", as_index=False)[["mm_net_long", "oi"]].sum()
            .assign(commodity=commodity)
        )
        agg["mm_net_pct_oi"] = (agg["mm_net_long"] / agg["oi"]).clip(-1, 1)
        rows.append(agg[["date", "commodity", "mm_net_long", "oi", "mm_net_pct_oi"]])

    if missing_in_recent:
        log.warning("CFTC mapping health: %d/%d commodities missing latest data: %s",
                    len(missing_in_recent), len(CFTC_MAP), missing_in_recent)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> int:
    current_year = datetime.now(timezone.utc).year
    years = list(range(current_year - YEARS_BACK, current_year + 1))

    frames: list[pd.DataFrame] = []
    for year in years:
        try:
            frames.append(normalise(fetch_year(year)))
        except Exception as e:
            log.error("Year %d failed: %s", year, e)

    if not frames:
        log.error("No CFTC data fetched")
        return 1

    raw_combined = pd.concat(frames, ignore_index=True)
    universe_df = aggregate_to_universe(raw_combined)
    universe_df = universe_df.sort_values(["commodity", "date"]).reset_index(drop=True)

    out_path = RAW_DIR / "cftc.parquet"
    universe_df.to_parquet(out_path, index=False)
    log.info("Wrote %d rows across %d commodities → %s",
             len(universe_df), universe_df["commodity"].nunique(), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
