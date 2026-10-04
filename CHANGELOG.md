# Changelog

## 0.1.0 (released 2026-10-04)

First public version, built from the 2026-10-03 snapshot.

- Panel of 17 monthly series: Census MARTS, MRTS, M3 and MTIS; BLS CPI and PPI; BTS TSI.
- Agency anchor layer with SHA-256 provenance. ALFRED real-time layer distributed as reconstruction code plus hash-verified vintage manifests, pinned to `realtime_end` 2026-10-03.
- Vintage-pair footprints for every consecutive vintage, including a distribution-shift statistic and a censored-depth flag.
- Stable event IDs; rule-based proposals; agency releases grouped into review clusters; an evidence registry of agency documents with automated consistency checks.
- Labels verified by the label owner at rule, release and event level. The label status of every event is published.
- Benchmark tasks: T1 (revision-cause attribution) and T2 (real-time revision correction), with leakage-free calendar splits and simple baselines.
- QA suite (Q01–Q20), release gate, and a reproducible release archive with a SHA-256 manifest.

### Corrections made before release (relative to the internal draft of 2026-10-03)

- The internal draft said the CPI February seasonal revision reached back "about 19 months" before 1995. That was an artifact of ALFRED's 19-month archival window. BLS documented 5-year replacement from 1977. Depth is now flagged as censored where it reaches the start of the vintage.
- The draft treated the 2026-09-28 retail revision and the M3 date gap as open questions. Both are now documented from Census sources: the 2026 annual revision based on the Annual Integrated Economic Survey, and the M3 benchmark issued 2025-05-16 that entered ALFRED with the next regular reports.
- The draft's T2 split allowed training targets published after test inputs. The splits are now separated in calendar time, and the separation is asserted in code.
