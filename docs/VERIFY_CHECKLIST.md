# FedDrift v0.1 verification checklist (Tosin completes before any release)

Initial and date each line in your own copy. `code/publish_gate.py` checks the mechanical items. Everything else here is yours.

## Reproduce
- [ ] Fresh run on your Mac: `FRED_API_KEY=... bash run_all.sh`. Row counts match `data/raw/PROVENANCE.txt`, or the drift is explained (agencies publish between runs).
- [ ] `data/processed/qa_report.txt` section 2: 0 hash mismatches.
- [ ] Every number in README and the paper draft comes from `paper/stats.json` after your re-run.

## Source-level checks
- [ ] Open five agency files by hand and compare with `anchor_vintage.csv`: one each from MARTS, M3, MTIS, BLS CPI and BTS TSI.
- [ ] Re-read the FRED API Terms of Use and the BTS, Census and BLS terms. Nothing forbids what `docs/LICENSING_PROTOCOL.md` redistributes.
- [ ] Confirm the MRTS anchor note in the QA report against the Census release of 2026-09-28.

## Named spot checks (QA report section 6, all eight)
- [ ] FD-CPIAUCSL-20260213: SA revision back to 2021-01
- [ ] FD-CPIAUCNS-19880226: rebase to 1982-84=100
- [ ] FD-RSAFS-20180525: annual revision + new MRTS sample + 2012 NAICS
- [ ] FD-DGORDER-20250527: M3 benchmark (Census date 2025-05-16)
- [ ] FD-RSAFS-20221215: new MARTS sample, linked (routine footprint)
- [ ] FD-RSAFS-20260928: deep off-season revision (currently unclassified)
- [ ] FD-PPIACO-20260910: routine 4-month recalculation
- [ ] FD-TSIFRGHT-20261001: TSI full-history re-estimation

## Labels (the core of FedDrift)
- [ ] All `label_level = rule` rows in `labels/rule_sheet.csv` decided, each with an agency source URL and quote
- [ ] All rows in `labels/event_label_sheet.csv` labeled, each with an agency source; zero `unclassified` remain
- [ ] `python code/08_apply_labels.py` prints zero `unverified` drift events
- [ ] The 40 currently unclassified events reviewed, especially Aug/Sep 2003 and 2005 (M3/MTIS), Jan 2010 (M3/MTIS), the NSA CPI corrections (2000-09-28, 2016-10-18) and CPI 2002-02-20 (181-month SA revision)

## Judgment calls to own (agree, or change and document)
- [ ] **Licensing:** ALFRED tags all 17 series `public domain: citation requested`. Keep the stricter rule from the brief (no FRED values shipped)? Keep or move the derived % magnitudes (LICENSING_PROTOCOL.md, Layer C)?
- [ ] **BTS:** withhold the full MTS file (third-party columns), ship TSI fields only
- [ ] **Routine windows** per series (`config/revision_rules.csv`): accept the empirical depths or set them from agency policy
- [ ] **Census SA routine window ~14 months:** confirm concurrent seasonal adjustment as the explanation, or relabel
- [ ] **TSI:** treat every release as `routine_reestimation`, or label individual TSI events
- [ ] **T2 design:** 36-month maturity, first releases only (lag ≤ 3 months), train ≤ 2015-12, test 2016-01..2022-09
- [ ] **T1 split:** train vintages < 2015-01-01, test ≥ 2015-01-01
- [ ] **Observation window** stated as 1947–2026. The anchor keeps pre-1947 CPI/PPI values as published; the benchmark starts at 1947-01.

## Before it goes public
- [ ] README, LIMITATIONS, LICENSING_PROTOCOL and the paper draft rewritten in your own voice; nothing remains that you cannot defend
- [ ] AI-assistance statement in README and paper is accurate: Claude wrote retrieval and harmonization code and drafted docs; you own every label and analytic decision
- [ ] Regenerate with `python code/09_figures_stats.py --final` and `python code/11_build_docs.py --final`; `python code/publish_gate.py .` passes
- [ ] `[date]` and `[DOI]` filled from the real Zenodo deposit (reserve the DOI first)
- [ ] Revoke the GitHub token pasted into chat on 2026-10-03; create a fresh one at publish time
- [ ] Evidence-log row written on release day
