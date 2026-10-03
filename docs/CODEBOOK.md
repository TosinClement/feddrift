# FedDrift codebook and data dictionary

Dates are ISO 8601. A **vintage** is the date a version of a series became part of the public real-time record (ALFRED `realtime_start`). An **observation month** (`obs`) is the reference month of a value, written as the first day of that month. The column order of `drift_events.csv` is locked in `config/schema.json`, and QA check Q06 enforces it.

## Cause taxonomy (`config/causes.csv`)

| Cause | Definition | Allowed as final label |
|---|---|---|
| `advance_to_revised` | Scheduled routine revision: an advance or preliminary estimate replaced in the next regular release(s). Includes the routine concurrent seasonal re-estimation that accompanies each release, and the BLS PPI recalculation four months after first publication | yes |
| `annual_benchmark` | Annual or periodic revision: monthly estimates benchmarked to annual surveys or the Economic Census, usually with historical corrections and updated seasonal models | yes |
| `seasonal_factor_recompute` | Recalculation of seasonal factors that revises several years of SA data without benchmarking (BLS CPI and PPI with the January release; M3 seasonal-model updates) | yes |
| `sample_redesign` | A new survey sample is introduced | yes |
| `rebase_or_definition` | Change of index reference base, units, classification system (e.g. NAICS restatement) or coverage definition (e.g. employer-only) | yes |
| `methodology_change` | Documented change in estimation method, weights or industry coverage that revises history | yes |
| `routine_reestimation` | Model-based series whose history is re-estimated at every release (BTS TSI) | yes |
| `correction` | Agency-announced correction of erroneous published values | yes |
| `unknown` | Agency sources do not establish the cause. An honest final label | yes |
| `unclassified` | Proposal-only state: no rule applies | **no** |
| `none_extension_only`, `none_archival_window` | Not drift events (nothing revised) | excluded |

## `data/processed/drift_events.csv`: one row per consecutive vintage pair

`data/processed/event_inventory.csv` has the same columns, restricted to drift events (`is_drift_event = True`).

| Column | Type | Definition | Produced by |
|---|---|---|---|
| `event_id` | string | `FD-<series_id>-<vintage_next YYYYMMDD>`; unique and stable | 05 |
| `series_id` | string | FRED/ALFRED series ID (`config/panel.csv`) | 04 |
| `vintage_prev`, `vintage_next` | date | The two consecutive ALFRED vintages compared | 04 |
| `vintage_month`, `vintage_year` | int | Month and year of `vintage_next` | 04 |
| `days_between` | int | Days between the two vintages | 04 |
| `n_obs_prev`, `n_obs_next` | int | Observations (from 1947-01) in each vintage | 04 |
| `n_overlap` | int | Observation months present in both vintages | 04 |
| `n_new_obs`, `n_dropped_obs` | int | Months only in `vintage_next` / only in `vintage_prev` | 04 |
| `n_revised` | int | Shared months whose value changed (relative change > 1e-9) | 04 |
| `share_revised` | float | `n_revised / n_overlap` | 04 |
| `first_obs_prev` | date | First observation in `vintage_prev` | 04 |
| `first_obs_overlap` | date | First observation shared by both vintages | 04 |
| `earliest_revised_obs`, `latest_revised_obs` | date | Range of revised months; empty if nothing was revised | 04 |
| `revision_depth_months` | int | Vintage month minus earliest revised month | 04 |
| `depth_censored` | bool | Earliest revised month within 2 months of `first_obs_overlap`; depth is a lower bound | 04 |
| `revision_span_months` | int | Months from the earliest to the latest revised month, inclusive | 04 |
| `mean_abs_pct_revision`, `max_abs_pct_revision` | float | Mean and max of \|new − old\| / \|old\| × 100 over revised months | 04 |
| `net_pct_revision` | float | Mean signed % revision over revised months | 04 |
| `share_up` | float | Share of revised months revised upward | 04 |
| `mean_abs_growth_revision_pp` | float | Mean \|Δ\| of m/m % growth over revised months, in percentage points | 04 |
| `ks_growth_window`, `ks_growth_window_p` | float | Two-sample KS statistic and p-value comparing m/m growth before and after the revision, within the revised window; empty if the window has fewer than 5 months | 04 |
| `rebase_like` | bool | At least 95% of shared months rescaled by a near-constant ratio | 04 |
| `release_program` | string | MARTS, MRTS, M3, MTIS, CPI, PPI or TSI | 05 |
| `proposed_rule`, `proposed_cause` | string | Rule that fired (`config/revision_rules.csv`) and the cause it proposes. Machine output, not a label | 05 |
| `review_level` | string | `excluded`, `rule` (routine) or `release` (non-routine) | 05 |
| `is_drift_event` | bool | True if at least one published value was revised | 05 |
| `release_cluster_id` | string | `FDC-<program>-<YYYYMMDD>` for release-level events | 05 |
| `recommended_cause`, `recommended_secondary_cause` | string | Claude's evidence-based recommendation (release level), or the rule's cause (rule level). Not a label | 08 |
| `recommendation_confidence` | string | `strong`, `moderate`, `weak` or `none` (release level); `program_policy` (rule level) | 08 |
| `final_cause`, `final_secondary_cause` | string | **The label owner's verified label.** Empty while unverified | 08 |
| `label_status` | string | `excluded_not_drift`, `rule_pending_review`, `rule_verified`, `rule_rejected`, `release_pending_review`, `release_verified`, `unknown_verified` or `override_verified` | 08 |
| `label_basis` | string | `rule:<rule_id>`, `release:<cluster_id>`, `override` or `mechanical:<rule_id>` | 08 |
| `label_source_ids` | string | `;`-separated source IDs in `evidence/source_registry.csv` | 08 |
| `label_source_titles`, `label_source_publishers`, `label_source_publication_dates`, `label_source_urls` | string | Source details, `‖`-separated in the same order | 08 |
| `label_source_locator` | string | Page or section of the source where available | 08 |
| `reviewer`, `verified_date` | string, date | Who verified the label, and when (from `labels/decisions/`) | 08 |

## Other tables

| File | Grain | Key columns |
|---|---|---|
| `data/processed/anchor_vintage.csv` | Series × observation month (agency value) | `series_id`, `obs_date`, `value`, `anchor_source`, `anchor_file`, `anchor_file_sha256`, `snapshot_date` |
| `data/processed/vintage_pairs.csv` | Series × consecutive vintage pair (footprints only) | Footprint columns of `drift_events.csv` |
| `data/processed/proposed_events.csv` | As `vintage_pairs` plus identity, proposal and review columns | Columns 1–35 of `drift_events.csv` |
| `data/processed/release_clusters.csv` | Agency release | `release_cluster_id`, `release_program`, `vintage_date`, `series`, `n_events`, `event_ids`, `proposed_causes`, `proposed_rules`, `earliest_revised_obs`, `max_depth_months`, `any_depth_censored`, `max_mean_abs_pct_revision`, `any_rebase_like` |
| `data/processed/label_status.json` | Run | Counts by label status; `n_verified`; `n_unverified`; `n_final_unknown`; `final_cause_counts` |
| `data/processed/t2_split_counts.csv` | Series × T2 split | Observation counts |
| `data/manifests/<SERIES>.vintages.csv` | Vintage | `series_id`, `vintage_date`, `n_obs`, `first_obs`, `last_obs`, `vintage_sha256` |
| `data/manifests/alfred_manifest.json` | Series | Metadata, copyright tags, request parameters, cache hash |
| `evidence/source_registry.csv` | Agency document | `source_id`, `publisher`, `title`, `doc_type`, `document_id`, `publication_date`, `url`, `retrieval`, `accessed_utc`, `sha256`, `bytes` |
| `evidence/rule_evidence.csv` | Rule × source | `rule_id`, `source_id`, `quote`, `locator` |
| `evidence/cluster_evidence.csv` | Release | Sources, quotes, locator, agency issue date, `automated_check`, recommendation, `confidence`, `recommendation_basis` |
| `labels/decisions/*.csv` | Author decision | Judgment calls, rule decisions, release decisions, event overrides; each with `verified_by` and `verified_date` |
| `paper/tables/t2_overall.csv`, `t2_by_series.csv`, `t1_results.csv` | Baseline (× series) | MAE, RMSE, intervals; macro-F1, accuracy |
