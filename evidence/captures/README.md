# Browser excerpt captures

bts.gov returns HTTP 403 to scripted clients, so these two BTS pages could not be downloaded by the pipeline. On 2026-10-03 they were opened by ordinary browser access (the built-in browser pane of the Claude desktop app), and the relevant text of each page's `<main>` element was saved here. Nothing was done to bypass access controls.

| File | Page | Captured (UTC) | Capture SHA-256 | Rendered page HTML at capture time |
|---|---|---|---|---|
| `bts_tsi_revision_policy.excerpt.txt` | Revision Policy for the Transportation Services Index (dated on page: Friday, November 22, 2024) | 2026-10-03T22:36:37Z | cd4ba5042df3b85433b9427abda27223162084ea76d1e24e73278e00a49ff00a | 103,214 bytes, SHA-256 feeee572744fab6737b258a3a770b75107fc546cc87dd75748d68e61624bf10c |
| `bts_tsi_release_2025-07-10.excerpt.txt` | May 2025 Freight TSI release, BTS 42-25 (dated on page: Thursday, July 10, 2025) | 2026-10-03T22:35:05Z | e277184d27a6ac40e4aab8c49fabe2fd0a446506817b5051de1c9ae804713805 | 275,972 bytes, SHA-256 165e03529e8a6d001c2364f2e72c39f2eca1f28979fa0378fe13b2d886925bec |

Each capture's SHA-256 was computed inside the browser on the same text and matched the local file. These files are dated **excerpt captures of rendered page text**. They are not the original server files: the policy capture runs from the page title to the end of "Reasons for Revision", and the release capture holds the title, date, release number, the "Revisions" paragraph and the note to Table A. The rendered-HTML hashes are recorded only as a fingerprint and were not stored. The non-breaking spaces in the original text are preserved.

## TSI release captures (2026-10-03, for the screened TSI releases)

These three captures were made the same way, with one difference: all three pages were requested from inside one bts.gov page the user approved in the browser (same-origin requests). The capture holds selected lines of each page's `<main>` text from the HTML served to the browser. The page HTML hash is of that served HTML.

| File | Page | Capture SHA-256 | Page HTML at capture time |
|---|---|---|---|
| `bts_tsi_release_2020-10-15.excerpt.txt` | August 2020 Freight TSI (dated on page: Thursday, October 15, 2020) | 7538d7bbe61fd241f6facbab63a0317e231dceb614285865aca18e584635f97a | 134,489 bytes, SHA-256 cc6677d4fbb74a8f3216150e2a991f41d0d533da4dc7f1bfbbf0a1f35334f958 |
| `bts_tsi_release_2021-03-30_corrected.excerpt.txt` | CORRECTED January 2021 Freight TSI, BTS 17-21 Corrected (dated on page: Tuesday, March 30, 2021) | d5b2ffcb50f8d20432bee2bed38fc977b038ce8d942b731465c38c3f5226daff | 238,186 bytes, SHA-256 aada334e3425910530f248e289707dd6f8c45c65bdc0a1342108589694752371 |
| `bts_tsi_release_2021-06-09.excerpt.txt` | April 2021 Freight TSI, BTS 37-21 (dated on page: Wednesday, June 9, 2021) | 494c76fc3e4f2b70e26f63c5b5439ec911bb9948ea1d6e13edf9d8c23bdcb397 | 281,647 bytes, SHA-256 a13bc82d5d9c336b98302a3b8900c8b799e52b7b37b086b80060197937a5a57f |

All three were captured at 2026-10-03T23:12:34Z. Each capture hash was computed in the browser and matches the local file.

## BLS Bulletin 1039 (1951), captured 2026-10-03

| File | Page | Capture SHA-256 | Page HTML at capture time |
|---|---|---|---|
| `bls_bulletin1039_1951.fraser_fulltext.excerpt.txt` | FRASER (Federal Reserve Bank of St. Louis) full-text page of BLS Bulletin No. 1039, *Interim Adjustment of Consumers' Price Index* (letter of transmittal dated June 29, 1951) | 9932c29567e806d5b26f447a39c56ddc5aa9d63713f8c6550687cdfd68f7ca53 | 274,347 bytes, SHA-256 d5466107542c2ba2820421509b29b06dc65ff8a26274adb48f6b61303af8eb82 |

This capture was taken at 2026-10-03T23:44:04Z. It holds selected sentences from FRASER's OCR text of the scanned bulletin, so the OCR artifacts (broken words, soft hyphens) are kept as they appear. It is a capture of a library's full-text rendering, not the BLS original.

## Treasury statement on the 2000 CPI revision, captured 2026-10-04

| File | Page | Capture SHA-256 | Page HTML at capture time |
|---|---|---|---|
| `treasury_slgs_statement_2000-09-28.excerpt.txt` | Bureau of the Public Debt, *Statement on CPI Revision and Inflation-Indexed Securities* (dated on page: September 28, 2000), served at slgs.gov (TreasuryDirect) | 77c865c01776d6e53f8a2dc9495426f7ce167fc43077569bf590d4456732e017 | 43,128 bytes, SHA-256 d31ad4aff98b471de432332709b4516cb75a17f7ecd5995d448cc0feca628e4f |

Captured at 2026-10-04T04:01:58Z from one page load the user approved in the built-in browser. The capture is the full `<main>` text, including the site's navigation lines, exactly as hashed in the browser; the hash matches the local file. Before this capture the source was cited only from a web-reader quote with no local file (see `evidence/evidence_limitations.csv`). This is a capture of rendered page text, not the original 2000 file. It is secondary evidence: the label for FDC-CPI-20000928 rests on the BLS source SRC-F5255A6C17.
