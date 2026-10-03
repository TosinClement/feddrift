# FedDrift codebook (DRAFT v0.1)

All dates are ISO 8601. In FedDrift, **"vintage"** means the date a version of a series became publicly available, which is ALFRED's `realtime_start`. **"obs"** means the reference month of an observation, written as the first day of that month.

## Cause taxonomy (`proposed_cause`, `final_cause`)

| Cause | Meaning | Typical footprint |
|---|---|---|
| `advance_to_revised` | Routine scheduled revision. An advance or preliminary estimate is replaced by a revised one, sometimes together with routine concurrent seasonal re-estimation. For PPI this is the scheduled recalculation about four months after first publication. | Shallow: within the series' routine window |
| `annual_benchmark` | Annual revision. Benchmarking to annual surveys or the Economic Census, often with updated seasonal factors. | Deep (years), spring |
| `seasonal_factor_recompute` | Annual recalculation of seasonal factors. For BLS CPI and PPI this happens with the January release and revises five years of SA data. | February; depth about 60 months (about 19 months before 1995 for CPI) |
| `sample_redesign` | A new survey sample is introduced. | Varies. The agency may link samples so that no level shift appears |
| `rebase_or_definition` | Change of index reference base, unit, or classification (for example NAICS restatement). | Nearly all history rescaled |
| `routine_reestimation` | Model-based series (TSI) re-estimated over most of the history at every release. | Very deep, every release |
| `correction` | Agency-announced correction of published values. | Usually shallow and off-schedule |
| `other_major` | A documented non-routine revision that fits none of the above. | Any |
| `unclassified` | No rule applies. Only valid as a proposal, never as a final label. | Any |
| `none_extension_only` | Not a drift event: new observations appended, nothing revised. | No revisions |
| `none_archival_window` | Not a drift event: ALFRED's early vintages hold a rolling window, so the oldest observation drops out. | No revisions, one dropped obs |

`final_secondary_cause` holds a second cause when one release carries two (for example `annual_benchmark` with `sample_redesign`).

## `data/processed/drift_events.csv` (main release table; one row per consecutive vintage pair)

| Column | Definition | Source / transformation |
|---|---|---|
| `pair_id` | `FD-<series_id>-<vintage_next as YYYYMMDD>` | constructed |
| `series_id` | FRED/ALFRED series identifier | `config/panel.csv` |
| `vintage_prev`, `vintage_next` | The two consecutive ALFRED vintage dates being compared | FRED API `series/vintagedates` |
| `vintage_month`, `vintage_year` | Calendar month and year of `vintage_next` | derived |
| `days_between` | Days between the two vintages | derived |
| `n_obs_prev`, `n_obs_next` | Observations (from 1947-01) in each vintage | derived from ALFRED |
| `n_overlap` | Observation months present in both vintages | derived |
| `n_new_obs` | Months in `vintage_next` but not in `vintage_prev` | derived |
| `n_dropped_obs` | Months in `vintage_prev` but not in `vintage_next` | derived |
| `n_revised` | Overlapping months whose value changed (relative change > 1e-9) | derived |
| `share_revised` | `n_revised / n_overlap` | derived |
| `earliest_revised_obs`, `latest_revised_obs` | Range of revised observation months | derived |
| `revision_depth_months` | (vintage month) − (earliest revised obs month), in months | derived |
| `revision_span_months` | Months from the earliest to the latest revised obs, inclusive | derived |
| `mean_abs_pct_revision`, `max_abs_pct_revision` | Mean and max of \|new − old\| / \|old\| × 100 over revised months | derived; no levels released |
| `net_pct_revision` | Mean signed % revision over revised months | derived |
| `share_up` | Share of revised months revised upward | derived |
| `mean_abs_growth_revision_pp` | Mean \|Δ\| of month-over-month % growth over revised months, in percentage points | derived |
| `ks_growth_window`, `ks_growth_window_p` | Two-sample Kolmogorov–Smirnov statistic and p-value comparing the m/m growth distributions inside the revised window, before and after. This is the distribution-shift measure. Empty when the window has fewer than 5 months | `scipy.stats.ks_2samp` |
| `rebase_like` | True when ≥95% of shared months are rescaled by an almost constant ratio (sd of log ratio < 1e-3, mean ≠ 0) | derived |
| `is_drift_event` | False only for `none_extension_only` and `none_archival_window` | rule engine |
| `proposed_rule`, `proposed_cause` | Rule that fired and the cause it proposes (`config/revision_rules.csv`) | `code/05_propose_labels.py` |
| `proposed_secondary_cause`, `doc_event_key` | Secondary cause and key of an agency-documented event matched to this vintage (`config/agency_documented_events.csv`) | `code/05` |
| `final_cause`, `final_secondary_cause` | **The author's verified label** | `labels/` via `code/08_apply_labels.py` |
| `label_status` | `individually_verified`, `rule_verified`, `unverified`, or `not_a_drift_event` | `code/08` |
| `label_source_url`, `verified_date` | Agency methodology source the author relied on, and the date of verification | `labels/` |

## `data/processed/anchor_vintage.csv` (agency anchor vintage; public-domain values)

`series_id`, `obs_date`, `value` (as published by the agency), `anchor_source` (program, category, data type and adjustment, plus the agency's "data updated" stamp), `anchor_file` (path of the raw file), `anchor_file_sha256`, `snapshot_date`. Observations before 1947 are kept as published (CPI-U NSA and PPI start in 1913). The benchmark tables start at 1947-01.

## `data/manifests/` (Layer B reconstruction; no values)

- `<SERIES>.vintages.csv`: `series_id`, `vintage_date`, `n_obs`, `first_obs`, `last_obs`, `vintage_sha256`. The hash is the SHA-256 of the lines `YYYY-MM-DD,value\n`, sorted by date, built from the vintage's ALFRED values exactly as the API returned them as strings.
- `alfred_manifest.json`: per series, the title, units, SA flag, FRED `last_updated`, FRED copyright tags, vintage count and range, real-time row count, SHA-256 of the local cache file, fetch time, and the exact API request parameters.

## `labels/` (author-owned; see `labels/README.md`)

- `rule_sheet.csv`: one row per rule. Machine columns come from `config/revision_rules.csv`, plus `n_pairs`, `n_series` and `label_level`. Author columns: `tosin_decision` (`accept` / `modify` / `reject`), `tosin_source_url`, `tosin_source_quote`, `tosin_verified_date`, `tosin_notes`.
- `event_label_sheet.csv`: one row per event that needs an individual label. Machine columns give the footprint and proposal. Author columns: `final_cause`, `final_secondary_cause`, `agency_source_url`, `agency_source_quote`, `verified_by`, `verified_date`, `notes`.

## Benchmark outputs

- `paper/benchmark_results.json`: T1 status or scores, and T2 overall metrics for baselines B0, B1 and B2.
- `data/processed/t2_series_metrics.csv`: per series, `n_test`, `n_train`, `mean_abs_revision_pp`, `share_sign_flip` (first-release and mature growth differ in sign), and MAE and RMSE for each baseline.
