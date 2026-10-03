# Reproducibility

## Environment

- Python 3.11 or later. Tested with CPython 3.13.16 on Linux x86-64.
- Exact package pins are in `requirements.txt`.
- A free FRED API key in `FRED_API_KEY` (step 03 only).
- Optional, needed only to re-harvest evidence (`--harvest`): poppler-utils (`pdftotext`, `pdftoppm`, `pdfinfo`) and `tesseract`.

## Commands

```bash
git clone <repository> feddrift && cd feddrift
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export FRED_API_KEY=...
bash run_all.sh            # steps 02-05, 07-12, then pytest
```

## Clean-clone result (2026-10-03, recorded by the build)

The pipeline was run from a fresh `git clone` of the repository, in a new virtual environment installed only from `requirements.txt`. The run exited 0 in 2 min 45 s.

**Results**
- QA: Q01–Q19 PASS or NOTE; Q20 BLOCKING (labels await the label owner, as expected).
- Tests: 13 passed.

**Regenerated outputs identical to the committed versions (byte-for-byte)**
- `data/manifests/<SERIES>.vintages.csv` for all 17 series, which means all vintage content hashes match.
- `data/processed/` tables: `anchor_vintage.csv`, `vintage_pairs.csv`, `proposed_events.csv`, `release_clusters.csv`, `drift_events.csv`, `event_inventory.csv`, `label_status.json`, `t2_split_counts.csv`.
- `paper/benchmark_results.json` and `paper/tables/*.csv`: all T2 metrics and bootstrap intervals.
- The SHA-256 of every ALFRED cache file (recorded in `alfred_manifest.json`).

**Expected differences (by design)**

| File | Difference | Why |
|---|---|---|
| `data/manifests/alfred_manifest.json` | `fetched_utc` only | Fetch time of the rebuild |
| `data/processed/qa.json`, `qa_report.md`, `paper/stats.json`, `paper/feddrift_data_descriptor.md` | Q02 is NOTE instead of PASS | A clone does not contain the withheld full BTS MTS file. The committed TSI extract is used, and the full file is re-fetchable by URL and SHA-256 |
| `labels/review/FedDrift_label_review.xlsx` | Container timestamps | xlsx (zip) entry times; the cell contents are identical |
| `paper/figures/*.png` | Pixel-level anti-aliasing | Font rasterization differs between the system matplotlib build and the PyPI wheel. The plotted data are identical |

## Determinism

- **ALFRED:** queried with `realtime_end` pinned in `config/snapshot.json`, so later vintages never enter a rebuild.
- **Agency layer:** read from the committed snapshot. `--refresh-agency` deliberately fetches a new one.
- **Random seed:** 20261003, used by the T1 decision tree and the T2 bootstrap. Nothing else is stochastic.
- **Release archive:** `code/13_package.py` writes archive members with zeroed mtimes and owners, in sorted order.
