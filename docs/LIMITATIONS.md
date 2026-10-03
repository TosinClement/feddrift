# Limitations (DRAFT v0.1; read before using or citing FedDrift)

1. **Labels are unverified until the label owner signs them.** In this draft every drift-event cause is a *proposal* from a rule engine. That engine was fitted by eye to revision patterns in the data. A pattern such as "deep revision in May" is evidence of an annual benchmark. It is not proof. No final label exists until it has been checked against agency methodology (`labels/README.md`).

2. **Vintage dates are ALFRED's, not the agency's.** A vintage date is the day ALFRED recorded a new version, and it can trail the agency's release. Example: Census dates the 2025 M3 benchmark to 2025-05-16, but the benchmarked durable-goods values first appear in ALFRED's 2025-05-27 vintage. Event dates in FedDrift are ALFRED dates unless a label says otherwise.

3. **Vintage coverage is uneven.** ALFRED's archive starts at different dates for different series: 1949 for NSA CPI, 2017 for MRTS retail sales. Some early vintages hold only a rolling window of observations (CPI-U SA, 1972–1994). FedDrift reports these windows (`none_archival_window`) instead of treating them as revisions, but it cannot recover vintages that ALFRED never archived. Observations start in 1947 only where a series and its vintages reach that far back.

4. **One release can carry several causes.** Census annual revisions often bundle benchmarking, new seasonal factors, sample changes and classification restatements together. The schema allows one primary and one secondary cause. Finer decomposition would need the agency's own revision tables.

5. **Routine windows are empirical.** The routine-revision depth for each series was set from the modal depth in the data (`config/revision_rules.csv`). It has not yet been confirmed against each agency's revision policy. On seasonally adjusted Census series the routine window reaches about 14 months, consistent with concurrent seasonal adjustment. This still needs an agency source.

6. **Agency anchor is a single snapshot.** The redistributable agency layer reflects the files as fetched on the snapshot date. Agency files can be reissued between ALFRED vintages. The MRTS file reissued on 2026-09-28 is an example: QA reports it as 66.5% agreement with ALFRED's latest vintage.

7. **Derived magnitudes come from ALFRED values.** Percentage revisions and KS statistics are computed from Layer B values that FedDrift does not redistribute. The author must confirm that redistributing these derived statistics is consistent with the licensing protocol (`docs/LICENSING_PROTOCOL.md`).

8. **T2 is a narrow task.** It measures revisions to month-over-month growth at a fixed 36-month maturity, scored only on genuine first releases (published within 3 months of the reference month). Other definitions of "mature" (latest vintage, post-benchmark) or of the target (levels, annual growth) will give different numbers. The baselines are deliberately simple.

9. **T1 cannot be scored until labels exist.** The scorer refuses to grade against the rule engine's proposals, because doing so would measure the rules against themselves.

10. **Panel scope.** v0.1 covers 17 headline series. It does not cover industry detail, other agencies (BEA, Federal Reserve G.17), or quarterly series. Conclusions about "federal statistics" in general should not be drawn from it.
