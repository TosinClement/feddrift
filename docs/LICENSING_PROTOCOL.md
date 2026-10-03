# FedDrift licensing protocol

**Status:** DRAFT v0.1. The author must review this before release.

FedDrift draws on two kinds of source. This protocol decides what each kind contributes to the public release, and it is enforced in code by `code/10_package.py`.

## Layer A: agency anchor vintage (redistributed)

These values come straight from the agency that publishes them. They are works of the U.S. federal government and are not subject to copyright in the United States (17 U.S.C. § 105).

| Agency | File(s) | What FedDrift redistributes |
|---|---|---|
| U.S. Census Bureau | EITS bulk files for MARTS, MRTS, M3 and MTIS | Raw zips and the extracted panel series |
| Bureau of Labor Statistics | LABSTAT flat files `cu` (CPI) and `wp` (PPI) | Raw flat files and the extracted panel series |
| Bureau of Transportation Statistics | Monthly Transportation Statistics (Socrata `crem-w557`), labelled *Public Domain U.S. Government* | **Only the BTS-produced TSI fields**, extracted into `anchor_vintage.csv`. The full MTS file is **not** redistributed (see below) |

The full MTS file is held back because it is compiled from many contributors. Some of its columns, for example the truck tonnage index, are produced by private organizations. The dataset-level public-domain label does not settle the status of every column. FedDrift therefore keeps only the columns BTS itself produces. Anyone who wants the full file can re-fetch it using the URL and SHA-256 recorded in `data/raw/PROVENANCE.txt`.

## Layer B: real-time vintage history from ALFRED (reconstructed, not redistributed)

Each series' revision history comes from ALFRED, which is operated by the Federal Reserve Bank of St. Louis, through the FRED API. The FRED API Terms of Use apply to how the data is accessed. FRED marks each series with a copyright tag. On the 2026-10-03 snapshot, all 17 panel series carry the tag `public domain: citation requested` (recorded per series in `data/manifests/alfred_manifest.json`).

Even so, FedDrift **does not redistribute ALFRED observation values**. This conservative rule was set by the author in the project brief. It keeps the release independent of any change to FRED's terms or tags, and of any later panel series that is not in the public domain. What FedDrift ships instead:

1. **Reconstruction code:** `code/03_fetch_alfred.py`. Anyone with a free FRED API key can rebuild the identical history.
2. **Vintage manifests:** `data/manifests/<SERIES>.vintages.csv`. There is one row per vintage, holding the vintage date, the observation count, the first and last observation, and a SHA-256 content hash of that vintage.
3. **Verification:** `code/06_qa.py`, section 2. It rebuilds every vintage and checks it against the published hash, so a user can confirm they hold exactly the data FedDrift was built from.

The local cache `data/raw/alfred_cache/` is excluded from the release by `.gitignore` and by `code/10_package.py`.

## Layer C: derived statistics and labels (redistributed, CC BY 4.0)

`drift_events.csv`, the label sheets, the QA outputs and the benchmark results are FedDrift's own contribution. This covers revision footprints (depth, counts, percentage magnitudes, KS statistics) and the cause labels. None of these files contains an observation level from Layer B.

> **[VERIFY] Author decision required.** Percentage revision magnitudes are derived from ALFRED values. The author confirms that redistributing these derived statistics fits the protocol's intent, or chooses to move those columns into the reconstruction path instead.

## Licenses

- Code: MIT (`LICENSE`).
- FedDrift's own data and documentation (Layer C): CC BY 4.0 (`LICENSE-DATA.md`).
- Layer A values: public domain U.S. government works, redistributed with attribution to each agency.
- Layer B: not redistributed. Users who rebuild it are bound by the FRED API Terms of Use.

## Adding a series

Before adding a series to `config/panel.csv`:

1. Check its FRED copyright tag. Any series tagged `copyrighted: ...` stays out of Layer A and out of the derived magnitudes until the author approves it in writing in this file.
2. Confirm that the agency file the anchor comes from is a government work.
3. Re-run `code/10_package.py`. It refuses to package if its checks fail.
