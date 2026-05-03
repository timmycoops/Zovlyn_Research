# Commodity Hate Index

A weekly-updating GitHub Pages site that ranks commodities by a composite **Hate Score** (capitulation signal) and overlays sector rotation (RRG) so the buy zone — hated AND rotating — is visible at a glance.

🔗 **Live**: see Pages URL after first deploy

## What it does

For each of 12 commodities (lithium, uranium, copper, gold, silver, rare earths, oil, gas, PGMs, iron ore, coal, nickel), every Saturday morning AEST:

1. Pulls weekly price data, CFTC positioning, ETF flows, sentiment.
2. Computes a composite z-score across six capitulation signals.
3. Computes a Relative Rotation Graph vs the ASX 200.
4. Flags commodities that are both deeply hated AND rotating into Improving / Leading.
5. Rebuilds the dashboard at `docs/index.html` and pushes to Pages.

## Quick start

```bash
make install          # pip install
make refresh          # run the full pipeline locally
make serve            # preview the dashboard at localhost:8000
```

## How it works

- **Data layer**: parquet files in `data/raw/` (one per source) and `data/processed/` (scores, RRG).
- **Pipeline**: Python scripts in `scripts/`, runs in <60s on a GitHub Actions runner.
- **Dashboard**: single-file `docs/index.html` using React + Recharts via CDN. No build step.
- **Schedule**: `.github/workflows/weekly.yml` cron, Saturday 08:00 AEST.

## Spec

Full technical brief in [docs/SPEC.md](docs/SPEC.md). Includes universe, exact formulas for each component, RRG math, signal definition, and the JSON output contract.

## Disclaimer

Personal research tool. Not investment advice. Data may be stale, incomplete, or wrong. Use at your own risk.
