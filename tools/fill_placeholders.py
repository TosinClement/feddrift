#!/usr/bin/env python3
"""Replace registered external placeholders ({{NAME}}) in publishable text files once the identifier exists.

Usage:  python tools/fill_placeholders.py --set ZENODO_DOI=10.5281/zenodo.1234567 --set RELEASE_DATE=2026-10-20
        python tools/fill_placeholders.py --list        # show where each placeholder occurs
Only names listed in config/placeholders.json are accepted. Values are validated by simple format rules.
Also re-run code/12_build_docs.py --final afterwards, because README and the descriptor are generated
(the generator reads the values from config/release_identifiers.json, which this tool updates).
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMATS = {"ZENODO_DOI": r"10\.5281/zenodo\.\d+", "ZENODO_CONCEPT_DOI": r"10\.5281/zenodo\.\d+",
           "RELEASE_DATE": r"\d{4}-\d{2}-\d{2}", "GITHUB_REPO_URL": r"https://github\.com/[\w.-]+/[\w.-]+",
           "ARXIV_ID": r"\d{4}\.\d{4,5}(v\d+)?"}
SKIP = {".git", "dist", "evidence_cache", "alfred_cache", "_archive", "__pycache__"}


def files():
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for f in fs:
            if f.endswith((".md", ".cff", ".json", ".txt", ".csv", ".yml", ".yaml")):
                yield os.path.join(d, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    reg = json.load(open(os.path.join(ROOT, "config", "placeholders.json")))["placeholders"]
    if a.list:
        for p in files():
            t = open(p, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r"\{\{([A-Z0-9_]+)\}\}", t):
                print(f"{m.group(1):20s} {os.path.relpath(p, ROOT)}:{t.count(chr(10), 0, m.start()) + 1}")
        return
    vals = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        if k not in reg:
            raise SystemExit(f"{k} is not a registered placeholder")
        if not re.fullmatch(FORMATS[k], v):
            raise SystemExit(f"{k}={v} does not match the expected format {FORMATS[k]}")
        vals[k] = v
    idp = os.path.join(ROOT, "config", "release_identifiers.json")
    ids = json.load(open(idp)) if os.path.exists(idp) else {}
    ids.update(vals)
    json.dump(ids, open(idp, "w"), indent=1)
    n = 0
    for p in files():
        if p.endswith("placeholders.json"):
            continue
        t = open(p, encoding="utf-8").read()
        t2 = t
        for k, v in vals.items():
            t2 = t2.replace("{{" + k + "}}", v)
        if t2 != t:
            open(p, "w", encoding="utf-8").write(t2)
            n += 1
    print(f"filled {sorted(vals)} in {n} files; identifiers recorded in config/release_identifiers.json")


if __name__ == "__main__":
    main()
