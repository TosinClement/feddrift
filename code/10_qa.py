#!/usr/bin/env python3
"""09 - Quality assurance. Every check has an id, an expected result, the actual result and a status.

Writes data/processed/qa_report.md (human table + detail sections) and data/processed/qa.json.
Status values: PASS, FAIL, NOTE (passes with a documented, explained exception), BLOCKING (release-gate
condition not yet met, e.g. labels awaiting the label owner), SKIP (input unavailable, with the reason).

The process exits non-zero if any check is FAIL. BLOCKING does not fail QA; it fails the release gate
(code/publish_gate.py and code/13_package.py --release).
"""

import hashlib
import json
import os
import re
import sys

import pandas as pd

from fd_common import (ALFRED_CACHE, CONFIG, MANIFESTS, PAPER, PROCESSED, PROVENANCE_LOG, ROOT, load_panel,
                       load_snapshot, sha256_file)

ANCHOR_NOTES = {
    "MRTSSM44X72USS": "Census reissued the MRTS file on 2026-09-28 with its annual revision (adjusted estimates revised "
                      "from January 2015); ALFRED's newest MRTS vintage in the snapshot is 2026-09-16. Every mismatch "
                      "lies in 2015-01..2026-07. Timing difference between the two archives, not a pipeline error "
                      "(source: Census MARTS release CB26-153 notice of revision; Census 2026 annual revision introduction).",
}
VERIFIED = {"rule_verified", "release_verified", "unknown_verified", "override_verified"}
STATUSES = VERIFIED | {"excluded_not_drift", "rule_pending_review", "rule_rejected", "release_pending_review"}
SECRET_PATTERNS = [(r"github_pat_[A-Za-z0-9_]{30,}", "GitHub fine-grained PAT"), (r"ghp_[A-Za-z0-9]{30,}", "GitHub PAT"),
                   (r"api_key=[0-9a-f]{32}", "FRED API key in URL"), (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
                   (r"(?i)(?:secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "hard-coded credential")]
SCAN_SKIP_DIRS = {".git", "evidence_cache", "alfred_cache", "dist", "__pycache__", ".pytest_cache", "_archive",
                  "alfred_cache_run1"}

RESULTS, DETAIL = [], []


def check(cid, desc, expected, actual, ok, status_if_not="FAIL"):
    RESULTS.append({"id": cid, "check": desc, "expected": str(expected), "actual": str(actual),
                    "status": "PASS" if ok else status_if_not})


def vintage_hash(dates, values):
    return hashlib.sha256("".join(f"{d},{v}\n" for d, v in sorted(zip(dates, values))).encode()).hexdigest()


def secret_scan():
    hits = []
    pats = [(re.compile(p), n) for p, n in SECRET_PATTERNS]
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SCAN_SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), ROOT)
            if f in (".env",) or f.endswith((".pem", ".key")):
                hits.append((rel, "credential file"))
                continue
            if rel in ("code/10_qa.py", "code/13_package.py", "code/publish_gate.py", "tests/test_pipeline.py"):
                continue  # these files contain the detection patterns themselves
            try:
                txt = open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for p, n in pats:
                if p.search(txt):
                    hits.append((rel, n))
    return hits


def main():
    snap = load_snapshot()
    panel = load_panel()
    ev = pd.read_csv(os.path.join(PROCESSED, "drift_events.csv"), keep_default_na=False, low_memory=False)
    ev["is_drift_event"] = ev.is_drift_event.astype(str) == "True"
    num = lambda c: pd.to_numeric(ev[c].replace("", None), errors="coerce")

    # Q01-Q02 provenance
    logged = {}
    for line in open(PROVENANCE_LOG, encoding="utf-8"):
        parts = [p.strip() for p in line.split("|")]
        logged[parts[1]] = parts[3].replace("sha256:", "")
    snapdir = os.path.join(ROOT, snap["agency_snapshot_dir"])
    files = sorted(os.path.relpath(os.path.join(d, f), ROOT) for d, _, fs in os.walk(snapdir) for f in fs)
    present = [f for f in files if os.path.exists(os.path.join(ROOT, f))]
    mism = [f for f in present if logged.get(f) != sha256_file(os.path.join(ROOT, f))]
    unlogged = [f for f in files if f not in logged]
    missing = [f for f in logged if f.startswith(snap["agency_snapshot_dir"]) and not os.path.exists(os.path.join(ROOT, f))]
    check("Q01", "Agency snapshot files match PROVENANCE.txt SHA-256", "0 mismatches, 0 unlogged",
          f"{len(mism)} mismatches, {len(unlogged)} unlogged, {len(files)} files", not mism and not unlogged)
    note_missing = [m for m in missing if m.endswith("crem-w557.csv")]
    check("Q02", "Every logged agency file is present (withheld BTS file excepted)", "0 missing",
          f"{len(missing)} missing ({', '.join(missing) or 'none'})", set(missing) <= set(note_missing),
          ) if True else None
    if note_missing and RESULTS[-1]["status"] == "PASS":
        RESULTS[-1]["status"] = "NOTE"
        RESULTS[-1]["actual"] += " - full BTS MTS file withheld by licensing protocol; re-fetchable by URL + hash"

    # Q03-Q04 reconstruction
    if os.path.isdir(ALFRED_CACHE) and all(os.path.exists(os.path.join(ALFRED_CACHE, f"{p['series_id']}.observations.json"))
                                           for p in panel):
        tot = bad = late = 0
        for p in panel:
            sid = p["series_id"]
            man = pd.read_csv(os.path.join(MANIFESTS, f"{sid}.vintages.csv"))
            j = json.load(open(os.path.join(ALFRED_CACHE, f"{sid}.observations.json")))
            df = pd.DataFrame(j["observations"])
            df = df[df.value != "."]
            for r in man.itertuples():
                live = df[(df.realtime_start <= r.vintage_date) & (df.realtime_end >= r.vintage_date)]
                bad += vintage_hash(live.date.tolist(), live.value.tolist()) != r.vintage_sha256
            tot += len(man)
            late += int((man.vintage_date > snap["alfred_realtime_end"]).sum())
        check("Q03", "Every ALFRED vintage rebuilt from the FRED API matches its published manifest hash",
              "0 mismatches", f"{bad} mismatches of {tot} vintages", bad == 0)
        check("Q04", "No vintage after the pinned snapshot date", f"0 vintages > {snap['alfred_realtime_end']}",
              f"{late}", late == 0)
    else:
        RESULTS.append({"id": "Q03", "check": "ALFRED reconstruction hashes", "expected": "0 mismatches",
                        "actual": "ALFRED cache absent (needs FRED_API_KEY and code/03_fetch_alfred.py)", "status": "SKIP"})
        RESULTS.append({"id": "Q04", "check": "No vintage after snapshot", "expected": "0", "actual": "cache absent",
                        "status": "SKIP"})

    # Q05 anchor agreement
    anchor = pd.read_csv(os.path.join(PROCESSED, "anchor_vintage.csv"))
    agree, problems = {}, []
    if os.path.isdir(ALFRED_CACHE):
        for p in panel:
            sid = p["series_id"]
            fp = os.path.join(ALFRED_CACHE, f"{sid}.observations.json")
            if not os.path.exists(fp):
                continue
            j = json.load(open(fp))
            df = pd.DataFrame(j["observations"])
            latest = j["vintage_dates"][-1]
            live = df[(df.realtime_start <= latest) & (df.realtime_end >= latest) & (df.value != ".")]
            dec = live.value.map(lambda s: len(s.split(".")[1]) if "." in s else 0)
            tol = pd.Series((0.5 * 10.0 ** (-dec) + 1e-12).values, index=live.date.values)
            alf = pd.Series(live.value.astype(float).values, index=live.date.values)
            a = anchor[(anchor.series_id == sid) & (anchor.obs_date >= "1947-01-01")].drop_duplicates("obs_date")
            a = a.set_index("obs_date").value
            common = alf.index.intersection(a.index)
            ok = (alf.loc[common] - a.loc[common]).abs().values <= tol.loc[common].values
            rate = float(ok.mean()) if len(common) else None
            bad_dates = list(common[~ok])
            agree[sid] = {"alfred_vintage": latest, "common": int(len(common)), "match_rate": round(rate, 6),
                          "mismatch_range": [min(bad_dates), max(bad_dates)] if bad_dates else None}
            if rate != 1.0 and sid not in ANCHOR_NOTES:
                problems.append(sid)
        exceptions = [k for k, v in agree.items() if v["match_rate"] != 1.0]
        check("Q05", "Agency anchor equals newest ALFRED vintage (half a unit in the last published digit)",
              "100% for every series, or a documented timing exception",
              f"{sum(v['match_rate'] == 1.0 for v in agree.values())}/{len(agree)} exact; exceptions: "
              + ", ".join(f"{k} {agree[k]['match_rate'] * 100:.1f}% (mismatches {agree[k]['mismatch_range']})" for k in exceptions),
              not problems)
        if not problems and exceptions:
            RESULTS[-1]["status"] = "NOTE"
    else:
        RESULTS.append({"id": "Q05", "check": "Anchor agreement", "expected": "100%", "actual": "ALFRED cache absent",
                        "status": "SKIP"})

    # Q06 schema
    schema = json.load(open(os.path.join(CONFIG, "schema.json")))
    cols = list(ev.columns)
    exp = schema["drift_events"]
    check("Q06", "drift_events.csv columns equal the locked schema (config/schema.json)", f"{len(exp)} columns in order",
          f"{len(cols)} columns; missing {sorted(set(exp) - set(cols))}; extra {sorted(set(cols) - set(exp))}", cols == exp)

    # Q07 uniqueness
    check("Q07", "event_id unique; (series_id, vintage_next) unique", "no duplicates",
          f"{ev.event_id.duplicated().sum()} duplicate ids, {ev.duplicated(['series_id', 'vintage_next']).sum()} duplicate keys",
          ev.event_id.is_unique and not ev.duplicated(["series_id", "vintage_next"]).any())

    # Q08 date ordering
    de = ev[ev.is_drift_event]
    o1 = (ev.vintage_prev >= ev.vintage_next).sum()
    o2 = (de.earliest_revised_obs > de.latest_revised_obs).sum()
    o3 = (de.earliest_revised_obs >= de.vintage_next).sum()
    check("Q08", "vintage_prev < vintage_next; earliest <= latest revised obs < vintage_next", "0 violations",
          f"{o1} / {o2} / {o3}", o1 == o2 == o3 == 0)

    # Q09 missingness
    req = ["earliest_revised_obs", "latest_revised_obs", "revision_depth_months", "mean_abs_pct_revision"]
    miss = {c: int((de[c] == "").sum()) for c in req}
    nd = ev[~ev.is_drift_event]
    leak = int((nd.earliest_revised_obs != "").sum())
    check("Q09", "Revision fields present for every drift event and empty for every non-event", "0 / 0",
          f"missing {miss}; non-events with revision fields {leak}", sum(miss.values()) == 0 and leak == 0)

    # Q10 label vocabulary
    causes = pd.read_csv(os.path.join(CONFIG, "causes.csv"))
    allowed = set(causes[causes.allowed_as_final != "no"].cause)
    badc = sorted(set(ev.final_cause[ev.final_cause != ""]) - allowed)
    bads = sorted(set(ev.label_status) - STATUSES)
    check("Q10", "final_cause and label_status use the controlled vocabularies", "no unknown values",
          f"bad causes {badc}; bad statuses {bads}", not badc and not bads)

    # Q11 label honesty
    ver = ev[ev.label_status.isin(VERIFIED)]
    no_rev = int(((ver.reviewer == "") | (ver.verified_date == "")).sum())
    unver_with_final = int((de[~de.label_status.isin(VERIFIED)].final_cause != "").sum())
    dec_dir = os.path.join(ROOT, "labels", "decisions")
    reviewers = set()
    if os.path.isdir(dec_dir):
        for f in os.listdir(dec_dir):
            if f.endswith(".csv"):
                reviewers |= set(pd.read_csv(os.path.join(dec_dir, f), dtype=str).fillna("").get("verified_by", []))
    stray = sorted(set(ver.reviewer) - reviewers)
    check("Q11", "A label is verified only if a decision row names the reviewer and date; unverified events carry no final cause",
          "0 / 0 / no reviewer outside labels/decisions", f"{no_rev} verified without reviewer/date; {unver_with_final} unverified "
          f"with a final cause; reviewers not in decision files: {stray}", no_rev == 0 and unver_with_final == 0 and not stray)

    # Q12 count reconciliation
    clusters = pd.read_csv(os.path.join(PROCESSED, "release_clusters.csv"))
    n_rule, n_rel, n_ex = (int((ev.review_level == k).sum()) for k in ("rule", "release", "excluded"))
    ok12 = (n_rule + n_rel == len(de)) and (n_rel == int(clusters.n_events.sum())) and (n_ex == len(ev) - len(de)) \
        and n_ex == int(ev.proposed_rule.isin(["R00_EXTENSION", "R01_ARCHIVE_WINDOW"]).sum())
    check("Q12", "Counts reconcile: pairs = drift events + excluded; drift events = rule-level + release-level; "
          "release-level = sum of cluster sizes", "all equalities hold",
          f"pairs {len(ev)} = {len(de)} + {n_ex}; {len(de)} = {n_rule} + {n_rel}; clusters {len(clusters)} hold "
          f"{int(clusters.n_events.sum())}", ok12)

    # Q13 negative control
    sh = ev.groupby("series_id").apply(lambda g: (pd.to_numeric(g.n_revised) > 0).mean(), include_groups=False)
    check("Q13", "Negative control: NSA CPI-U revised in under 2% of releases", "< 2%",
          f"{sh['CPIAUCNS'] * 100:.2f}% (SA CPI-U {sh['CPIAUCSL'] * 100:.2f}%)", sh["CPIAUCNS"] < 0.02)

    # Q14-Q15 leakage
    bres_path = os.path.join(PAPER, "benchmark_results.json")
    if os.path.exists(bres_path):
        b = json.load(open(bres_path))
        lc = b["T2_realtime_revision_correction"]["leakage_checks"]
        ok14 = lc["train_mature_max"] < lc["validation_first_min"] and lc["validation_mature_max"] < lc["test_first_min"]
        check("Q14", "T2: every target used for fitting/selection is published before the first test input",
              "train mature < val first; val mature < test first", json.dumps(lc), ok14)
    t1s = ev[ev.is_drift_event & (ev.release_cluster_id != "")].copy()
    t1s["split"] = pd.cut(pd.to_datetime(t1s.vintage_next), [pd.Timestamp("1900-01-01"), pd.Timestamp("2010-01-01"),
                          pd.Timestamp("2015-01-01"), pd.Timestamp("2100-01-01")], right=False, labels=["tr", "va", "te"])
    span = int((t1s.groupby("release_cluster_id").split.nunique() > 1).sum())
    check("Q15", "T1: no agency release spans two splits", "0 releases", f"{span}", span == 0)

    # Q16 evidence completeness
    evd = os.path.join(ROOT, "evidence")
    reg = pd.read_csv(os.path.join(evd, "source_registry.csv"), dtype=str).fillna("")
    cev = pd.read_csv(os.path.join(evd, "cluster_evidence.csv"), dtype=str).fillna("")
    rev = pd.read_csv(os.path.join(evd, "rule_evidence.csv"), dtype=str).fillna("")
    cited = {s for x in list(cev.source_ids) + list(rev.source_id) for s in str(x).split(";") if s}
    unreg = sorted(cited - set(reg.source_id))
    nohash = int(((reg.retrieval == "direct_download") & (reg.sha256 == "")).sum())
    nocl = sorted(set(clusters.release_cluster_id) - set(cev.release_cluster_id))
    rules = pd.read_csv(os.path.join(CONFIG, "revision_rules.csv"), dtype=str)
    norule = sorted(set(rules[rules.review_level == "rule"].rule_id) - set(rev[rev.source_id != ""].rule_id))
    check("Q16", "Evidence complete: every release has an evidence row, every routine rule an agency source, every "
          "cited source is registered, every downloaded source has a SHA-256",
          "0 / 0 / 0 / 0", f"releases without evidence {len(nocl)}; rules without source {norule}; unregistered {unreg}; "
          f"downloads without hash {nohash}", not nocl and not norule and not unreg and nohash == 0)

    # Q17 secret scan
    hits = secret_scan()
    check("Q17", "Secret scan of the working tree (tokens, keys, credential files)", "0 findings",
          f"{len(hits)} findings {hits[:5]}", not hits)

    # Q18 package restrictions (dry run of the release packager's content checks)
    sys.path.insert(0, os.path.join(ROOT, "code"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("pkg", os.path.join(ROOT, "code", "13_package.py"))
    pkg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pkg)
    inc, probs = pkg.content_problems()
    check("Q18", "Release-package content rules (no ALFRED value rows, no keys, no cache, no withheld file)",
          "0 violations", f"{len(probs)} violations in {len(inc)} files {probs[:3]}", not probs)

    # Q19 git: restricted files never tracked, in the index or in any commit
    import subprocess
    restricted = re.compile(r"(^|/)alfred_cache[^/]*/|crem-w557\.csv$|(^|/)\.env$|\.key$|evidence_cache/")
    if os.path.isdir(os.path.join(ROOT, ".git")):
        tracked = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True).stdout.split()
        hist = subprocess.run(["git", "-C", ROOT, "log", "--all", "--name-only", "--pretty=format:"],
                              capture_output=True, text=True).stdout.split()
        bad_git = sorted({f for f in tracked + hist if restricted.search(f)})
        check("Q19", "Git index and history contain no restricted file (ALFRED cache, withheld BTS file, credentials, evidence cache)",
              "0 paths", f"{len(bad_git)} {bad_git[:3]}", not bad_git)
    else:
        RESULTS.append({"id": "Q19", "check": "Git restricted-file check", "expected": "0 paths",
                        "actual": "not a git checkout", "status": "SKIP"})

    # Q20 label coverage (release gate)
    nun = int((~de.label_status.isin(VERIFIED)).sum())
    check("Q20", "Every drift event carries a label verified by the label owner (release-gate condition)",
          "0 unverified", f"{nun} of {len(de)} unverified "
          f"({de.label_status.value_counts().to_dict()})", nun == 0, status_if_not="BLOCKING")

    # report
    qa = {"checks": RESULTS, "anchor_agreement": agree,
          "share_pairs_revised": {k: round(float(v), 4) for k, v in sh.items()}}
    json.dump(qa, open(os.path.join(PROCESSED, "qa.json"), "w"), indent=1, default=str)
    lines = ["# FedDrift QA report", "", f"Snapshot {snap['snapshot_id']}. Generated by `code/10_qa.py`.", "",
             "| ID | Check | Expected | Actual | Status |", "|---|---|---|---|---|"]
    for r in RESULTS:
        a = r["actual"].replace("|", "/")
        lines.append(f"| {r['id']} | {r['check']} | {r['expected']} | {a} | **{r['status']}** |")
    lines += ["", "## Notes on exceptions", ""] + [f"- **{k}**: {v}" for k, v in ANCHOR_NOTES.items()]
    lines += ["", "## Anchor agreement by series", "", "| Series | ALFRED vintage | Shared obs | Match rate |",
              "|---|---|---|---|"]
    lines += [f"| {k} | {v['alfred_vintage']} | {v['common']} | {v['match_rate'] * 100:.2f}% |" for k, v in agree.items()]
    open(os.path.join(PROCESSED, "qa_report.md"), "w").write("\n".join(lines) + "\n")
    old = os.path.join(PROCESSED, "qa_report.txt")
    if os.path.exists(old):
        os.remove(old)
    for r in RESULTS:
        print(f"{r['id']} {r['status']:8s} {r['check'][:70]}")
    if any(r["status"] == "FAIL" for r in RESULTS):
        raise SystemExit("QA FAILED")


if __name__ == "__main__":
    main()
