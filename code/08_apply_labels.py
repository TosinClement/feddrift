#!/usr/bin/env python3
"""08 - Apply the author's verified labels and write the release table data/processed/drift_events.csv.

Label precedence for each drift event:
  1. labels/event_label_sheet.csv  final_cause (with verified_by and verified_date filled) -> "individually_verified"
  2. labels/rule_sheet.csv         tosin_decision == "accept" for the event's proposed rule  -> "rule_verified"
                                   (only for rules whose label_level is "rule")
  3. otherwise                     final_cause empty                                        -> "unverified"

The release gate (docs/VERIFY_CHECKLIST.md, code/publish_gate.py --labels) refuses to pass while any
drift event is "unverified".
"""

import os

import pandas as pd

from fd_common import PROCESSED, ROOT

LABELS = os.path.join(ROOT, "labels")
ALLOWED = {"advance_to_revised", "annual_benchmark", "seasonal_factor_recompute", "sample_redesign",
           "rebase_or_definition", "routine_reestimation", "correction", "other_major", "unclassified",
           "none_extension_only", "none_archival_window"}

RELEASE_COLS = ["pair_id", "series_id", "vintage_prev", "vintage_next", "vintage_month", "vintage_year",
                "days_between", "n_obs_prev", "n_obs_next", "n_overlap", "n_new_obs", "n_dropped_obs",
                "n_revised", "share_revised", "earliest_revised_obs", "latest_revised_obs",
                "revision_depth_months", "revision_span_months", "mean_abs_pct_revision",
                "max_abs_pct_revision", "net_pct_revision", "share_up", "mean_abs_growth_revision_pp",
                "ks_growth_window", "ks_growth_window_p", "rebase_like", "is_drift_event",
                "proposed_rule", "proposed_cause", "proposed_secondary_cause", "doc_event_key",
                "final_cause", "final_secondary_cause", "label_status", "label_source_url", "verified_date"]


def main():
    ev = pd.read_csv(os.path.join(PROCESSED, "proposed_events.csv"), dtype={"proposed_secondary_cause": str,
                                                                              "doc_event_key": str})
    rules = pd.read_csv(os.path.join(LABELS, "rule_sheet.csv"), dtype=str, keep_default_na=False)
    ind = pd.read_csv(os.path.join(LABELS, "event_label_sheet.csv"), dtype=str, keep_default_na=False)

    bad = sorted(set(ind.final_cause[ind.final_cause != ""]) - ALLOWED)
    if bad:
        raise SystemExit(f"event_label_sheet.csv has causes outside the codebook: {bad}")

    ev["final_cause"], ev["final_secondary_cause"] = "", ""
    ev["label_status"], ev["label_source_url"], ev["verified_date"] = "unverified", "", ""

    # non-events carry their mechanical cause
    ne = ~ev.is_drift_event
    ev.loc[ne, "final_cause"] = ev.loc[ne, "proposed_cause"]
    ev.loc[ne, "label_status"] = "not_a_drift_event"

    acc = rules[(rules.label_level == "rule") & (rules.tosin_decision.str.lower() == "accept")]
    for _, r in acc.iterrows():
        m = ev.is_drift_event & (ev.proposed_rule == r.rule_id)
        ev.loc[m, "final_cause"] = r.cause
        ev.loc[m, "label_status"] = "rule_verified"
        ev.loc[m, "label_source_url"] = r.tosin_source_url
        ev.loc[m, "verified_date"] = r.tosin_verified_date

    done = ind[(ind.final_cause != "") & (ind.verified_by != "") & (ind.verified_date != "")]
    for _, r in done.iterrows():
        m = ev.pair_id == r.pair_id
        ev.loc[m, "final_cause"] = r.final_cause
        ev.loc[m, "final_secondary_cause"] = r.final_secondary_cause
        ev.loc[m, "label_status"] = "individually_verified"
        ev.loc[m, "label_source_url"] = r.agency_source_url
        ev.loc[m, "verified_date"] = r.verified_date
    # an individually-labeled rule's events must come from the event sheet, never from a rule decision
    ev.loc[ev.is_drift_event & (ev.label_status == "rule_verified")
           & ev.pair_id.isin(ind.pair_id), ["final_cause", "label_status"]] = ["", "unverified"]
    ev.loc[ev.pair_id.isin(done.pair_id), "label_status"] = "individually_verified"
    ev.loc[ev.pair_id.isin(done.pair_id), "final_cause"] = ev.pair_id.map(dict(zip(done.pair_id, done.final_cause)))

    ev[RELEASE_COLS].to_csv(os.path.join(PROCESSED, "drift_events.csv"), index=False)
    s = ev[ev.is_drift_event].label_status.value_counts()
    print("drift-event label status:", s.to_dict())


if __name__ == "__main__":
    main()
