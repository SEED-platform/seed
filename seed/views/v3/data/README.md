# Benchmark CSV Sources

This directory contains file-backed benchmark datasets served by the SEED v3 benchmark data API.

Current files:

- `energystar_site_eui_by_category.csv`
- `energystar_site_eui_by_subcategory.csv`

Provenance:

- Source repository: [SEED-platform/compare-building-data](https://github.com/SEED-platform/compare-building-data)
- Source notebook: [1_pull_data.ipynb](https://github.com/SEED-platform/compare-building-data/blob/main/1_pull_data.ipynb)

Notes:

- These CSVs were copied into SEED for direct API serving without loading them into database tables.
- If the upstream extraction logic changes, regenerate the CSVs from the source notebook and replace the files in this directory.
- The API endpoint that serves these files is under `/api/v3/benchmark_data/site_eui/`.
- That endpoint defaults to `dataset=category` and `output_format=json` when those query parameters are omitted.
