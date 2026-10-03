#!/usr/bin/env python3
"""04 - Turn each series' ALFRED history into vintage-pair footprints (one row per consecutive vintage pair).

For every consecutive pair (v_prev -> v_next) of a series, compares the two vintage vectors over the
observation dates they share and records:
  n_new_obs, n_dropped_obs, n_overlap, n_revised, earliest/latest revised obs, revision depth (months
  between the vintage month and the earliest revised observation), revision magnitudes in percent of level,
  revision magnitude on month-over-month growth rates, a two-sample KS statistic between the growth-rate
  distributions of the revised window before and after (the distribution-shift measure), net direction,
  a rebasing indicator (constant ratio across the whole history), and depth_censored (the revision reaches,
  within two months, the first observation both vintages share, so the measured depth is only a lower bound: early ALFRED
  vintages of some series hold a short rolling window, e.g. CPI-U SA vintages of 1972-1993 hold 19 months).

No observation values are written: the output is derived statistics only (docs/LICENSING_PROTOCOL.md).

Output: data/processed/vintage_pairs.csv
"""

import json
import os
import warnings

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from fd_common import ALFRED_CACHE, PROCESSED, load_panel

REL_TOL = 1e-9
CENSOR_SLACK_MONTHS = 2


def months(d):
    d = pd.Timestamp(d)
    return d.year * 12 + d.month


def vintages(sid):
    j = json.load(open(os.path.join(ALFRED_CACHE, f"{sid}.observations.json")))
    df = pd.DataFrame(j["observations"])
    df = df[df.value != "."].copy()
    df["value"] = df.value.astype(float)
    out = {}
    for v in j["vintage_dates"]:
        live = df[(df.realtime_start <= v) & (df.realtime_end >= v)]
        out[v] = pd.Series(live.value.values, index=live.date.values).sort_index()
    return out


def growth(s):
    return (s / s.shift(1) - 1.0) * 100.0


def pair_stats(sid, vp, vn, a, b):
    common = a.index.intersection(b.index)
    new = b.index.difference(a.index)
    dropped = a.index.difference(b.index)
    av, bv = a.loc[common], b.loc[common]
    diff = (bv - av)
    rel = diff.abs() / av.abs().replace(0, np.nan)
    revised = common[(rel > REL_TOL).fillna(diff.abs() > 0).values]
    row = {
        "series_id": sid, "vintage_prev": vp, "vintage_next": vn,
        "vintage_month": int(vn[5:7]), "vintage_year": int(vn[:4]),
        "days_between": (pd.Timestamp(vn) - pd.Timestamp(vp)).days,
        "n_obs_prev": len(a), "n_obs_next": len(b), "n_overlap": len(common),
        "n_new_obs": len(new), "n_dropped_obs": len(dropped), "n_revised": len(revised),
        "share_revised": round(len(revised) / len(common), 6) if len(common) else np.nan,
        "first_obs_prev": a.index.min() if len(a) else "",
        "first_obs_overlap": common.min() if len(common) else "",
    }
    if len(revised):
        pct = (diff.loc[revised] / av.loc[revised].abs()) * 100.0
        ga, gb = growth(a).loc[common], growth(b).loc[common]
        gd = (gb - ga).loc[revised].dropna()
        e, l = revised.min(), revised.max()
        win_a, win_b = ga.loc[e:l].dropna(), gb.loc[e:l].dropna()
        ks = ks_2samp(win_a, win_b) if len(win_a) >= 5 and len(win_b) >= 5 else None
        ratio = np.log((bv / av).replace([np.inf, -np.inf], np.nan).dropna())
        row.update({
            "earliest_revised_obs": e, "latest_revised_obs": l,
            "revision_depth_months": months(vn) - months(e),
            # True when the revision reaches (within two months) the first observation both vintages share:
            # the true depth may be larger, because the vintage (or the series) holds no earlier data, so the
            # measured depth is a lower bound. The two-month allowance covers early months whose rounded
            # published value happened not to change.
            "depth_censored": bool(months(e) - months(common.min()) <= CENSOR_SLACK_MONTHS),
            "revision_span_months": months(l) - months(e) + 1,
            "mean_abs_pct_revision": round(float(pct.abs().mean()), 6),
            "max_abs_pct_revision": round(float(pct.abs().max()), 6),
            "net_pct_revision": round(float(pct.mean()), 6),
            "share_up": round(float((pct > 0).mean()), 4),
            "mean_abs_growth_revision_pp": round(float(gd.abs().mean()), 6) if len(gd) else np.nan,
            "ks_growth_window": round(float(ks.statistic), 6) if ks else np.nan,
            "ks_growth_window_p": float(ks.pvalue) if ks else np.nan,
            "rebase_like": bool(len(revised) >= 0.95 * len(common) and len(ratio) > 12
                                and float(ratio.std()) < 1e-3 and abs(float(ratio.mean())) > 1e-3),
        })
    return row


def main():
    warnings.filterwarnings("ignore", message="ks_2samp: Exact calculation unsuccessful")
    rows = []
    for p in load_panel():
        sid = p["series_id"]
        vs = vintages(sid)
        keys = list(vs)
        for vp, vn in zip(keys[:-1], keys[1:]):
            rows.append(pair_stats(sid, vp, vn, vs[vp], vs[vn]))
        n = sum(1 for r in rows if r["series_id"] == sid)
        print(f"{sid:16s} {n:4d} pairs")
    df = pd.DataFrame(rows)
    df.insert(0, "pair_id", "FD-" + df.series_id + "-" + df.vintage_next.str.replace("-", ""))
    os.makedirs(PROCESSED, exist_ok=True)
    df.to_csv(os.path.join(PROCESSED, "vintage_pairs.csv"), index=False)
    print(f"wrote {len(df)} vintage pairs; with revisions: {(df.n_revised > 0).sum()}")


if __name__ == "__main__":
    main()
