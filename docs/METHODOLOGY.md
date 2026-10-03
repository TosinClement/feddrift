# FedDrift methodology

This document specifies how FedDrift is built, from source files to benchmark scores. Every count quoted in the README or the data descriptor is generated from `paper/stats.json`. This document gives no counts, only rules.

## 1. Panel and snapshot

- The panel is `config/panel.csv`: 17 monthly series. They come from Census (MARTS, MRTS, M3, MTIS), BLS (CPI, PPI) and BTS (Transportation Services Index). NSA CPI-U (`CPIAUCNS`) is included as a negative control, because BLS does not routinely revise published NSA CPI values.
- The snapshot is `config/snapshot.json`. It holds the ALFRED real-time cutoff (`alfred_realtime_end`), the committed agency snapshot directory, and the start of the observation window (1947-01). Every published number is computed from this snapshot.

## 2. Two data layers

**Agency anchor (Layer A).** `code/01_fetch_agency.py` downloads the current agency files:
- the Census Economic Indicators bulk zips;
- the BLS LABSTAT flat files `cu` and `wp`;
- BTS Monthly Transportation Statistics (Socrata `crem-w557`).

Each file is logged in `data/raw/PROVENANCE.txt` with its URL, timestamp, size and SHA-256. `code/02_build_anchor.py` extracts the panel series into `data/processed/anchor_vintage.csv`.

**Real-time history (Layer B).** `code/03_fetch_alfred.py` queries the FRED API for each series with these parameters:
- `realtime_start = 1776-07-04`
- `realtime_end = alfred_realtime_end`
- `observation_start = 1947-01-01`
- `output_type = 1` (real-time periods)

The vintage dates come from `series/vintagedates` with the same cutoff. The results are cached locally and never redistributed. For each vintage, `data/manifests/<SERIES>.vintages.csv` records:
- the vintage date;
- the number of observations;
- the first and last observation;
- a content hash: SHA-256 over the lines `YYYY-MM-DD,value\n`, sorted by date, using the values exactly as the API returns them.

## 3. Vintage reconstruction and drift footprints

For a vintage date *v*, the vintage vector is every real-time row with `realtime_start <= v <= realtime_end` and a value other than `"."`.

`code/04_vintage_pairs.py` compares each pair of consecutive vintages (*v*<sub>prev</sub>, *v*<sub>next</sub>) of a series on the observation months they share. An observation counts as revised when its relative change exceeds 1e-9. For each pair it records:

- **Counts:** new, dropped, shared and revised observations, and the share revised.
- **Range:** earliest and latest revised observation.
- **Depth:** months from the vintage month back to the earliest revised observation. Span: the inclusive months between the earliest and latest revised observation.
- **Magnitude:** mean, max and net percentage revision over revised observations, |new − old| / |old| × 100.
- **Direction:** share of revised observations revised up.
- **Growth revision:** mean absolute revision of month-over-month percentage growth over revised observations, in percentage points.
- **Distribution shift:** a two-sample Kolmogorov–Smirnov statistic and p-value comparing the m/m growth rates inside the revised window, before and after. Left empty when the window has fewer than 5 months.
- **`rebase_like`:** at least 95% of shared observations revised, more than 12 of them, by a near-constant ratio (sd of log ratio < 1e-3, non-zero mean).
- **`depth_censored`:** the earliest revised observation lies within two months of the first observation both vintages share. The measured depth is then only a lower bound, because the vintage (or the series) holds no earlier data. This matters most for early ALFRED CPI-U SA vintages: 1972–1993 vintages hold only 19 months, so the February seasonal revisions in those years appear about 19 months deep even though BLS stated in 1977 that each annual update would replace five years.

## 4. Events, rules, releases and labels

**Event identity.** Every pair gets `event_id = FD-<series_id>-<vintage_next as YYYYMMDD>`. A series has at most one ALFRED vintage per date, so the ID is unique and stable across runs. A drift event is a pair that revises at least one published value. Pairs that only append observations, or that show ALFRED's rolling archival window, are kept in the table but marked `excluded_not_drift`.

**Rule proposals.** `code/05_propose_labels.py` applies `config/revision_rules.csv` in priority order. Each rule proposes one cause from `config/causes.csv`. Routine rules (R2x) cover shallow revisions within a per-series routine window, set from the modal depth plus one month and backed by a program-level agency policy statement. Release rules (R02 rebase, R10 BLS February seasonal recompute, R30 Census spring annual revision, R90 unclassified) send the event to release-level review.

**Release clusters.** Release-level events are grouped by release program and vintage date (`FDC-<program>-<YYYYMMDD>`). One agency release has one document and one cause. Its events differ only by series.

**Evidence.** `code/06_harvest_evidence.py` downloads agency documents and registers each in `evidence/source_registry.csv` (publisher, title, document id, publication date, URL, retrieval method, access time, SHA-256). The documents are:
- Census annual-revision reports, M3 full reports, MTIS releases and MARTS releases;
- BLS CPI and PPI news releases, errata and methodology pages;
- BTS revision-policy pages.

For each cluster the script:
- extracts the agency's revision statement;
- runs an automated consistency check (for example, whether the first month the agency says it revised equals the earliest revised observation, or whether the agency's issue date precedes the vintage);
- records Claude's recommended cause with a confidence grade: strong, moderate, weak or none.

M3 reports issued before about 2003 are scanned images. They are read with OCR, and quotes from them are marked as such.

**Labels.** Only the label owner decides labels, in `labels/decisions/`, through the review workbook (`code/07_build_review.py`, `code/import_review.py`). The two levels are:
- **Rule level:** approving a rule labels every routine event it covers (`rule_verified`).
- **Release level:** approving, setting or marking `unknown` labels every event of that release (`release_verified` / `unknown_verified`).
- **Overrides:** single events can be relabeled individually (`override_verified`).

`code/08_apply_labels.py` writes `final_cause`, the label provenance (source IDs, titles, publishers, publication dates, URLs, locator), the reviewer and the verification date. An event is never marked verified without a decision row naming the reviewer and date. `unknown` is a legitimate final label.

## 5. Benchmark tasks

Both tasks are defined in `code/09_benchmark.py`. The random seed is 20261003, and it is used only by the decision tree and the bootstrap.

### T1 — revision-cause attribution
- **Unit:** one drift event.
- **Features:** vintage month; counts of revised, new and dropped observations; share revised; depth and span; `depth_censored`; mean, max and net % revision; share up; mean absolute growth revision; KS statistic; days between vintages; `rebase_like`; release program (one-hot). All are computable on the release day from the two vintages.
- **Target:** `final_cause`. Events labeled `unknown` are counted but not scored.
- **Splits (by `vintage_next`):** train < 2010-01-01; validation 2010-01-01 to 2014-12-31; test ≥ 2015-01-01. All events of one agency release share a date, so a release never spans two splits (QA check Q15).
- **Baselines:**
  - majority class;
  - calendar: majority cause per series × vintage month, from train;
  - decision tree: depth chosen on validation from {2, 3, 4, 6, 8}, refit on train + validation.
- **Metrics:** macro-F1 over causes present in test, accuracy, per-cause support.
- **When it runs:** only when every drift event carries a verified label.

### T2 — real-time revision correction
- **Unit:** one observation month of one series.
- **Kept:** genuine first releases only, meaning the first vintage containing the month was published within 3 months of it. The observation also needs a mature value: the m/m growth in the first vintage at least 36 months after first release.
- **Input:** first-release m/m growth *g*1. **Target:** mature m/m growth *g*M.
- **Splits (by first-release vintage *v*1), leakage-free in calendar time:**
  - train: mature vintage < 2009-01-01;
  - validation: *v*1 ≥ 2009-01-01 and mature vintage < 2016-01-01;
  - test: 2016-01-01 ≤ *v*1 ≤ 2022-09-30.
  - Observations between these windows are excluded and counted.
  - Assertions in code: every train target is published before the first validation input, and every validation target before the first test input (QA check Q14).
- **Baselines:**
  - B0: no revision.
  - B1: *g*1 plus the series' mean train revision.
  - B2: per-series OLS of *g*M on *g*1, fitted on train.
  - B3: per series, whichever of B0–B2 has the lowest validation MAE.
  - B1 and B2 need at least 24 train observations, otherwise they fall back to B0.
- **Metrics:** MAE and RMSE in percentage points, pooled and per series. The pooled MAE difference against B0 gets a 95% bootstrap interval (2,000 i.i.d. resamples of test observations). This ignores serial correlation, so the interval is only indicative.

## 6. Quality assurance and release gate

`code/10_qa.py` runs checks Q01–Q20 and writes `data/processed/qa_report.md`. Each check has an expected result, the actual result and a status. The checks cover:
- provenance and reconstruction hashes;
- the snapshot cutoff;
- anchor agreement;
- schema, uniqueness, date ordering and missingness;
- label vocabulary and label honesty;
- count reconciliation and the negative control;
- leakage;
- evidence completeness;
- the secret scan and package content rules;
- restricted files in Git (index and history);
- label coverage.

`code/publish_gate.py` checks that:
- no secrets are present;
- no draft markers remain;
- the only placeholders are the registered external identifiers (allowed at the `pre-deposit` stage, none at the `final` stage);
- every label is verified;
- QA is clean;
- figures and documents were generated in final mode.

`code/13_package.py --release` refuses to build the archive unless the gate passes.
