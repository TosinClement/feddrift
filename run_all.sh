#!/usr/bin/env bash
# FedDrift pipeline. Run from the repository root.
#
#   bash run_all.sh                    reproduce: pinned snapshot, rebuild ALFRED layer (needs FRED_API_KEY),
#                                      committed evidence, current label decisions, QA, benchmark, docs, tests
#   bash run_all.sh --final            same, but figures/documents in final mode (refused unless labels verified)
#   bash run_all.sh --from 08          start at step 08 (e.g. after importing label decisions)
#   bash run_all.sh --harvest          also re-download agency evidence documents (step 06, network)
#   bash run_all.sh --refresh-agency   fetch a NEW agency snapshot (step 01); changes published numbers
set -euo pipefail
cd "$(dirname "$0")"
FROM=02; FINAL=""; HARVEST=0; REFRESH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --from) FROM="$2"; shift 2 ;;
    --final) FINAL="--final"; shift ;;
    --harvest) HARVEST=1; shift ;;
    --refresh-agency) REFRESH=1; FROM=01; shift ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
done
step() { [[ "$1" < "$FROM" ]] && return 0; echo "== $1 $2"; shift 2; "$@"; }
[[ $REFRESH == 1 ]] && step 01 "fetch agency snapshot" python code/01_fetch_agency.py
step 02 "build agency anchor"   python code/02_build_anchor.py
if [[ "03" > "$FROM" || "03" == "$FROM" ]]; then
  : "${FRED_API_KEY:?Set FRED_API_KEY (free: https://fredaccount.stlouisfed.org/apikeys)}"
fi
step 03 "fetch ALFRED (pinned)" python code/03_fetch_alfred.py
step 04 "vintage-pair footprints" python code/04_vintage_pairs.py
step 05 "events, proposals, releases" python code/05_propose_labels.py
if [[ $HARVEST == 1 ]]; then step 06 "harvest agency evidence" python code/06_harvest_evidence.py; fi
step 07 "review package"        python code/07_build_review.py
step 08 "apply label decisions" python code/08_apply_labels.py
step 09 "benchmark"             python code/09_benchmark.py
step 10 "quality assurance"     python code/10_qa.py
step 11 "figures and stats"     python code/11_figures_stats.py $FINAL
step 12 "README, descriptor, Zenodo text" python code/12_build_docs.py $FINAL
echo "== tests"; python -m pytest -q tests
