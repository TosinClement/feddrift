#!/usr/bin/env python3
"""10 - FedDrift benchmark tasks: splits, baselines, scoring. Fully specified in docs/METHODOLOGY.md, section 5.

T1  Revision-cause attribution (needs verified labels)
    Unit     : one drift event (consecutive vintage pair with at least one revised value).
    Input    : the footprint features in FEATURES plus release program and SA flag; all observable on the
               release day from the two vintages (no labels, no later vintages).
    Target   : final_cause (author-verified). Events whose final cause is 'unknown' are reported, not scored.
    Splits   : by vintage_next. train < 2010-01-01; validation 2010-01-01..2014-12-31; test >= 2015-01-01.
               Events of one agency release share a date, so they never straddle splits.
    Metrics  : macro-F1 over causes present in the test split; accuracy; per-cause support.
    Baselines: majority class; calendar (series x vintage month majority, train only); decision tree
               (max_depth chosen on validation from {2,3,4,6,8}, random_state = SEED).
    Runs only when every drift event carries a verified label; otherwise status = pending_author_labels.

T2  Real-time revision correction (label-independent)
    Unit     : one observation month t of one series.
    Kept     : genuine first releases only (first vintage containing t published <= 3 months after t) whose
               mature value exists: gM(t) = m/m % growth of t in the first vintage >= 36 months after first release.
    Input    : g1(t), the m/m % growth in the first-release vintage. Target: gM(t).
    Splits   : by first-release vintage v1, leakage-free in calendar time:
               train      : mature vintage < 2009-01-01
               validation : v1 >= 2009-01-01 and mature vintage < 2016-01-01
               test       : 2016-01-01 <= v1 <= 2022-09-30
               Every target used to fit or select is published before the first test prediction (asserted).
    Baselines: B0 no revision (gM_hat = g1); B1 g1 + train mean revision of the series; B2 per-series OLS
               gM ~ g1 on train; B3 per series, whichever of B0-B2 has the lowest validation MAE.
               B1/B2 need >= 24 train observations, otherwise they fall back to B0 (reported).
    Metrics  : MAE and RMSE (percentage points), pooled and per series; 95% bootstrap interval for the pooled
               MAE difference vs B0 (2,000 resamples of test observations, seed SEED; i.i.d. resampling ignores
               serial correlation, so the interval is indicative only).

Outputs: paper/benchmark_results.json, paper/tables/t2_overall.csv, paper/tables/t2_by_series.csv,
         paper/tables/t1_results.csv (when available), data/processed/t2_split_counts.csv
"""

import json
import os

import numpy as np
import pandas as pd

from fd_common import ALFRED_CACHE, PAPER, PROCESSED, load_panel

SEED = 20261003
MATURITY_MONTHS = 36
FIRST_RELEASE_MAX_LAG = 3
T2_TRAIN_MATURE_BEFORE = "2009-01-01"
T2_VAL_START, T2_VAL_MATURE_BEFORE = "2009-01-01", "2016-01-01"
T2_TEST_START, T2_TEST_END = "2016-01-01", "2022-09-30"
T1_TRAIN_END, T1_VAL_END = "2010-01-01", "2015-01-01"
MIN_TRAIN = 24
FEATURES = ["vintage_month", "n_revised", "share_revised", "revision_depth_months", "revision_span_months",
            "depth_censored", "mean_abs_pct_revision", "max_abs_pct_revision", "net_pct_revision", "share_up",
            "mean_abs_growth_revision_pp", "ks_growth_window", "n_new_obs", "n_dropped_obs", "days_between",
            "rebase_like"]
VERIFIED = {"rule_verified", "release_verified", "unknown_verified", "override_verified"}
TABLES = os.path.join(PAPER, "tables")


def months_between(a, b):
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    return (b.year - a.year) * 12 + b.month - a.month


def first_and_mature(sid):
    j = json.load(open(os.path.join(ALFRED_CACHE, f"{sid}.observations.json")))
    df = pd.DataFrame(j["observations"])
    df = df[df.value != "."].copy()
    df["value"] = df.value.astype(float)
    vds = pd.to_datetime(pd.Series(j["vintage_dates"]))
    cache = {}

    def vec(v):
        if v not in cache:
            live = df[(df.realtime_start <= v) & (df.realtime_end >= v)]
            cache[v] = pd.Series(live.value.values, index=live.date.values)
        return cache[v]

    rows = []
    for t, v1 in df.groupby("date").realtime_start.min().items():
        if months_between(t, v1) > FIRST_RELEASE_MAX_LAG:
            continue
        prev = (pd.Timestamp(t) - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        a = vec(v1)
        if prev not in a.index or t not in a.index:
            continue
        later = vds[vds >= pd.Timestamp(v1) + pd.DateOffset(months=MATURITY_MONTHS)]
        if later.empty:
            continue
        vm = later.iloc[0].strftime("%Y-%m-%d")
        b = vec(vm)
        if prev not in b.index or t not in b.index:
            continue
        rows.append({"series_id": sid, "obs": t, "first_vintage": v1, "mature_vintage": vm,
                     "g1": (a[t] / a[prev] - 1) * 100, "gM": (b[t] / b[prev] - 1) * 100})
    return pd.DataFrame(rows)


def assign_t2_split(d):
    s = np.full(len(d), "excluded_gap", dtype=object)
    s[(d.mature_vintage < T2_TRAIN_MATURE_BEFORE).values] = "train"
    s[((d.first_vintage >= T2_VAL_START) & (d.mature_vintage < T2_VAL_MATURE_BEFORE)).values] = "validation"
    s[((d.first_vintage >= T2_TEST_START) & (d.first_vintage <= T2_TEST_END)).values] = "test"
    return s


def t2():
    d = pd.concat([first_and_mature(p["series_id"]) for p in load_panel()], ignore_index=True)
    d["r"] = d.gM - d.g1
    d["split"] = assign_t2_split(d)
    tr, va, te = (d[d.split == k].copy() for k in ("train", "validation", "test"))
    # leakage assertions (calendar time)
    assert tr.mature_vintage.max() < va.first_vintage.min(), "train targets must precede validation inputs"
    assert va.mature_vintage.max() < te.first_vintage.min(), "validation targets must precede test inputs"
    assert tr.mature_vintage.max() < te.first_vintage.min()

    mean_r, coef = {}, {}
    for sid, g in tr.groupby("series_id"):
        if len(g) >= MIN_TRAIN:
            mean_r[sid] = g.r.mean()
            b, a = np.polyfit(g.g1, g.gM, 1)
            coef[sid] = (a, b)

    def predict(frame):
        f = frame.copy()
        f["B0"] = f.g1
        f["B1"] = f.g1 + f.series_id.map(mean_r).fillna(0.0)
        f["B2"] = [coef[s][0] + coef[s][1] * x if s in coef else x for s, x in zip(f.series_id, f.g1)]
        return f

    va, te = predict(va), predict(te)
    choice = {}
    for sid in te.series_id.unique():
        g = va[va.series_id == sid]
        choice[sid] = "B0" if g.empty else min(["B0", "B1", "B2"], key=lambda m: (g[m] - g.gM).abs().mean())
    te["B3"] = [r[choice[r.series_id]] for _, r in te.iterrows()]

    rng = np.random.default_rng(SEED)
    overall = []
    for m in ["B0", "B1", "B2", "B3"]:
        e = te[m] - te.gM
        diff = (e.abs() - (te.B0 - te.gM).abs()).values
        boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
        overall.append({"baseline": m, "n_test": len(te), "MAE_pp": round(float(e.abs().mean()), 4),
                        "RMSE_pp": round(float(np.sqrt((e ** 2).mean())), 4),
                        "MAE_minus_B0": round(float(diff.mean()), 4),
                        "MAE_minus_B0_ci95_low": round(float(np.percentile(boots, 2.5)), 4),
                        "MAE_minus_B0_ci95_high": round(float(np.percentile(boots, 97.5)), 4)})
    per = []
    for sid, g in te.groupby("series_id"):
        row = {"series_id": sid, "n_train": int((tr.series_id == sid).sum()),
               "n_validation": int((va.series_id == sid).sum()), "n_test": len(g),
               "fitted": sid in coef, "val_selected": choice[sid],
               "mean_abs_revision_pp": round(float(g.r.abs().mean()), 4),
               "share_sign_flip": round(float((np.sign(g.g1) != np.sign(g.gM)).mean()), 4)}
        for m in ["B0", "B1", "B2", "B3"]:
            e = g[m] - g.gM
            row[f"{m}_MAE"] = round(float(e.abs().mean()), 4)
            row[f"{m}_RMSE"] = round(float(np.sqrt((e ** 2).mean())), 4)
        per.append(row)
    os.makedirs(TABLES, exist_ok=True)
    pd.DataFrame(overall).to_csv(os.path.join(TABLES, "t2_overall.csv"), index=False)
    pd.DataFrame(per).to_csv(os.path.join(TABLES, "t2_by_series.csv"), index=False)
    counts = d.groupby(["series_id", "split"]).size().unstack(fill_value=0)
    counts.to_csv(os.path.join(PROCESSED, "t2_split_counts.csv"))
    return {"status": "scored", "seed": SEED, "maturity_months": MATURITY_MONTHS,
            "first_release_max_lag_months": FIRST_RELEASE_MAX_LAG,
            "splits": {"train": f"mature vintage < {T2_TRAIN_MATURE_BEFORE}",
                       "validation": f"first vintage >= {T2_VAL_START} and mature vintage < {T2_VAL_MATURE_BEFORE}",
                       "test": f"{T2_TEST_START} <= first vintage <= {T2_TEST_END}"},
            "n": {k: int((d.split == k).sum()) for k in ["train", "validation", "test", "excluded_gap"]},
            "n_obs_total": int(len(d)), "n_series_test": int(te.series_id.nunique()),
            "series_without_fit": sorted(set(te.series_id) - set(coef)),
            "leakage_checks": {"train_mature_max": tr.mature_vintage.max(), "validation_first_min": va.first_vintage.min(),
                               "validation_mature_max": va.mature_vintage.max(), "test_first_min": te.first_vintage.min()},
            "overall": overall}


def t1():
    ev = pd.read_csv(os.path.join(PROCESSED, "drift_events.csv"), keep_default_na=False)
    ev = ev[ev.is_drift_event.astype(str) == "True"]
    n_ver = int(ev.label_status.isin(VERIFIED).sum())
    if n_ver < len(ev):
        return {"status": "pending_author_labels", "n_drift_events": len(ev), "n_verified": n_ver,
                "splits": {"train": f"vintage_next < {T1_TRAIN_END}", "validation": f"{T1_TRAIN_END} <= vintage_next < {T1_VAL_END}",
                           "test": f"vintage_next >= {T1_VAL_END}"}}
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.tree import DecisionTreeClassifier
    lab = ev[ev.final_cause != "unknown"].copy()
    for c in FEATURES:
        lab[c] = pd.to_numeric(lab[c].replace({"True": 1, "False": 0}), errors="coerce").fillna(-1)
    prog = pd.get_dummies(lab.release_program, prefix="prog").astype(int)
    X = pd.concat([lab[FEATURES], prog], axis=1)
    tr = lab.vintage_next < T1_TRAIN_END
    va = (lab.vintage_next >= T1_TRAIN_END) & (lab.vintage_next < T1_VAL_END)
    te = lab.vintage_next >= T1_VAL_END
    y = lab.final_cause
    maj = y[tr].mode().iloc[0]
    cal = lab[tr].groupby(["series_id", "vintage_month"]).final_cause.agg(lambda s: s.mode().iloc[0])
    best = max([2, 3, 4, 6, 8], key=lambda dpt: f1_score(
        y[va], DecisionTreeClassifier(max_depth=dpt, random_state=SEED).fit(X[tr], y[tr]).predict(X[va]),
        average="macro"))
    clf = DecisionTreeClassifier(max_depth=best, random_state=SEED).fit(X[tr | va], y[tr | va])
    preds = {"majority": [maj] * int(te.sum()),
             "calendar": [cal.get((s, m), maj) for s, m in zip(lab[te].series_id, lab[te].vintage_month)],
             "footprint_tree": list(clf.predict(X[te]))}
    rows = []
    for k, p in preds.items():
        rows.append({"baseline": k, "n_test": int(te.sum()),
                     "macro_F1": round(float(f1_score(y[te], p, average="macro")), 4),
                     "accuracy": round(float(accuracy_score(y[te], p)), 4)})
    os.makedirs(TABLES, exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join(TABLES, "t1_results.csv"), index=False)
    return {"status": "scored_on_author_labels", "seed": SEED, "tree_max_depth": best,
            "n": {"train": int(tr.sum()), "validation": int(va.sum()), "test": int(te.sum()),
                  "unknown_not_scored": int((ev.final_cause == "unknown").sum())},
            "test_support": {k: int(v) for k, v in y[te].value_counts().items()}, "results": rows}


def main():
    out = {"T1_cause_attribution": t1(), "T2_realtime_revision_correction": t2()}
    os.makedirs(PAPER, exist_ok=True)
    json.dump(out, open(os.path.join(PAPER, "benchmark_results.json"), "w"), indent=1, default=str)
    print(json.dumps({"T1": out["T1_cause_attribution"]["status"],
                      "T2": out["T2_realtime_revision_correction"]["overall"],
                      "T2_n": out["T2_realtime_revision_correction"]["n"]}, indent=1))


if __name__ == "__main__":
    main()
