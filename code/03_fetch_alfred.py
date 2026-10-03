#!/usr/bin/env python3
"""03 - Fetch the full real-time (ALFRED) revision history of every panel series via the FRED API.

Requires a free FRED API key in the environment variable FRED_API_KEY
(https://fredaccount.stlouisfed.org/apikeys). The key is never written to disk by this script;
it is redacted from every logged URL.

Writes
  data/raw/alfred_cache/<SERIES>.observations.json   full real-time observations  (NOT redistributed)
  data/raw/alfred_cache/<SERIES>.series.json          series metadata              (NOT redistributed)
  data/manifests/<SERIES>.vintages.csv                one row per vintage: date, n_obs, content hash
  data/manifests/alfred_manifest.json                 per-series metadata, copyright tags, cache hashes

The manifests contain no observation values. With them and this script, anyone holding a FRED key can
rebuild the identical vintage history and confirm it byte-for-byte against the published hashes
(see code/verify_reconstruction.py and docs/LICENSING_PROTOCOL.md).

Usage:  FRED_API_KEY=... python code/03_fetch_alfred.py [--series RSAFS CPIAUCSL ...]
"""

import argparse
import datetime as dt
import hashlib
import json
import os

import pandas as pd

from fd_common import ALFRED_CACHE, MANIFESTS, http_get, load_panel, log_provenance

API = "https://api.stlouisfed.org/fred/"
EARLIEST, LATEST = "1776-07-04", "9999-12-31"
OBS_START = "1947-01-01"          # FedDrift observation window starts January 1947
PAGE = 100000


def fred(endpoint, key, **params):
    params.update(api_key=key, file_type="json")
    r = http_get(API + endpoint, params=params, pause=0.6)
    return r


def vintage_hash(dates, values):
    """Canonical content hash of one vintage: 'YYYY-MM-DD,value\\n' lines sorted by date."""
    s = "".join(f"{d},{v}\n" for d, v in sorted(zip(dates, values)))
    return hashlib.sha256(s.encode()).hexdigest()


def reconstruct(obs):
    """Real-time observation rows -> {vintage_date: (dates, values)} for every vintage date."""
    df = pd.DataFrame(obs)
    df = df[df["value"] != "."]
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", nargs="*")
    a = ap.parse_args()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise SystemExit("Set FRED_API_KEY (free: https://fredaccount.stlouisfed.org/apikeys)")
    os.makedirs(ALFRED_CACHE, exist_ok=True)
    os.makedirs(MANIFESTS, exist_ok=True)
    panel = [p for p in load_panel() if not a.series or p["series_id"] in a.series]
    mpath = os.path.join(MANIFESTS, "alfred_manifest.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {"series": {}}

    for p in panel:
        sid = p["series_id"]
        # 1. metadata and copyright tags
        r = fred("series", key, series_id=sid)
        meta = r.json()["seriess"][0]
        tags = fred("series/tags", key, series_id=sid).json()["tags"]
        cc_tags = [t["name"] for t in tags if t.get("group_id") == "cc"]
        spath = os.path.join(ALFRED_CACHE, f"{sid}.series.json")
        json.dump({"series": meta, "tags": tags}, open(spath, "w"), indent=1)
        log_provenance(spath, r.url, f"FRED series metadata + tags for {sid}", redact=key)

        # 2. vintage dates
        vd = []
        off = 0
        while True:
            j = fred("series/vintagedates", key, series_id=sid, realtime_start=EARLIEST,
                     realtime_end=LATEST, limit=10000, offset=off).json()
            vd += j["vintage_dates"]
            off += len(j["vintage_dates"])
            if off >= j["count"] or not j["vintage_dates"]:
                break

        # 3. full real-time observations (output_type=1: one row per value per real-time period)
        obs, off, first_url = [], 0, None
        while True:
            r = fred("series/observations", key, series_id=sid, realtime_start=EARLIEST,
                     realtime_end=LATEST, observation_start=OBS_START, output_type=1,
                     limit=PAGE, offset=off, sort_order="asc")
            first_url = first_url or r.url
            j = r.json()
            obs += j["observations"]
            off += len(j["observations"])
            if off >= j["count"] or not j["observations"]:
                break
        opath = os.path.join(ALFRED_CACHE, f"{sid}.observations.json")
        json.dump({"series_id": sid, "vintage_dates": vd, "observations": obs}, open(opath, "w"))
        log_provenance(opath, first_url, f"ALFRED real-time observations {sid}: {len(obs)} rows, "
                       f"{len(vd)} vintages (cache only; not redistributed)", redact=key)

        # 4. per-vintage manifest: number of observations and content hash of each vintage
        df = pd.DataFrame(obs)
        df = df[df["value"] != "."]
        rows = []
        for v in vd:
            live = df[(df.realtime_start <= v) & (df.realtime_end >= v)]
            rows.append({"series_id": sid, "vintage_date": v, "n_obs": len(live),
                         "first_obs": live.date.min() if len(live) else "",
                         "last_obs": live.date.max() if len(live) else "",
                         "vintage_sha256": vintage_hash(live.date.tolist(), live.value.tolist())})
        pd.DataFrame(rows).to_csv(os.path.join(MANIFESTS, f"{sid}.vintages.csv"), index=False)

        manifest["series"][sid] = {
            "title": meta["title"], "units": meta["units"],
            "seasonal_adjustment": meta["seasonal_adjustment_short"],
            "frequency": meta["frequency_short"], "observation_start": meta["observation_start"],
            "fred_last_updated": meta["last_updated"], "copyright_tags": cc_tags,
            "n_vintages": len(vd), "first_vintage": vd[0] if vd else None,
            "last_vintage": vd[-1] if vd else None, "n_realtime_rows": len(obs),
            "cache_sha256": hashlib.sha256(open(opath, "rb").read()).hexdigest(),
            "fetched_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "request": {"endpoint": "fred/series/observations", "realtime_start": EARLIEST,
                        "realtime_end": LATEST, "observation_start": OBS_START, "output_type": 1},
        }
        json.dump(manifest, open(mpath, "w"), indent=1, sort_keys=True)
        print(f"{sid:16s} vintages={len(vd):4d} ({vd[0]}..{vd[-1]})  rows={len(obs):7d}  cc={cc_tags}")


if __name__ == "__main__":
    main()
