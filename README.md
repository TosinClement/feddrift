# FedDrift

**Status:** DRAFT v0.1 (unverified) | **Maintainer:** Tosin Clement, ORCID [0009-0001-2055-5113](https://orcid.org/0009-0001-2055-5113) | **License:** code MIT, data CC BY 4.0 | **DOI:** [DOI]

> **DRAFT v0.1, not verified.** Revision-event causes are rule-engine proposals until the label owner verifies each one against agency methodology. Do not cite.

FedDrift is an open benchmark of **vintage-labeled distribution shift** in U.S. federal economic and freight statistics. Each time an agency revises a published series, the series' history shifts. FedDrift records every such shift for 17 headline series from the Census Bureau, the Bureau of Labor Statistics and the Bureau of Transportation Statistics. For each shift it records when it happened (the vintage date), how far back it reached, how large it was, and why. The why is one of a fixed set of causes: advance-to-revised transitions, annual benchmarking, sample redesign, seasonal-factor recomputation (including the January recomputation of five years of CPI seasonal factors), and rebasing.

## At a glance (from `paper/stats.json`)

- **17 series**, **6,312 vintages** (1949-03-24 to 2026-10-02), observations from 1947-01.
- **6,295 consecutive vintage pairs**, of which **4,109 are drift events** (at least one published value revised). The remaining 2,186 only append new months, or are ALFRED archival-window artifacts.
- Agency files fetched directly from the agencies match ALFRED's newest vintage exactly for 16 of 17 series. Partial matches, with explanations, are in `data/processed/qa_report.txt`.
- Negative control: NSA CPI-U is revised in 0.97% of releases (9 vintages), against 8.68% for the seasonally adjusted CPI-U.
- Labels: 445 events need individual labels; 40 are currently unclassified.

| Cause | Events | Median depth (months) | Median mean abs. revision (%) | Median KS (growth) |
|---|---:|---:|---:|---:|
| `advance_to_revised` | 3,400 | 3 | 0.156 | 0.083 |
| `annual_benchmark` | 309 | 159 | 0.299 | 0.035 |
| `routine_reestimation` | 267 | 237 | 0.111 | 0.019 |
| `seasonal_factor_recompute` | 89 | 60 | 0.057 | 0.083 |
| `unclassified` | 40 | 58 | 0.139 | 0.057 |
| `rebase_or_definition` | 4 | 235 | 42.561 | 0.110 |

*Causes above are proposals from the rule engine, pending verification.*

## Benchmark tasks

**T1: Revision-cause attribution.** Given the footprint of a vintage pair (what changed, how far back, how much, and when), predict its cause. Temporal split (train before 2015, test 2015 onward), macro-F1. Status: `pending_author_labels`. T1 is scored only against author-verified labels.

**T2: Real-time revision correction.** Given a first-release month-over-month growth rate, predict its value 36 months later. Test observations: 2016-01-01 to 2022-09-01 (1,352 observations, 17 series).

| Baseline | MAE (pp) | RMSE (pp) |
|---|---:|---:|
| B0 no revision | 0.4864 | 0.8687 |
| B1 mean-revision correction | 0.4886 | 0.8699 |
| B2 per-series OLS | 0.4934 | 0.8759 |

## What is here

```
code/       numbered pipeline, run in order (run_all.sh)
config/     panel definition, revision rules, agency-documented events
data/raw/agency/     agency files as fetched (public domain), with PROVENANCE.txt
data/manifests/      ALFRED vintage manifests: dates, counts, content hashes (no values)
data/processed/      drift_events.csv (main table), anchor_vintage.csv, QA report
labels/     the author's label sheets and labeling instructions
docs/       CODEBOOK, LICENSING_PROTOCOL, LIMITATIONS, VERIFY_CHECKLIST, NEXT_STEPS
paper/      stats.json, benchmark results, figures, data-descriptor draft
```

## Run it

```
pip install -r requirements.txt
export FRED_API_KEY=your_key   # free: https://fredaccount.stlouisfed.org/apikeys
bash run_all.sh
```

Agency files need no key. The ALFRED layer is rebuilt from the FRED API. `code/06_qa.py` then checks every rebuilt vintage against the published hashes in `data/manifests/`.

## Sources

| Source | What | License / terms | Snapshot |
|---|---|---|---|
| ALFRED, Federal Reserve Bank of St. Louis (FRED API) | Real-time vintage histories | FRED API Terms of Use; series tagged public domain: citation requested. **Not redistributed:** rebuilt from manifests | 2026-10-03 |
| U.S. Census Bureau, Economic Indicators (MARTS, MRTS, M3, MTIS) | Agency anchor vintage | Public domain (U.S. government work) | 2026-10-03 |
| U.S. Bureau of Labor Statistics, LABSTAT (CPI `cu`, PPI `wp`) | Agency anchor vintage | Public domain | 2026-10-03 |
| U.S. DOT Bureau of Transportation Statistics, Monthly Transportation Statistics | TSI anchor values (BTS-produced fields only) | Public domain U.S. Government | 2026-10-03 |

See `docs/LICENSING_PROTOCOL.md` for what is and is not redistributed, and why.

## Limitations

Read `docs/LIMITATIONS.md` before using or citing anything here.

## Contributions and AI assistance

Tosin Clement designed FedDrift, chose the panel and the cause taxonomy, and owns every revision-event label. Each label is verified against the issuing agency's published methodology. Claude (Anthropic) assisted with retrieval code, harmonization, QA scaffolding and documentation drafts.

## Citation

See `CITATION.cff`. Clement, T. (2026). *FedDrift: an open benchmark of vintage-labeled distribution shift in U.S. federal economic and freight statistics* (v0.1.0). Zenodo. [DOI]
