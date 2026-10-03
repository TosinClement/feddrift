#!/usr/bin/env python3
"""Import the label owner's decisions from the review workbook into labels/decisions/*.csv.

Usage:  python code/import_review.py labels/review/FedDrift_label_review.xlsx

Validation (the import refuses the whole file if any check fails):
  - every decision is one of the allowed values for its sheet
  - every decided row has verified_by and an ISO verified_date (YYYY-MM-DD)
  - final causes come from config/causes.csv (allowed_as_final = yes); 'set' requires final_cause
  - override event_ids exist in data/processed/proposed_events.csv
Rows left blank in the workbook keep any decision already present in labels/decisions/ (nothing is erased).
"""

import os
import re
import sys

import pandas as pd

from fd_common import CONFIG, PROCESSED, ROOT

DEC = os.path.join(ROOT, "labels", "decisions")
SPECS = {
    "Judgment calls": ("judgment_calls.csv", "decision_id", None),
    "Rules": ("rule_decisions.csv", "rule_id", {"approve", "reject"}),
    "Releases": ("release_decisions.csv", "release_cluster_id", {"approve", "set", "unknown"}),
}
KEEP = {
    "judgment_calls.csv": ["decision_id", "decision", "verified_by", "verified_date", "notes"],
    "rule_decisions.csv": ["rule_id", "decision", "verified_by", "verified_date", "notes"],
    "release_decisions.csv": ["release_cluster_id", "decision", "final_cause", "final_secondary_cause", "verified_by",
                              "verified_date", "notes"],
    "event_overrides.csv": ["event_id", "final_cause", "final_secondary_cause", "reason", "source_url", "verified_by",
                            "verified_date"],
}
JUDGMENT_OPTIONS = {"J1": {"keep_no_values", "ship_values"}, "J2": {"ship_derived", "reconstruct_only"},
                    "J3": {"withhold_full_file", "ship_full_file"}, "J4": {"review_per_release", "review_per_event"},
                    "J5": {"strong_or_moderate", "strong_only", "any"}}


def clean(df):
    return df.fillna("").astype(str).apply(lambda c: c.str.strip())


def merge(path, new, key):
    if os.path.exists(path):
        old = clean(pd.read_csv(path, dtype=str))
        old = old[~old[key].isin(new[key])]
        new = pd.concat([old, new], ignore_index=True)
    return new.sort_values(key)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    xl = sys.argv[1]
    causes = pd.read_csv(os.path.join(CONFIG, "causes.csv"))
    final = set(causes[causes.allowed_as_final == "yes"].cause)
    events = set(pd.read_csv(os.path.join(PROCESSED, "proposed_events.csv")).event_id)
    errors, out = [], {}
    for sheet, (fn, key, allowed) in SPECS.items():
        df = clean(pd.read_excel(xl, sheet_name=sheet, dtype=str))
        df = df[df.decision != ""]
        for r in df.itertuples():
            k = getattr(r, key)
            ok = JUDGMENT_OPTIONS.get(k, set()) if sheet == "Judgment calls" else allowed
            if r.decision not in ok:
                errors.append(f"{sheet} {k}: decision '{r.decision}' not in {sorted(ok)}")
            if not r.verified_by:
                errors.append(f"{sheet} {k}: verified_by is empty")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.verified_date.split(" ")[0]):
                errors.append(f"{sheet} {k}: verified_date '{r.verified_date}' is not YYYY-MM-DD")
            if sheet == "Releases":
                if r.decision == "set" and r.final_cause not in final:
                    errors.append(f"{sheet} {k}: 'set' needs final_cause from {sorted(final)}")
                if r.final_cause and r.final_cause not in final:
                    errors.append(f"{sheet} {k}: final_cause '{r.final_cause}' not allowed")
                if r.final_secondary_cause and r.final_secondary_cause not in final:
                    errors.append(f"{sheet} {k}: final_secondary_cause '{r.final_secondary_cause}' not allowed")
        df["verified_date"] = df.verified_date.str.split(" ").str[0]
        out[fn] = (df[KEEP[fn]], key)
    ov = clean(pd.read_excel(xl, sheet_name="Event overrides", dtype=str))
    ov = ov[ov.event_id != ""]
    for r in ov.itertuples():
        if r.event_id not in events:
            errors.append(f"override {r.event_id}: unknown event_id")
        if r.final_cause not in final:
            errors.append(f"override {r.event_id}: final_cause '{r.final_cause}' not allowed")
        if not r.verified_by or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.verified_date.split(" ")[0]):
            errors.append(f"override {r.event_id}: verified_by and verified_date (YYYY-MM-DD) required")
    ov["verified_date"] = ov.verified_date.str.split(" ").str[0]
    out["event_overrides.csv"] = (ov[KEEP["event_overrides.csv"]], "event_id")
    if errors:
        raise SystemExit("Import refused; nothing written:\n  " + "\n  ".join(errors))
    os.makedirs(DEC, exist_ok=True)
    for fn, (df, key) in out.items():
        merged = merge(os.path.join(DEC, fn), df, key)
        merged.to_csv(os.path.join(DEC, fn), index=False)
        print(f"{fn}: {len(df)} decisions imported ({len(merged)} total)")


if __name__ == "__main__":
    main()
