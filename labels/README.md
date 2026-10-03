# Labeling FedDrift: instructions for the label owner

**Label owner:** Tosin Clement. A label is verified only when the label owner has recorded a decision, with her name and date, in `labels/decisions/`. The machine proposal (`proposed_cause`) and Claude's evidence-based recommendation (`recommended_cause`, with a confidence grade) are inputs to that decision. They are never labels.

## What you review

| Level | Covers | Where | One decision applies to |
|---|---|---|---|
| Judgment calls | Project-level choices: licensing (J1–J3), review granularity (J4), evidence bar (J5) | *Judgment calls* sheet | The project |
| Rule | Routine events (advance → revised, PPI 4-month recalculation, TSI re-estimation) | *Rules* sheet | Every event the rule covers |
| Release | Non-routine events: annual benchmarks, seasonal recomputes, rebases, corrections, unclassified | *Releases* sheet | Every event in that agency release (same program, same date) |
| Override | Any single event you want to label differently from its rule or release | *Event overrides* sheet | That event |

The *Events* sheet lists every drift event together with the rule or release that governs it. The *Sources* sheet lists every agency document cited, with URL, publication date and SHA-256.

## How to decide

- **Rules:** read the condition, the agency quotes and the event counts, then spot-check a few events. Choose `approve` or `reject`. If you reject a rule, its events are not labeled and the release gate stays closed until they are relabeled.
- **Releases:**
  - `approve` uses `recommended_cause` (and `recommended_secondary_cause`).
  - `set` uses the `final_cause` you enter.
  - `unknown` records that the evidence does not establish a cause.

  Check the quote, the source and the *automated_check* column. "MATCH" means the month the agency says the revision starts equals the earliest revised observation in the data.
- Fill `verified_by` (your name) and `verified_date` (YYYY-MM-DD) on every row you decide. A row without them is ignored.

## Then

```
python code/import_review.py labels/review/FedDrift_label_review.xlsx
bash run_all.sh --from 08
```

The import validates every row and writes nothing if any row is invalid. Rows you leave blank keep any decision already recorded. Regenerating the review workbook (`code/07_build_review.py`) never touches `labels/decisions/`.
