#!/usr/bin/env python3
"""02 - Parse the agency files fetched by 01 into one long table: the agency anchor vintage.

Output: data/processed/anchor_vintage.csv
  series_id, obs_date (YYYY-MM-01), value, anchor_source, anchor_file, anchor_file_sha256, snapshot_date

Fails loudly if any panel series cannot be located in its agency file.
Usage:  python code/02_build_anchor.py [--date YYYY-MM-DD]   (defaults to the newest snapshot)
"""

import argparse
import io
import os
import zipfile

import pandas as pd

from fd_common import AGENCY_RAW, PROCESSED, ROOT, load_panel, sha256_file

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def parse_census_mf(zpath):
    """Census EITS '-mf.csv' files: sections separated by blank lines, each headed by a title line."""
    with zipfile.ZipFile(zpath) as z:
        name = [n for n in z.namelist() if n.endswith("-mf.csv")][0]
        text = z.read(name).decode("utf-8", errors="replace")
    sections, title, buf = {}, None, []
    for line in text.splitlines():
        s = line.strip()
        if title is None:
            if s:
                title = s
            continue
        if s == "" and buf:
            sections[title] = buf
            title, buf = None, []
        elif s:
            buf.append(line)
    if title and buf:
        sections[title] = buf
    def table(key):
        return pd.read_csv(io.StringIO("\n".join(sections[key])))
    cats, dts, pers, data = table("CATEGORIES"), table("DATA TYPES"), table("TIME PERIODS"), table("DATA")
    updated = " ".join(sections.get("DATA UPDATED ON", [""])).strip()
    pers["obs_date"] = pers["per_name"].map(
        lambda p: f"{p.split('-')[1]}-{MONTHS[p.split('-')[0]]:02d}-01")
    df = (data.merge(cats[["cat_idx", "cat_code"]], on="cat_idx")
              .merge(dts[["dt_idx", "dt_code"]], on="dt_idx")
              .merge(pers[["per_idx", "obs_date"]], on="per_idx"))
    if "et_idx" in df.columns:
        df = df[df["et_idx"] == 0]          # estimates only; et_idx>0 rows are sampling-error measures
    return df, updated


def parse_bls(paths):
    frames = []
    for p in paths:
        d = pd.read_csv(p, sep="\t", dtype=str)
        d.columns = [c.strip() for c in d.columns]
        d = d.apply(lambda c: c.str.strip())
        d["_file"] = p
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d = d[d["period"].str.match(r"M(0[1-9]|1[0-2])$")]      # monthly only; drops M13 annual averages
    d["obs_date"] = d["year"] + "-" + d["period"].str[1:] + "-01"
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    snap = a.date or sorted(os.listdir(AGENCY_RAW))[-1]
    base = os.path.join(AGENCY_RAW, snap)
    panel = load_panel()
    rows = []

    census_cache = {}
    bls_cache = {}
    for s in panel:
        sid, src = s["series_id"], s["anchor_source"]
        if src == "census_eits":
            prog = s["anchor_program"]
            zpath = os.path.join(base, "census", f"{prog}.zip")
            if prog not in census_cache:
                census_cache[prog] = parse_census_mf(zpath)
            df, updated = census_cache[prog]
            sel = df[(df.cat_code == s["anchor_category"]) & (df.dt_code == s["anchor_datatype"])
                     & (df.is_adj == int(s["anchor_is_adj"]))]
            if "geo_idx" in sel.columns:
                sel = sel[sel.geo_idx == 1]
            out = pd.DataFrame({"obs_date": sel.obs_date, "value": pd.to_numeric(sel.val, errors="coerce")})
            fpath, note = zpath, f"Census {prog} {s['anchor_category']}/{s['anchor_datatype']}/adj={s['anchor_is_adj']}; file updated {updated}"
        elif src == "bls_flat":
            survey = s["anchor_program"]
            files = sorted(os.path.join(base, "bls", f) for f in os.listdir(os.path.join(base, "bls"))
                           if f.startswith(f"{survey}.data."))
            if survey not in bls_cache:
                bls_cache[survey] = parse_bls(files)
            d = bls_cache[survey]
            sel = d[d.series_id == s["anchor_bls_series"]].drop_duplicates(["obs_date"])
            out = pd.DataFrame({"obs_date": sel.obs_date, "value": sel.value})
            if sel.empty:
                raise SystemExit(f"{sid}: {s['anchor_bls_series']} not found in {files}")
            fpath = sel["_file"].iloc[0]
            note = f"BLS {s['anchor_bls_series']}"
        elif src == "bts_socrata":
            fpath = os.path.join(base, "bts", f"{s['anchor_program']}.csv")
            d = pd.read_csv(fpath, dtype=str)
            out = pd.DataFrame({"obs_date": d["date"].str[:10],
                                "value": pd.to_numeric(d[s["anchor_bts_field"]], errors="coerce")})
            note = f"BTS MTS field {s['anchor_bts_field']}"
        else:
            raise SystemExit(f"unknown anchor source {src}")
        out = out.dropna(subset=["value"]).sort_values("obs_date")
        if out.empty:
            raise SystemExit(f"{sid}: no anchor observations found ({note})")
        out.insert(0, "series_id", sid)
        out["anchor_source"] = note
        out["anchor_file"] = os.path.relpath(fpath, ROOT)
        out["anchor_file_sha256"] = sha256_file(fpath)
        out["snapshot_date"] = snap
        rows.append(out)
        print(f"{sid:16s} {len(out):5d} obs  {out.obs_date.min()} .. {out.obs_date.max()}  [{note}]")

    res = pd.concat(rows, ignore_index=True)
    os.makedirs(PROCESSED, exist_ok=True)
    res.to_csv(os.path.join(PROCESSED, "anchor_vintage.csv"), index=False)
    print(f"wrote {len(res)} rows for {res.series_id.nunique()} series")


if __name__ == "__main__":
    main()
