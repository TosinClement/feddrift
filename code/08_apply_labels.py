#!/usr/bin/env python3
"""08 - Apply the label owner's decisions and write the release tables.

Inputs : data/processed/proposed_events.csv, evidence/*.csv, labels/decisions/*.csv (author decisions; may be absent)
Outputs: data/processed/drift_events.csv     every vintage pair (6,295 rows) with labels and label provenance
         data/processed/event_inventory.csv  the drift events only (is_drift_event = True)
         data/processed/label_status.json    counts by status, used by the release gate

label_status values
  excluded_not_drift      no published value changed (extension or archival window); not a drift event
  rule_pending_review     routine event; its rule has not been decided by the label owner
  rule_verified           routine event; the label owner approved its rule against the cited agency source
  rule_rejected           routine event; the label owner rejected its rule (must be relabeled before release)
  release_pending_review  non-routine event; its agency release has not been decided
  release_verified        non-routine event; the label owner decided its release with a cause
  unknown_verified        the label owner reviewed the evidence and set final_cause = unknown
  override_verified       the label owner labeled this single event individually

Labels are never marked verified unless a decision row with verified_by and verified_date exists.
"""

import json
import os

import pandas as pd

from fd_common import PROCESSED, ROOT

DEC = os.path.join(ROOT, "labels", "decisions")
EVID = os.path.join(ROOT, "evidence")
VERIFIED = {"rule_verified", "release_verified", "unknown_verified", "override_verified"}


def read_dec(name, cols):
    p = os.path.join(DEC, name)
    if not os.path.exists(p):
        return pd.DataFrame(columns=cols)
    d = pd.read_csv(p, dtype=str).fillna("")
    d = d[(d.verified_by != "") & (d.verified_date != "")]
    return d


def src_fields(ids, reg):
    ids = [s for s in str(ids).split(";") if s and s in reg.index]
    get = lambda col: " || ".join(str(reg.loc[s, col]) for s in ids)
    return {"label_source_ids": ";".join(ids), "label_source_titles": get("title"),
            "label_source_publishers": get("publisher"), "label_source_publication_dates": get("publication_date"),
            "label_source_urls": get("url")}


def main():
    ev = pd.read_csv(os.path.join(PROCESSED, "proposed_events.csv"))
    reg = pd.read_csv(os.path.join(EVID, "source_registry.csv"), dtype=str).fillna("").set_index("source_id")
    rev = pd.read_csv(os.path.join(EVID, "rule_evidence.csv"), dtype=str).fillna("")
    cev = pd.read_csv(os.path.join(EVID, "cluster_evidence.csv"), dtype=str).fillna("").set_index("release_cluster_id")
    rules = read_dec("rule_decisions.csv", ["rule_id", "decision", "verified_by", "verified_date", "notes"])
    rels = read_dec("release_decisions.csv", ["release_cluster_id", "decision", "final_cause", "final_secondary_cause",
                                             "verified_by", "verified_date", "notes"])
    ovs = read_dec("event_overrides.csv", ["event_id", "final_cause", "final_secondary_cause", "reason", "source_url",
                                          "source_ids", "verified_by", "verified_date", "notes"])
    for c in ("source_ids", "notes"):
        if c not in ovs.columns:
            ovs[c] = ""

    for c in ["recommended_cause", "recommended_secondary_cause", "recommendation_confidence", "final_cause",
              "final_secondary_cause", "label_status", "label_basis", "label_source_ids", "label_source_titles",
              "label_source_publishers", "label_source_publication_dates", "label_source_urls", "label_source_locator",
              "reviewer", "verified_date"]:
        ev[c] = ""

    # recommendations (Claude) shown alongside, never as final
    rl = ev.review_level == "release"
    ev.loc[rl, "recommended_cause"] = ev.loc[rl, "release_cluster_id"].map(cev.recommended_cause)
    ev.loc[rl, "recommended_secondary_cause"] = ev.loc[rl, "release_cluster_id"].map(cev.recommended_secondary_cause)
    ev.loc[rl, "recommendation_confidence"] = ev.loc[rl, "release_cluster_id"].map(cev.confidence)
    ru = ev.review_level == "rule"
    ev.loc[ru, "recommended_cause"] = ev.loc[ru, "proposed_cause"]
    ev.loc[ru, "recommendation_confidence"] = "program_policy"

    ex = ev.review_level == "excluded"
    ev.loc[ex, "final_cause"] = ev.loc[ex, "proposed_cause"]
    ev.loc[ex, "label_status"] = "excluded_not_drift"
    ev.loc[ex, "label_basis"] = "mechanical:" + ev.loc[ex, "proposed_rule"]
    ev.loc[ru, "label_status"] = "rule_pending_review"
    ev.loc[ru, "label_basis"] = "rule:" + ev.loc[ru, "proposed_rule"]
    ev.loc[rl, "label_status"] = "release_pending_review"
    ev.loc[rl, "label_basis"] = "release:" + ev.loc[rl, "release_cluster_id"]

    for r in rules.itertuples():
        m = ru & (ev.proposed_rule == r.rule_id)
        if r.decision == "approve":
            ids = ";".join(s for s in rev[rev.rule_id == r.rule_id].source_id if s)
            ev.loc[m, "final_cause"] = ev.loc[m, "proposed_cause"]
            ev.loc[m, "label_status"] = "rule_verified"
            for k, v in src_fields(ids, reg).items():
                ev.loc[m, k] = v
            ev.loc[m, "label_source_locator"] = " || ".join(x for x in rev[rev.rule_id == r.rule_id].locator if x)
        else:
            ev.loc[m, "label_status"] = "rule_rejected"
        ev.loc[m, "reviewer"] = r.verified_by
        ev.loc[m, "verified_date"] = r.verified_date

    for r in rels.itertuples():
        m = rl & (ev.release_cluster_id == r.release_cluster_id)
        c = cev.loc[r.release_cluster_id] if r.release_cluster_id in cev.index else None
        if r.decision == "approve":
            cause, sec = c.recommended_cause, (r.final_secondary_cause or c.recommended_secondary_cause)
        elif r.decision == "set":
            cause, sec = r.final_cause, r.final_secondary_cause
        else:
            cause, sec = "unknown", ""
        ev.loc[m, "final_cause"] = cause
        ev.loc[m, "final_secondary_cause"] = sec
        ev.loc[m, "label_status"] = "unknown_verified" if cause == "unknown" else "release_verified"
        if c is not None and cause != "unknown":
            for k, v in src_fields(c.source_ids, reg).items():
                ev.loc[m, k] = v
            ev.loc[m, "label_source_locator"] = c.evidence_locator
        ev.loc[m, "reviewer"] = r.verified_by
        ev.loc[m, "verified_date"] = r.verified_date

    for r in ovs.itertuples():
        m = ev.event_id == r.event_id
        ev.loc[m, "final_cause"] = r.final_cause
        ev.loc[m, "final_secondary_cause"] = r.final_secondary_cause
        ev.loc[m, "label_status"] = "override_verified" if r.final_cause != "unknown" else "unknown_verified"
        ev.loc[m, "label_basis"] = "override"
        for k in ["label_source_ids", "label_source_titles", "label_source_publishers", "label_source_publication_dates",
                  "label_source_urls"]:
            ev.loc[m, k] = ""
        if r.source_ids and r.final_cause != "unknown":
            for k, v in src_fields(r.source_ids, reg).items():
                ev.loc[m, k] = v
        else:
            ev.loc[m, "label_source_urls"] = r.source_url
        ev.loc[m, "label_source_locator"] = r.reason
        ev.loc[m, "reviewer"] = r.verified_by
        ev.loc[m, "verified_date"] = r.verified_date

    bad = ev[ev.label_status.isin(VERIFIED) & ev.final_cause.isin(["", "unclassified"])]
    if len(bad):
        raise SystemExit(f"{len(bad)} verified events have no valid final cause, e.g. {bad.event_id.iloc[0]}")

    ev.to_csv(os.path.join(PROCESSED, "drift_events.csv"), index=False)
    ev[ev.is_drift_event].to_csv(os.path.join(PROCESSED, "event_inventory.csv"), index=False)
    de = ev[ev.is_drift_event]
    status = {
        "n_pairs": int(len(ev)), "n_drift_events": int(len(de)), "n_excluded": int((~ev.is_drift_event).sum()),
        "by_status": {k: int(v) for k, v in de.label_status.value_counts().items()},
        "by_review_level": {k: int(v) for k, v in de.review_level.value_counts().items()},
        "n_verified": int(de.label_status.isin(VERIFIED).sum()),
        "n_unverified": int((~de.label_status.isin(VERIFIED)).sum()),
        "n_final_unknown": int((de.final_cause == "unknown").sum()),
        "final_cause_counts": {k: int(v) for k, v in de[de.label_status.isin(VERIFIED)].final_cause.value_counts().items()},
        "decision_files_present": sorted(f for f in os.listdir(DEC)) if os.path.isdir(DEC) else [],
    }
    json.dump(status, open(os.path.join(PROCESSED, "label_status.json"), "w"), indent=1)
    print(json.dumps({k: status[k] for k in ["n_drift_events", "by_status", "n_verified", "n_unverified"]}))


if __name__ == "__main__":
    main()
