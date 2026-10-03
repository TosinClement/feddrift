#!/usr/bin/env python3
"""11 - Build README.md and the arXiv data-descriptor draft from paper/stats.json (the stats-file rule:
no number is typed into prose by hand).

Usage:  python code/11_build_docs.py [--final]
Without --final, both documents carry a DRAFT banner.
"""

import argparse
import json
import os

from fd_common import PAPER, ROOT

BANNER = ("> **DRAFT v0.1, not verified.** Revision-event causes are rule-engine proposals until the label owner "
          "verifies each one against agency methodology. Do not cite.\n\n")


def fmt(n):
    return f"{n:,}"


def cause_table(s):
    rows = ["| Cause | Events | Median depth (months) | Median mean abs. revision (%) | Median KS (growth) |",
            "|---|---:|---:|---:|---:|"]
    for r in sorted(s["events_by_proposed_cause"], key=lambda r: -r["n"]):
        rows.append(f"| `{r['cause']}` | {fmt(r['n'])} | {r['median_depth_months']:.0f} | "
                    f"{r['median_mean_abs_pct_revision']:.3f} | {r['median_ks']:.3f} |")
    return "\n".join(rows)


def t2_table(s):
    o = s["benchmark"]["T2_realtime_revision_correction"]["overall"]
    names = {"B0": "B0 no revision", "B1": "B1 mean-revision correction", "B2": "B2 per-series OLS"}
    rows = ["| Baseline | MAE (pp) | RMSE (pp) |", "|---|---:|---:|"]
    rows += [f"| {names[k]} | {v['MAE']:.4f} | {v['RMSE']:.4f} |" for k, v in o.items()]
    return "\n".join(rows)


def readme(s, final):
    t2 = s["benchmark"]["T2_realtime_revision_correction"]
    t1 = s["benchmark"]["T1_cause_attribution"]
    status = "v0.1.0, released [date]" if final else "DRAFT v0.1 (unverified)"
    return f"""# FedDrift

**Status:** {status} | **Maintainer:** Tosin Clement, ORCID [0009-0001-2055-5113](https://orcid.org/0009-0001-2055-5113) | **License:** code MIT, data CC BY 4.0 | **DOI:** [DOI]

{'' if final else BANNER}FedDrift is an open benchmark of **vintage-labeled distribution shift** in U.S. federal economic and freight statistics. Each time an agency revises a published series, the series' history shifts. FedDrift records every such shift for {s['n_series']} headline series from the Census Bureau, the Bureau of Labor Statistics and the Bureau of Transportation Statistics. For each shift it records when it happened (the vintage date), how far back it reached, how large it was, and why. The why is one of a fixed set of causes: advance-to-revised transitions, annual benchmarking, sample redesign, seasonal-factor recomputation (including the January recomputation of five years of CPI seasonal factors), and rebasing.

## At a glance (from `paper/stats.json`)

- **{s['n_series']} series**, **{fmt(s['n_vintages'])} vintages** ({s['first_vintage']} to {s['last_vintage']}), observations from {s['obs_window'][0]}.
- **{fmt(s['n_vintage_pairs'])} consecutive vintage pairs**, of which **{fmt(s['n_drift_events'])} are drift events** (at least one published value revised). The remaining {fmt(s['n_not_events'])} only append new months, or are ALFRED archival-window artifacts.
- Agency files fetched directly from the agencies match ALFRED's newest vintage exactly for {len(s['anchor_full_match_series'])} of {s['n_series']} series. Partial matches, with explanations, are in `data/processed/qa_report.txt`.
- Negative control: NSA CPI-U is revised in {s['share_pairs_revised']['CPIAUCNS'] * 100:.2f}% of releases ({s['cpiaucns_revising_vintages']} vintages), against {s['share_pairs_revised']['CPIAUCSL'] * 100:.2f}% for the seasonally adjusted CPI-U.
- Labels: {fmt(s['n_individual_labels_needed'])} events need individual labels; {s['n_unclassified']} are currently unclassified.

{cause_table(s)}

*Causes above are {'final, author-verified labels' if final else 'proposals from the rule engine, pending verification'}.*

## Benchmark tasks

**T1: Revision-cause attribution.** Given the footprint of a vintage pair (what changed, how far back, how much, and when), predict its cause. Temporal split (train before 2015, test 2015 onward), macro-F1. Status: `{t1['status']}`. T1 is scored only against author-verified labels.

**T2: Real-time revision correction.** Given a first-release month-over-month growth rate, predict its value 36 months later. Test observations: {t2['split']['test'][0]} to {t2['split']['test'][1]} ({fmt(t2['n_test'])} observations, {t2['n_series_test']} series).

{t2_table(s)}

## What is here

```
code/       numbered pipeline, run in order (run_all.sh)
config/     panel definition, revision rules, agency-documented events
data/raw/agency/     agency files as fetched (public domain), with PROVENANCE.txt
data/manifests/      ALFRED vintage manifests: dates, counts, content hashes (no values)
data/processed/      drift_events.csv (main table), anchor_vintage.csv, QA report
labels/     the author's label sheets and labeling instructions
docs/       CODEBOOK, LICENSING_PROTOCOL, LIMITATIONS, VERIFY_CHECKLIST, NEXT_STEPS
paper/      stats.json, benchmark results, figures, data-descriptor draft
```

## Run it

```
pip install -r requirements.txt
export FRED_API_KEY=your_key   # free: https://fredaccount.stlouisfed.org/apikeys
bash run_all.sh
```

Agency files need no key. The ALFRED layer is rebuilt from the FRED API. `code/06_qa.py` then checks every rebuilt vintage against the published hashes in `data/manifests/`.

## Sources

| Source | What | License / terms | Snapshot |
|---|---|---|---|
| ALFRED, Federal Reserve Bank of St. Louis (FRED API) | Real-time vintage histories | FRED API Terms of Use; series tagged {', '.join(s['copyright_tags'])}. **Not redistributed:** rebuilt from manifests | {s['snapshot_date']} |
| U.S. Census Bureau, Economic Indicators (MARTS, MRTS, M3, MTIS) | Agency anchor vintage | Public domain (U.S. government work) | {s['snapshot_date']} |
| U.S. Bureau of Labor Statistics, LABSTAT (CPI `cu`, PPI `wp`) | Agency anchor vintage | Public domain | {s['snapshot_date']} |
| U.S. DOT Bureau of Transportation Statistics, Monthly Transportation Statistics | TSI anchor values (BTS-produced fields only) | Public domain U.S. Government | {s['snapshot_date']} |

See `docs/LICENSING_PROTOCOL.md` for what is and is not redistributed, and why.

## Limitations

Read `docs/LIMITATIONS.md` before using or citing anything here.

## Contributions and AI assistance

Tosin Clement designed FedDrift, chose the panel and the cause taxonomy, and owns every revision-event label. Each label is verified against the issuing agency's published methodology. Claude (Anthropic) assisted with retrieval code, harmonization, QA scaffolding and documentation drafts.

## Citation

See `CITATION.cff`. Clement, T. (2026). *FedDrift: an open benchmark of vintage-labeled distribution shift in U.S. federal economic and freight statistics* (v0.1.0). Zenodo. [DOI]
"""


def descriptor(s, final):
    t2 = s["benchmark"]["T2_realtime_revision_correction"]
    sp = s["share_pairs_revised"]
    return f"""---
title: "FedDrift: an open benchmark of vintage-labeled distribution shift in U.S. federal economic and freight statistics"
author: "Tosin Clement (Independent Researcher; ORCID 0009-0001-2055-5113; clementtosin92@gmail.com)"
date: "[date]"
---

{'' if final else BANNER}## Abstract

[VERIFY: author to rewrite in her own voice.] Official statistics change after publication. Advance estimates are revised, annual surveys are benchmarked, seasonal factors are re-estimated, and indexes are rebased. Each change shifts the distribution that downstream models were trained on. FedDrift turns these shifts into a labeled benchmark. It covers {s['n_series']} monthly series from the Census Bureau (MARTS, MRTS, M3, MTIS), the Bureau of Labor Statistics (CPI, PPI) and the Bureau of Transportation Statistics (TSI). From {fmt(s['n_vintages'])} real-time vintages it derives {fmt(s['n_vintage_pairs'])} consecutive vintage pairs, {fmt(s['n_drift_events'])} of which revise previously published values. Each event carries its government release date, a footprint (depth, breadth, magnitude, and a Kolmogorov-Smirnov shift statistic on growth rates) and a cause label verified against agency methodology. Values are redistributed only for public-domain agency files. The real-time layer is shipped as reconstruction code and hash-verified vintage manifests. Two tasks are defined: revision-cause attribution (T1) and real-time revision correction (T2). On T2, simple bias corrections do not improve on assuming no revision (MAE {t2['overall']['B0']['MAE']:.3f} pp vs {t2['overall']['B1']['MAE']:.3f} pp).

## 1. Background and motivation
[VERIFY: author section.] Real-time data literature (ALFRED; the Philadelphia Fed Real-Time Data Set for Macroeconomists); distribution shift in machine learning; why government-dated, cause-labeled shift events are a useful test bed.

## 2. Sources and licensing
Agency anchor files (public domain) and ALFRED via the FRED API (not redistributed). See `docs/LICENSING_PROTOCOL.md`. Snapshot date {s['snapshot_date']}.

## 3. Construction
Vintage reconstruction from real-time periods; consecutive-pair footprints; rule-engine proposals; author verification workflow (`labels/README.md`).

## 4. Technical validation
- Reconstruction: {s['vintages_hash_mismatch']} hash mismatches across {fmt(s['n_vintages'])} vintages.
- Anchor agreement: exact for {len(s['anchor_full_match_series'])}/{s['n_series']} series; partial: {', '.join(f'{k} ({v * 100:.1f}%)' for k, v in s['anchor_partial_match'].items())}, explained in the QA report.
- Negative control: NSA CPI-U revised in {sp['CPIAUCNS'] * 100:.2f}% of releases vs {sp['CPIAUCSL'] * 100:.2f}% (SA CPI-U).
- Named spot checks verified by hand (QA report section 6).

## 5. Data records
`drift_events.csv` and the other files (see `docs/CODEBOOK.md`).

{cause_table(s)}

## 6. Benchmark tasks and baselines
T1 status: `{s['benchmark']['T1_cause_attribution']['status']}`.

T2 ({fmt(t2['n_test'])} test observations):

{t2_table(s)}

## 7. Limitations
See `docs/LIMITATIONS.md`.

## 8. Availability
Code and data: GitHub and Zenodo [DOI]. Code MIT; data CC BY 4.0.

## Author contributions and AI disclosure
Tosin Clement: conceptualization, methodology, validation, data curation (all revision-event labels), writing. Claude (Anthropic) assisted with retrieval and harmonization code and with drafting documentation. The author verified all outputs.

## Figures
![Fig. 1](figures/fig1_event_timeline.png)
![Fig. 2](figures/fig2_cpi_seasonal_depth.png)
![Fig. 3](figures/fig3_revision_frequency.png)
![Fig. 4](figures/fig4_t2_revision_size.png)
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    s = json.load(open(os.path.join(PAPER, "stats.json")))
    open(os.path.join(ROOT, "README.md"), "w").write(readme(s, a.final))
    open(os.path.join(PAPER, "feddrift_data_descriptor.md"), "w").write(descriptor(s, a.final))
    print("wrote README.md and paper/feddrift_data_descriptor.md")


if __name__ == "__main__":
    main()
