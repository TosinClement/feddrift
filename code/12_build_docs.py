#!/usr/bin/env python3
"""12 - Generate README.md, CITATION.cff, the arXiv data descriptor and the Zenodo deposit text from paper/stats.json.

Stats-file rule: no number is typed into these documents by hand; every count comes from paper/stats.json,
paper/benchmark_results.json or data/processed/label_status.json. Re-run after any pipeline change.

Without --final the documents carry a status banner stating that labels are pending (a release-gate blocker).
External identifiers that cannot exist before deposit are written as registered placeholders ({{ZENODO_DOI}},
{{RELEASE_DATE}}, {{GITHUB_REPO_URL}}) unless config/release_identifiers.json supplies them.

Usage:  python code/12_build_docs.py [--final]
"""

import argparse
import json
import os

import pandas as pd

from fd_common import CONFIG, PAPER, PROCESSED, ROOT

FRED_NOTICE = "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."


def ident(name):
    p = os.path.join(CONFIG, "release_identifiers.json")
    ids = json.load(open(p)) if os.path.exists(p) else {}
    return ids.get(name, "{{" + name + "}}")


def fmt(n):
    return f"{n:,}"


def pct(x):
    return f"{x * 100:.2f}%"


def status_banner(s):
    if s["final_mode"]:
        return ""
    return (f"> **Status: DRAFT, not released.** {fmt(s['n_unverified'])} of {fmt(s['n_drift_events'])} drift events "
            "do not yet carry a label verified by the label owner; causes shown are recommendations. "
            "Do not cite until the v0.1.0 release.\n\n")


def cause_table(rows, title_col):
    if not rows:
        return "_No verified labels yet._"
    out = [f"| {title_col} | Events | Median depth (months) | Median mean abs. revision (%) | Median KS (growth) |",
           "|---|---:|---:|---:|---:|"]
    for r in sorted(rows, key=lambda r: -r["n"]):
        name = r.get("final_cause") or r.get("recommended_cause")
        ks = "" if pd.isna(r["median_ks"]) else f"{r['median_ks']:.3f}"
        out.append(f"| `{name}` | {fmt(r['n'])} | {r['median_depth_months']:.0f} | "
                   f"{r['median_mean_abs_pct_revision']:.3f} | {ks} |")
    return "\n".join(out)


def status_table(s):
    order = ["rule_verified", "release_verified", "unknown_verified", "override_verified", "rule_pending_review",
             "release_pending_review", "rule_rejected"]
    out = ["| Label status | Events |", "|---|---:|"]
    for k in order:
        if k in s["label_status"]:
            out.append(f"| `{k}` | {fmt(s['label_status'][k])} |")
    out.append(f"| **drift events total** | **{fmt(s['n_drift_events'])}** |")
    out.append(f"| `excluded_not_drift` (no value revised) | {fmt(s['n_excluded'])} |")
    return "\n".join(out)


def t2_table(b):
    names = {"B0": "B0 no revision", "B1": "B1 + train mean revision", "B2": "B2 per-series OLS",
             "B3": "B3 validation-selected"}
    out = ["| Baseline | MAE (pp) | RMSE (pp) | MAE − B0 (95% bootstrap interval) |", "|---|---:|---:|---|"]
    for r in b["overall"]:
        ci = "—" if r["baseline"] == "B0" else (f"{r['MAE_minus_B0']:+.4f} ({r['MAE_minus_B0_ci95_low']:+.4f}, "
                                               f"{r['MAE_minus_B0_ci95_high']:+.4f})")
        out.append(f"| {names[r['baseline']]} | {r['MAE_pp']:.4f} | {r['RMSE_pp']:.4f} | {ci} |")
    return "\n".join(out)


def t2_reading(b, short=False):
    """Interpretation generated from the numbers: does any simple correction beat B0 beyond bootstrap noise?"""
    rows = {r["baseline"]: r for r in b["overall"]}
    b0 = rows["B0"]["MAE_pp"]
    better = [k for k, r in rows.items() if k != "B0" and r["MAE_minus_B0_ci95_high"] < 0]
    worse = [k for k, r in rows.items() if k != "B0" and r["MAE_minus_B0_ci95_low"] > 0]
    if not better:
        txt = (f"no simple correction improves on the no-revision baseline B0 (MAE {b0:.3f} pp): every 95% bootstrap "
               "interval for the MAE difference to B0 includes zero" + (f", and {', '.join(worse)} is worse" if worse else "")
               + ".")
        if not short:
            txt = txt[0].upper() + txt[1:] + (" This is consistent with revisions carrying new information that was not "
                                              "available at first release, but the test set does not establish why.")
        return txt
    return (f"{', '.join(better)} improve(s) on B0 (MAE {b0:.3f} pp) with a 95% bootstrap interval below zero.")


def t1_text(t1):
    if t1["status"] != "scored_on_author_labels":
        return (f"T1 is scored only on labels verified by the label owner. Status: `{t1['status']}` "
                f"({fmt(t1.get('n_verified', 0))} of {fmt(t1.get('n_drift_events', 0))} drift events verified).")
    rows = ["| Baseline | Macro-F1 | Accuracy |", "|---|---:|---:|"]
    rows += [f"| {r['baseline']} | {r['macro_F1']:.4f} | {r['accuracy']:.4f} |" for r in t1["results"]]
    return (f"Test split: {fmt(t1['n']['test'])} events ({fmt(t1['n']['unknown_not_scored'])} events labeled `unknown` "
            "are not scored).\n\n" + "\n".join(rows))


def readme(s):
    b2, b1 = s["benchmark"]["T2_realtime_revision_correction"], s["benchmark"]["T1_cause_attribution"]
    T2_TEST_RANGE = b2["splits"]["test"].replace(" <= first vintage <= ", " to ")
    rel = "released " + ident("RELEASE_DATE") if s["final_mode"] else "draft, not released"
    unknown_line = (f"{fmt(s['n_final_unknown'])} drift events carry the honest final label `unknown`: agency sources "
                    "did not establish their cause." if s["n_final_unknown"] else "")
    return f"""# FedDrift

**Vintage-labeled distribution shift in U.S. federal economic and freight statistics**

**Version:** 0.1.0 ({rel}) · **Maintainer:** Tosin Clement, ORCID [0009-0001-2055-5113](https://orcid.org/0009-0001-2055-5113) · **License:** code MIT, data CC BY 4.0 · **DOI:** {ident("ZENODO_DOI")}

{status_banner(s)}FedDrift records every revision of {s['n_series']} monthly U.S. federal statistics. The series come from the Census Bureau (retail sales, manufacturers' orders, business inventories), the Bureau of Labor Statistics (CPI, PPI) and the Bureau of Transportation Statistics (Transportation Services Index). For each revision FedDrift gives:

- the date the revised numbers entered the public real-time record;
- what changed, how far back and by how much;
- a distribution-shift statistic;
- a cause label verified by the label owner and citing the agency document it rests on, or `unknown` where no agency source establishes the cause.

The causes are advance-to-revised transitions, annual benchmarks, seasonal-factor recomputation, sample redesign, rebasing or definition changes, methodology changes and corrections.

## At a glance (generated from `paper/stats.json`)

- {s['n_series']} series; {fmt(s['n_vintages'])} real-time vintages from {s['first_vintage']} to {s['last_vintage']}; observations {s['first_obs'][:7]} to {s['last_obs'][:7]}.
- {fmt(s['n_vintage_pairs'])} consecutive vintage pairs. {fmt(s['n_drift_events'])} are **drift events** (at least one published value revised). The other {fmt(s['n_excluded'])} only add new months.
- Drift events by review level: {fmt(s['n_rule_level_events'])} routine events under {s['n_rules_for_review']} rules; {fmt(s['n_release_level_events'])} non-routine events in {fmt(s['n_release_clusters'])} agency releases.
- Evidence: {fmt(s['n_sources'])} agency documents registered with URL, publication date and SHA-256.
- Agency files fetched directly from the agencies match ALFRED's newest vintage exactly for {len(s['anchor_full_match_series'])} of {s['n_series']} series. The exception is explained in `data/processed/qa_report.md`.
- Negative control: NSA CPI-U is revised in {pct(s['share_pairs_revised']['CPIAUCNS'])} of releases, against {pct(s['share_pairs_revised']['CPIAUCSL'])} for SA CPI-U.

### Label status

{status_table(s)}

{unknown_line}

### Drift events by verified cause

{cause_table(s['events_by_final_cause'], 'Final cause')}

## Benchmark tasks

**T1 — revision-cause attribution.** Predict the cause of a drift event from its footprint. Splits are by vintage date (train before 2010, validation 2010–2014, test 2015 onward); the metric is macro-F1.
{t1_text(b1)}

**T2 — real-time revision correction.** Predict the month-over-month growth rate as it stands 36 months after first release, from the first-release value. Splits are leakage-free in calendar time; the test set covers first releases from {T2_TEST_RANGE} ({fmt(b2['n']['test'])} observations, {b2['n_series_test']} series).

{t2_table(b2)}

{t2_reading(b2)} See `paper/tables/t2_by_series.csv` for per-series results, and `docs/METHODOLOGY.md` §5 for the full specification.

## Reproduce

```bash
git clone {ident("GITHUB_REPO_URL")} feddrift && cd feddrift
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export FRED_API_KEY=your_key        # free: https://fredaccount.stlouisfed.org/apikeys
bash run_all.sh                     # pinned snapshot: rebuilds the ALFRED layer, verifies hashes, QA, benchmark, docs, tests
```

The ALFRED layer is rebuilt with `realtime_end` pinned to {s['alfred_realtime_end']}, so later vintages never enter. QA check Q03 compares every rebuilt vintage with its published SHA-256. `bash run_all.sh --harvest` also re-downloads the agency evidence documents.

## Repository

```
code/       01-13 pipeline in run order; import_review.py; publish_gate.py
config/     panel, snapshot, causes, rules, schema, placeholders
data/raw/agency/2026-10-03/   agency files (public domain) + data/raw/PROVENANCE.txt
data/manifests/               ALFRED vintage manifests: dates, counts, SHA-256 (no values)
data/processed/               drift_events.csv, event_inventory.csv, anchor_vintage.csv, release_clusters.csv, QA
evidence/   source registry, rule evidence, release evidence with automated checks
labels/     review package (labels/review/) and the label owner's decisions (labels/decisions/)
paper/      stats.json, benchmark results, tables, figures, data descriptor
docs/       METHODOLOGY, CODEBOOK, PROVENANCE, REPRODUCIBILITY, LICENSING_PROTOCOL, ETHICS_AND_LIMITATIONS, CONTRIBUTIONS, RELEASE_CHECKLIST
zenodo/     deposit metadata and description
```

## Data use and licensing

- Agency values: U.S. Government works, public domain.
- FedDrift's tables, labels and documentation: CC BY 4.0.
- Code: MIT.
- ALFRED observation values are **not** redistributed. They are rebuilt with your own FRED API key, under the FRED API Terms of Use.

See `docs/LICENSING_PROTOCOL.md`.

{FRED_NOTICE}

## Limitations

Read `docs/ETHICS_AND_LIMITATIONS.md` before using FedDrift. In short:
- vintage dates are ALFRED's, not always the agency's;
- some early vintages censor revision depth;
- evidence strength varies and is graded per label.

## Contributions

Tosin Clement designed FedDrift and owns every substantive labeling decision. Claude (Anthropic) assisted with code, data harmonization, evidence retrieval and documentation drafts. See `docs/CONTRIBUTIONS.md`.

## Citation

Clement, T. (2026). *FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics* (Version 0.1.0) [Data set]. Zenodo. https://doi.org/{ident("ZENODO_DOI")}
"""


def citation_cff(s):
    return f"""cff-version: 1.2.0
message: "If you use FedDrift, please cite it as below."
type: dataset
title: "FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics"
version: "0.1.0"
date-released: "{ident('RELEASE_DATE')}"
doi: "{ident('ZENODO_DOI')}"
repository-code: "{ident('GITHUB_REPO_URL')}"
license: CC-BY-4.0
authors:
  - family-names: "Clement"
    given-names: "Tosin"
    orcid: "https://orcid.org/0009-0001-2055-5113"
    email: "clementtosin92@gmail.com"
    affiliation: "Independent Researcher"
abstract: "Revision events for {s['n_series']} U.S. federal economic and freight series (Census MARTS, MRTS, M3, MTIS; BLS CPI, PPI; BTS TSI) built from {s['n_vintages']} ALFRED real-time vintages, with revision footprints, cause labels verified by the author against cited agency documents, an agency-sourced anchor vintage, hash-verified reconstruction manifests, and two benchmark tasks."
keywords:
  - real-time data
  - data revisions
  - distribution shift
  - official statistics
  - ALFRED
  - benchmark
"""


def label_sentence(s):
    if s["n_unverified"]:
        return (f"In this draft, cause labels are recommendations awaiting the author's verification "
                f"({fmt(s['n_verified'])} of {fmt(s['n_drift_events'])} verified).")
    return (f"The author verified every label against agency documents registered with URL, publication date and "
            f"SHA-256; {fmt(s['n_final_unknown'])} events carry the label `unknown` because no source established "
            "their cause.")


def descriptor(s):
    b2, b1 = s["benchmark"]["T2_realtime_revision_correction"], s["benchmark"]["T1_cause_attribution"]
    sp = s["share_pairs_revised"]
    q = s["qa_status"]
    qa_line = ", ".join(f"{k} {v}" for k, v in sorted(q.items()))
    return f"""---
title: "FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics"
author: "Tosin Clement (Independent Researcher; ORCID 0009-0001-2055-5113; clementtosin92@gmail.com)"
date: "{ident('RELEASE_DATE')}"
---

{status_banner(s)}## Abstract

Published official statistics change. Advance estimates are revised, monthly surveys are benchmarked to annual surveys and censuses, seasonal factors are re-estimated, and indexes are rebased. Every such change shifts the data that downstream models were trained and evaluated on.

FedDrift records these shifts for {s['n_series']} monthly U.S. federal series from the Census Bureau, the Bureau of Labor Statistics and the Bureau of Transportation Statistics. From {fmt(s['n_vintages'])} ALFRED real-time vintages it derives {fmt(s['n_vintage_pairs'])} consecutive vintage pairs, of which {fmt(s['n_drift_events'])} revise previously published values. Each such drift event records its vintage date, how far back and how much the series was revised, a Kolmogorov–Smirnov statistic on growth rates, and a cause label. {label_sentence(s)}

FedDrift redistributes values only from public-domain agency files. The real-time layer ships as reconstruction code and hash-verified manifests. Two tasks are defined: revision-cause attribution (T1) and real-time revision correction (T2). On T2, {t2_reading(b2, short=True)}

## 1. Background

Real-time data sets keep each published version ("vintage") of a series so that analyses can use the data as known at the time. Examples are the Federal Reserve Bank of Philadelphia's Real-Time Data Set for Macroeconomists (Croushore and Stark, 2001) and ALFRED (Federal Reserve Bank of St. Louis). FedDrift adds what those archives do not record: the cause of each revision, linked to an agency document, in a form suited to evaluating methods that must cope with shifting data.

## 2. Sources and data use

Agency anchor files come from Census, BLS and BTS (public domain). The real-time history comes from ALFRED via the FRED API; it is not redistributed. Licensing is in `docs/LICENSING_PROTOCOL.md`. The snapshot is {s['snapshot_id']}, with ALFRED pinned to `realtime_end` {s['alfred_realtime_end']}.

## 3. Construction

See `docs/METHODOLOGY.md`. In brief:
- vintage reconstruction from real-time periods;
- footprints of each consecutive pair, with a censored-depth flag where the revision reaches the start of the archived vintage ({fmt(s['n_depth_censored_events'])} events);
- rule proposals;
- agency releases grouped into {fmt(s['n_release_clusters'])} review clusters;
- evidence harvested from {fmt(s['n_sources'])} agency documents, with automated consistency checks;
- labels decided by the author at rule, release and event level.

## 4. Technical validation

QA checks (`data/processed/qa_report.md`): {qa_line}.
- Reconstruction: {s['reconstruction']}.
- Anchor agreement is exact for {len(s['anchor_full_match_series'])}/{s['n_series']} series. The exception is the 2026-09-28 Census reissue of the MRTS file, which ALFRED had not vintaged by the snapshot date.
- Negative control: NSA CPI-U is revised in {pct(sp['CPIAUCNS'])} of releases, against {pct(sp['CPIAUCSL'])} for SA CPI-U.

## 5. Data records

The main table is `data/processed/drift_events.csv`, one row per vintage pair; see `docs/CODEBOOK.md`.

{status_table(s)}

{cause_table(s['events_by_final_cause'], 'Final cause')}

## 6. Benchmark tasks

**T1.** {t1_text(b1)}

**T2** ({fmt(b2['n']['test'])} test observations; train {fmt(b2['n']['train'])}, validation {fmt(b2['n']['validation'])}):

{t2_table(b2)}

Bootstrap intervals resample test observations i.i.d. and ignore serial correlation; treat them as indicative.

## 7. Limitations

See `docs/ETHICS_AND_LIMITATIONS.md`.

## 8. Availability

Code and data: {ident('GITHUB_REPO_URL')} and https://doi.org/{ident('ZENODO_DOI')}. Code is MIT; FedDrift data is CC BY 4.0; agency values are public domain. {FRED_NOTICE}

## Author contributions and AI disclosure

Tosin Clement: conceptualization, methodology, validation, data curation (all verified labels), writing. Claude (Anthropic) assisted with retrieval, harmonization, QA and benchmark code, evidence retrieval and documentation drafts; its proposals are kept separate from the author's verified labels. The author is accountable for the content.

## References

- Croushore, D., and Stark, T. (2001). A real-time data set for macroeconomists. *Journal of Econometrics*, 105(1), 111–130.
- Federal Reserve Bank of St. Louis. ALFRED: Archival Federal Reserve Economic Data. https://alfred.stlouisfed.org/
- Agency documents cited as evidence: `evidence/source_registry.csv` ({fmt(s['n_sources'])} documents).

## Figures

![Figure 1. Drift events by series and vintage date, coloured by cause.](figures/fig1_event_timeline.png)

![Figure 2. Depth of the February CPI-U (SA) revision; hollow markers are lower bounds.](figures/fig2_cpi_seasonal_depth.png)

![Figure 3. Share of releases that revise at least one value, by series.](figures/fig3_revision_frequency.png)

![Figure 4. T2: mean absolute revision of first-release growth after 36 months, by series.](figures/fig4_t2_revision_size.png)
"""


def zenodo(s):
    b2 = s["benchmark"]["T2_realtime_revision_correction"]
    desc = (f"<p>FedDrift is an open benchmark of vintage-labeled distribution shift in U.S. federal economic and freight "
            f"statistics. It covers {s['n_series']} monthly series: Census MARTS, MRTS, M3 and MTIS; BLS CPI and PPI; "
            f"and the BTS Transportation Services Index. From {fmt(s['n_vintages'])} ALFRED real-time vintages it derives "
            f"{fmt(s['n_vintage_pairs'])} consecutive vintage pairs, of which {fmt(s['n_drift_events'])} revise published "
            "values. Each such drift event records its vintage date, a revision footprint, a distribution-shift "
            "statistic and a cause label. The author verified each label against agency documents, cited with URL, "
            "publication date and SHA-256.</p>"
            f"<p>Label status: {fmt(s['n_verified'])} verified; {fmt(s['n_final_unknown'])} with final label "
            "<em>unknown</em>.</p>"
            "<p>Agency values are redistributed as public-domain U.S. Government works. ALFRED values are not "
            "redistributed: reconstruction code and SHA-256 vintage manifests let users rebuild them with a FRED API key. "
            f"{FRED_NOTICE}</p>"
            f"<p>Benchmark tasks: T1 revision-cause attribution; T2 real-time revision correction "
            f"(test MAE of the no-revision baseline: {b2['overall'][0]['MAE_pp']:.3f} percentage points).</p>"
            "<p>Contributions: Tosin Clement designed FedDrift and made and verified all substantive labeling "
            "decisions. Claude (Anthropic) assisted with code, harmonization, evidence retrieval and documentation "
            "drafts.</p>")
    meta = {
        "title": "FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics",
        "upload_type": "dataset", "version": "0.1.0", "publication_date": ident("RELEASE_DATE"),
        "description": desc, "access_right": "open", "license": "cc-by-4.0",
        "creators": [{"name": "Clement, Tosin", "affiliation": "Independent Researcher", "orcid": "0009-0001-2055-5113"}],
        "keywords": ["real-time data", "data revisions", "distribution shift", "official statistics", "ALFRED",
                     "Census", "BLS", "BTS", "benchmark"],
        "related_identifiers": [{"identifier": ident("GITHUB_REPO_URL"), "relation": "isSupplementTo", "scheme": "url"}],
        "notes": "Code MIT; data CC BY 4.0; agency values public domain. " + FRED_NOTICE,
    }
    return meta, desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    s = json.load(open(os.path.join(PAPER, "stats.json")))
    if a.final and not s["final_mode"]:
        raise SystemExit("--final refused: paper/stats.json was not generated in final mode (run 11 --final first)")
    if not a.final:
        s["final_mode"] = False
    open(os.path.join(ROOT, "README.md"), "w").write(readme(s))
    open(os.path.join(ROOT, "CITATION.cff"), "w").write(citation_cff(s))
    open(os.path.join(PAPER, "feddrift_data_descriptor.md"), "w").write(descriptor(s))
    os.makedirs(os.path.join(ROOT, "zenodo"), exist_ok=True)
    meta, desc = zenodo(s)
    json.dump({"metadata": meta}, open(os.path.join(ROOT, "zenodo", "zenodo_metadata.json"), "w"), indent=1)
    open(os.path.join(ROOT, "zenodo", "description.md"), "w").write(desc.replace("</p><p>", "\n\n").replace("<p>", "")
                                                                   .replace("</p>", "\n").replace("<em>", "*").replace("</em>", "*"))
    print("wrote README.md, CITATION.cff, paper/feddrift_data_descriptor.md, zenodo/zenodo_metadata.json, zenodo/description.md")


if __name__ == "__main__":
    main()
