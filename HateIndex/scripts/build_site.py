"""
Read processed parquet files and emit docs/data.json matching the schema in SPEC.md.

Reads:
    data/processed/hate_scores.parquet
    data/processed/rrg.parquet
Writes:
    docs/data.json
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"

TICKER_MAP: dict[str, str] = {
    "Lithium": "LIT", "Uranium": "URA", "Copper": "COPX", "Gold": "GLD",
    "Silver": "SLV", "Rare Earths": "REMX", "Crude Oil": "USO", "Nat Gas": "UNG",
    "PGMs": "PPLT", "Iron Ore": "IRON.AX", "Thermal Coal": "BTU", "Nickel": "PICK",
}
BENCHMARK = "^AXJO"

HISTORY_WEEKS = 104
ROTATION_TAIL_LEN = 6
STALE_THRESHOLD_DAYS = 10

# Use the unicode arrow per SPEC.md output contract
ARROW = "→"


def make_status(quadrants: list[str]) -> tuple[str, bool]:
    if not quadrants:
        return ("N/A", False)
    valid = [q for q in quadrants if q != "N/A"]
    if not valid:
        return ("N/A", False)
    start, end = valid[0], valid[-1]
    transitioned = start != end
    just_entered = transitioned and end in ("Improving", "Leading")
    status = f"{start}{ARROW}{end}" if transitioned else end
    return (status, just_entered)


def build() -> dict:
    scores_path = PROC_DIR / "hate_scores.parquet"
    rrg_path = PROC_DIR / "rrg.parquet"

    if not scores_path.exists() or not rrg_path.exists():
        raise FileNotFoundError("Missing processed parquet files. Run scoring + RRG first.")

    scores = pd.read_parquet(scores_path)
    rrg = pd.read_parquet(rrg_path)

    scores["date"] = pd.to_datetime(scores["date"], utc=True)
    rrg["date"] = pd.to_datetime(rrg["date"], utc=True)

    as_of = min(scores["date"].max(), rrg["date"].max())
    log.info("as_of = %s", as_of.date())

    age_days = (pd.Timestamp.now(tz="UTC") - as_of).days
    is_stale = age_days > STALE_THRESHOLD_DAYS
    if is_stale:
        log.warning("Data is %d days old (> %d threshold); marking is_stale=true",
                    age_days, STALE_THRESHOLD_DAYS)

    commodities_payload = []
    for commodity in TICKER_MAP:
        s_sub = (
            scores[(scores["commodity"] == commodity) & (scores["date"] <= as_of)]
            .sort_values("date")
        )
        r_sub = (
            rrg[(rrg["commodity"] == commodity) & (rrg["date"] <= as_of)]
            .sort_values("date")
        )
        if s_sub.empty or r_sub.empty:
            log.warning("Skipping %s: missing data", commodity)
            continue

        latest = s_sub.iloc[-1]
        rrg_tail = r_sub.tail(ROTATION_TAIL_LEN)
        tail_pairs = [
            [round(float(r), 2), round(float(m), 2)]
            for r, m in zip(rrg_tail["rs_ratio"], rrg_tail["rs_momentum"])
        ]
        status, just_entered = make_status(rrg_tail["quadrant"].tolist())

        history = (
            s_sub.tail(HISTORY_WEEKS)
            .assign(date_str=lambda d: d["date"].dt.strftime("%Y-%m-%d"))
            [["date_str", "score"]]
            .rename(columns={"date_str": "date"})
            .to_dict("records")
        )

        components = {
            "drawdown":    nullable(latest.get("z_drawdown")),
            "momentum":    nullable(latest.get("z_momentum")),
            "positioning": nullable(latest.get("z_positioning")),
            "flows":       None,
            "valuation":   None,
            "sentiment":   None,
        }

        commodities_payload.append({
            "name": commodity,
            "ticker": TICKER_MAP[commodity],
            "score": round(float(latest["score"]), 2),
            "components": components,
            "rrg_tail": tail_pairs,
            "status": status,
            "just_entered": bool(just_entered),
            "score_history": history,
        })

    commodities_payload.sort(key=lambda c: c["score"], reverse=True)
    flagged = [c["name"] for c in commodities_payload
               if c["score"] >= 4 and c["just_entered"]]

    payload = {
        "as_of": as_of.strftime("%Y-%m-%d"),
        "build": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M"),
        "benchmark": BENCHMARK,
        "is_stale": bool(is_stale),
        "age_days": int(age_days),
        "commodities": commodities_payload,
        "flagged": flagged,
    }
    return payload


def nullable(v) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v), 2)


def main() -> int:
    try:
        payload = build()
    except Exception as e:
        log.error("Site build failed: %s", e)
        return 1

    out_path = DOCS_DIR / "data.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Wrote %s (%d commodities, %d flagged)",
             out_path, len(payload["commodities"]), len(payload["flagged"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
