FedDrift is an open benchmark of vintage-labeled distribution shift in U.S. federal economic and freight statistics. It covers 17 monthly series: Census MARTS, MRTS, M3 and MTIS; BLS CPI and PPI; and the BTS Transportation Services Index. From 6,312 ALFRED real-time vintages it derives 6,295 consecutive vintage pairs, of which 4,109 revise published values. Each such drift event records its vintage date, a revision footprint, a distribution-shift statistic and a cause label. The author verified each label against agency documents, cited with URL, publication date and SHA-256.

Label status: 3,766 verified; 31 with final label *unknown*.

Agency values are redistributed as public-domain U.S. Government works. ALFRED values are not redistributed: reconstruction code and SHA-256 vintage manifests let users rebuild them with a FRED API key. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

Benchmark tasks: T1 revision-cause attribution; T2 real-time revision correction (test MAE of the no-revision baseline: 0.490 percentage points).

Contributions: Tosin Clement designed FedDrift and made and verified all substantive labeling decisions. Claude (Anthropic) assisted with code, harmonization, evidence retrieval and documentation drafts.
