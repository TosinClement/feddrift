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
