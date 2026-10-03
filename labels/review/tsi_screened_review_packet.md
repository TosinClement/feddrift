# Review packet: 11 screened TSI releases (R27_TSI_SCREENED)

Prepared 2026-10-03 for the label owner. **These are recommendations, not decisions.** Nothing here is applied to labels until Tosin decides each release in chat.

## Count reconciliation (before writing this packet)

The "Before R26: 470" figure in the chat summary of 2026-10-03 was an arithmetic error in that message only. No file in the repository ever contained it. Committed outputs at 4103bf4 (before the R26 split) and 4569ee4 (after) give these counts:

| | Before (4103bf4) | After (4569ee4) |
|---|---|---|
| Vintage pairs | 6,295 | 6,295 |
| Drift events | 4,109 | 4,109 |
| Rule-level | 3,667 (incl. R26 267) | 3,653 (incl. R26 253) |
| Release-level | 442 in 220 releases | 456 in 231 releases |

Checks on the split:
- The event_id set is identical before and after, with 0 duplicates.
- Exactly 14 rows changed, all from R26/rule to R27/release, and all in TSIFRGHT or TSITTL.
- No other event changed rule, level or release cluster.
- 3,653 + 456 = 4,109.

## Evidence retrieval

BTS release pages were read in the built-in browser by ordinary access: one approved page load, then same-origin requests from that page. The quotes below are exact text from each page's `<main>` element. SHA-256 values are of the full page HTML as served at retrieval (2026-10-03, about 23:10–23:20 UTC), computed in the browser. No local capture file has been saved yet. Local excerpt captures will be made for the releases whose evidence the label owner accepts.

| Release | Date (on page) | No. | URL slug (www.bts.gov/newsroom/…) | HTML SHA-256 |
|---|---|---|---|---|
| Feb 2018 TSI | Wed, April 11, 2018 | — | february-2018-freight-transportation-services-index-tsi | b417d9e3118386e2671973aae3a881fecb5a325bad96258c1fb5811497385566 |
| Apr 2018 TSI | Wed, June 13, 2018 | — | april-2018-freight-transportation-services-index-tsi | 19d298a800ab6a5017a4d8d6e1b43a91bcf457941d1e699f0a8e131d6bd68362 |
| May 2020 TSI | Thu, July 9, 2020 | — | may-2020-freight-index-tsi-16-largest-one-month-rise-two-years | (not hashed) |
| Jun 2020 TSI | Wed, August 12, 2020 | — | june-2020-freight-transportation-services-index-tsi | 6a8977e443c001f481558b56554a0c9840a165f047871104de93069514cff5e9 |
| Aug 2020 TSI | Thu, October 15, 2020 | — | august-2020-freight-transportation-services-index-tsi-down-13-july | cc6677d4fbb74a8f3216150e2a991f41d0d533da4dc7f1bfbbf0a1f35334f958 |
| Jan 2021 TSI, CORRECTED | Tue, March 30, 2021 | BTS 17-21 Corrected | corrected-january-2021-freight-transportation-services-index-tsi-rose-11-december | aada334e3425910530f248e289707dd6f8c45c65bdc0a1342108589694752371 |
| Feb 2021 TSI | Wed, April 14, 2021 | — | february-2021-freight-transportation-services-index-tsi-largest-monthly-decline-onset | 81f0645eb3b695d40ee2e3d99f00b5814c3787790df0dea7c60e6e1cc509b895 |
| Apr 2021 TSI | Wed, June 9, 2021 | BTS 37-21 | april-2021-freight-transportation-services-index-tsi-equaled-highest-level-start-pandemic | a13bc82d5d9c336b98302a3b8900c8b799e52b7b37b086b80060197937a5a57f |
| Nov 2022 TSI | Thu, January 12, 2023 | BTS 02-23 | november-2022-freight-transportation-services-index-tsi-0 | de774b41f6429ab45bef12aa913628ff48fcf1ea4da8619c87c1886e0988d52f |

Not located: the November 2015 release (expected around 2016-01-13), the July 2020 release (expected around 2020-09-10), and the original March 10, 2021 version of the January 2021 release. That page now exists only in its corrected form.

### Exact quotes used

- **BTS 37-21 (June 9, 2021):** "The March index was revised to 135.9 from 130.0 in last month’s release due primarily to a 7.9% upward revision in the American Trucking Associations’ unadjusted truck tonnage index.  January was revised down slightly and February was revised up slightly. The entire series was revised to incorporate revised economic weights for 2020."
- **BTS 37-21:** "BTS is withholding the scheduled release of the passenger and combined indexes for April. … The March passenger and combined indexes are available on the BTS website."
- **BTS 17-21 Corrected (March 30, 2021):** "The numbers in this release are corrected from the release issued on March 10 in which the December index number was incorrect."
- **BTS 17-21 Corrected:** "Data revisions due to changes in source data from previous months: The December index was revised to 134.6 from 136.3 in last month’s release following a downward revision in truck tonnage. … The revisions were released previously in the March 10 release."
- **Aug 2020 release (October 15, 2020):** "The July index was revised to 132.8 from 128.9 in last month’s release. This was largely due to a revision in the (non-seasonally adjusted) ATA truck tonnage index from an advanced estimate of a 2.5% decrease, to a final estimate of a 1.3% increase."
- **May 2020 release (July 9, 2020):** "Although the May Passenger TSI is being withheld because of the difficulty of estimating air passenger miles and other modes, the April index is now being released."
- **Every release above:** "Revisions: Monthly data has changed from previous releases due to the use of concurrent seasonal analysis, which results in seasonal analysis factors changing as each month’s data are added."

## Releases

See the chat table of 2026-10-03, about 18:30 CT, for the recommendations. The release decisions will be recorded in `labels/decisions/` only after the label owner decides.
