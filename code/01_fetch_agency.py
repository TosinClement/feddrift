#!/usr/bin/env python3
"""01 - Fetch the agency "anchor vintage" for every panel series, straight from the publishing agency.

Sources (all U.S. government works, public domain, no key required):
  - Census Economic Indicators Time Series bulk files (MARTS, MRTS, M3 full report, MTIS)
      https://www.census.gov/econ_getzippedfile/?programCode=<PROGRAM>
  - BLS LABSTAT flat files for CPI (cu) and PPI (wp)
      https://download.bls.gov/pub/time.series/<survey>/<file>
  - BTS Monthly Transportation Statistics (Socrata dataset crem-w557)
      https://data.bts.gov/resource/crem-w557.csv

Each raw file is saved under data/raw/agency/<date>/ and logged to data/raw/PROVENANCE.txt.
These files are the redistributable part of FedDrift (see docs/LICENSING_PROTOCOL.md).

Usage:  python code/01_fetch_agency.py [--date YYYY-MM-DD]
"""

import argparse
import datetime as dt
import os

import pandas as pd

from fd_common import AGENCY_RAW, http_get, load_panel, log_provenance

CENSUS_URL = "https://www.census.gov/econ_getzippedfile/?programCode={program}"
BLS_URL = "https://download.bls.gov/pub/time.series/{survey}/{file}"
BTS_URL = "https://data.bts.gov/resource/{dataset}.csv"
BTS_META_URL = "https://data.bts.gov/api/views/{dataset}.json"

# BLS flat files that contain the panel's BLS series (verified by 02_build_anchor.py, which fails loudly
# if a panel series is not found in the listed files).
BLS_FILES = {
    "cu": ["cu.data.1.AllItems", "cu.data.2.Summaries", "cu.data.20.USCommoditiesServicesSpecial", "cu.series", "cu.footnote", "cu.txt"],
    "wp": ["wp.data.1.AllCommodities", "wp.data.22.FD-ID", "wp.series", "wp.footnote", "wp.txt"],
}
# BLS asks automated clients to identify themselves with a contact address in the User-Agent.
BLS_UA = "FedDrift/0.1 research pipeline clementtosin92@gmail.com"
# The Census site rejects some non-browser agents; this string identifies the project.
CENSUS_UA = "Mozilla/5.0 (compatible; FedDrift/0.1; +mailto:clementtosin92@gmail.com)"


def save(content, path, url, note):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    print(log_provenance(path, url, note))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="snapshot folder name")
    a = ap.parse_args()
    out = os.path.join(AGENCY_RAW, a.date)
    panel = load_panel()

    programs = sorted({r["anchor_program"] for r in panel if r["anchor_source"] == "census_eits"})
    for p in programs:
        url = CENSUS_URL.format(program=p)
        r = http_get(url, ua=CENSUS_UA, pause=3.0)
        if not r.content.startswith(b"PK"):
            raise SystemExit(f"Census {p}: expected a zip, got {r.headers.get('content-type')}")
        save(r.content, os.path.join(out, "census", f"{p}.zip"), url, f"Census EITS bulk file, program {p}")

    for survey, files in BLS_FILES.items():
        for fn in files:
            url = BLS_URL.format(survey=survey, file=fn)
            r = http_get(url, ua=BLS_UA, pause=2.0, timeout=300)
            save(r.content, os.path.join(out, "bls", fn if fn.endswith(".txt") else fn + ".txt"), url, f"BLS LABSTAT flat file {fn}")

    for ds in sorted({r["anchor_program"] for r in panel if r["anchor_source"] == "bts_socrata"}):
        url = BTS_URL.format(dataset=ds)
        r = http_get(url, params={"$limit": 50000, "$order": "date"})
        full = os.path.join(out, "bts", f"{ds}.csv")
        save(r.content, full, r.url, "BTS Monthly Transportation Statistics (Socrata)")
        fields = [p["anchor_bts_field"] for p in panel if p["anchor_program"] == ds]
        ext = os.path.join(out, "bts", f"{ds}.tsi_columns.csv")
        pd.read_csv(full, dtype=str)[["date"] + fields].to_csv(ext, index=False)
        print(log_provenance(ext, f"derived: columns date, {', '.join(fields)} of {ds}.csv (logged above)",
                             "BTS-produced TSI columns extracted from the withheld full MTS file; redistributable extract"))
        murl = BTS_META_URL.format(dataset=ds)
        m = http_get(murl)
        save(m.content, os.path.join(out, "bts", f"{ds}.metadata.json"), murl,
             "Socrata metadata: license, attribution, per-column source notes")


if __name__ == "__main__":
    main()
