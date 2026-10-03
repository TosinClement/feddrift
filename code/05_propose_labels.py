#!/usr/bin/env python3
"""05 - Assign stable event IDs, propose a cause for every vintage pair, and group events into releases.

The rule engine only PROPOSES causes. Final labels are decided by the label owner (labels/README.md) and
applied by code/08_apply_labels.py. This script never reads or writes author decisions.

Inputs : data/processed/vintage_pairs.csv, config/revision_rules.csv, config/panel.csv
Outputs: data/processed/proposed_events.csv   every vintage pair: event_id, proposal, review level, cluster
         data/processed/release_clusters.csv  one row per (release program, vintage date) needing release review

Event IDs are deterministic and stable: FD-<series_id>-<vintage_next as YYYYMMDD>. A series has at most one
ALFRED vintage per date, so the ID is unique and does not depend on run order.

Review levels
  excluded : not a drift event (nothing revised)
  rule     : routine event; covered by a rule-level decision of the label owner
  release  : non-routine; reviewed per agency release (cluster = same program, same vintage date)
"""

import os

import pandas as pd

from fd_common import CONFIG, PROCESSED, load_panel


def series_set(cell):
    return None if cell == "ALL" else set(cell.split(";"))


def propose(row, rules):
    d, m = row.revision_depth_months, row.vintage_month
    for r in rules.itertuples():
        applies = series_set(r.series)
        if applies is not None and row.series_id not in applies:
            continue
        rid = r.rule_id
        if rid == "R00_EXTENSION":
            if row.n_revised == 0 and row.n_dropped_obs == 0:
                return rid
            continue
        if rid == "R01_ARCHIVE_WINDOW":
            if row.n_revised == 0 and row.n_dropped_obs > 0 and row.n_obs_next == row.n_obs_prev:
                return rid
            continue
        if row.n_revised == 0:
            continue
        if rid == "R02_REBASE" and bool(row.rebase_like):
            return rid
        if rid == "R10_BLS_SA_FEB" and m == 2 and ((50 <= d <= 62) or bool(row.depth_censored)):
            return rid
        if rid.startswith("R2") and rid != "R26_ROUTINE_TSI" and d <= float(r.routine_window_months):
            return rid
        if rid == "R26_ROUTINE_TSI":
            return rid
        if rid == "R30_CENSUS_ANNUAL" and 3 <= m <= 7:
            return rid
        if rid == "R90_UNCLASSIFIED":
            return rid
    # pairs with dropped observations that are not a clean rolling window and revise nothing
    return "R90_UNCLASSIFIED"


def main():
    pairs = pd.read_csv(os.path.join(PROCESSED, "vintage_pairs.csv"))
    rules = pd.read_csv(os.path.join(CONFIG, "revision_rules.csv"), dtype=str).fillna("")
    rules["priority"] = rules.priority.astype(int)
    rules = rules.sort_values("priority")
    panel = {p["series_id"]: p for p in load_panel()}

    pairs.insert(0, "event_id", "FD-" + pairs.series_id + "-" + pairs.vintage_next.str.replace("-", ""))
    if "pair_id" in pairs.columns:
        pairs = pairs.drop(columns="pair_id")
    assert pairs.event_id.is_unique, "event_id must be unique"
    pairs["release_program"] = pairs.series_id.map(lambda s: panel[s]["release_program"])
    pairs["proposed_rule"] = pairs.apply(lambda r: propose(r, rules), axis=1)
    rmap = rules.set_index("rule_id")
    pairs["proposed_cause"] = pairs.proposed_rule.map(rmap.proposed_cause)
    pairs["review_level"] = pairs.proposed_rule.map(rmap.review_level)
    pairs["is_drift_event"] = pairs.review_level != "excluded"
    pairs["release_cluster_id"] = ""
    rel = pairs.review_level == "release"
    pairs.loc[rel, "release_cluster_id"] = ("FDC-" + pairs.loc[rel, "release_program"] + "-"
                                            + pairs.loc[rel, "vintage_next"].str.replace("-", ""))
    pairs.to_csv(os.path.join(PROCESSED, "proposed_events.csv"), index=False)

    c = pairs[rel].groupby("release_cluster_id").agg(
        release_program=("release_program", "first"), vintage_date=("vintage_next", "first"),
        series=("series_id", lambda s: ";".join(sorted(s))), n_events=("event_id", "size"),
        event_ids=("event_id", lambda s: ";".join(sorted(s))),
        proposed_causes=("proposed_cause", lambda s: ";".join(sorted(set(s)))),
        proposed_rules=("proposed_rule", lambda s: ";".join(sorted(set(s)))),
        earliest_revised_obs=("earliest_revised_obs", "min"),
        max_depth_months=("revision_depth_months", "max"),
        any_depth_censored=("depth_censored", "max"),
        max_mean_abs_pct_revision=("mean_abs_pct_revision", "max"),
        any_rebase_like=("rebase_like", "max")).reset_index()
    c.to_csv(os.path.join(PROCESSED, "release_clusters.csv"), index=False)

    print(pairs.groupby(["review_level", "proposed_rule"]).size().to_string())
    print(f"pairs {len(pairs)} | drift events {int(pairs.is_drift_event.sum())} | rule-level "
          f"{int((pairs.review_level == 'rule').sum())} | release-level events {int(rel.sum())} "
          f"in {len(c)} releases")


if __name__ == "__main__":
    main()
