# Labeling FedDrift: instructions for the label owner

**Label owner:** Tosin Clement. Every final label in FedDrift is a ruling by the label owner, checked against the agency's published methodology or release notes. The rule engine (`code/05_propose_labels.py`) only proposes labels. The release gate refuses to pass while any drift event in `data/processed/drift_events.csv` has `label_status = unverified`.

## Step 1: rule-level decisions (`rule_sheet.csv`, rows with `label_level = rule`)

These rules cover the routine events: thousands of monthly releases that follow a documented schedule. For each rule:

1. Read `condition` and `rationale`. If `candidate_source_url` is filled, open it. Claude found these sources and has not verified them.
2. Find the agency statement that establishes the rule. Methodology page, technical notes, or release text all count.
3. Fill in `tosin_decision` (`accept`, `modify` or `reject`), `tosin_source_url`, `tosin_source_quote` (the exact sentence), and `tosin_verified_date` (YYYY-MM-DD).
4. If you choose `modify`, change the rule in `config/revision_rules.csv` (and in `code/05` if the condition logic changes), then re-run steps 05–09. Your typed columns are preserved on re-run.

Accepting a rule labels every event that rule covers. Spot-check a few by hand before accepting: `n_pairs` tells you how many events depend on your decision.

## Step 2: individual events (`event_label_sheet.csv`)

This sheet covers every annual benchmark, seasonal-factor recompute, rebase, agency-documented event, and every unclassified event. For each row:

1. Find the agency release or notice for `vintage_next`. Use the agency's historical releases, the FRED/ALFRED series notes, or the agency's revision announcements.
2. Fill in `final_cause` with one value from the taxonomy in `docs/CODEBOOK.md`. `unclassified` is not allowed as a final label. If no source can be found, use `other_major` and say so in `notes`.
3. Fill in `agency_source_url`, `agency_source_quote`, `verified_by` (your name) and `verified_date`.
4. Fill in `final_secondary_cause` if one release carries two causes, for example a benchmark together with a new sample.

Rows are not applied until `final_cause`, `verified_by` and `verified_date` are all filled.

## Step 3: apply and rebuild

```
python code/08_apply_labels.py      # applies your labels; prints label-status counts
python code/07_benchmark.py         # T1 scores appear once labels exist
python code/09_figures_stats.py     # figures and stats.json reflect final labels
```

## Ground rules

- Never copy a proposed label without checking it against a source. The proposals encode patterns in the data, and a pattern is not a cause.
- If the agency's documented date and the ALFRED vintage date disagree, record both in `notes` (example: M3 benchmark 2025-05-16 vs. ALFRED vintage 2025-05-27).
- Keep a copy of every source page you rely on (PDF or web archive). Agency pages move.
