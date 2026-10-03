#!/usr/bin/env python3
"""09 - Figures and the stats file. Every number quoted in README or paper comes from paper/stats.json.

Figures carry a DRAFT stamp unless run with --final (only after the verification gate).
Palette: reference categorical slots 1-3 (blue, orange, aqua), validated all-pairs; cause is also encoded
by marker shape so identity is never carried by color alone.

Usage:  python code/09_figures_stats.py [--final]
"""

import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fd_common import FIGURES, MANIFESTS, PAPER, PROCESSED, ROOT, load_panel, load_snapshot  # noqa: E402

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#a9a8a2", "#e6e5e0", "#fcfcfb"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
STYLE = {  # display group -> (color, marker, size, legend label); identity also carried by marker shape
    "routine": (MUTED, "|", 18, "Routine (advance to revised; TSI re-estimation)"),
    "annual_benchmark": (BLUE, "o", 22, "Annual benchmark"),
    "seasonal_factor_recompute": (ORANGE, "s", 22, "Seasonal-factor recompute"),
    "definition": (AQUA, "D", 30, "Rebase, definition, method change or correction"),
    "unknown": (INK, "x", 36, "Unknown / not yet classified"),
}
GROUP = {"advance_to_revised": "routine", "routine_reestimation": "routine", "annual_benchmark": "annual_benchmark",
         "seasonal_factor_recompute": "seasonal_factor_recompute", "rebase_or_definition": "definition",
         "methodology_change": "definition", "correction": "definition", "sample_redesign": "definition",
         "unknown": "unknown", "unclassified": "unknown"}
VERIFIED = {"rule_verified", "release_verified", "unknown_verified", "override_verified"}


def base_style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURFACE,
                         "axes.facecolor": SURFACE, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6})


def stamp(fig, final):
    if not final:
        fig.text(0.99, 0.01, "DRAFT - labels not yet verified", ha="right", va="bottom", fontsize=8,
                 color="#b42318", alpha=0.9)
    fig.text(0.01, 0.01, "FedDrift v0.1 | Tosin Clement | sources: ALFRED, Census, BLS, BTS", ha="left",
             va="bottom", fontsize=7, color=INK2)


def label_col(ev):
    """Final (author-verified) cause where it exists, otherwise Claude's recommendation. Figures say which."""
    ver = ev.label_status.isin(VERIFIED)
    return ev.final_cause.where(ver, ev.recommended_cause)


def fig_timeline(ev, final):
    order = [p["series_id"] for p in load_panel()][::-1]
    e = ev[ev.is_drift_event].copy()
    e["cause"] = label_col(e).map(GROUP).fillna("unknown")
    e["x"] = pd.to_datetime(e.vintage_next)
    all_ver = bool(e.label_status.isin(VERIFIED).all())
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for cause, (c, m, s, lab) in STYLE.items():
        g = e[e.cause == cause]
        ax.scatter(g.x, g.series_id.map({k: i for i, k in enumerate(order)}), c=c, marker=m, s=s,
                   linewidths=1.2 if m in "|x" else 0.6, edgecolors=SURFACE if m not in "|x" else None,
                   label=lab, zorder=3 if cause != "routine" else 2)
    ax.set_yticks(range(len(order)), order)
    ax.set_xlabel("Vintage (release) date")
    ax.grid(axis="y", visible=False)
    ax.set_title("Every drift event in the FedDrift panel, by " + ("verified cause" if all_ver else
                 "recommended cause (not yet verified by the label owner)"), loc="left", color=INK, fontsize=11)
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=1)
    stamp(fig, final)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig1_event_timeline.png"), dpi=200)
    plt.close(fig)


def fig_cpi_regime(ev, final):
    e = ev[(ev.series_id == "CPIAUCSL") & (ev.vintage_month == 2) & (ev.n_revised > 0)].copy()
    e["x"] = pd.to_datetime(e.vintage_next)
    cens = e.depth_censored.astype(str) == "True"
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.plot(e.x, e.revision_depth_months, color=BLUE, lw=1.2, zorder=2)
    ax.scatter(e.x[~cens], e.revision_depth_months[~cens], color=BLUE, s=22, zorder=3, label="measured depth")
    ax.scatter(e.x[cens], e.revision_depth_months[cens], facecolors=SURFACE, edgecolors=BLUE, s=26, zorder=3,
               linewidths=1.2, label="lower bound: revision reaches the start of the archived vintage")
    ax.axhline(60, color=MUTED, lw=1, ls="--")
    ax.text(e.x.min(), 63, "5 years (60 months)", color=INK2, fontsize=8)
    for _, r in e[e.revision_depth_months > 100].iterrows():
        ax.annotate(f"{r.vintage_next}: {int(r.revision_depth_months)} months", (r.x, r.revision_depth_months),
                    xytext=(-130, -4), textcoords="offset points", fontsize=8, color=INK2,
                    arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_ylabel("Depth of the February revision (months)")
    ax.set_title("CPI-U (SA): how far back each February revision reached", loc="left", color=INK, fontsize=11)
    ax.legend(loc="upper left", frameon=False, fontsize=7.5)
    stamp(fig, final)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig2_cpi_seasonal_depth.png"), dpi=200)
    plt.close(fig)


def fig_share(qa, final):
    s = pd.Series(qa["share_pairs_revised"]).sort_values() * 100
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    colors = [ORANGE if k == "CPIAUCNS" else BLUE for k in s.index]
    ax.barh(s.index, s.values, color=colors, height=0.7)
    for i, (k, v) in enumerate(s.items()):
        ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=7.5, color=INK2)
    ax.set_xlabel("Share of consecutive vintages that revise at least one published value (%)")
    ax.set_xlim(0, 112)
    ax.grid(axis="y", visible=False)
    ax.set_title("How often each series is revised (NSA CPI = negative control)", loc="left", color=INK, fontsize=11)
    stamp(fig, final)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig3_revision_frequency.png"), dpi=200)
    plt.close(fig)


def fig_t2(final):
    t = pd.read_csv(os.path.join(PAPER, "tables", "t2_by_series.csv")).sort_values("mean_abs_revision_pp")
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.barh(t.series_id, t.mean_abs_revision_pp, color=BLUE, height=0.7)
    for i, (_, r) in enumerate(t.iterrows()):
        ax.text(r.mean_abs_revision_pp + 0.02, i, f"{r.mean_abs_revision_pp:.2f} pp | sign flips {r.share_sign_flip * 100:.0f}%",
                va="center", fontsize=7.5, color=INK2)
    ax.set_xlabel("Mean absolute revision of first-release m/m growth after 36 months (percentage points)")
    ax.set_xlim(0, t.mean_abs_revision_pp.max() * 1.6)
    ax.grid(axis="y", visible=False)
    ax.set_title("T2: how much first-release growth changes (test obs 2016-01 to 2022-09)", loc="left",
                 color=INK, fontsize=11)
    stamp(fig, final)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig4_t2_revision_size.png"), dpi=200)
    plt.close(fig)


def stats(ev, qa, bench, final):
    man = json.load(open(os.path.join(MANIFESTS, "alfred_manifest.json")))["series"]
    snap = load_snapshot()
    st = json.load(open(os.path.join(PROCESSED, "label_status.json")))
    de = ev[ev.is_drift_event]
    rec = de.groupby("recommended_cause").agg(
        n=("event_id", "size"), median_depth_months=("revision_depth_months", "median"),
        median_mean_abs_pct_revision=("mean_abs_pct_revision", "median"),
        median_ks=("ks_growth_window", "median")).round(4).reset_index()
    ver = de[de.label_status.isin(VERIFIED)]
    fin = ver.groupby("final_cause").agg(
        n=("event_id", "size"), median_depth_months=("revision_depth_months", "median"),
        median_mean_abs_pct_revision=("mean_abs_pct_revision", "median"),
        median_ks=("ks_growth_window", "median")).round(4).reset_index()
    checks = {c["id"]: c for c in qa["checks"]}
    anchor = qa["anchor_agreement"]
    mans = [pd.read_csv(os.path.join(MANIFESTS, f"{k}.vintages.csv")) for k in man]
    clusters = pd.read_csv(os.path.join(PROCESSED, "release_clusters.csv"))
    s = {
        "version": "0.1.0", "snapshot_id": snap["snapshot_id"], "alfred_realtime_end": snap["alfred_realtime_end"],
        "final_mode": bool(final),
        "n_series": int(ev.series_id.nunique()),
        "n_vintages": int(sum(v["n_vintages"] for v in man.values())),
        "first_vintage": min(v["first_vintage"] for v in man.values()),
        "last_vintage": max(v["last_vintage"] for v in man.values()),
        "first_obs": min(m.first_obs.min() for m in mans), "last_obs": max(m.last_obs.max() for m in mans),
        "n_vintage_pairs": int(len(ev)), "n_drift_events": int(len(de)), "n_excluded": int((~ev.is_drift_event).sum()),
        "n_rule_level_events": int((de.review_level == "rule").sum()),
        "n_release_level_events": int((de.review_level == "release").sum()), "n_release_clusters": int(len(clusters)),
        "n_rules_for_review": int(de[de.review_level == "rule"].proposed_rule.nunique()),
        "n_depth_censored_events": int((de.depth_censored.astype(str) == "True").sum()),
        "label_status": st["by_status"], "n_verified": st["n_verified"], "n_unverified": st["n_unverified"],
        "n_final_unknown": st["n_final_unknown"],
        "events_by_recommended_cause": rec.to_dict(orient="records"),
        "events_by_final_cause": fin.to_dict(orient="records"),
        "recommendation_confidence_by_release": pd.read_csv(os.path.join(ROOT, "evidence",
                                                                         "cluster_evidence.csv")).confidence.value_counts().to_dict(),
        "n_sources": int(len(pd.read_csv(os.path.join(ROOT, "evidence", "source_registry.csv")))),
        "copyright_tags": sorted({t for v in man.values() for t in v["copyright_tags"]}),
        "anchor_full_match_series": sorted(k for k, v in anchor.items() if v["match_rate"] == 1.0),
        "anchor_partial_match": {k: v["match_rate"] for k, v in anchor.items() if v["match_rate"] != 1.0},
        "qa_status": {k: v["status"] for k, v in checks.items()},
        "reconstruction": checks.get("Q03", {}).get("actual", ""),
        "share_pairs_revised": qa["share_pairs_revised"],
        "cpiaucns_revising_vintages": int((ev[ev.series_id == "CPIAUCNS"].n_revised > 0).sum()),
        "benchmark": bench,
    }
    json.dump(s, open(os.path.join(PAPER, "stats.json"), "w"), indent=1, default=str)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    os.makedirs(FIGURES, exist_ok=True)
    base_style()
    ev = pd.read_csv(os.path.join(PROCESSED, "drift_events.csv"), keep_default_na=False,
                     na_values={"revision_depth_months": [""], "mean_abs_pct_revision": [""],
                                "ks_growth_window": [""]})
    ev["is_drift_event"] = ev.is_drift_event.astype(str) == "True"
    for c in ["revision_depth_months", "mean_abs_pct_revision", "ks_growth_window", "n_revised"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    if a.final:
        unv = int((ev.is_drift_event & ~ev.label_status.isin(VERIFIED)).sum())
        qa0 = json.load(open(os.path.join(PROCESSED, "qa.json")))
        bad = [c["id"] for c in qa0["checks"] if c["status"] in ("FAIL", "BLOCKING")]
        if unv or bad:
            raise SystemExit(f"--final refused: {unv} drift events lack a verified label; QA not clean: {bad}. "
                             "See labels/README.md and data/processed/qa_report.md.")
    qa = json.load(open(os.path.join(PROCESSED, "qa.json")))
    bench = json.load(open(os.path.join(PAPER, "benchmark_results.json")))
    fig_timeline(ev, a.final)
    fig_cpi_regime(ev, a.final)
    fig_share(qa, a.final)
    fig_t2(a.final)
    s = stats(ev, qa, bench, a.final)
    print(json.dumps({k: s[k] for k in ["n_series", "n_vintages", "n_vintage_pairs", "n_drift_events",
                                         "n_release_clusters", "n_verified", "n_unverified", "final_mode"]}))


if __name__ == "__main__":
    main()
