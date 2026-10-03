#!/usr/bin/env python3
"""10 - Build the redistributable release archive and enforce the licensing protocol.

Excludes the ALFRED cache and the full BTS MTS file; refuses to package if any included file looks like it
carries ALFRED observation values (real-time period columns) or a FRED API key.

Usage:  python code/10_package.py [--version 0.1.0]
Output: dist/feddrift-<version>.tar.gz and dist/MANIFEST.sha256
"""

import argparse
import hashlib
import os
import re
import tarfile

from fd_common import ROOT

EXCLUDE_DIRS = {".git", "__pycache__", "dist", "alfred_cache", ".pytest_cache"}
EXCLUDE_FILES = [re.compile(r"data/raw/agency/[^/]+/bts/crem-w557\.csv$"), re.compile(r"\.orphaned\.csv$"),
                 re.compile(r"(^|/)\.env$"), re.compile(r"\.key$")]
FORBIDDEN = [(re.compile(rb'"realtime_start": ?"\d{4}-\d\d-\d\d", ?"realtime_end": ?"\d{4}-\d\d-\d\d", ?"date"'),
              "ALFRED real-time observation rows (JSON)"),
             (re.compile(rb"realtime_start,realtime_end,date,value"), "ALFRED real-time observation rows (CSV)"),
             (re.compile(rb"api_key=[0-9a-f]{32}"), "FRED API key")]
ALLOW_TEXT_MENTION = {"code/10_package.py"}   # this file names the patterns it forbids


def files():
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in EXCLUDE_DIRS]
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), ROOT)
            if not any(p.search(rel) for p in EXCLUDE_FILES):
                yield rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="0.1.0")
    a = ap.parse_args()
    inc = sorted(files())
    problems = []
    for rel in inc:
        b = open(os.path.join(ROOT, rel), "rb").read()
        for pat, what in FORBIDDEN:
            if pat.search(b) and not (what.startswith("ALFRED") and rel in ALLOW_TEXT_MENTION):
                problems.append(f"{rel}: {what}")
    if problems:
        raise SystemExit("Licensing protocol violation, not packaged:\n  " + "\n  ".join(problems))
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"feddrift-{a.version}.tar.gz")
    with tarfile.open(out, "w:gz") as t:
        for rel in inc:
            t.add(os.path.join(ROOT, rel), arcname=f"feddrift-{a.version}/{rel}")
    with open(os.path.join(ROOT, "dist", "MANIFEST.sha256"), "w") as m:
        for rel in inc:
            m.write(f"{hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()}  {rel}\n")
    print(f"packaged {len(inc)} files -> {os.path.relpath(out, ROOT)} ({os.path.getsize(out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
