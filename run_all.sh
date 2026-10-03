#!/usr/bin/env bash
# Full FedDrift pipeline, in order. Requires FRED_API_KEY for step 03.
set -euo pipefail
cd "$(dirname "$0")"
: "${FRED_API_KEY:?Set FRED_API_KEY (free: https://fredaccount.stlouisfed.org/apikeys)}"
python code/01_fetch_agency.py
python code/02_build_anchor.py
python code/03_fetch_alfred.py
python code/04_vintage_pairs.py
python code/05_propose_labels.py
python code/06_qa.py
python code/08_apply_labels.py
python code/07_benchmark.py
python code/09_figures_stats.py "$@"
python code/11_build_docs.py "$@"
python -m pytest -q tests
