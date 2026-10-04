#!/usr/bin/env python3
"""FedDrift release gate. Exit 0 = clear for the requested stage; exit 1 = blocked (every blocker is listed).

Stages
  pre-deposit  everything is final except the registered external identifiers in config/placeholders.json
               (Zenodo DOI, release date, GitHub URL, arXiv id), which cannot exist before deposit.
  final        nothing may remain: no draft marker and no placeholder of any kind.

Checks
  1. Secrets anywhere in the tree (tokens, keys, credential files) - always blocking.
  2. Draft markers in publishable files (README, CITATION, docs/, paper/, data/processed/, labels/README.md,
     evidence/): DRAFT, [VERIFY], [ASK], [TARGET], TODO, FIXME, bracketed placeholders, unregistered {{...}}.
  3. Registered placeholders {{NAME}}: allowed at pre-deposit, blocking at final.
  4. Every drift event carries a verified label (data/processed/label_status.json).
  5. QA has no FAIL and no BLOCKING check (data/processed/qa.json).
  6. Figures and documents were generated in final mode (paper/stats.json: final_mode = true).
The human half of the gate - the label owner's own review - is recorded in labels/decisions/ and checked by 4.

Usage:  python code/publish_gate.py <project_dir> --stage pre-deposit|final
"""

import argparse
import json
import os
import re
import sys

TEXT_EXT = {".md", ".txt", ".html", ".csv", ".json", ".cff", ".yml", ".yaml", ".bib", ".tex"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "dist", "evidence_cache", "alfred_cache", "_archive",
             ".pytest_cache", "alfred_cache_run1"}
PUBLISHABLE = ("README.md", "CITATION.cff", "CHANGELOG.md", "LICENSE-DATA.md", "docs/", "paper/", "data/processed/",
               "labels/README.md", "evidence/", "zenodo/", "release/",
               "config/", "labels/")  # config/ and labels/ added 2026-10-03: they ship in the archive
DRAFT_PATTERNS = [
    (re.compile(r"\bDRAFT\b"), "DRAFT marker"),
    (re.compile(r"\[VERIFY[^\]]*\]"), "[VERIFY] tag"),
    (re.compile(r"\[ASK[^\]]*\]"), "[ASK] tag"),
    (re.compile(r"\[TARGET\]"), "[TARGET] tag"),
    (re.compile(r"\b(TODO|FIXME|TBD)\b"), "TODO/FIXME/TBD"),
    (re.compile(r"\[(insert|DOI|journal|tracking number|repository URL|date|name)[^\]]*\]", re.I), "bracketed placeholder"),
]
SECRETS = [
    (re.compile(r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"), "GitHub token"),
    (re.compile(r"api_key=[0-9a-f]{32}"), "FRED API key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
]
SELF_PATTERN_FILES = {"code/publish_gate.py", "code/10_qa.py", "code/13_package.py", "tests/test_pipeline.py"}
PH = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--stage", choices=["pre-deposit", "final"], required=True)
    a = ap.parse_args()
    root = os.path.abspath(a.project_dir)
    registered = json.load(open(os.path.join(root, "config", "placeholders.json")))["placeholders"]
    blockers, noted = [], []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), root)
            if f == ".env" or f.endswith((".pem", ".key")):
                blockers.append(f"credential file present: {rel}")
                continue
            try:
                text = open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if rel not in SELF_PATTERN_FILES:
                for p, lab in SECRETS:
                    if p.search(text):
                        blockers.append(f"{lab}: {rel}")
            if os.path.splitext(f)[1].lower() not in TEXT_EXT or not rel.startswith(PUBLISHABLE):
                continue
            for p, lab in DRAFT_PATTERNS:
                for m in p.finditer(text):
                    blockers.append(f"{lab}: {rel}:{text.count(chr(10), 0, m.start()) + 1}")
                    break
            for m in PH.finditer(text):
                name = m.group(1)
                line = text.count("\n", 0, m.start()) + 1
                if name not in registered:
                    blockers.append(f"unregistered placeholder {{{{{name}}}}}: {rel}:{line}")
                elif a.stage == "final":
                    blockers.append(f"placeholder {{{{{name}}}}} must be filled ({registered[name]['final_action']}): {rel}:{line}")
                else:
                    noted.append(f"{name} @ {rel}:{line}")
    sp = os.path.join(root, "data", "processed", "label_status.json")
    st = json.load(open(sp)) if os.path.exists(sp) else {"n_unverified": "missing"}
    if st.get("n_unverified") != 0:
        blockers.append(f"labels: {st.get('n_unverified')} drift events without a verified label")
    qp = os.path.join(root, "data", "processed", "qa.json")
    qa = json.load(open(qp)) if os.path.exists(qp) else {"checks": [{"id": "QA", "status": "FAIL"}]}
    bad = [f"{c['id']}={c['status']}" for c in qa["checks"] if c["status"] in ("FAIL", "BLOCKING")]
    if bad:
        blockers.append(f"QA not clean: {', '.join(bad)}")
    stp = os.path.join(root, "paper", "stats.json")
    if not (os.path.exists(stp) and json.load(open(stp)).get("final_mode") is True):
        blockers.append("figures/documents not generated in final mode (run 11 and 12 with --final)")
    for n in sorted(set(noted)):
        print(f"allowed at pre-deposit: {n}")
    for b in blockers:
        print(f"BLOCKED  {b}")
    if blockers:
        print(f"gate ({a.stage}): BLOCKED - {len(blockers)} blocker(s)")
        sys.exit(1)
    print(f"gate ({a.stage}): CLEAR")


if __name__ == "__main__":
    main()
