# Browser excerpt captures

bts.gov returns HTTP 403 to scripted clients, so these two BTS pages could not be downloaded by the pipeline. On 2026-10-03 they were opened by ordinary browser access (the built-in browser pane of the Claude desktop app), and the relevant text of each page's `<main>` element was saved here. Nothing was done to bypass access controls.

| File | Page | Captured (UTC) | Capture SHA-256 | Rendered page HTML at capture time |
|---|---|---|---|---|
| `bts_tsi_revision_policy.excerpt.txt` | Revision Policy for the Transportation Services Index (dated on page: Friday, November 22, 2024) | 2026-10-03T22:36:37Z | cd4ba5042df3b85433b9427abda27223162084ea76d1e24e73278e00a49ff00a | 103,214 bytes, SHA-256 feeee572744fab6737b258a3a770b75107fc546cc87dd75748d68e61624bf10c |
| `bts_tsi_release_2025-07-10.excerpt.txt` | May 2025 Freight TSI release, BTS 42-25 (dated on page: Thursday, July 10, 2025) | 2026-10-03T22:35:05Z | e277184d27a6ac40e4aab8c49fabe2fd0a446506817b5051de1c9ae804713805 | 275,972 bytes, SHA-256 165e03529e8a6d001c2364f2e72c39f2eca1f28979fa0378fe13b2d886925bec |

Each capture's SHA-256 was computed inside the browser on the same text and matched the local file. These files are dated **excerpt captures of rendered page text**. They are not the original server files: the policy capture runs from the page title to the end of "Reasons for Revision", and the release capture holds the title, date, release number, the "Revisions" paragraph and the note to Table A. The rendered-HTML hashes are recorded only as a fingerprint and were not stored. The non-breaking spaces in the original text are preserved.
