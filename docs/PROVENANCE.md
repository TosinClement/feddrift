# Provenance

FedDrift records where every input came from, when it was fetched, and how to check that a copy is identical.

| Record | What it holds | Written by |
|---|---|---|
| `data/raw/PROVENANCE.txt` | One line per agency file in the snapshot: UTC fetch time, path, bytes, SHA-256, source URL, note | `code/01_fetch_agency.py` |
| `data/manifests/alfred_manifest.json` | Per ALFRED series: title, units, SA flag, FRED `last_updated`, FRED copyright tags, number and range of vintages, real-time row count, cache SHA-256, fetch time, exact API request (endpoint, `realtime_start`, `realtime_end`, `observation_start`, `output_type`) | `code/03_fetch_alfred.py` |
| `data/manifests/<SERIES>.vintages.csv` | Per vintage: date, observation count, first and last observation, content SHA-256 | `code/03_fetch_alfred.py` |
| `data/raw/alfred_cache/FETCH_LOG.txt` | Local log of each FRED API call, with the key redacted. Not redistributed | `code/03_fetch_alfred.py` |
| `evidence/source_registry.csv` | Every agency document cited as evidence: publisher, title, document id, publication date, URL, retrieval method, access time, SHA-256, bytes | `code/06_harvest_evidence.py` |
| `config/snapshot.json` | The pinned snapshot: agency snapshot directory and ALFRED real-time cutoff | committed by hand |

## Checking a copy

- **Agency files:** run `sha256sum` (macOS: `shasum -a 256`) on any file under `data/raw/agency/2026-10-03/` and compare the result with its line in `PROVENANCE.txt`. QA check Q01 does this for every file.
- **ALFRED history:** run `FRED_API_KEY=… python code/03_fetch_alfred.py`, then `python code/10_qa.py`. QA check Q03 rebuilds every vintage and compares it with the published manifest hash.
- **Evidence documents:** download the URL and compare its SHA-256 with the registry. Agency pages that change after the access date will differ. The quote recorded in `evidence/cluster_evidence.csv` is what the label owner reviewed.

## Retrieval notes

- Census bulk files: `https://www.census.gov/econ_getzippedfile/?programCode=<PROGRAM>`. The singular parameter `programCode` is required; the plural form returns HTTP 400.
- Census rejects some scripted user agents. FedDrift identifies itself with a browser-compatible string that includes a contact address.
- BLS LABSTAT asks automated clients to send a User-Agent with contact details. FedDrift does.
- bts.gov returns HTTP 403 to scripted clients. The two BTS revision-policy pages were read with a web reader, and the registry marks them `web_reader_quote_only` with no hash. The BTS data itself comes from `data.bts.gov` (Socrata), which allows scripted access.
- Census M3 full reports from before about 2003 are scanned images. The evidence step reads their first eight pages with OCR (tesseract), and the extracted text says so.
