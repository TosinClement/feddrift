# Data license

FedDrift's own data products are licensed under the **Creative Commons Attribution 4.0 International License (CC BY 4.0)**: https://creativecommons.org/licenses/by/4.0/. They are:
- `data/processed/` (event tables, footprints, QA);
- `data/manifests/`;
- `labels/`;
- `evidence/` (registry and quotes);
- `paper/`, `zenodo/` and the documentation.

Attribution: Clement, T. (2026). FedDrift: vintage-labeled distribution shift in U.S. federal economic and freight statistics (Version 0.1.0). Zenodo. https://doi.org/10.5281/zenodo.23143665

Agency values in `data/raw/agency/` and `data/processed/anchor_vintage.csv` are works of the U.S. Government and are in the public domain in the United States; FedDrift claims no rights in them. Sources: U.S. Census Bureau; U.S. Bureau of Labor Statistics; U.S. Department of Transportation, Bureau of Transportation Statistics.

ALFRED/FRED observation values are not redistributed (`docs/LICENSING_PROTOCOL.md`). Users who rebuild them with `code/03_fetch_alfred.py` are bound by the FRED API Terms of Use. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.
