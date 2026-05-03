.PHONY: help install ingest score rrg site backtest refresh test clean

help:
	@echo "Targets:"
	@echo "  install   - pip install -r requirements.txt"
	@echo "  refresh   - run the full weekly pipeline (ingest -> score -> rrg -> site)"
	@echo "  ingest    - pull prices and CFTC into data/raw/"
	@echo "  score     - compute hate scores from raw"
	@echo "  rrg       - compute RRG from raw"
	@echo "  site      - build docs/data.json"
	@echo "  backtest  - run historical signal backtest (Phase 6)"
	@echo "  test      - run pytest"
	@echo "  serve     - serve docs/ on localhost:8000 for dashboard preview"

install:
	pip install -r requirements.txt

ingest:
	python scripts/ingest_prices.py
	python scripts/ingest_cftc.py

score:
	python scripts/compute_scores.py

rrg:
	python scripts/compute_rrg.py

site:
	python scripts/build_site.py

backtest:
	python scripts/backtest.py

refresh: ingest score rrg site
	@echo "Pipeline refresh complete. Open docs/index.html or run 'make serve'."

test:
	pytest -v tests/

serve:
	@echo "Serving docs/ at http://localhost:8000"
	cd docs && python -m http.server 8000

clean:
	rm -rf data/raw/*.parquet data/processed/*.parquet docs/data.json
