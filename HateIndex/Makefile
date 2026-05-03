# Use the venv's python by default (created by `make install`); fall back to system python3.
# Absolute paths so targets that `cd` (e.g. `serve`) still find the binary.
# Override on the command line if you want, e.g. `make ingest PYTHON=python3.12`.
PYTHON ?= $(shell test -x $(CURDIR)/.venv/bin/python && echo $(CURDIR)/.venv/bin/python || echo python3)
PIP    ?= $(shell test -x $(CURDIR)/.venv/bin/pip    && echo $(CURDIR)/.venv/bin/pip    || echo pip3)

.PHONY: help install ingest constituents flows score rrg site backtest refresh test serve clean

help:
	@echo "Targets:"
	@echo "  install   - create .venv and pip install -r requirements.txt"
	@echo "  refresh   - run the full weekly pipeline (ingest -> score -> rrg -> site)"
	@echo "  ingest    - pull prices and CFTC into data/raw/"
	@echo "  constituents - pull weekly closes for sector constituents"
	@echo "  flows     - pull ASIC short sales and compute flow z-scores"
	@echo "  score     - compute hate scores from raw"
	@echo "  rrg       - compute RRG from raw"
	@echo "  site      - build docs/data.json"
	@echo "  backtest  - run historical signal backtest (Phase 6)"
	@echo "  test      - run pytest"
	@echo "  serve     - serve docs/ on localhost:8000 for dashboard preview"

install:
	test -d .venv || python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

ingest:
	$(PYTHON) -m scripts.ingest_prices
	$(PYTHON) -m scripts.ingest_cftc

constituents:
	$(PYTHON) -m scripts.ingest_constituents

flows:
	$(PYTHON) -m scripts.ingest_short_sales
	$(PYTHON) -m scripts.compute_flows

score:
	$(PYTHON) -m scripts.compute_scores

rrg:
	$(PYTHON) -m scripts.compute_rrg

site:
	$(PYTHON) -m scripts.build_site

backtest:
	$(PYTHON) -m scripts.backtest

refresh: ingest constituents flows score rrg site
	@echo "Pipeline refresh complete. Open docs/index.html or run 'make serve'."

test:
	$(PYTHON) -m pytest -v tests/

serve:
	@echo "Serving docs/ at http://localhost:8000"
	cd docs && $(PYTHON) -m http.server 8000

clean:
	rm -rf data/raw/*.parquet data/processed/*.parquet docs/data.json
