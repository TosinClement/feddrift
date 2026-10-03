# FedDrift v0.1.0 release checklist

Do the steps in order. Steps marked **[Tosin]** require the author personally. Every other step is a command.

## A. Labels (gate condition)
1. **[Tosin]** Open `labels/review/FedDrift_label_review.xlsx`. Fill the yellow cells on the *Judgment calls*, *Rules* and *Releases* sheets, and any *Event overrides*.
2. `python code/import_review.py labels/review/FedDrift_label_review.xlsx`. The import refuses invalid rows and writes `labels/decisions/*.csv`.
3. `bash run_all.sh --from 08`. Check that `data/processed/label_status.json` reports `n_unverified: 0`.

## B. Reproduce
4. On a clean clone: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.
5. `export FRED_API_KEY=…` then `bash run_all.sh`. Expect QA with no FAIL and the release-level numbers unchanged (compare `paper/stats.json` with the committed copy).
6. `python -m pytest -q` passes.

## C. Final documents
7. `python code/11_figures_stats.py --final && python code/12_build_docs.py --final`.
8. **[Tosin]** Read `README.md`, `paper/feddrift_data_descriptor.md`, `docs/ETHICS_AND_LIMITATIONS.md` and `docs/LICENSING_PROTOCOL.md`. Revise anything you would not defend, in your own voice. Re-run step 7 if you edit generated text at its source (`code/12_build_docs.py`).
9. `python code/publish_gate.py . --stage pre-deposit` reports CLEAR. The only items it may list are the registered external identifiers.

## D. Identifiers and publication
10. **[Tosin]** Revoke the GitHub token pasted into chat on 2026-10-03 (GitHub → Settings → Developer settings → Personal access tokens). If authentication is needed, create a new fine-grained token limited to the single new repository with Contents: read/write.
11. **[Tosin]** Create the empty public repository on GitHub, for example `feddrift`.
12. **[Tosin]** Zenodo → New upload → *Reserve DOI*. Copy the DOI.
13. `python tools/fill_placeholders.py --set GITHUB_REPO_URL=https://github.com/<user>/feddrift --set ZENODO_DOI=<reserved DOI> --set RELEASE_DATE=<YYYY-MM-DD>`, then repeat step 7.
14. `python code/publish_gate.py . --stage final` reports CLEAR.
15. `python code/13_package.py --release`. This builds `dist/feddrift-0.1.0.tar.gz` and its `.MANIFEST.sha256`.
16. `git add -A && git commit -m "Release v0.1.0" && git tag -a v0.1.0 -m "FedDrift v0.1.0"`.
17. **[Tosin]** `git remote add origin https://github.com/<user>/feddrift.git && git push -u origin main --tags`.
18. **[Tosin]** Zenodo: upload `dist/feddrift-0.1.0.tar.gz`. Paste the metadata from `zenodo/zenodo_metadata.json` and the description from `zenodo/description.md`. Publish.
19. **[Tosin]** arXiv: submit `paper/feddrift_data_descriptor.md`, converted to PDF with figures, under `stat.ME` or `econ.EM`. The AI-assistance statement is in the descriptor. Once announced, fill `ARXIV_ID` with `tools/fill_placeholders.py`.
20. **[Tosin]** Record the URL, DOI, date and arXiv ID in your evidence log on the day of release.
