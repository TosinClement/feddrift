# FedDrift

**Vintage-labeled distribution shift in U.S. federal economic and freight statistics**

**Version:** 0.1.0 (draft, not released) · **Maintainer:** Tosin Clement, ORCID [0009-0001-2055-5113](https://orcid.org/0009-0001-2055-5113) · **License:** code MIT, data CC BY 4.0 · **DOI:** {{ZENODO_DOI}}

> **Status: DRAFT, not released.** 102 of 4,109 drift events do not yet carry a label verified by the label owner; causes shown are recommendations. Do not cite until the v0.1.0 release.

FedDrift records every revision of 17 monthly U.S. federal statistics. The series come from the Census Bureau (retail sales, manufacturers' orders, business inventories), the Bureau of Labor Statistics (CPI, PPI) and the Bureau of Transportation Statistics (Transportation Services Index). For each revision FedDrift gives:

- the date the revised numbers entered the public real-time record;
- what changed, how far back and by how much;
- a distribution-shift statistic;
- a cause label verified by the label owner and citing the agency document it rests on, or `unknown` where no agency source establishes the cause.

The causes are advance-to-revised transitions, annual benchmarks, seasonal-factor recomputation, sample redesign, rebasing or definition changes, methodology changes and corrections.

## At a glance (generated from `paper/stats.json`)

- 17 series; 6,312 real-time vintages from 1949-03-24 to 2026-10-02; observations 1947-01 to 2026-08.
- 6,295 consecutive vintage pairs. 4,109 are **drift events** (at least one published value revised). The other 2,186 only add new months.
- Drift events by review level: 3,653 routine events under 7 rules; 456 non-routine events in 231 agency releases.
- Evidence: 359 agency documents registered with URL, publication date and SHA-256.
- Agency files fetched directly from the agencies match ALFRED's newest vintage exactly for 16 of 17 series. The exception is explained in `data/processed/qa_report.md`.
- Negative control: NSA CPI-U is revised in 0.97% of releases, against 8.68% for SA CPI-U.

### Label status

| Label status | Events |
|---|---:|
| `rule_verified` | 3,653 |
| `release_verified` | 307 |
| `unknown_verified` | 46 |
| `override_verified` | 1 |
| `release_pending_review` | 102 |
| **drift events total** | **4,109** |
| `excluded_not_drift` (no value revised) | 2,186 |

46 drift events carry the honest final label `unknown`: agency sources did not establish their cause.

### Drift events by verified cause

| Final cause | Events | Median depth (months) | Median mean abs. revision (%) | Median KS (growth) |
|---|---:|---:|---:|---:|
| `advance_to_revised` | 3,401 | 3 | 0.156 | 0.083 |
| `routine_reestimation` | 253 | 234 | 0.108 | 0.019 |
| `annual_benchmark` | 193 | 159 | 0.367 | 0.037 |
| `seasonal_factor_recompute` | 95 | 61 | 0.061 | 0.077 |
| `unknown` | 46 | 108 | 0.175 | 0.053 |
| `correction` | 7 | 8 | 0.066 | 0.188 |
| `rebase_or_definition` | 7 | 113 | 14.016 | 0.102 |
| `methodology_change` | 5 | 181 | 0.191 | 0.034 |

## Benchmark tasks

**T1 — revision-cause attribution.** Predict the cause of a drift event from its footprint. Splits are by vintage date (train before 2010, validation 2010–2014, test 2015 onward); the metric is macro-F1.
T1 is scored only on labels verified by the label owner. Status: `pending_author_labels` (4,007 of 4,109 drift events verified).

**T2 — real-time revision correction.** Predict the month-over-month growth rate as it stands 36 months after first release, from the first-release value. Splits are leakage-free in calendar time; the test set covers first releases from 2016-01-01 to 2022-09-30 (1,349 observations, 17 series).

| Baseline | MAE (pp) | RMSE (pp) | MAE − B0 (95% bootstrap interval) |
|---|---:|---:|---|
| B0 no revision | 0.4899 | 0.8745 | — |
| B1 + train mean revision | 0.4897 | 0.8726 | -0.0002 (-0.0019, +0.0016) |
| B2 per-series OLS | 0.4953 | 0.8871 | +0.0054 (-0.0041, +0.0154) |
| B3 validation-selected | 0.4916 | 0.8836 | +0.0017 (-0.0045, +0.0084) |

No simple correction improves on the no-revision baseline B0 (MAE 0.490 pp): every 95% bootstrap interval for the MAE difference to B0 includes zero. This is consistent with revisions carrying new information that was not available at first release, but the test set does not establish why. See `paper/tables/t2_by_series.csv` for per-series results, and `docs/METHODOLOGY.md` §5 for the full specification.

## Reproduce

```bash
git clone {{GITHUB_REPO_URL}} feddrift && cd feddrift
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export FRED_API_KEY=your_key        # free: https://fredaccount.stlouisfed.org/apikeys
bash run_all.sh                     # pinned snapshot: rebuilds the ALFRED layer, verifies hashes, QA, benchmark, docs, tests
```

The ALFRED layer is rebuilt with `realtime_end` pinned to 2026-10-03, so later vintages never enter. QA check Q03 compares every rebuilt vintage with its published SHA-256. `bash run_all.sh --harvest` also re-downloads the agency evidence documents.

## Repository

```
code/       01-13 pipeline in run order; import_review.py; publish_gate.py
config/     panel, snapshot, causes, rules, schema, placeholders
data/raw/agency/2026-10-03/   agency files (public domain) + data/raw/PROVENANCE.txt
data/manifests/               ALFRED vintage manifests: dates, counts, SHA-256 (no values)
data/processed/               drift_events.csv, event_inventory.csv, anchor_vintage.csv, release_clusters.csv, QA
evidence/   source registry, rule evidence, release evidence with automated checks
labels/     review package (labels/review/) and the label owner's decisions (labels/decisions/)
paper/      stats.json, benchmark results, tables, figures, data descriptor
docs/       METHODOLOGY, CODEBOOK, PROVENANCE, REPRODUCIBILITY, LICENSING_PROTOCOL, ETHICS_AND_LIMITATIONS, CONTRIBUTIONS, RELEASE_CHECKLIST
zenodo/     deposit metadata and description
```

## Data use and licensing

- Agency values: U.S. Government works, public domain.
- FedDrift's tables, labels and documentation: CC BY 4.0.
- Code: MIT.
- ALFRED observation values are **not** redistributed. They are rebuilt with your own FRED API key, under the FRED API Terms of Use.

See `docs/LICENSING_PROTOCOL.md`.

This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

## Limitations

Read `docs/ETHICS_AND_LIMITATIONS.md` before using FedDrift. In short:
- vintage dates are ALFRED's, not always the agency's;
- some early vintages censor revision depth;
- evidence strength varies and is graded per label.

## Contributions

Tosin Clement designed FedDrift and owns every substantive labeling decision. Claude (Anthropic) assisted with code, data harmonization, evidence retrieval and documentation drafts. See `docs/CONTRIBUTIONS.md`.

## Citation

Clement, T. (2026). *FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics* (Version 0.1.0) [Data set]. Zenodo. https://doi.org/{{ZENODO_DOI}}
