# Limitations and ethics statement

## Ethics

- **No personal data.** FedDrift contains only published aggregate national statistics and their publication histories. It has no microdata, no respondent-level information and nothing about identifiable people or businesses. No human-subjects review applies.
- **Honest labeling.** Every cause label is a claim about why a government agency changed its published numbers. FedDrift keeps the machine proposal, Claude's recommendation and the label owner's verified decision in separate columns. An event is marked verified only when a decision row names the reviewer and the date. Where agency sources do not establish a cause, the label is `unknown`.
- **Agency attribution.** Every verified label cites the agency document it rests on. FedDrift interprets agency practice from public documents; it does not speak for any agency.
- **Use.** FedDrift is built to study data revisions and to evaluate methods that must cope with them. Do not use the labels as statements about an agency's competence or intent: revisions are a normal, documented part of producing official statistics.

## Limitations

1. **Archive dates are not release dates.** A vintage date is the day ALFRED recorded a new version of a series, and it can differ from the agency's announcement. Examples:
   - Census issued the 2025 M3 benchmark on 2025-05-16. It entered ALFRED with the next regular reports: 2025-05-27 for DGORDER and NEWORDER (the advance report) and 2025-06-03 for AMTMNO (the full report).
   - BLS posts revised seasonally adjusted CPI and PPI data a few days before the January-data news release.

   FedDrift dates events by ALFRED vintage and records the agency's issue date separately where a source gives it.
2. **Censored depth.** Some early ALFRED vintages hold only a short rolling window. For example, CPI-U SA vintages from 1972–1993 hold 19 months. Revision depth in those vintages is a lower bound (`depth_censored`).
3. **Coverage starts when ALFRED's archive starts.** That date differs by series: 1949 for NSA CPI-U, 2017 for the MRTS series. Earlier revisions are not observed.
4. **One primary cause per event.** Agency annual revisions bundle benchmarking, historical corrections, seasonal-model updates and sometimes classification restatements. FedDrift records one primary and one secondary cause.
5. **Routine windows are empirical.** Each series' routine-revision window is set from the modal depth in the data and is supported by a program-level agency policy statement. Events just past a window go to release review instead of being labeled routine.
6. **Evidence strength varies.** Recent releases have release-specific documents that can be checked against the data automatically. For many older releases only program-level policy or OCR-read scanned reports exist. The confidence grade of each recommendation is published with the label.
7. **Agency files change between archives.** The agency layer is one snapshot. On the snapshot date the Census MRTS file already carried the 2026-09-28 annual revision, which ALFRED had not yet vintaged (QA check Q05 NOTE).
8. **T2 is narrow by design.** It covers month-over-month growth, a 36-month maturity and genuine first releases only. Other definitions of "mature" give different numbers. The baselines are deliberately simple.
9. **T1 class imbalance.** Routine revisions dominate, so macro-F1 is the headline metric. Per-cause support is reported.
10. **Panel scope.** v0.1 covers 17 headline series from three agencies. It is not a census of federal statistics, and findings should not be generalized beyond the panel without new evidence.
