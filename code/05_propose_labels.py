#!/usr/bin/env python3
"""05 - Propose a cause for every vintage pair with the rule engine, and write the author's label sheets.

The rule engine only PROPOSES. Final labels are the author's: see labels/README.md.

Inputs : data/processed/vintage_pairs.csv, config/revision_rules.csv, config/agency_documented_events.csv
Outputs: data/processed/proposed_events.csv     every vintage pair + proposed cause + rule id
         labels/rule_sheet.csv                  one row per rule, for rule-level verification
         labels/event_label_sheet.csv           one row per event that needs an individual label

Re-running never overwrites anything the author has typed into the label sheets: author columns are
carried over by key (rule_id / pair_id); only the machine columns are refreshed.
"""

import os

import pandas as pd

from fd_common import CONFIG, PROCESSED, ROOT, load_panel

LABELS = os.path.join(ROOT, "labels")
CAUSES = ["advance_to_revised", "annual_benchmark", "seasonal_factor_recompute", "sample_redesign",
          "rebase_or_definition", "routine_reestimation", "correction", "other_major", "unclassified"]
RULE_AUTHOR_COLS = ["tosin_decision", "tosin_source_url", "tosin_source_quote", "tosin_verified_date", "tosin_notes"]
EVENT_AUTHOR_COLS = ["final_cause", "final_secondary_cause", "agency_source_url", "agency_source_quote",
                     "verified_by", "verified_date", "notes"]
INDIVIDUAL_RULES = {"R02_REBASE", "R10_CPI_SA_5Y", "R11_CPI_SA_PRE1995", "R12_PPI_SA_5Y",
                    "R30_CENSUS_ANNUAL", "R90_UNCLASSIFIED"}


def series_list(cell):
    return None if cell == "ALL" else set(cell.split(";"))


def routine_window(rules, sid):
    """The routine depth limit for a series = the max depth in its R2x routine rule condition."""
    for _, r in rules.iterrows():
        if r.rule_id.startswith("R2") and sid in (series_list(r.series) or set()) and "<=" in r.condition:
            return int(r.condition.split("<=")[1].strip())
    return 0


def propose(row, rules, windows):
    sid, d, m, y = row.series_id, row.revision_depth_months, row.vintage_month, row.vintage_year
    for _, r in rules.sort_values("priority").iterrows():
        applies = series_list(r.series)
        if applies is not None and sid not in applies:
            continue
        rid = r.rule_id
        if rid == "R00_EXTENSION" and row.n_revised == 0 and row.n_dropped_obs == 0:
            return rid
        if rid == "R01_ARCHIVE_WINDOW" and row.n_revised == 0 and row.n_dropped_obs > 0 \
                and row.n_obs_next == row.n_obs_prev:
            return rid
        if row.n_revised == 0:
            continue
        if rid == "R02_REBASE" and bool(row.rebase_like):
            return rid
        if rid == "R10_CPI_SA_5Y" and m == 2 and y >= 1995 and 50 <= d <= 62:
            return rid
        if rid == "R11_CPI_SA_PRE1995" and m == 2 and y < 1995 and 14 <= d <= 21:
            return rid
        if rid == "R12_PPI_SA_5Y" and m == 2 and 50 <= d <= 62:
            return rid
        if rid.startswith("R2") and rid != "R26_ROUTINE_TSI" and d <= windows[sid]:
            return rid
        if rid == "R26_ROUTINE_TSI":
            return rid
        if rid == "R30_CENSUS_ANNUAL" and d > windows[sid] and 3 <= m <= 7:
            return rid
        if rid == "R90_UNCLASSIFIED":
            return rid
    return "R90_UNCLASSIFIED"


def merge_author(new, path, key, author_cols):
    """Keep whatever the author already typed; refresh everything else."""
    if os.path.exists(path):
        old = pd.read_csv(path, dtype=str, keep_default_na=False)
        keep = old[[key] + [c for c in author_cols if c in old.columns]]
        new = new.drop(columns=[c for c in author_cols if c in new.columns]).merge(keep, on=key, how="left")
        lost = set(old[key]) - set(new[key])
        if lost:
            orphan = old[old[key].isin(lost)]
            orphan.to_csv(path.replace(".csv", ".orphaned.csv"), index=False)
            print(f"WARNING: {len(lost)} previously labeled rows no longer exist; saved to *.orphaned.csv")
    for c in author_cols:
        if c not in new.columns:
            new[c] = ""
    return new.fillna("")


def main():
    pairs = pd.read_csv(os.path.join(PROCESSED, "vintage_pairs.csv"))
    rules = pd.read_csv(os.path.join(CONFIG, "revision_rules.csv"), dtype=str).fillna("")
    rules["priority"] = rules.priority.astype(int)
    docs = pd.read_csv(os.path.join(CONFIG, "agency_documented_events.csv"), dtype=str).fillna("")
    panel = {p["series_id"]: p for p in load_panel()}
    windows = {sid: routine_window(rules, sid) for sid in panel}

    pairs["proposed_rule"] = pairs.apply(lambda r: propose(r, rules, windows), axis=1)
    cause = dict(zip(rules.rule_id, rules.cause))
    pairs["proposed_cause"] = pairs.proposed_rule.map(cause)
    pairs["is_drift_event"] = ~pairs.proposed_rule.isin(["R00_EXTENSION", "R01_ARCHIVE_WINDOW"])
    pairs["routine_window_months"] = pairs.series_id.map(windows)

    # attach agency-documented events: first non-routine revising vintage
    # on/after the release date within 14 days (else the first revising one)
    pairs["doc_event_key"], pairs["proposed_secondary_cause"] = "", ""
    for _, e in docs.iterrows():
        progs = set(e.programs.split(";"))
        rel = pd.Timestamp(e.release_date)
        for sid, p in panel.items():
            if p["program"] not in progs:
                continue
            c = pairs[(pairs.series_id == sid) & (pairs.n_revised > 0)
                      & (pd.to_datetime(pairs.vintage_next) >= rel)
                      & (pd.to_datetime(pairs.vintage_next) <= rel + pd.Timedelta(days=14))]
            if len(c):
                deep = c[~c.proposed_rule.str.startswith("R2")]   # prefer a non-routine vintage if one exists
                i = (deep if len(deep) else c).index[0]
                pairs.loc[i, "doc_event_key"] = ";".join(filter(None, [pairs.loc[i, "doc_event_key"], e.event_key]))
                if e.secondary_cause:
                    pairs.loc[i, "proposed_secondary_cause"] = ";".join(
                        filter(None, [pairs.loc[i, "proposed_secondary_cause"], e.secondary_cause]))

    pairs.to_csv(os.path.join(PROCESSED, "proposed_events.csv"), index=False)

    # rule sheet
    os.makedirs(LABELS, exist_ok=True)
    cov = pairs.groupby("proposed_rule").agg(n_pairs=("pair_id", "size"),
                                             n_series=("series_id", "nunique")).reset_index()
    rs = rules.merge(cov, left_on="rule_id", right_on="proposed_rule", how="left").drop(columns="proposed_rule")
    rs["n_pairs"] = rs.n_pairs.fillna(0).astype(int)
    rs["n_series"] = rs.n_series.fillna(0).astype(int)
    rs["label_level"] = rs.rule_id.map(lambda r: "individual" if r in INDIVIDUAL_RULES else "rule")
    rs = merge_author(rs, os.path.join(LABELS, "rule_sheet.csv"), "rule_id", RULE_AUTHOR_COLS)
    rs.to_csv(os.path.join(LABELS, "rule_sheet.csv"), index=False)

    # individual event sheet: every event under an individual-label rule, plus every doc-matched event
    ind = pairs[pairs.proposed_rule.isin(INDIVIDUAL_RULES) | (pairs.doc_event_key != "")].copy()
    cols = ["pair_id", "series_id", "vintage_prev", "vintage_next", "n_revised", "earliest_revised_obs",
            "latest_revised_obs", "revision_depth_months", "mean_abs_pct_revision", "max_abs_pct_revision",
            "net_pct_revision", "ks_growth_window", "rebase_like", "proposed_rule", "proposed_cause",
            "proposed_secondary_cause", "doc_event_key"]
    ind = merge_author(ind[cols], os.path.join(LABELS, "event_label_sheet.csv"), "pair_id", EVENT_AUTHOR_COLS)
    ind.to_csv(os.path.join(LABELS, "event_label_sheet.csv"), index=False)

    print(pairs.groupby(["proposed_rule"]).size().to_string())
    print(f"drift events: {int(pairs.is_drift_event.sum())} of {len(pairs)} pairs; "
          f"individual labels needed: {len(ind)}; rule-level decisions needed: {(rs.label_level == 'rule').sum()}")
    print("doc-matched:", pairs[pairs.doc_event_key != ""][["series_id", "vintage_next", "doc_event_key",
                                                              "proposed_cause"]].to_string())


if __name__ == "__main__":
    main()
