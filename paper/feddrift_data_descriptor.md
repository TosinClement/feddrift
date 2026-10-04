---
title: "FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics"
author: "Tosin Clement (Independent Researcher; ORCID 0009-0001-2055-5113; clementtosin92@gmail.com)"
date: "{{RELEASE_DATE}}"
---

## Abstract

Published official statistics change. Advance estimates are revised, monthly surveys are benchmarked to annual surveys and censuses, seasonal factors are re-estimated, and indexes are rebased. Every such change shifts the data that downstream models were trained and evaluated on.

FedDrift records these shifts for 17 monthly U.S. federal series from the Census Bureau, the Bureau of Labor Statistics and the Bureau of Transportation Statistics. From 6,312 ALFRED real-time vintages it derives 6,295 consecutive vintage pairs, of which 4,109 revise previously published values. Each such drift event records its vintage date, how far back and how much the series was revised, a Kolmogorov–Smirnov statistic on growth rates, and a cause label. The author verified every label against agency documents registered with URL, publication date and SHA-256; 50 events carry the label `unknown` because no source established their cause.

FedDrift redistributes values only from public-domain agency files. The real-time layer ships as reconstruction code and hash-verified manifests. Two tasks are defined: revision-cause attribution (T1) and real-time revision correction (T2). On T2, no simple correction improves on the no-revision baseline B0 (MAE 0.490 pp): every 95% bootstrap interval for the MAE difference to B0 includes zero.

## 1. Background

Real-time data sets keep each published version ("vintage") of a series so that analyses can use the data as known at the time. Examples are the Federal Reserve Bank of Philadelphia's Real-Time Data Set for Macroeconomists (Croushore and Stark, 2001) and ALFRED (Federal Reserve Bank of St. Louis). FedDrift adds what those archives do not record: the cause of each revision, linked to an agency document, in a form suited to evaluating methods that must cope with shifting data.

## 2. Sources and data use

Agency anchor files come from Census, BLS and BTS (public domain). The real-time history comes from ALFRED via the FRED API; it is not redistributed. Licensing is in `docs/LICENSING_PROTOCOL.md`. The snapshot is 2026-10-03, with ALFRED pinned to `realtime_end` 2026-10-03.

## 3. Construction

See `docs/METHODOLOGY.md`. In brief:
- vintage reconstruction from real-time periods;
- footprints of each consecutive pair, with a censored-depth flag where the revision reaches the start of the archived vintage (215 events);
- rule proposals;
- agency releases grouped into 231 review clusters;
- evidence harvested from 361 agency documents, with automated consistency checks;
- labels decided by the author at rule, release and event level.

## 4. Technical validation

QA checks (`data/processed/qa_report.md`): Q01 PASS, Q02 PASS, Q03 PASS, Q04 PASS, Q05 NOTE, Q06 PASS, Q07 PASS, Q08 PASS, Q09 PASS, Q10 PASS, Q11 PASS, Q12 PASS, Q13 PASS, Q14 PASS, Q15 PASS, Q16 PASS, Q17 PASS, Q18 PASS, Q19 PASS, Q20 PASS.
- Reconstruction: 0 mismatches of 6312 vintages.
- Anchor agreement is exact for 16/17 series. The exception is the 2026-09-28 Census reissue of the MRTS file, which ALFRED had not vintaged by the snapshot date.
- Negative control: NSA CPI-U is revised in 0.97% of releases, against 8.68% for SA CPI-U.

## 5. Data records

The main table is `data/processed/drift_events.csv`, one row per vintage pair; see `docs/CODEBOOK.md`.

| Label status | Events |
|---|---:|
| `rule_verified` | 3,653 |
| `release_verified` | 405 |
| `unknown_verified` | 50 |
| `override_verified` | 1 |
| **drift events total** | **4,109** |
| `excluded_not_drift` (no value revised) | 2,186 |

| Final cause | Events | Median depth (months) | Median mean abs. revision (%) | Median KS (growth) |
|---|---:|---:|---:|---:|
| `advance_to_revised` | 3,401 | 3 | 0.156 | 0.083 |
| `annual_benchmark` | 283 | 159 | 0.349 | 0.035 |
| `routine_reestimation` | 253 | 234 | 0.108 | 0.019 |
| `seasonal_factor_recompute` | 101 | 61 | 0.061 | 0.073 |
| `unknown` | 50 | 104 | 0.175 | 0.053 |
| `correction` | 7 | 8 | 0.066 | 0.188 |
| `rebase_or_definition` | 7 | 113 | 14.016 | 0.102 |
| `methodology_change` | 5 | 181 | 0.191 | 0.034 |
| `sample_redesign` | 2 | 94 | 0.444 | 0.065 |

## 6. Benchmark tasks

**T1.** Test split: 2,129 events (50 events labeled `unknown` are not scored).

| Baseline | Macro-F1 | Accuracy |
|---|---:|---:|
| majority | 0.1466 | 0.7853 |
| calendar | 0.3261 | 0.8102 |
| footprint_tree | 0.3718 | 0.8704 |

**T2** (1,349 test observations; train 1,655, validation 541):

| Baseline | MAE (pp) | RMSE (pp) | MAE − B0 (95% bootstrap interval) |
|---|---:|---:|---|
| B0 no revision | 0.4899 | 0.8745 | — |
| B1 + train mean revision | 0.4897 | 0.8726 | -0.0002 (-0.0019, +0.0016) |
| B2 per-series OLS | 0.4953 | 0.8871 | +0.0054 (-0.0041, +0.0154) |
| B3 validation-selected | 0.4916 | 0.8836 | +0.0017 (-0.0045, +0.0084) |

Bootstrap intervals resample test observations i.i.d. and ignore serial correlation; treat them as indicative.

## 7. Limitations

See `docs/ETHICS_AND_LIMITATIONS.md`.

## 8. Availability

Code and data: {{GITHUB_REPO_URL}} and https://doi.org/{{ZENODO_DOI}}. Code is MIT; FedDrift data is CC BY 4.0; agency values are public domain. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

## Author contributions and AI disclosure

Tosin Clement: conceptualization, methodology, validation, data curation (all verified labels), writing. Claude (Anthropic) assisted with retrieval, harmonization, QA and benchmark code, evidence retrieval and documentation drafts; its proposals are kept separate from the author's verified labels. The author is accountable for the content.

## References

- Croushore, D., and Stark, T. (2001). A real-time data set for macroeconomists. *Journal of Econometrics*, 105(1), 111–130.
- Federal Reserve Bank of St. Louis. ALFRED: Archival Federal Reserve Economic Data. https://alfred.stlouisfed.org/
- Agency documents cited as evidence: `evidence/source_registry.csv` (361 documents).

## Figures

![Figure 1. Drift events by series and vintage date, coloured by cause.](figures/fig1_event_timeline.png)

![Figure 2. Depth of the February CPI-U (SA) revision; hollow markers are lower bounds.](figures/fig2_cpi_seasonal_depth.png)

![Figure 3. Share of releases that revise at least one value, by series.](figures/fig3_revision_frequency.png)

![Figure 4. T2: mean absolute revision of first-release growth after 36 months, by series.](figures/fig4_t2_revision_size.png)
