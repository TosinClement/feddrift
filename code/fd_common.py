"""Shared helpers for the FedDrift pipeline: paths, polite HTTP, provenance logging."""

import csv
import datetime as dt
import hashlib
import os
import time

import requests

ROOT = os.environ.get("FEDDRIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")
RAW = os.path.join(ROOT, "data", "raw")
AGENCY_RAW = os.path.join(RAW, "agency")
ALFRED_CACHE = os.path.join(RAW, "alfred_cache")   # never redistributed (see docs/LICENSING_PROTOCOL.md)
MANIFESTS = os.path.join(ROOT, "data", "manifests")
PROCESSED = os.path.join(ROOT, "data", "processed")
PAPER = os.path.join(ROOT, "paper")
FIGURES = os.path.join(PAPER, "figures")
PROVENANCE_LOG = os.path.join(RAW, "PROVENANCE.txt")

USER_AGENT = "FedDrift/0.1 research pipeline (contact: clementtosin92@gmail.com)"


def load_snapshot():
    """The pinned snapshot every published number is computed from (config/snapshot.json)."""
    import json
    with open(os.path.join(CONFIG, "snapshot.json"), encoding="utf-8") as f:
        return json.load(f)


def load_panel():
    with open(os.path.join(CONFIG, "panel.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def log_provenance(path, url, note="", redact=None, log=None):
    """Append one fetch record. `redact` is a secret string to strip from the URL (API keys)."""
    if redact:
        url = url.replace(redact, "<FRED_API_KEY>")
    line = " | ".join([
        dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        os.path.relpath(path, ROOT),
        f"{os.path.getsize(path)} bytes",
        f"sha256:{sha256_file(path)}",
        url,
        note,
    ]).rstrip(" |")
    log = log or PROVENANCE_LOG
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def http_get(url, params=None, ua=USER_AGENT, retries=4, pause=1.0, timeout=120):
    """GET with a descriptive User-Agent, retry with backoff, and a polite pause after each call."""
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": ua}, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code} for {url}")
                time.sleep(pause * (2 ** (attempt + 1)))
                continue
            if 400 <= r.status_code < 500:
                raise SystemExit(f"HTTP {r.status_code} (not retried) for {url}")
            time.sleep(pause)
            return r
        except requests.RequestException as e:  # network errors: back off and retry
            last = e
            time.sleep(pause * (2 ** (attempt + 1)))
    raise RuntimeError(f"GET failed after {retries} attempts: {url}: {last}")
