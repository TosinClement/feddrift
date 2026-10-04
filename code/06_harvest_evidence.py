#!/usr/bin/env python3
"""06 - Harvest agency evidence for every rule and every release-level cluster, and propose a recommendation.

This step reads public agency documents and writes:
  evidence/source_registry.csv  one row per source document: publisher, title, document id, publication date,
                                URL, retrieval method, access time, SHA-256, bytes
  evidence/rule_evidence.csv    program-level policy statements supporting each routine rule
  evidence/cluster_evidence.csv one row per release cluster: matched source(s), quoted text, locator, an
                                automated consistency check against the observed footprint, and Claude's
                                RECOMMENDED cause with a confidence grade

Everything here is a recommendation for the label owner. Nothing in this file is a verified label.

Downloaded documents are cached in evidence_cache/ (git-ignored; re-creatable from the URLs and checkable
against the registry hashes). Run with --offline to rebuild the CSVs from the cache without network access.

Requires network for the first run; uses pdftotext (poppler) when available, otherwise pypdf.
Usage:  python code/06_harvest_evidence.py [--offline]
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

import pandas as pd
import requests

from fd_common import PROCESSED, ROOT

EVID = os.path.join(ROOT, "evidence")
CACHE = os.path.join(ROOT, "evidence_cache")
UA = "Mozilla/5.0 (compatible; FedDrift/0.1 research; +mailto:clementtosin92@gmail.com)"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
MON_RE = "(" + "|".join(MONTHS) + r")\s+(\d{4})"
MABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

OFFLINE = False
REGISTRY = {}


# ----------------------------------------------------------------------------------------------- fetching
def cache_path(url):
    ext = os.path.splitext(url.split("?")[0])[1][:6] or ".html"
    return os.path.join(CACHE, hashlib.sha256(url.encode()).hexdigest()[:20] + ext)


def fetch(url, publisher, title, doc_type, doc_id="", pub_date="", must=False):
    """Download (or reuse cached) document; register it; return (source_id, local path) or (None, None)."""
    os.makedirs(CACHE, exist_ok=True)
    p = cache_path(url)
    if not os.path.exists(p):
        if OFFLINE:
            return None, None
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=90)
            time.sleep(0.4)
        except requests.RequestException:
            return None, None
        if r.status_code != 200 or len(r.content) < 600 or (url.endswith(".pdf") and not r.content.startswith(b"%PDF")):
            if must:
                raise SystemExit(f"required source unavailable: {url} (HTTP {r.status_code})")
            return None, None
        open(p, "wb").write(r.content)
    b = open(p, "rb").read()
    sid = "SRC-" + hashlib.sha256(url.encode()).hexdigest()[:10].upper()
    REGISTRY[sid] = {"source_id": sid, "publisher": publisher, "title": title, "doc_type": doc_type,
                     "document_id": doc_id, "publication_date": pub_date, "url": url,
                     "retrieval": "direct_download",
                     "accessed_utc": dt.datetime.fromtimestamp(os.path.getmtime(p), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
    return sid, p


def register_reader(url, publisher, title, doc_type, pub_date, accessed, note):
    """Sources the shell cannot download (host blocks scripted clients) but that were read with a web reader."""
    sid = "SRC-" + hashlib.sha256(url.encode()).hexdigest()[:10].upper()
    REGISTRY[sid] = {"source_id": sid, "publisher": publisher, "title": title, "doc_type": doc_type,
                     "document_id": "", "publication_date": pub_date, "url": url,
                     "retrieval": "web_reader_quote_only (" + note + ")", "accessed_utc": accessed,
                     "sha256": "", "bytes": ""}
    return sid


def register_capture(url, publisher, title, doc_type, pub_date, capture_file, captured_utc, rendered_sha, rendered_bytes,
                     doc_id="", how="text of the page's <main> element, built-in browser"):
    """A page read in an ordinary browser and saved as a dated text excerpt capture (not the server's file)."""
    p = os.path.join(EVID, "captures", capture_file)
    b = open(p, "rb").read()
    sid = "SRC-" + hashlib.sha256(url.encode()).hexdigest()[:10].upper()
    REGISTRY[sid] = {"source_id": sid, "publisher": publisher, "title": title, "doc_type": doc_type,
                     "document_id": doc_id, "publication_date": pub_date, "url": url,
                     "retrieval": (f"browser_excerpt_capture: evidence/captures/{capture_file} ({how}, {captured_utc}); "
                                   f"sha256 is of the capture, not the server file; page HTML at capture time: "
                                   f"{rendered_bytes} bytes, "
                                   f"sha256 {rendered_sha} (not stored)"),
                     "accessed_utc": captured_utc, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
    return sid


def text_of(path):
    tp = path + ".txt"
    if os.path.exists(tp):
        return open(tp, encoding="utf-8", errors="replace").read()
    if path.endswith(".pdf"):
        if shutil.which("pdftotext"):
            t = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
        else:
            from pypdf import PdfReader
            t = "\f".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
        if len(t.strip()) < 200 and shutil.which("tesseract") and shutil.which("pdftoppm"):
            # Scanned release (e.g. M3 full reports before ~2003). OCR pages 1-2 (headline and notes) and the
            # last page (where "upcoming revisions" notices are printed) at 150 dpi.
            import tempfile
            n = 1
            if shutil.which("pdfinfo"):
                info = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
                m_ = re.search(r"Pages:\s+(\d+)", info)
                n = int(m_.group(1)) if m_ else 1
            pages = sorted({1, min(2, n), n})
            parts = []
            with tempfile.TemporaryDirectory() as td:
                for pg in pages:
                    subprocess.run(["pdftoppm", "-r", "150", "-f", str(pg), "-l", str(pg), "-gray", "-png", path,
                                    os.path.join(td, f"p{pg}")], capture_output=True)
                for f_ in sorted(os.listdir(td)):
                    parts.append(subprocess.run(["tesseract", os.path.join(td, f_), "-", "--psm", "4"],
                                                capture_output=True, text=True).stdout)
            t = f"[OCR pages {pages} of {n}]\n" + "\f".join(parts)
    else:
        raw = open(path, encoding="utf-8", errors="replace").read()
        raw = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", raw)
        import html as _h
        t = _h.unescape(re.sub(r"<[^>]+>", "\n", raw))
    open(tp, "w", encoding="utf-8").write(t)
    return t


def flat(s):
    return re.sub(r"\s+", " ", s).strip()


def page_of(text, needle):
    i = text.find(needle[:40])
    return "" if i < 0 else f"p. {text[:i].count(chr(12)) + 1}"


def first_month(s):
    m = re.search(MON_RE, s)
    return f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}-01" if m else ""


def release_date(text):
    """First full date in the document header (release documents print their release date first)."""
    head = re.sub(r"\s+", " ", text[:1500])
    m = re.search(r"(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2}),?\s+(\d{4}|\d{2})\b", head, re.I)
    if not m:
        return ""
    y = int(m.group(3))
    y = y + (1900 if y > 50 else 2000) if y < 100 else y
    mon = [x.lower() for x in MONTHS].index(m.group(1).lower()) + 1
    return f"{y}-{mon:02d}-{int(m.group(2)):02d}"


def sentences(text, must, any_of=(), limit=3, maxlen=700):
    out = []
    for s in re.split(r"(?<=[.;])\s+(?=[A-Z(])", flat(text)):
        low = s.lower()
        if all(k in low for k in must) and (not any_of or any(k in low for k in any_of)):
            out.append(s[:maxlen])
            if len(out) >= limit:
                break
    return out


BOILER = ["first published on a naics basis", "adjusted data were revised due to concurrent seasonal adjustment", "no revisions were made to not adjusted",
          "this explains the revision to retail estimates from a year ago", "(r) revised", "(p) preliminary"]
NOTICE_KEYS = ["notice", "intention to revise", "revisions to the", "were released on", "were issued on",
               "will be issued", "reflect revisions", "begin with", "benchmark", "annual revision", "revised historical",
               "were published", "are reflected in this release", "naics", "semiconductor", "new sample",
               "upcoming revisions", "revised historical series", "consistent with the revised"]


def notice_sentences(text, limit=8):
    out = []
    for s_ in re.split(r"(?<=\.)\s+", flat(text)):
        low = s_.lower()
        if any(b in low for b in BOILER) or len(s_) < 25:
            continue
        if any(k in low for k in NOTICE_KEYS) and ("revis" in low or "benchmark" in low or "naics" in low
                                                    or "sample" in low or "semiconductor" in low):
            if s_[:600] not in out:
                out.append(s_[:600])
        if len(out) >= limit:
            break
    return out


def begin_with(sents):
    """'Revisions to the adjusted ... begin with January 1992' -> 1992-01-01 (adjusted statements preferred)."""
    for s_ in sents:
        low = s_.lower()
        if ("begin with" in low or "beginning with" in low or "back to" in low or "revised for" in low) and "adjusted" in low \
                and "unadjusted" not in low[:low.find("adjusted") + 1]:
            return first_month(s_[low.find("begin") if "begin" in low else 0:])
    return ""


# --------------------------------------------------------------------------------------- rule evidence
def rule_evidence():
    rows = []

    def add(rule, sid, quote, locator=""):
        rows.append({"rule_id": rule, "source_id": sid, "quote": quote, "locator": locator})

    sid, p = fetch("https://www2.census.gov/retail/releases/historical/marts/adv2608.pdf", "U.S. Census Bureau",
                   "Advance Monthly Sales for Retail and Food Services, August 2026 (CB26-153)", "release",
                   "CB26-153", "2026-09-16", must=True)
    t = text_of(p)
    q1 = sentences(t, ["concurrently adjusted"], limit=1) + sentences(t, ["concurrent seasonal adjustment uses"], limit=1)
    q2 = sentences(t, ["advance estimates are based on early reports"], limit=1)
    for rule in ["R20_ROUTINE_MARTS_SA", "R22_ROUTINE_MRTS"]:
        add(rule, sid, " ".join(q1 + q2), "Table 1 footnotes (2), (3)")
    add("R21_ROUTINE_MARTS_NSA", sid, " ".join(q2) + " Table legend: (a) Advance estimate (p) Preliminary estimate (r) Revised estimate.",
        "Table 1 legend and footnote (3)")
    sid, p = fetch("https://www.census.gov/manufacturing/m3/historical_data/pressreleases/prel/2025/apr25prel.pdf",
                   "U.S. Census Bureau", "Full Report on Manufacturers' Shipments, Inventories, and Orders, April 2025 (CB 25-71)",
                   "release", "CB 25-71", "2025-06-03", must=True)
    t = text_of(p)
    add("R23_ROUTINE_M3", sid, " ".join(sentences(t, ["corrections will be published in the full report"], limit=1)
                                        + sentences(t, ["corrections received after the full report"], limit=1)
                                        + sentences(t, ["revisions made later than two months"], limit=1)),
        "Reliability of Estimates")
    sid, p = fetch("https://www2.census.gov/mtis/historical/mtis2606.pdf", "U.S. Census Bureau",
                   "Manufacturing and Trade Inventories and Sales, June 2026", "release", "", "", must=True)
    t = text_of(p)
    REGISTRY[sid]["publication_date"] = release_date(t)          # read from the release header, not the filename
    m_ = re.search(r"Release Number:\s*(CB\d{2}-\d+)", t)
    if m_:
        REGISTRY[sid]["document_id"] = m_.group(1)
    q = sentences(t, ["concurrent"], ["seasonal"], limit=1) + sentences(t, ["preliminary"], ["superseded", "revised"], limit=1)
    add("R24_ROUTINE_MTIS", sid, " ".join(q) or flat(t[:400]), "explanatory notes")
    sid, p = fetch("https://www.bls.gov/news.release/archives/ppi_09102026.pdf", "U.S. Bureau of Labor Statistics",
                   "Producer Price Indexes - August 2026 (news release)", "release", "", "2026-09-10", must=True)
    t = text_of(p)
    q = sentences(t, ["subject to revision for 4 months"], limit=1)
    add("R25_ROUTINE_PPI", sid, " ".join(q), page_of(t, q[0]) if q else "")
    # BLS Handbook of Methods: the PPI revision procedure and its November-2021 change (added at the label
    # owner's request, 2026-10-03; quotes verified against the live pages)
    for page, title, needles, loc in [
            ("presentation", "Handbook of Methods: Producer Price Indexes - Presentation",
             ["beginning in the 1970s and continuing through october 2021", "effective with the release of data for november 2021",
              "indexes undergo five iterative updates"], "section: Index revision"),
            ("calculation", "Handbook of Methods: Producer Price Indexes - Calculation",
             ["with the release of data for november 2021", "indexes undergo five iterative updates"], "section: Index revisions")]:
        sid2, p2 = fetch(f"https://www.bls.gov/opub/hom/ppi/{page}.htm", "U.S. Bureau of Labor Statistics", title,
                         "methodology", "", "", must=True)
        t2 = text_of(p2)
        lm = re.search(r"Last Modified Date:\s*(" + "|".join(MONTHS) + r") (\d{1,2}), (\d{4})", flat(t2))
        if lm:
            REGISTRY[sid2]["publication_date"] = (f"{lm.group(3)}-{MONTHS.index(lm.group(1)) + 1:02d}-"
                                                  f"{int(lm.group(2)):02d} (last modified)")
        qq = [x for n in needles for x in sentences(t2, [n], limit=1)]
        if len(qq) != len(needles):
            raise SystemExit(f"BLS Handbook PPI {page}: expected statements not found; page may have changed")
        add("R25_ROUTINE_PPI", sid2, " ".join(qq), loc)
    add("R10_BLS_SA_FEB", sid, " ".join(q), page_of(t, q[0]) if q else "")
    # bts.gov refuses scripted downloads (HTTP 403). The two BTS pages were opened in the built-in browser pane
    # (ordinary browser access, 2026-10-03) and the relevant text of each page's <main> element was saved as a dated
    # excerpt capture in evidence/captures/. Each capture's SHA-256 equals the hash computed inside the browser on the
    # same text. These are captures, not the original server files.
    s1 = register_capture("https://www.bts.gov/browse-statistical-products-and-data/transportation-economic-trends/revision-policy-tsi",
                          "Bureau of Transportation Statistics", "Revision Policy for the Transportation Services Index",
                          "methodology", "2024-11-22", "bts_tsi_revision_policy.excerpt.txt", "2026-10-03T22:36:37Z",
                          "feeee572744fab6737b258a3a770b75107fc546cc87dd75748d68e61624bf10c", 103214)
    t1 = open(os.path.join(EVID, "captures", "bts_tsi_revision_policy.excerpt.txt"), encoding="utf-8").read()
    add("R26_ROUTINE_TSI", s1, " ".join(sentences(t1, ["publishes the tsi monthly"], limit=1)
                                        + sentences(t1, ["monthly publication includes"], limit=1)
                                        + sentences(t1, ["occasionally, the sources for tsi input data"], limit=1)
                                        + sentences(t1, ["such changes in source data"], limit=1)
                                        + sentences(t1, ["adding a new data point"], limit=1)),
        "Policy Summary; Reasons for Revision (excerpt capture)")
    s2 = register_capture("https://www.bts.gov/newsroom/may-2025-freight-transportation-services-index-tsi-down-01-previous-month-and-down-09-same",
                          "Bureau of Transportation Statistics",
                          "May 2025 Freight Transportation Services Index (TSI) Down 0.1% from the Previous Month and Down 0.9% "
                          "from the Same Month Last Year (BTS 42-25)", "release", "2025-07-10",
                          "bts_tsi_release_2025-07-10.excerpt.txt", "2026-10-03T22:35:05Z",
                          "165e03529e8a6d001c2364f2e72c39f2eca1f28979fa0378fe13b2d886925bec", 275972, doc_id="BTS 42-25")
    t2 = open(os.path.join(EVID, "captures", "bts_tsi_release_2025-07-10.excerpt.txt"), encoding="utf-8").read()
    add("R26_ROUTINE_TSI", s2, " ".join(sentences(t2, ["monthly data has changed"], limit=1)
                                        + sentences(t2, ["the entire freight tsi is revised monthly"], limit=1)),
        "'Revisions' paragraph; note to Table A (excerpt capture)")
    sid, p = fetch("https://www.bls.gov/cpi/seasonal-adjustment/", "U.S. Bureau of Labor Statistics",
                   "Seasonal Adjustment in the CPI", "methodology", "", "", must=True)
    t = text_of(p)
    add("R10_BLS_SA_FEB", sid, " ".join(sentences(t, ["seasonal adjustment factors are recalculated"], limit=1)
                                        + sentences(t, ["previous 5 years"], limit=1)), "web page")
    sid, p = fetch("https://www.bls.gov/cpi/seasonal-adjustment/timeline-seasonal-adjustment-methodology-changes.htm",
                   "U.S. Bureau of Labor Statistics", "Timeline of Seasonal Adjustment Methodological Changes (CPI)",
                   "methodology", "2021-02-08", "", must=True)
    t = text_of(p)
    add("R10_BLS_SA_FEB", sid, " ".join(sentences(t, ["subsequent annual updates would replace 5 years"], limit=1)),
        "entry: 1977")
    add("R00_EXTENSION", "", "Mechanical: no published value changed.", "")
    add("R01_ARCHIVE_WINDOW", "", "Mechanical: ALFRED vintage holds a fixed-length window (see data/manifests n_obs).", "")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ cluster evidence
def retail_benchmark_doc(year):
    """Census annual retail revision document published in `year`.
    2009+: benchmark/<year>/Introduction.pdf (published in <year>).
    1996-2007: annpub<YY>.pdf is named for the DATA year and issued the following spring, so the document
    for an event in year Y is annpub<Y-1>; its 'Issued <Month> <Y>' line is checked before use."""
    if year >= 2009:
        url = f"https://www.census.gov/retail/mrts/www/benchmark/{year}/pdf/Introduction.pdf"
        title = f"Annual Revision of Monthly Retail and Food Services: Introduction / Explanation of Revisions ({year})"
        return fetch(url, "U.S. Census Bureau", title, "benchmark_report", f"retail-annual-{year}", "")
    if year == 2008:
        # annpub07.pdf on the server is the March 2007 report (byte-identical to annpub06.pdf); the 2008 revision
        # is documented by the summary on the 2008 annual-revision page (annrev08.html), found on manual review.
        return fetch("https://www.census.gov/retail/mrts/www/benchmark/2008/html/summary.pdf", "U.S. Census Bureau",
                     "Annual Revision of Monthly Retail and Food Services: Sales and Inventories, January 1992 Through "
                     "March 2008 (summary)", "benchmark_report", "retail-annual-2008", "")
    if 1996 <= year <= 2007:
        yy = str(year - 1)[2:]
        url = f"https://www2.census.gov/retail/releases/benchmark/annpub{yy}.pdf"
        sid, p = fetch(url, "U.S. Census Bureau", f"Annual Benchmark Report for Retail Trade and Food Services "
                       f"(data year {year - 1})", "benchmark_report", f"annpub{yy}", "")
        if sid:
            m = re.search(r"Issued\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", text_of(p))
            if not m or int(m.group(2)) != year:
                del REGISTRY[sid]
                return None, None
            REGISTRY[sid]["publication_date"] = f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}"
        return sid, p
    return None, None


def retail_starts(text):
    """Earliest revised month for adjusted (SA) and not adjusted (NSA) monthly sales, as stated by Census."""
    f = flat(text)
    sa = nsa = ""
    for s in re.split(r"(?<=\.)\s+", f):
        low = s.lower()
        if "monthly sales" not in low or "revised" not in low:
            continue
        if low.startswith("not adjusted and adjusted") or "not adjusted and adjusted" in low[:60]:
            sa = sa or first_month(s)
            nsa = nsa or first_month(s)
        elif "not adjusted" in low[:80]:
            nsa = nsa or first_month(s)
        elif "adjusted" in low[:80]:
            sa = sa or first_month(s)
    if not sa:
        # 2007-2017 wording: "New seasonal, trading-day, and holiday factors are computed and used to adjust sales for
        # January YYYY through ..." (industry-specific exceptions start with "For NAICS ..." and are not headlines)
        for s in re.split(r"(?<=\.)\s+", f):
            if re.match(r"(seasonally adjusted estimates )?new seasonal, trading-day, and holiday factors are computed "
                        r"and used to adjust sales", s.lower()):
                sa = first_month(s)
                break
    return sa, nsa


def cluster_retail(c, ev):
    y = int(c.vintage_date[:4])
    sid, p = retail_benchmark_doc(y)
    if not sid:
        return [], "no annual-revision document located for this year"
    t = text_of(p)
    sa, nsa = retail_starts(t)
    head = flat(t[max(0, t.find("EXPLANATION OF REVISIONS")):][:900]) if "EXPLANATION OF REVISIONS" in t else flat(t[:900])
    quote = head
    flags = []
    low = flat(t).lower()
    if "new sample" in low or "sample revision" in low or "new mrts sample" in low:
        flags.append("sample_redesign")
    if "naics" in low and "restat" in low:  # tightened 2026-10-03: "NAICS ... basis" alone is not a stated restatement
        flags.append("rebase_or_definition(NAICS)")
    if "employer-only" in low or "employer only" in low:
        flags.append("rebase_or_definition(employer-only)")
    # every month-year stated in a revision sentence of the document (aggregates can be revised further back
    # than the headline statement, e.g. 2018: NAICS 443/451 and aggregates containing them back to 1992)
    stated_any = set()
    for s_ in re.split(r"(?<=\.)\s+", flat(t)):
        lw = s_.lower()
        if "revis" in lw or "beginning" in lw or "adjust sales" in lw or "far back" in lw:
            for mm in re.finditer(MON_RE, s_):
                stated_any.add(f"{mm.group(2)}-{MONTHS.index(mm.group(1)) + 1:02d}-01")
    checks = []
    for e in ev.itertuples():
        stated = nsa if e.series_id == "RSAFSNA" else sa
        obs = str(e.earliest_revised_obs)
        if stated and stated == obs:
            checks.append(f"{e.series_id}: headline stated start {stated[:7]} = observed {obs[:7]} -> MATCH")
        elif obs in stated_any:
            checks.append(f"{e.series_id}: observed start {obs[:7]} appears in the document's revision statements -> MATCH")
        elif stated:
            checks.append(f"{e.series_id}: headline stated start {stated[:7]} vs observed {obs[:7]} -> DIFFERENT")
        else:
            checks.append(f"{e.series_id}: observed start {obs[:7]} not found among stated months -> DIFFERENT")
    return [{"source_id": sid, "quote": quote, "locator": page_of(t, "EXPLANATION") or "p. 1",
             "stated_sa_start": sa, "stated_nsa_start": nsa, "secondary_flags": ";".join(flags),
             "check": " | ".join(checks)}], ""


def m3_docs_near(v):
    """M3 full-report PDFs for data months v-4 .. v-1 (the full report is released ~5 weeks after the month)."""
    out = []
    vd = pd.Timestamp(v)
    for k in range(1, 5):
        d = vd - pd.DateOffset(months=k)
        url = (f"https://www.census.gov/manufacturing/m3/historical_data/pressreleases/prel/{d.year}/"
               f"{MABBR[d.month - 1]}{str(d.year)[2:]}prel.pdf")
        sid, p = fetch(url, "U.S. Census Bureau", f"Full Report on Manufacturers' Shipments, Inventories, and Orders, "
                       f"{MONTHS[d.month - 1]} {d.year}", "release", "", "")
        if sid:
            t = text_of(p)
            REGISTRY[sid]["publication_date"] = release_date(t)
            out.append((sid, t))
    return out


def cluster_m3(c, ev):
    docs = m3_docs_near(c.vintage_date)
    rows = []
    for sid, t in docs:
        f = flat(t)
        blocks = []
        i = f.lower().find("benchmark notice")
        if i >= 0:
            blocks.append(f[i:i + 900])
        k2 = f.lower().find("notice of revision")
        if k2 >= 0 and not any(f[k2:k2 + 50] in b for b in blocks):
            blocks.append(f[k2:k2 + 900])
        for kw in ["revised historical data", "revised historical series", "upcoming revisions", "annual revision",
                   "benchmark revision", "revisions to the m3", "revised to reflect"]:
            j = f.lower().find(kw)
            if j >= 0 and not any(f[j:j + 50] in b for b in blocks):
                blocks.append(f[max(0, j - 150):j + 600])
        extra = [x for x in notice_sentences(t) if not any(x[:60] in b for b in blocks)]
        blocks += extra[:4]
        if not blocks:
            continue
        issued = ""
        m = re.search(r"(?:issued|released)(?: on)? (" + "|".join(MONTHS) + r") (\d{1,2}), (\d{4})", " ".join(blocks)) or \
            re.search(r"\bOn (" + "|".join(MONTHS) + r") (\d{1,2}), (\d{4}), (?:monthly|revised|the)", " ".join(blocks))
        if m:
            issued = f"{m.group(3)}-{MONTHS.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
        span = re.search(r"spanned the seasonally adjusted data for " + MON_RE, " ".join(blocks))
        chk = []
        if issued:
            lag = (pd.Timestamp(c.vintage_date) - pd.Timestamp(issued)).days
            chk.append(f"agency issue date {issued}; ALFRED vintage {c.vintage_date} ({lag:+d} days)")
        if span:
            st = f"{span.group(2)}-{MONTHS.index(span.group(1)) + 1:02d}-01"
            for e in ev.itertuples():
                chk.append(f"{e.series_id}: stated SA start {st[:7]} vs observed {str(e.earliest_revised_obs)[:7]} -> "
                           + ("MATCH" if st == e.earliest_revised_obs else "DIFFERENT"))
        rows.append({"source_id": sid, "quote": " ... ".join(blocks)[:1500],
                     "locator": "notice section" + (f"; release dated {REGISTRY[sid]['publication_date']}" if REGISTRY[sid]['publication_date'] else ""),
                     "agency_issue_date": issued, "check": " | ".join(chk)})
    return rows, "" if rows else "no revision notice found in M3 full reports released near this vintage"


def cluster_mtis(c, ev):
    vd = pd.Timestamp(c.vintage_date)
    exact = None
    for k in range(1, 4):
        d = vd - pd.DateOffset(months=k)
        stem = f"mtis{str(d.year)[2:]}{d.month:02d}"
        ext = ".pdf" if d.year >= 2001 else ".txt"
        sid, p = fetch(f"https://www2.census.gov/mtis/historical/{stem}{ext}", "U.S. Census Bureau",
                       f"Manufacturing and Trade Inventories and Sales, {MONTHS[d.month - 1]} {d.year}", "release", stem, "")
        if not sid:
            continue
        t = text_of(p)
        rd = release_date(t)
        REGISTRY[sid]["publication_date"] = rd
        if rd == c.vintage_date:
            exact = (sid, t)
    if not exact:
        return [], "no MTIS release dated exactly on this vintage was located in the Census archive"
    sid, t = exact
    q = notice_sentences(t)
    chk = ["release date matches ALFRED vintage"]
    st = begin_with(q)
    if st:
        for e in ev.itertuples():
            chk.append(f"{e.series_id}: stated adjusted-data revisions begin {st[:7]} vs observed {str(e.earliest_revised_obs)[:7]} -> "
                       + ("MATCH" if st == e.earliest_revised_obs else "DIFFERENT"))
    if not q:
        chk.append("no revision notice in the release text")
    return [{"source_id": sid, "quote": " ".join(q)[:1800], "locator": f"release dated {c.vintage_date}, notice section",
             "check": " | ".join(chk)}], ""


BLS_INDEX = {}


def bls_release(kind, v):
    """BLS posts revised seasonally adjusted data a few days before the January-data release, so ALFRED's vintage
    can precede the news release. Match the archived news release dated on or up to 10 days after the vintage."""
    if kind not in BLS_INDEX:
        sid, p = fetch(f"https://www.bls.gov/bls/news-release/{kind}.htm", "U.S. Bureau of Labor Statistics",
                       f"{kind.upper()} archived news releases (index)", "index", "", "")
        txt = open(p, encoding="utf-8", errors="replace").read() if p else ""
        BLS_INDEX[kind] = sorted(set(re.findall(kind + r"_(\d{8})\.pdf", txt)))
    d = pd.Timestamp(v)
    cands = []
    for s8 in BLS_INDEX[kind]:
        rd = pd.Timestamp(f"{s8[4:]}-{s8[:2]}-{s8[2:4]}")
        if 0 <= (rd - d).days <= 10:
            cands.append((rd, s8))
    if not cands:
        return None, None, None
    rd, s8 = min(cands)
    name = {"cpi": "Consumer Price Index", "ppi": "Producer Price Indexes"}[kind]
    sid, p = fetch(f"https://www.bls.gov/news.release/archives/{kind}_{s8}.pdf", "U.S. Bureau of Labor Statistics",
                   f"{name} news release ({rd.date()})", "release", "", str(rd.date()))
    return sid, p, str(rd.date())


def cluster_bls_feb(c, ev, kind):
    sid, p, rd = bls_release(kind, c.vintage_date)
    if not sid:
        return [], "no archived BLS news release within 10 days after this vintage (archive starts June 2002)"
    t = text_of(p)
    q = sentences(t, ["seasonal"], ["revis", "recalculat"], limit=3)
    y = int(c.vintage_date[:4])
    lag = (pd.Timestamp(rd) - pd.Timestamp(c.vintage_date)).days
    chk = [f"news release dated {rd} ({lag:+d} days after the ALFRED vintage)"]
    for e in ev.itertuples():
        # BLS: the new factors revise the previous five calendar years (January of year y-5 onward)
        inside = str(e.earliest_revised_obs)[:4] == str(y - 5)
        chk.append(f"{e.series_id}: earliest revised {str(e.earliest_revised_obs)[:7]}; stated window starts {y - 5}-01 -> "
                   + ("MATCH (within first year of the 5-year window)" if inside else "DIFFERENT"))
    return [{"source_id": sid, "quote": " ".join(q)[:1500], "locator": page_of(t, q[0]) if q else "",
             "check": " | ".join(chk)}], ""


SPECIAL = {}   # filled in main(): cluster_id -> callable returning (rows, note, recommendation)


def specials():
    out = {}
    sid, p = fetch("https://www.bls.gov/cpi/seasonal-adjustment/timeline-seasonal-adjustment-methodology-changes.htm",
                   "U.S. Bureau of Labor Statistics", "Timeline of Seasonal Adjustment Methodological Changes (CPI)",
                   "methodology", "2021-02-08", "")
    t = text_of(p) if p else ""
    q = sentences(t, ["seasonally adjusted indexes for dependently adjusted series were revised from january 1987"], limit=1)
    out["FDC-CPI-20020220"] = ([{"source_id": sid, "quote": " ".join(q), "locator": "entry: January 2002",
                                 "check": "stated start 1987-01 vs observed 1987-01 (CPIAUCSL, CPILFESL) -> MATCH"}],
                               "methodology_change", "seasonal_factor_recompute", "strong")
    sid, p = fetch("https://www.bls.gov/bls/errata/cpi-price-corrections-10182016.htm", "U.S. Bureau of Labor Statistics",
                   "Corrections to Consumer Price Index Data (published October 18, 2016)", "errata", "", "2016-10-18")
    t = text_of(p) if p else ""
    q = sentences(t, ["incorrect as published for may 2016 through august 2016"], limit=1)
    out["FDC-CPI-20161018"] = ([{"source_id": sid, "quote": " ".join(q), "locator": "web page",
                                 "check": "stated May-Aug 2016 vs observed 2016-05..2016-08 -> MATCH"}], "correction", "", "strong")
    # Earlier (before 2026-10-04) this source was only quoted from a web reader, with no local file. It is now a dated
    # browser excerpt capture of the page's <main> text; no original server file was obtained.
    s2 = register_capture("https://slgs.gov/news/2000/release-09-28/", "Bureau of the Public Debt (U.S. Treasury)",
                          "Statement on CPI Revision and Inflation-Indexed Securities (September 28, 2000)", "statement",
                          "2000-09-28", "treasury_slgs_statement_2000-09-28.excerpt.txt", "2026-10-04T04:01:58Z",
                          "d31ad4aff98b471de432332709b4516cb75a17f7ecd5995d448cc0feca628e4f", 43128,
                          how="full text of the page's <main> element, built-in browser")
    out["FDC-CPI-20000928"] = ([{"source_id": s2, "quote": "The Bureau of Labor Statistics today released revised index "
                                 "numbers for the consumer price index numbers previously reported for January through August 2000.",
                                 "locator": "web page", "check": "stated Jan-Aug 2000 vs observed 2000-01..2000-08 -> MATCH; "
                                 "reason for the revision not stated in this source (secondary source: Treasury, not BLS)"}],
                               "correction", "", "moderate")
    sid, p = fetch("https://www.bls.gov/opub/hom/cpi/history.htm", "U.S. Bureau of Labor Statistics",
                   "Handbook of Methods: Consumer Price Index - History", "methodology", "", "")
    t = text_of(p) if p else ""
    q53 = sentences(t, ["1953: the second comprehensive revision"], limit=1) or ["1953: The second comprehensive revision"]
    q50 = sentences(t, ["1950: weight updates"], limit=1) or ["1950: Weight updates and new items added"]
    out["FDC-CPI-19530227"] = ([{"source_id": sid, "quote": flat(" ".join(q53))[:600], "locator": "Key developments: 1953",
                                 "check": "comprehensive revision dated 1953 (month not stated); observed revision of all 1947-1952 "
                                 "values by ~40% is consistent with a change of reference base"}],
                               "methodology_change", "rebase_or_definition", "moderate")
    # CPI reference-base changes and the 2000 correction: BLS documents located on manual review (2026-10-03).
    def doc(url, title, pub, doc_id=""):
        publ = "U.S. Bureau of Labor Statistics" + (" (via FRASER, Federal Reserve Bank of St. Louis)" if "fraser" in url else "")
        sid_, p_ = fetch(url, publ, title, "release" if "cpi_" in url else "bulletin", doc_id, pub)
        return sid_, flat(text_of(p_)) if p_ else ""
    def one(t, needle, maxlen=700, upto="."):
        i = t.lower().find(needle.lower())
        if i < 0:
            return ""
        j = t.find(upto, i + len(needle))
        return t[i:(j + len(upto)) if j >= 0 else i + maxlen][:maxlen]
    sid, t = doc("https://fraser.stlouisfed.org/files/docs/publications/bls/bls_1140_1953.pdf",
                 "The Consumer Price Index: A Layman's Guide (BLS Bulletin No. 1140)", "1953", "BLS Bulletin 1140")
    out["FDC-CPI-19530227"] = ([{"source_id": sid, "quote": " ".join(x for x in [
        one(t, "the Bureau in 1949 began a comprehensive program for revising the index"),
        one(t, "from the average for the years 1947")] if x),
        "locator": "Bulletin 1140 text", "check": "stated: the January 1953 index was the first on the revised basis, with "
        "1947-49 = 100; observed: this vintage (January 1953 data) rescales all 1947-1952 values by about -40%, the size of a "
        "1935-39 -> 1947-49 base change"}], "methodology_change", "rebase_or_definition", "strong")
    sid, t = doc("https://fraser.stlouisfed.org/files/docs/publications/cpi/1970s/cpi_011971.pdf",
                 "The Consumer Price Index, January 1971 (BLS release)", "1971-02")
    out["FDC-CPI-19710219"] = ([{"source_id": sid, "quote": one(t, "Beginning with the release of data for January 1971"),
        "locator": "release text, 'New base period for Consumer Price Index'", "check": "stated: reference base 1967=100 "
        "beginning with January 1971 data; observed: this vintage (January 1971 data) rescales the whole history by a constant "
        "ratio (-14%) -> MATCH"}], "rebase_or_definition", "", "strong")
    sid, t = doc("https://fraser.stlouisfed.org/files/docs/publications/cpidr/1980s/cpi_011988.pdf",
                 "CPI Detailed Report, Data for January 1988", "1988")
    out["FDC-CPI-19880226"] = ([{"source_id": sid, "quote": one(t, "NOTE: Effective with the release of the January 1988 CPI"),
        "locator": "cover and note", "check": "stated: official reference base changed from 1967=100 to 1982-84=100 effective "
        "with the January 1988 CPI; observed: this vintage rescales CPIAUCNS (whole history) and CPIAUCSL (whole vintage "
        "window) by a constant ratio (-66.6%) -> MATCH"}], "rebase_or_definition", "", "strong")
    sid, t = doc("https://www.bls.gov/news.release/history/cpi_10182000.txt",
                 "Consumer Price Index news release, September 2000 data (2000-10-18)", "2000-10-18")
    q = one(t, "r = Revised percent changes based on indexes recalculated to correct for", 900, upto="made available on September 28.")
    prev = out.get("FDC-CPI-20000928", ([], "", "", ""))[0]
    out["FDC-CPI-20000928"] = ([{"source_id": sid, "quote": q, "locator": "note to the summary table",
        "check": "stated: indexes recalculated to correct an error in the residential rent and owners' equivalent rent "
        "components; corrected values made available on September 28 (= this vintage); observed revisions 2000-01..2000-08 "
        "-> MATCH"}] + prev, "correction", "", "strong")

    # 1951: BLS Bulletin 1039 (interim adjustment of the CPI), read on FRASER in the built-in browser and saved as a
    # dated excerpt capture of the full-text (OCR) page; found on manual review 2026-10-03.
    fr = register_capture("https://fraser.stlouisfed.org/title/interim-adjustment-consumers-price-index-correction-new-unit-"
                          "bias-rent-component-consumers-price-index-relative-importance-items-4427/fulltext",
                          "U.S. Bureau of Labor Statistics (via FRASER, Federal Reserve Bank of St. Louis)",
                          "Interim Adjustment of Consumers' Price Index: Correction of New Unit Bias in Rent Component of "
                          "Consumers' Price Index and Relative Importance of Items (BLS Bulletin No. 1039)", "bulletin",
                          "1951-06-29", "bls_bulletin1039_1951.fraser_fulltext.excerpt.txt", "2026-10-03T23:44:04Z",
                          "d5466107542c2ba2820421509b29b06dc65ff8a26274adb48f6b61303af8eb82", 274347,
                          doc_id="BLS Bulletin 1039",
                          how="selected sentences of the FRASER full-text (OCR) page, built-in browser")
    ft = open(os.path.join(EVID, "captures", "bls_bulletin1039_1951.fraser_fulltext.excerpt.txt"), encoding="utf-8").read()
    out["FDC-CPI-19510302"] = ([{"source_id": fr, "quote": " ".join(l for l in ft.split("\n")[3:7]),
                                 "locator": "Bulletin 1039 text (FRASER OCR full text; excerpt capture)",
                                 "check": "stated: published indexes back to January 1950 recalculated; all-items index for "
                                          "January 1950 raised by 1.3 points. Observed CPIAUCNS 1950-01 166.9 -> 168.2 (+1.3) "
                                          "and revisions over 1950-01..1950-12 -> MATCH. Bulletin dated June 29, 1951 "
                                          "(after this vintage); release date of the first adjusted index not stated"}],
                               "methodology_change", "", "strong")
    # TSI releases screened out of R26 (R27_TSI_SCREENED). bts.gov refuses scripted downloads; the three release pages
    # below were read in the built-in browser (ordinary access, 2026-10-03) and saved as dated excerpt captures.
    def bts(slug, title, date, cap, html_sha, html_bytes, doc_id=""):
        return register_capture("https://www.bts.gov/newsroom/" + slug, "Bureau of Transportation Statistics", title,
                                "release", date, cap, "2026-10-03T23:12:34Z", html_sha, html_bytes, doc_id=doc_id,
                                how="selected lines of the <main> text of the HTML served to the built-in browser "
                                    "(same-origin request from an approved bts.gov page)")
    def cap_lines(cap, *starts):
        t = open(os.path.join(EVID, "captures", cap), encoding="utf-8").read().split("\n")
        return " ".join(l for l in t if any(l.startswith(x) for x in starts))
    a = bts("august-2020-freight-transportation-services-index-tsi-down-13-july",
            "August 2020 Freight Transportation Services Index (TSI) Down 1.3% from July", "2020-10-15",
            "bts_tsi_release_2020-10-15.excerpt.txt",
            "cc6677d4fbb74a8f3216150e2a991f41d0d533da4dc7f1bfbbf0a1f35334f958", 134489)
    out["FDC-TSI-20201015"] = ([{"source_id": a, "quote": cap_lines("bts_tsi_release_2020-10-15.excerpt.txt",
                                                                   "The July index was revised"),
                                 "locator": "release text, revisions paragraph (excerpt capture)",
                                 "check": "stated July 2020 128.9 -> 132.8 vs observed TSIFRGHT 2020-07 128.9 -> 132.8 -> MATCH; "
                                          "revision is upstream (ATA truck tonnage advanced -> final estimate)"}],
                               "advance_to_revised", "", "strong")
    c = bts("corrected-january-2021-freight-transportation-services-index-tsi-rose-11-december",
            "CORRECTED: January 2021 Freight Transportation Services Index (TSI) Rose 1.1% from December", "2021-03-30",
            "bts_tsi_release_2021-03-30_corrected.excerpt.txt",
            "aada334e3425910530f248e289707dd6f8c45c65bdc0a1342108589694752371", 238186, doc_id="BTS 17-21 Corrected")
    cq = cap_lines("bts_tsi_release_2021-03-30_corrected.excerpt.txt", "The numbers in this release are corrected",
                   "Data revisions due to changes")
    out["FDC-TSI-20210414"] = ([{"source_id": c, "quote": cq, "locator": "correction notice (excerpt capture)",
                                 "check": "corrected December 2020 value 134.6 vs observed TSIFRGHT 2020-12 141.3 -> 134.6 "
                                          "in this vintage -> MATCH"}], "correction", "", "strong")
    out["FDC-TSI-20210310"] = ([{"source_id": c, "quote": cq, "locator": "correction notice (excerpt capture)",
                                 "check": "TSIFRGHT 2020-12 136.3 -> 141.3 in this vintage is the value BTS later declared "
                                          "incorrect; no cause of the change stated. TSITTL revisions not addressed"}],
                               "unknown", "", "none")
    d = bts("april-2021-freight-transportation-services-index-tsi-equaled-highest-level-start-pandemic",
            "April 2021 Freight Transportation Services Index (TSI) Equaled Highest Level since Start of Pandemic",
            "2021-06-09", "bts_tsi_release_2021-06-09.excerpt.txt",
            "a13bc82d5d9c336b98302a3b8900c8b799e52b7b37b086b80060197937a5a57f", 281647, doc_id="BTS 37-21")
    out["FDC-TSI-20210609"] = ([{"source_id": d, "quote": cap_lines("bts_tsi_release_2021-06-09.excerpt.txt",
                                                                   "The March index was revised"),
                                 "locator": "release text, freight revisions paragraph (excerpt capture)",
                                 "check": "stated March 2021 130.0 -> 135.9 vs observed TSIFRGHT 2021-03 130.0 -> 135.9 -> MATCH "
                                          "(freight only); combined-index (TSITTL) revisions not explained"}],
                               "unknown", "", "none")
    return out


# MTIS releases whose revision notice the keyword screen in recommend() does not catch (found on manual review,
# 2026-10-03). Both files are registered by cluster_mtis(); the 1999 text file is fixed-width and the server copy
# truncates lines at 140 characters, so the notice is quoted as it appears in the file.
MTIS_MANUAL = {
    "FDC-MTIS-19990813": ("https://www2.census.gov/mtis/historical/mtis9906.txt", "Notice of Revised Estimates",
                          "notice states retail and wholesale estimates were revised using 1997 Census of Retail Trade and "
                          "1997 Census of Wholesale Trade results; no revision start month stated (no numeric check); source "
                          "lines truncated at 140 characters in the server file", "annual_benchmark", "moderate"),
    "FDC-MTIS-20010614": ("https://www2.census.gov/mtis/historical/mtis0104.pdf", "SPECIAL NOTICE",
                          "notice states this and all subsequent releases use NAICS in place of SIC and that data series from "
                          "January 1992 were released on a NAICS basis; observed earliest revised month 1992-01 (BUSINV, "
                          "ISRATIO) -> MATCH", "rebase_or_definition", "strong"),
    "FDC-MTIS-20060613": ("https://www2.census.gov/mtis/historical/mtis0604.pdf", "Notice of Revison",
                          "notice states revised manufacturing shipments and inventories were released on May 19, 2006 (see "
                          "release FDC-M3-20060519); the type of revision is not stated in this source; label owner (2026-10-03): cause carried from FDC-M3-20060519 (annual_benchmark), moderate", "annual_benchmark", "moderate"),
    "FDC-MTIS-20070613": ("https://www2.census.gov/mtis/historical/mtis0704.pdf", "Notice of Revision",
                          "notice states revised manufacturing shipments and inventories were released on May 18, 2007 (see "
                          "release FDC-M3-20070518); the type of revision is not stated in this source; label owner (2026-10-03): cause carried from FDC-M3-20070518 (annual_benchmark), moderate", "annual_benchmark", "moderate"),
    "FDC-MTIS-20050915": ("https://www2.census.gov/mtis/historical/mtis0507.pdf", "Notice of Revison",
                          "notice states revised manufacturing shipments and inventories were released on August 19, 2005 "
                          "(see release FDC-M3-20050819); the type of revision is not stated in this source; label owner (2026-10-03): cause carried from FDC-M3-20050819 (annual_benchmark), moderate", "annual_benchmark",
                          "moderate"),
}


# Manual reading of documents where the automated start-month check reports DIFFERENT although the observed first
# revised month lies inside a range the document states (2026-10-03). Overrides the recommendation and adds the note.
MANUAL_ASSESS = {
    "FDC-MTIS-20020715": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20080612": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20110614": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20120613": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20150611": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20160614": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20170614": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20200616": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20210615": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20220615": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20230615": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20250617": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 benchmark via the MTIS notice"),
    "FDC-MTIS-20140612": ("seasonal_factor_recompute", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 seasonal-model revision via the MTIS notice"),
    "FDC-MTIS-20190614": ("seasonal_factor_recompute", "", "moderate",
                        "label owner (2026-10-03): moderate; carried from the M3 seasonal-model revision via the MTIS notice"),
    "FDC-MTIS-20030915": ("annual_benchmark", "rebase_or_definition", "moderate",
                        "label owner (2026-10-03): benchmark plus documented semiconductor coverage change"),
    "FDC-MTIS-20250515": ("annual_benchmark", "rebase_or_definition", "moderate",
                        "label owner (2026-10-03): retail benchmark with 2017 NAICS and employer-only restatement"),
    "FDC-MTIS-20130613": ("annual_benchmark", "sample_redesign", "strong",
                        "label owner (2026-10-03): direct MTIS notice"),
    "FDC-MTIS-20180614": ("annual_benchmark", "sample_redesign", "strong",
                        "label owner (2026-10-03): direct MTIS notice; 2012 NAICS introduction also documented"),
    "FDC-MTIS-20240515": ("annual_benchmark", "seasonal_factor_recompute", "moderate",
                        "label owner (2026-10-03): retail benchmark plus M3 seasonal-model revision"),
    "FDC-MTIS-19980814": ("unknown", "", "none",
                        "label owner (2026-10-03): revision type not established"),
    "FDC-MTIS-20100128": ("unknown", "", "none",
                        "label owner (2026-10-03): amendment documented; cause of incorporated M3 revision not established"),
    "FDC-MTIS-20030515": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20040413": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20080513": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20090513": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20110512": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20120515": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20140513": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20150513": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20160513": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20170512": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20190716": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20200515": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20210514": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20220517": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-20230516": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the verified retail release via the MTIS notice"),
    "FDC-MTIS-19970514": ("annual_benchmark", "", "strong",
                        "label owner (2026-10-03): direct MTIS notice naming the annual surveys"),
    "FDC-MTIS-20020515": ("annual_benchmark", "", "strong",
                        "label owner (2026-10-03): direct MTIS notice naming the annual surveys"),
    "FDC-MTIS-19970716": ("sample_redesign", "", "strong",
                        "label owner (2026-10-03): direct MTIS notice of a new retail sample design"),
    "FDC-MTIS-20100514": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; retail benchmark per MTIS notice; 1992-1995 portion unexplained (component ambiguity)"),
    "FDC-MTIS-20030414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20040312": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20080414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20090414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20100414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20110413": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20120416": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20140414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20150414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20160413": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20170414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20190418": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale report via the MTIS notice"),
    "FDC-MTIS-20050414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; retail and wholesale benchmarks carried via the MTIS notice"),
    "FDC-MTIS-20060413": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; retail and wholesale benchmarks carried via the MTIS notice"),
    "FDC-MTIS-20070416": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; retail and wholesale benchmarks carried via the MTIS notice"),
    "FDC-MTIS-20200415": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale revisions notice via the MTIS notice"),
    "FDC-MTIS-20210415": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale revisions notice via the MTIS notice"),
    "FDC-MTIS-20220414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale revisions notice via the MTIS notice"),
    "FDC-MTIS-20230414": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale revisions notice via the MTIS notice"),
    "FDC-MTIS-20240415": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale revisions notice via the MTIS notice"),
    "FDC-MTIS-20250416": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate; annual_benchmark carried from the Census wholesale revisions notice via the MTIS notice"),
    "FDC-M3-20200528": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate. Benchmark issued May 15, 2020; the same-day ALFRED snapshot shows only "
                        "routine revisions and the historical revisions first appear in this later snapshot (unexplained timing gap)"),
    "FDC-M3-20250527": ("annual_benchmark", "", "moderate",
                        "label owner (2026-10-03): moderate. Benchmark issued May 16, 2025; the same-day ALFRED snapshot shows only "
                        "routine revisions and the historical revisions first appear in this later snapshot (unexplained timing gap)"),
    "FDC-M3-20190524": ("seasonal_factor_recompute", "", "strong",
                        "manual: the notice is a seasonal-model revision, not a benchmark: 'On May 16, 2019, monthly seasonally "
                        "adjusted data ... were revised for January 2002 through March 2019'; historical data not seasonally adjusted "
                        "were unchanged. First ALFRED snapshot after May 16, 2019"),
    "FDC-M3-20190604": ("seasonal_factor_recompute", "", "strong",
                        "manual: as FDC-M3-20190524 (seasonal-model notice of May 16, 2019; not a benchmark)"),
    "FDC-M3-20240514": ("seasonal_factor_recompute", "", "strong",
                        "manual: the notice is a seasonal-model revision, not a benchmark: 'On May 14, 2024, monthly seasonally "
                        "adjusted data ... were revised for January 2012 through March 2024'; historical data not seasonally "
                        "adjusted were unchanged"),
    "FDC-M3-20010521": ("rebase_or_definition", "annual_benchmark", "strong",
                        "manual: the notice lists retabulating SIC-based monthly data to NAICS and benchmarking to the 1997 Economic "
                        "Census and 1998-1999 ASM (mixed causes); notices give May 21 and May 25, 2001 as the issue date"),
    "FDC-M3-20010525": ("rebase_or_definition", "annual_benchmark", "strong",
                        "manual: as FDC-M3-20010521 (SIC-to-NAICS retabulation plus benchmark; issue date stated as May 21 or "
                        "May 25, 2001)"),
    "FDC-M3-20130524": ("unknown", "", "none",
                        "manual: this snapshot restores values identical to the pre-benchmark snapshot of 2013-05-03; no government "
                        "source explains it"),
    "FDC-M3-20130528": ("unknown", "", "none",
                        "manual: this snapshot reinstates values identical to the benchmark snapshot of 2013-05-17; no government "
                        "source explains the reversal and reinstatement"),
    "FDC-M3-19970618": ("unknown", "", "weak",
                        "manual: the May 1997 full report says its data are consistent with the revised historical series released "
                        "June 18, 1997 (= this snapshot); the type of revision is not stated (cf. FDC-M3-19980729)"),
    "FDC-MARTS-20020503": ("annual_benchmark", "", "moderate",
                           "label owner (2026-10-03): moderate, not strong. The report identifies the revision periods, but its "
                           "two-column layout scrambles the extracted text; the January 1992 attribution partly relies on the report's title range. The standing paragraph on samples introduced with "
                           "the 1999 ARTS and March 2001 MRTS describes earlier survey design, not a sample introduced by this release"),
    "FDC-MARTS-20030430": ("annual_benchmark", "", "moderate",
                           "label owner (2026-10-03): moderate, not strong. The report identifies the revision periods, but its "
                           "two-column layout scrambles the extracted text. The standing paragraph on samples introduced with "
                           "the 1999 ARTS and March 2001 MRTS describes earlier survey design, not a sample introduced by this release"),
    "FDC-MARTS-20040330": ("annual_benchmark", "", "moderate",
                           "label owner (2026-10-03): moderate, not strong. The report identifies the revision periods, but its "
                           "two-column layout scrambles the extracted text. The standing paragraph on samples introduced with "
                           "the 1999 ARTS and March 2001 MRTS describes earlier survey design, not a sample introduced by this release"),
    "FDC-MARTS-20050331": ("annual_benchmark", "", "moderate",
                           "label owner (2026-10-03): moderate, not strong. The report identifies the revision periods, but its "
                           "two-column layout scrambles the extracted text. The standing paragraph on samples introduced with "
                           "the 1999 ARTS and March 2001 MRTS describes earlier survey design, not a sample introduced by this release"),
    "FDC-MARTS-20060330": ("annual_benchmark", "", "moderate",
                           "label owner (2026-10-03): moderate, not strong. The report identifies the revision periods, but its "
                           "two-column layout scrambles the extracted text. The standing paragraph on samples introduced with "
                           "the 1999 ARTS and March 2001 MRTS describes earlier survey design, not a sample introduced by this release"),
    "FDC-MARTS-20110429": ("annual_benchmark", "", "moderate",
                           "manual: RSXFS SA start 2000-01 = stated; RSAFS 1995-01 = stated NAICS 722 exception ('as far back "
                           "as January 1995'); RSAFSNA observed 1998-02 lies inside the stated NAICS 722 NSA range from "
                           "January 1998 (first revised month one month later than stated)"),
    "FDC-MARTS-20130531": ("annual_benchmark", "sample_redesign", "moderate",
                           "manual: document states the estimates reflect a newly selected sample on a 2007 NAICS basis and "
                           "that not adjusted sales (prior samples, historical corrections) and NAICS 446 adjusted sales are "
                           "revised from January 1992; observed starts 1992-05 (SA) and 1992-06 (NSA) lie inside that range"),
    "FDC-MARTS-20150513": ("annual_benchmark", "", "moderate",
                           "manual: RSAFSNA start 2003-01 = stated; SA observed 2000-02 lies inside the stated range for NAICS "
                           "levels affected by the NAICS 443112 revision (factors from January 2000)"),
    "FDC-MARTS-20160715": ("unknown", "", "none",
                           "manual: the 2016 annual revision is the separate release FDC-MARTS-20160513; no source explains this "
                           "July vintage (depth 16, one month beyond the routine window)"),
    "FDC-M3-19980729": ("unknown", "", "weak",
                        "manual: the next full report (June 1998, issued 1998-08-06) says its data are consistent with the "
                        "revised historical series released July 21, 1998, which ties this vintage's timing to that "
                        "historical revision; no located source states what kind of revision it was (the archived May 1998 "
                        "report's back page announcing upcoming revisions is not in the PDF)"),
    "FDC-M3-20020424": ("unknown", "", "none",
                        "manual: the located notice announces the benchmark revision for June 19, 2002, after this vintage; "
                        "no source explains this April vintage"),
    "FDC-MTIS-19980514": ("unknown", "", "none", "manual: release located (1998-05-14); its text carries no revision notice"),
    "FDC-MTIS-20000512": ("unknown", "", "none",
                          "manual: the archive copy for this release (mtis0003.txt) holds the data tables only, no text"),
    "FDC-MTIS-20000614": ("unknown", "", "none",
                          "manual: the archive copy for this release (mtis0004.txt) holds the data tables only, no text"),
    "FDC-MRTS-20180314": ("unknown", "", "none",
                          "manual: the 2018 annual revision is the separate release FDC-MRTS-20180525; its document does not "
                          "explain this March vintage"),
}


# Census Monthly Wholesale Trade annual revision (benchmark) reports, located on manual review 2026-10-03. They are the
# component documents for MTIS releases whose notice cites a wholesale revision.
WHOLESALE_DOC = {"FDC-MTIS-20030414": "2003", "FDC-MTIS-20040312": "2004", "FDC-MTIS-20050414": "2005",
                 "FDC-MTIS-20060413": "2006", "FDC-MTIS-20070416": "2007", "FDC-MTIS-20080414": "2008",
                 "FDC-MTIS-20090414": "2009", "FDC-MTIS-20100414": "2010", "FDC-MTIS-20110413": "2011",
                 "FDC-MTIS-20120416": "2012", "FDC-MTIS-20130613": "2013", "FDC-MTIS-20140414": "2014",
                 "FDC-MTIS-20150414": "2015", "FDC-MTIS-20160413": "2016", "FDC-MTIS-20170414": "2017",
                 "FDC-MTIS-20180614": "2018", "FDC-MTIS-20190418": "2019",
                 # 2020-2025 revisions notices: overlooked in the first search (folder listing truncated); identified
                 # by the label owner 2026-10-03
                 "FDC-MTIS-20200415": "2020", "FDC-MTIS-20210415": "2021", "FDC-MTIS-20220414": "2022",
                 "FDC-MTIS-20230414": "2023", "FDC-MTIS-20240415": "2024", "FDC-MTIS-20250416": "2025"}


def wholesale_row(cid):
    y = WHOLESALE_DOC[cid]
    name = f"{y}_mwts_revisions_notice.pdf" if int(y) >= 2019 else f"{y}_mwts_benchmark.pdf"
    url = "https://www2.census.gov/wholesale/pdf/mwts/historic/old_benchmarks/" + name
    title = (f"Monthly Wholesale Trade {y} Revisions Notice" if int(y) >= 2019
             else f"Monthly Wholesale Trade Survey annual revision (benchmark) report, {y}")
    sid, path = fetch(url, "U.S. Census Bureau", title, "benchmark_report", f"mwts-annual-{y}", "")
    if not sid:
        return None
    t = flat(text_of(path))
    q = [m.group(0) for m in re.finditer(r"[^.]{0,40}(?:[Ss]easonally adjusted|Corresponding seasonally adjusted|"
                                         r"[Uu]nadjusted|Not adjusted)[^.]{0,120}(?:are|were) revised for [^.]{0,80}\.", t)][:3]
    iss = re.search(r"Issued (?:" + "|".join(MONTHS) + r") \d{4}|[Rr]eleased (?:on )?(?:" + "|".join(MONTHS) + r") \d{1,2}, \d{4}", t)
    return {"source_id": sid, "quote": " ".join(q)[:1200] or (iss.group(0) if iss else ""),
            "locator": "wholesale annual revision report" + (f" ({iss.group(0)})" if iss else ""),
            "check": "component document (wholesale) for the revision named in the MTIS notice"}


def mtis_manual(cid):
    url, needle, check, cause, conf = MTIS_MANUAL[cid]
    sid = "SRC-" + hashlib.sha256(url.encode()).hexdigest()[:10].upper()
    path = cache_path(url)
    t = open(path + ".txt", encoding="utf-8", errors="replace").read() if os.path.exists(path + ".txt") else text_of(path)
    lines = t.split("\n")
    i = next((k for k, l in enumerate(lines) if needle in l), None)
    q = " ".join(l.strip() for l in lines[i:i + (4 if needle == "SPECIAL NOTICE" else 2)]) if i is not None else ""
    return {"source_id": sid, "quote": q, "locator": "release header, notice paragraph", "check": check}, \
        (cause, "", conf, "manual reading of the release notice (keyword screen missed it)")


def recommend(c, ev, rows, note):
    """Claude's recommendation. Confidence: strong = release-specific agency source + footprint match;
    moderate = release-specific source without a numeric check, or program-level source + consistent footprint;
    weak = context only; none = no source found (recommend unknown)."""
    rules = set(c.proposed_rules.split(";"))
    checks = " ".join(r.get("check", "") for r in rows)
    has_match = "MATCH" in checks and "DIFFERENT" not in checks
    has_diff = "DIFFERENT" in checks
    if "R02_REBASE" in rules:
        return "rebase_or_definition", "", "moderate" if not rows else "strong", \
            "constant-ratio rescaling of the whole shared history (data signature); release-specific source not located"
    if c.release_program in ("MARTS", "MRTS") and rows:
        sec = rows[0].get("secondary_flags", "")
        secondary = "sample_redesign" if "sample_redesign" in sec else ("rebase_or_definition" if "rebase" in sec else "")
        if "R30_CENSUS_ANNUAL" in rules or int(c.max_depth_months) > 24:
            return "annual_benchmark", secondary, "strong" if has_match else ("moderate" if not has_diff else "weak"), \
                "Census annual revision document for this year" + ("; stated revision start matches observed" if has_match else "")
    if c.release_program in ("MARTS", "MRTS") and int(c.max_depth_months) <= 24:
        return "advance_to_revised", "", "moderate", "depth slightly beyond the routine window; consistent with concurrent " \
            "seasonal adjustment (program-level source R20/R22); no release-specific notice"
    if c.release_program == "M3":
        q = " ".join(r["quote"].lower() for r in rows)
        # standing footnote in every 2001-2010s report; not a notice of a coverage change (fixed 2026-10-03)
        q = q.replace("figures on new and unfilled orders exclude data for semiconductor manufacturing", "")
        q = q.replace("unfilled orders to shipments ratio excludes semiconductor manufacturing", "")
        if re.search(r"(add|includ|now cover)[^.]{0,80}semiconductor|semiconductor[^.]{0,80}(added|now included)", q) \
                and "R30_CENSUS_ANNUAL" not in rules:
            return "methodology_change", "", "moderate", "M3 notice: revised estimates add the semiconductor industry"
        if "seasonal adjustment models" in q and "benchmark" not in q:
            return "seasonal_factor_recompute", "", "strong" if any(r.get("agency_issue_date") == c.vintage_date
                                                                   for r in rows) else "moderate", \
                "M3 notice: seasonally adjusted data revised because of updated seasonal adjustment models (no benchmark)"
        if rows and any(r.get("agency_issue_date") for r in rows):
            iss = [r["agency_issue_date"] for r in rows if r.get("agency_issue_date")]
            ok = any(0 <= (pd.Timestamp(c.vintage_date) - pd.Timestamp(x)).days <= 45 for x in iss)
            if ok:
                return "annual_benchmark", "", "strong" if (has_match or not has_diff) else "moderate", \
                    "M3 benchmark notice: historical data issued shortly before this vintage"
        if rows:
            return ("annual_benchmark" if "R30_CENSUS_ANNUAL" in rules else "unknown"), "", "weak", \
                "revision-related text found near this vintage but no dated benchmark notice"
    if c.release_program == "MTIS" and rows:
        q = " ".join(r["quote"].lower() for r in rows)
        q = q.replace("figures on new and unfilled orders exclude data for semiconductor manufacturing", "")
        q = q.replace("unfilled orders to shipments ratio excludes semiconductor manufacturing", "")
        if re.search(r"(add|includ|now cover)[^.]{0,80}semiconductor|semiconductor[^.]{0,80}(added|now included)", q):
            return "methodology_change", "", "moderate", "MTIS notice: revised manufacturing estimates add an industry " \
                "(coverage change), released outside the annual-revision season"
        if any(k in q for k in ["annual", "benchmark", "reflect revisions", "revisions to the", "were published",
                                "are reflected in this release", "revised historical"]):
            conf = "strong" if (has_match or (not has_diff and "R30_CENSUS_ANNUAL" in rules)) else "moderate"
            return "annual_benchmark", "", conf, "MTIS release dated on this vintage carries a revision notice for its " \
                "component surveys (retail, wholesale or manufacturing annual revision)"
        if "R30_CENSUS_ANNUAL" in rules:
            return "annual_benchmark", "", "weak", "MTIS release located but its text does not state the revision"
    if c.release_program in ("CPI", "PPI") and "R10_BLS_SA_FEB" in rules:
        if rows:
            return "seasonal_factor_recompute", "", "strong" if has_match else "moderate", \
                "BLS release on this date announces the annual seasonal-factor recalculation"
        return "seasonal_factor_recompute", "", "moderate", \
            "program-level BLS policy (5-year replacement since 1977); depth censored by the ALFRED vintage window" \
            if bool(c.any_depth_censored) else "program-level BLS policy; no release-specific document online"
    if "R30_CENSUS_ANNUAL" in rules:
        return "annual_benchmark", "", "weak", "spring timing and depth only; " + (note or "no source located")
    return "unknown", "", "none", note or "no agency source located"


def main():
    global OFFLINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    OFFLINE = ap.parse_args().offline
    os.makedirs(EVID, exist_ok=True)
    clusters = pd.read_csv(os.path.join(PROCESSED, "release_clusters.csv"))
    events = pd.read_csv(os.path.join(PROCESSED, "proposed_events.csv"))
    re_df = rule_evidence()
    spec = specials()
    out = []
    for c in clusters.itertuples():
        ev = events[events.release_cluster_id == c.release_cluster_id]
        rows, note, rec = [], "", None
        if c.release_cluster_id in spec:
            rows, cause, sec, conf = spec[c.release_cluster_id]
            rec = (cause, sec, conf, "release-specific source (see quote)")
        elif c.release_program in ("MARTS", "MRTS"):
            rows, note = cluster_retail(c, ev)
        elif c.release_program == "M3":
            rows, note = cluster_m3(c, ev)
        elif c.release_program == "MTIS":
            rows, note = cluster_mtis(c, ev)
        elif c.release_program in ("CPI", "PPI") and "R10_BLS_SA_FEB" in c.proposed_rules:
            rows, note = cluster_bls_feb(c, ev, c.release_program.lower())
        if rec is None:
            rec = recommend(c, ev, rows, note)
        if (c.release_program == "CPI" and "R10_BLS_SA_FEB" in c.proposed_rules and not rows
                and c.release_cluster_id not in spec):
            # program-level BLS source (retrospective): the 1977 entry of the seasonal-adjustment timeline
            tl_url = "https://www.bls.gov/cpi/seasonal-adjustment/timeline-seasonal-adjustment-methodology-changes.htm"
            tl_sid = "SRC-" + hashlib.sha256(tl_url.encode()).hexdigest()[:10].upper()
            tl_q = ("The updated seasonal data at the end of 1977 replaced data from 1967 to 1977. BLS announced that "
                    "subsequent annual updates would replace 5 years of seasonal data.")
            if int(c.vintage_date[:4]) >= 1978:
                rows = [{"source_id": tl_sid, "quote": tl_q, "locator": "timeline entry 1977 (program-level, retrospective)",
                         "check": note + (" | " if note else "") + "program-level: annual February replacement of 5 years of "
                                  "seasonal data announced by BLS at the end of 1977; no release-specific document"}]
            else:
                rec = ("unknown", "", "none", "the BLS 5-year annual replacement policy was announced at the end of 1977, after "
                       "this vintage; no source covers this February revision")
        if c.release_cluster_id in WHOLESALE_DOC:
            wr = wholesale_row(c.release_cluster_id)
            if wr:
                rows = rows + [wr]
        if c.release_cluster_id in MANUAL_ASSESS:
            cause_, sec_, conf_, note_ = MANUAL_ASSESS[c.release_cluster_id]
            rec = (cause_, sec_, conf_, note_)
            for r_ in rows:
                r_["check"] = (r_.get("check", "") + " || " + note_).strip(" |")
            if not rows:
                note = note_
        if c.release_cluster_id in MTIS_MANUAL:
            row, rec = mtis_manual(c.release_cluster_id)
            rows = [row] + [r for r in rows if r.get("source_id") != row["source_id"]]
        cause, sec, conf, basis = rec
        out.append({"release_cluster_id": c.release_cluster_id, "release_program": c.release_program,
                    "vintage_date": c.vintage_date, "series": c.series, "n_events": c.n_events,
                    "proposed_rules": c.proposed_rules, "earliest_revised_obs": c.earliest_revised_obs,
                    "max_depth_months": c.max_depth_months, "any_depth_censored": c.any_depth_censored,
                    "source_ids": ";".join(r["source_id"] for r in rows if r.get("source_id")),
                    "evidence_quote": " || ".join(r["quote"] for r in rows)[:3000],
                    "evidence_locator": " || ".join(r.get("locator", "") for r in rows),
                    "agency_issue_date": ";".join(r.get("agency_issue_date", "") for r in rows if r.get("agency_issue_date")),
                    "automated_check": " || ".join(r.get("check", "") for r in rows) or note,
                    "recommended_cause": cause, "recommended_secondary_cause": sec, "confidence": conf,
                    "recommendation_basis": basis})
        print(f"{c.release_cluster_id:28s} {cause:26s} {conf:9s} {len(rows)} src")
    pd.DataFrame(out).to_csv(os.path.join(EVID, "cluster_evidence.csv"), index=False)
    re_df.to_csv(os.path.join(EVID, "rule_evidence.csv"), index=False)
    reg = pd.DataFrame(sorted(REGISTRY.values(), key=lambda r: r["source_id"]))
    reg.to_csv(os.path.join(EVID, "source_registry.csv"), index=False)
    print(f"sources {len(reg)} | clusters {len(out)} | confidence: "
          f"{pd.Series([o['confidence'] for o in out]).value_counts().to_dict()}")


if __name__ == "__main__":
    main()
