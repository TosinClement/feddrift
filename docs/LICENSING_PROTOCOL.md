# FedDrift data-use and licensing protocol

This document decides what FedDrift redistributes and under which terms. `code/13_package.py` enforces it mechanically, and QA check Q18 tests that enforcement. Decisions marked **(J1)–(J3)** are the label owner's judgment calls, recorded in `labels/decisions/judgment_calls.csv`.

## Sources and their terms (as read on 2026-10-03)

| Layer | Source | Terms that apply | What FedDrift ships |
|---|---|---|---|
| A | U.S. Census Bureau Economic Indicators bulk files (MARTS, MRTS, M3, MTIS) | Works of the U.S. Government, not subject to U.S. copyright (17 U.S.C. § 105) | The raw files as fetched, plus the extracted panel values (`anchor_vintage.csv`) |
| A | U.S. Bureau of Labor Statistics LABSTAT flat files (`cu`, `wp`) | Same as above | Same as above |
| A | Bureau of Transportation Statistics, Monthly Transportation Statistics (Socrata `crem-w557`) | Dataset labelled "Public Domain U.S. Government". It compiles 136 columns from many providers, with no per-column source notes | **Only the two BTS-produced TSI columns**, extracted. The full file is withheld; its URL and SHA-256 are in `data/raw/PROVENANCE.txt` **(J3)** |
| B | ALFRED real-time vintages via the FRED® API (Federal Reserve Bank of St. Louis) | FRED API Terms of Use and FRED Legal. All 17 panel series are tagged *Public Domain: Citation Requested* (recorded per series in `data/manifests/alfred_manifest.json`) | Manifests and reconstruction code only; no observation values **(J1)** |
| C | FedDrift's own outputs: event table, footprints, labels, evidence registry, QA and benchmark results | CC BY 4.0 | Everything in `data/processed/`, `labels/`, `evidence/`, `paper/` |

### What the FRED terms say (quoted 2026-10-03)

- **FRED Legal, *Public Domain: Citation Requested*:** "These series may be under copyright or in the public domain and may be used without permission, provided you do not engage in any prohibited use. When using, please cite the data source and acknowledge that you obtained the data from FRED (example, 'Source: BLS via FRED') when displaying or publishing it."
- **FRED Legal, prohibited use:** "You may not take all the data on FRED or related services and claim it is a unique product or service or otherwise provide the essential experience of the FRED website, data, or service."
- **FRED API Terms of Use, third parties:** "Before using data series owned by third parties for anything other than your own personal use, you must contact the data owner to obtain permission."
- **FRED API Terms of Use, required notice:** applications must state "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis." FedDrift's reconstruction code uses the FRED API, so this notice appears in the README.

### Decision J1: ALFRED values

The tags as read permit redistribution with citation. FedDrift nevertheless follows the stricter rule set in the original project brief: it **ships no ALFRED observation values**. The reasons are:
1. A FRED tag can change after a release, and a no-values release never needs to be withdrawn.
2. The agency layer already redistributes current values directly from the agencies.
3. Hash-verified reconstruction gives users the identical history with a free FRED key.

The alternative, `ship_values`, remains open to the label owner.

### Decision J2: derived statistics

`drift_events.csv` contains statistics computed from ALFRED values: percentage revision magnitudes, growth-rate revisions and KS statistics. These are summaries of public-domain series. They contain no observation level and do not replicate the FRED experience, so FedDrift ships them. This keeps T1 usable without a FRED key. Users who rebuild Layer B reproduce them exactly (QA check Q03).

### Decision J3: BTS file

The full MTS file is withheld. Its dataset-level public-domain label does not establish the status of each of its third-party columns, and FedDrift needs only the TSI columns that BTS itself produces.

## Enforcement

`code/13_package.py` refuses to package any file that contains:
- ALFRED real-time observation rows (JSON or CSV form);
- a FRED API key or a GitHub token;
- a private key or credential file.

The following are always excluded from the archive: `data/raw/alfred_cache/`, `evidence_cache/` and the full BTS file.

## Citation requirements for users

When using FedDrift, cite FedDrift (see `CITATION.cff`). When displaying values, also cite the agencies: "Source: U.S. Census Bureau", "Source: U.S. Bureau of Labor Statistics", "Source: Bureau of Transportation Statistics". When displaying rebuilt ALFRED values, cite "Source: <agency> via FRED®, Federal Reserve Bank of St. Louis (ALFRED)".

## Adding a series later

1. Check its FRED copyright tag (`series/tags`, group `cc`). A series tagged `copyrighted: …` stays out until its owner grants written permission.
2. Confirm that the agency file it comes from is a U.S. Government work.
3. Re-run QA. Check Q18 must pass.
