# Next steps

## To reach v0.1.0 (release)
1. Complete `docs/VERIFY_CHECKLIST.md`, with labels first (`labels/README.md`).
2. Re-run the pipeline. Regenerate figures and docs with `--final`. Run `code/publish_gate.py`.
3. Publish: GitHub release, Zenodo DOI (reserve first, then fill `[DOI]` and `[date]`), arXiv data descriptor.

## v0.2 candidates
- Add BEA series (GDP, PCE) and Federal Reserve industrial production (G.17), each checked against the licensing protocol before inclusion.
- Add industry detail for MARTS/MRTS (NAICS 3-digit) and M3 categories.
- Store agency anchor snapshots on a schedule, so FedDrift builds its own agency-sourced vintage archive going forward and depends less on ALFRED.
- T1 extensions: series-held-out split; early-warning variant (predict the cause from the first k revised months).
- T2 extensions: alternative maturity definitions; level and annual-growth targets; stronger baselines (state-space revision models).
- Archive every agency source page the labels rely on (Internet Archive / Perma.cc) and store the archive URL in the label sheets.
