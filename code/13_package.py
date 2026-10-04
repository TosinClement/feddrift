#!/usr/bin/env python3
"""13 - Build the release archive and enforce the licensing protocol and release-gate conditions.

Modes
  --draft    build dist/feddrift-<version>-DRAFT.tar.gz for review. Content rules are enforced; label coverage
             and placeholders are reported but do not block. The archive name says DRAFT.
  --release  build dist/feddrift-<version>.tar.gz. Refuses unless ALL of the following hold:
               * content rules pass (below)
               * every drift event carries a verified label (data/processed/label_status.json)
               * QA has no FAIL (data/processed/qa.json)
               * code/publish_gate.py --stage final passes (no draft markers or placeholders remain)

Content rules (both modes): no ALFRED real-time observation rows (JSON or CSV form), no FRED API key, no
GitHub token, no credential files, no ALFRED cache, no evidence cache, no withheld full BTS MTS file.

Writes dist/MANIFEST.sha256 (one line per archived file) next to the archive.
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile

from fd_common import PROCESSED, ROOT

EXCLUDE_DIRS = {".git", "__pycache__", "dist", "alfred_cache", "alfred_cache_run1", "evidence_cache", ".pytest_cache",
                "_archive", ".venv", "venv"}
EXCLUDE_FILES = [re.compile(r"data/raw/agency/[^/]+/bts/crem-w557\.csv$"), re.compile(r"\.orphaned\.csv$"),
                 re.compile(r"(^|/)\.env$"), re.compile(r"\.(key|pem)$"), re.compile(r"(^|/)\.DS_Store$")]
FORBIDDEN = [(re.compile(rb'"realtime_start": ?"\d{4}-\d\d-\d\d", ?"realtime_end": ?"\d{4}-\d\d-\d\d", ?"date"'),
              "ALFRED real-time observation rows (JSON)"),
             (re.compile(rb"realtime_start,realtime_end,date,value"), "ALFRED real-time observation rows (CSV)"),
             (re.compile(rb"api_key=[0-9a-f]{32}"), "FRED API key"),
             (re.compile(rb"github_pat_[A-Za-z0-9_]{30,}|ghp_[A-Za-z0-9]{30,}"), "GitHub token"),
             (re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key")]
SELF = {"code/13_package.py", "code/10_qa.py", "code/publish_gate.py", "tests/test_pipeline.py"}


def included_files():
    out = []
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE_DIRS)
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(d, f), ROOT)
            if not any(p.search(rel) for p in EXCLUDE_FILES):
                out.append(rel)
    return out


def content_problems():
    inc = included_files()
    probs = []
    for rel in inc:
        if rel in SELF:
            continue
        b = open(os.path.join(ROOT, rel), "rb").read()
        for pat, what in FORBIDDEN:
            if pat.search(b):
                probs.append(f"{rel}: {what}")
    return inc, probs


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--draft", action="store_true")
    g.add_argument("--release", action="store_true")
    ap.add_argument("--version", default="0.1.0")
    a = ap.parse_args()
    inc, probs = content_problems()
    blockers = list(probs)
    st = json.load(open(os.path.join(PROCESSED, "label_status.json")))
    qa = json.load(open(os.path.join(PROCESSED, "qa.json")))
    fails = [c["id"] for c in qa["checks"] if c["status"] == "FAIL"]
    if fails:
        blockers.append(f"QA has FAIL checks: {fails}")
    gate_msgs = []
    if st["n_unverified"]:
        gate_msgs.append(f"{st['n_unverified']} of {st['n_drift_events']} drift events lack a verified label")
    gate = subprocess.run([sys.executable, os.path.join(ROOT, "code", "publish_gate.py"), ROOT, "--stage", "final"],
                          capture_output=True, text=True)
    if gate.returncode != 0:
        gate_msgs.append("publish_gate --stage final: " + gate.stdout.strip().splitlines()[-1])
    if a.release:
        blockers += gate_msgs
    if blockers:
        raise SystemExit("Packaging refused:\n  " + "\n  ".join(blockers))
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    name = f"feddrift-{a.version}" + ("-DRAFT" if a.draft else "")
    out = os.path.join(ROOT, "dist", f"{name}.tar.gz")
    # gzip header mtime fixed at 0 so the archive is byte-reproducible (fixed 2026-10-03; tarfile's "w:gz" stamps the
    # current time into the gzip header)
    with open(out, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, \
            tarfile.open(fileobj=gz, mode="w") as t:
        for rel in inc:
            info = t.gettarinfo(os.path.join(ROOT, rel), arcname=f"{name}/{rel}")
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""   # reproducible archive
            with open(os.path.join(ROOT, rel), "rb") as fh:
                t.addfile(info, fh)
    with open(os.path.join(ROOT, "dist", f"{name}.MANIFEST.sha256"), "w") as m:
        for rel in inc:
            m.write(f"{hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()}  {rel}\n")
    print(f"packaged {len(inc)} files -> dist/{name}.tar.gz ({os.path.getsize(out) / 1e6:.1f} MB)")
    if gate_msgs:
        print("DRAFT only - release gate not met:\n  " + "\n  ".join(gate_msgs))


if __name__ == "__main__":
    main()
