# FedDrift decision log

Every entry records a decision the label owner (Tosin Clement) explicitly approved, with the time and the channel. Claude records decisions here only after explicit approval; recommendations are never logged as decisions.

| # | Time (CT) | Item | Decision | Channel |
|---|---|---|---|---|
| 1 | 2026-10-03 15:28 | J1 ALFRED values | keep_no_values | chat |
| 2 | 2026-10-03 15:28 | J2 derived statistics | ship_derived | chat |
| 3 | 2026-10-03 15:28 | J3 full BTS file | withhold_full_file | chat |
| 4 | 2026-10-03 15:28 | J4 review granularity | review_per_release | chat |
| 5 | 2026-10-03 15:28 | J5 evidence bar | strong_or_moderate | chat |
| 6 | 2026-10-03 15:56 | Rule R20_ROUTINE_MARTS_SA (594 events) | approve -> advance_to_revised; note recorded in rule_decisions.csv | chat |
| 7 | 2026-10-03 16:01 | Rule R21_ROUTINE_MARTS_NSA (298 events) | approve -> advance_to_revised; note recorded in rule_decisions.csv | chat |
| 8 | 2026-10-03 16:03 | Rule R22_ROUTINE_MRTS (92 events) | approve -> advance_to_revised; note recorded; evidence limitation recorded in evidence/evidence_limitations.csv | chat |
| 9 | 2026-10-03 16:05 | Rule R23_ROUTINE_M3 (1,504 events) | approve -> advance_to_revised; note recorded in rule_decisions.csv | chat |
| 10 | 2026-10-03 16:10 | Rule R24_ROUTINE_MTIS (495 events) | approve -> advance_to_revised; note recorded; two limitations recorded; release-gate action: verify mtis2606.pdf header date | chat |
| 11 | 2026-10-03 17:14 | Rule R25_ROUTINE_PPI (417 events) | approve -> advance_to_revised; note recorded; BLS Handbook PPI Presentation and Calculation pages added as evidence (SRC-F17B3D6CD3, SRC-4B1675D716) | chat |
| 12 | 2026-10-03 17:19 | Rule R26_ROUTINE_TSI | approve option (b): routine_reestimation for the 253 TSI events with max single-month revision <= 3.0%; 14 events > 3.0% moved to release-level review (rule R27_TSI_SCREENED); note and limitations recorded | chat |
| 13 | 2026-10-03 18:11 | Releases: 11 screened TSI releases (14 events) | unknown: FDC-TSI-20160113, -20180411, -20180613 (2 events), -20200709, -20200812, -20200910, -20210310 (2 events), -20230117, FD-TSITTL-20210609; set advance_to_revised: FDC-TSI-20201015; set correction: FDC-TSI-20210414; override methodology_change: FD-TSIFRGHT-20210609; notes recorded verbatim in release_decisions.csv / event_overrides.csv | chat |
| 14 | 2026-10-03 18:37 | Releases batch 2 (9 releases, 10 events) | unknown: FDC-CPI-19720121, -19730522, -19740521, -19741022, -19741220 (2 events), -19750521, -19860225, -19900221; set annual_benchmark: FDC-MTIS-19990813 (2 events); FDC-MTIS-20050915 HELD pending FDC-M3-20050819 (no decision recorded); notes and limitations recorded | chat |
| 15 | 2026-10-03 18:55 | Releases batch 3 (16 releases, 35 events) | methodology_change: FDC-CPI-19510302; annual_benchmark: FDC-MARTS-20070329 (+sample_redesign), -20080430, -20090430, -20100430, -20110429, -20130531 (+sample_redesign), -20150513; rebase_or_definition: FDC-MTIS-20010614; unknown: FDC-MARTS-20160715, FDC-MRTS-20180314, FDC-M3-19980729, FDC-M3-20020424, FDC-MTIS-19980514, -20000512, -20000614; HELD: FDC-MTIS-20060613 (pending FDC-M3-20060519), FDC-MTIS-20070613 (pending FDC-M3-20070518). Qualification text received truncated; remainder received 19:13 and appended to the existing release notes and hold limitations (no new decision rows) | chat |
| 16 | 2026-10-03 19:13 | Releases batch 4 (26 releases, 53 events) | Group A seasonal_factor_recompute: 24 February CPI releases FDC-CPI-20030221 through FDC-CPI-20260213 (CPIAUCSL, CPILFESL; 48 events; per-year timing limitations recorded where the BLS release post-dates the snapshot); Group B methodology_change, no secondary cause: FDC-CPI-20020220 (2 events); Group C correction: FDC-CPI-20161018 (3 events) | chat |
