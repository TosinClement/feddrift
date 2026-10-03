#!/usr/bin/env python3
"""07 - FedDrift benchmark tasks, baselines and scoring.

T1  Revision-cause attribution (label-dependent).
    Input : the footprint of one vintage pair (features observable on the release day; no labels).
    Target: final_cause from labels/ (the author's verified labels; see code/08_apply_labels.py).
    Split : temporal - train vintage_next < 2015-01-01, test >= 2015-01-01.
    Metric: macro-F1 over causes present in the test set, plus accuracy.
    Runs ONLY on author-verified labels. Until labels exist it reports status "pending_author_labels";
    it never scores against the rule engine's proposals (that would grade the rules against themselves).

T2  Real-time revision correction (label-independent; computable now).
    For each series and observation month t: g1(t) = month-over-month % growth in the first vintage that
    contains t (kept only if published within 3 months of t, i.e. a genuine
    first release), gM(t) = the same growth in the first vintage at least 36 months after that, r = gM - g1.
    Predict gM from information available at first release.
    Split : train obs t <= 2015-12, test 2016-01 .. 2022-09 (all mature by the snapshot).
    Metric: MAE and RMSE in percentage points of m/m growth.
    Baselines: B0 no-revision (gM_hat = g1); B1 mean-revision correction; B2 per-series OLS gM ~ g1.

Output: paper/benchmark_results.json, data/processed/t2_series_metrics.csv (aggregates only, no values)
"""

import json
import os

import numpy as np
import pandas as pd

from fd_common import ALFRED_CACHE, PAPER, PROCESSED, ROOT, load_panel

MATURITY_MONTHS = 36
TRAIN_END, TEST_START, TEST_END = "2015-12-01", "2016-01-01", "2022-09-01"
T1_SPLIT = "2015-01-01"
FEATURES = ["vintage_month", "n_revised", "share_revised", "revision_depth_months", "revision_span_months",
            "mean_abs_pct_revision", "max_abs_pct_revision", "net_pct_revision", "share_up",
            "mean_abs_growth_revision_pp", "ks_growth_window", "n_new_obs", "n_dropped_obs", "days_between"]


def first_and_mature(sid):
    j = json.load(open(os.path.join(ALFRED_CACHE, f"{sid}.observations.json")))
    df = pd.DataFrame(j["observations"])
    df = df[df.value != "."].copy()
    df["value"] = df.value.astype(float)
    vds = pd.to_datetime(pd.Series(j["vintage_dates"]))
    rows = []
    cache = {}

    def vec(v):
        if v not in cache:
            live = df[(df.realtime_start <= v) & (df.realtime_end >= v)]
            cache[v] = pd.Series(live.value.values, index=live.date.values)
        return cache[v]

    first_seen = df.groupby("date").realtime_start.min()
    for t, v1 in first_seen.items():
        prev = (pd.Timestamp(t) - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        # keep only genuine first releases: the observation must be among the newest in its first vintage.
        # (Observations already present in a series' earliest archived vintage are not first releases.)
        lag = (pd.Timestamp(v1).year - pd.Timestamp(t).year) * 12 + pd.Timestamp(v1).month - pd.Timestamp(t).month
        if lag > 3:
            continue
        a = vec(v1)
        if prev not in a.index or t not in a.index:
            continue
        mat_date = pd.Timestamp(v1) + pd.DateOffset(months=MATURITY_MONTHS)
        later = vds[vds >= mat_date]
        if later.empty:
            continue
        vm = later.iloc[0].strftime("%Y-%m-%d")
        b = vec(vm)
        if prev not in b.index or t not in b.index:
            continue
        g1 = (a[t] / a[prev] - 1) * 100
        gm = (b[t] / b[prev] - 1) * 100
        rows.append({"series_id": sid, "obs": t, "first_vintage": v1, "mature_vintage": vm, "g1": g1, "gM": gm})
    return pd.DataFrame(rows)


def t2():
    frames = [first_and_mature(p["series_id"]) for p in load_panel()]
    d = pd.concat(frames, ignore_index=True)
    d["r"] = d.gM - d.g1
    tr = d[d.obs <= TRAIN_END]
    te = d[(d.obs >= TEST_START) & (d.obs <= TEST_END)].copy()
    mean_r = tr.groupby("series_id").r.mean()
    coefs = {}
    for sid, g in tr.groupby("series_id"):
        if len(g) >= 24:
            b, a = np.polyfit(g.g1, g.gM, 1)
            coefs[sid] = (a, b)
    te["B0"] = te.g1
    te["B1"] = te.g1 + te.series_id.map(mean_r).fillna(0.0)
    te["B2"] = [coefs[s][0] + coefs[s][1] * x if s in coefs else x for s, x in zip(te.series_id, te.g1)]
    per = []
    for sid, g in te.groupby("series_id"):
        row = {"series_id": sid, "n_test": len(g), "n_train": int((tr.series_id == sid).sum()),
               "mean_abs_revision_pp": round(float(g.r.abs().mean()), 4),
               "share_sign_flip": round(float((np.sign(g.g1) != np.sign(g.gM)).mean()), 4)}
        for m in ["B0", "B1", "B2"]:
            e = g[m] - g.gM
            row[f"{m}_MAE"] = round(float(e.abs().mean()), 4)
            row[f"{m}_RMSE"] = round(float(np.sqrt((e ** 2).mean())), 4)
        per.append(row)
    per = pd.DataFrame(per)
    per.to_csv(os.path.join(PROCESSED, "t2_series_metrics.csv"), index=False)
    overall = {m: {"MAE": round(float((te[m] - te.gM).abs().mean()), 4),
                   "RMSE": round(float(np.sqrt(((te[m] - te.gM) ** 2).mean())), 4)} for m in ["B0", "B1", "B2"]}
    return {"n_obs_total": int(len(d)), "n_train": int(len(tr)), "n_test": int(len(te)),
            "n_series_test": int(te.series_id.nunique()),
            "series_without_train": sorted(set(te.series_id) - set(coefs)),
            "overall": overall, "maturity_months": MATURITY_MONTHS,
            "split": {"train_end": TRAIN_END, "test": [TEST_START, TEST_END]}}


def t1():
    path = os.path.join(PROCESSED, "drift_events.csv")
    if not os.path.exists(path):
        return {"status": "pending_author_labels", "n_labeled": 0}
    ev = pd.read_csv(path)
    lab = ev[ev.is_drift_event & ev.final_cause.notna() & (ev.final_cause != "")]
    if lab.empty:
        return {"status": "pending_author_labels", "n_labeled": 0}
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.tree import DecisionTreeClassifier
    tr, te = lab[lab.vintage_next < T1_SPLIT], lab[lab.vintage_next >= T1_SPLIT]
    if tr.empty or te.empty:
        return {"status": "insufficient_labels", "n_labeled": int(len(lab))}
    res = {"status": "scored_on_author_labels", "n_train": int(len(tr)), "n_test": int(len(te))}
    maj = tr.final_cause.mode().iloc[0]
    preds = {"majority": [maj] * len(te)}
    cal = tr.groupby(["series_id", "vintage_month"]).final_cause.agg(lambda s: s.mode().iloc[0])
    preds["calendar"] = [cal.get((s, m), maj) for s, m in zip(te.series_id, te.vintage_month)]
    X = lambda f: f[FEATURES].fillna(-1).values
    clf = DecisionTreeClassifier(max_depth=6, random_state=0).fit(X(tr), tr.final_cause)
    preds["footprint_tree"] = clf.predict(X(te))
    for k, p in preds.items():
        res[k] = {"macro_F1": round(float(f1_score(te.final_cause, p, average="macro")), 4),
                  "accuracy": round(float(accuracy_score(te.final_cause, p)), 4)}
    return res


def main():
    os.makedirs(PAPER, exist_ok=True)
    out = {"T1_cause_attribution": t1(), "T2_realtime_revision_correction": t2()}
    json.dump(out, open(os.path.join(PAPER, "benchmark_results.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
