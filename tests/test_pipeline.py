"""Tests for FedDrift's label mechanics and footprint computation (run: python -m pytest -q tests)."""
import importlib.util
import os
import shutil
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CODE = os.path.join(REPO, "code")
sys.path.insert(0, CODE)


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), os.path.join(CODE, name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_pair_stats_detects_rebase_and_depth():
    m = load("04_vintage_pairs.py")
    idx = pd.date_range("2000-01-01", periods=36, freq="MS").strftime("%Y-%m-%d")
    a = pd.Series(range(100, 136), index=idx, dtype=float)
    b = a * 2.0                                            # constant rescale: rebase
    r = m.pair_stats("X", "2003-01-15", "2003-02-15", a, b)
    assert r["n_revised"] == 36 and r["rebase_like"] and r["revision_depth_months"] == 37
    c = a.copy(); c.iloc[-2:] += 1.0                       # shallow routine revision
    r2 = m.pair_stats("X", "2003-01-15", "2003-02-15", a, c)
    assert r2["n_revised"] == 2 and not r2["rebase_like"] and r2["revision_depth_months"] == 3  # Feb-2003 vintage, earliest revised Nov-2002


def test_labels_apply_and_preserve_author_columns(tmp_path):
    for d in ["data/processed", "labels", "config"]:
        os.makedirs(tmp_path / d)
    shutil.copy(os.path.join(REPO, "data/processed/proposed_events.csv"), tmp_path / "data/processed")
    for f in ["rule_sheet.csv", "event_label_sheet.csv"]:
        shutil.copy(os.path.join(REPO, "labels", f), tmp_path / "labels")
    rs = pd.read_csv(tmp_path / "labels/rule_sheet.csv", dtype=str, keep_default_na=False)
    rs.loc[rs.rule_id == "R23_ROUTINE_M3", ["tosin_decision", "tosin_verified_date"]] = ["accept", "2026-10-03"]
    rs.to_csv(tmp_path / "labels/rule_sheet.csv", index=False)
    es = pd.read_csv(tmp_path / "labels/event_label_sheet.csv", dtype=str, keep_default_na=False)
    pid = es.pair_id.iloc[0]
    es.loc[0, ["final_cause", "verified_by", "verified_date"]] = ["annual_benchmark", "TEST", "2026-10-03"]
    es.to_csv(tmp_path / "labels/event_label_sheet.csv", index=False)
    env = dict(os.environ, FEDDRIFT_ROOT=str(tmp_path))
    subprocess.run([sys.executable, os.path.join(CODE, "08_apply_labels.py")], env=env, check=True)
    ev = pd.read_csv(tmp_path / "data/processed/drift_events.csv", keep_default_na=False)
    m3 = ev[(ev.proposed_rule == "R23_ROUTINE_M3") & (ev.is_drift_event.astype(str) == "True")]
    assert (m3.label_status == "rule_verified").all() and (m3.final_cause == "advance_to_revised").all()
    row = ev[ev.pair_id == pid].iloc[0]
    assert row.label_status == "individually_verified" and row.final_cause == "annual_benchmark"
    other = ev[(ev.is_drift_event.astype(str) == "True") & ~ev.proposed_rule.isin(["R23_ROUTINE_M3"]) & (ev.pair_id != pid)]
    assert (other.label_status == "unverified").all()


def test_label_sheet_merge_keeps_author_text():
    m = load("05_propose_labels.py")
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "s.csv")
        pd.DataFrame({"k": ["a", "b"], "x": [1, 2], "final_cause": ["annual_benchmark", ""]}).to_csv(p, index=False)
        new = pd.DataFrame({"k": ["a", "b"], "x": [9, 9]})
        out = m.merge_author(new, p, "k", ["final_cause"])
        assert out.set_index("k").final_cause["a"] == "annual_benchmark" and (out.x == 9).all()
