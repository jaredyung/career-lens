# CareerLens

CareerLens is a labor-market intelligence dashboard for data careers, built with
Python, Adzuna job postings, DuckDB, and Streamlit. It helps users compare sampled
roles, employers, locations, and estimated compensation.

## Architecture

```text
Adzuna API
  → Python ingestion and normalization
  → title-based role classification
  → DuckDB
  → Streamlit labor-market intelligence dashboard
```

## Dashboard

- Global filters: job title, company, location, role, and minimum salary.
- Summary: Jobs Analyzed, Companies, Estimated Average Salary, and Estimated Median Salary.
- Role comparison: postings, employers, and estimated compensation side by side.
- Company intelligence: posting counts, career paths, locations, salaries, and listings.
- Salary analysis: a ten-bin distribution of salary-range midpoints.
- Job explorer: sortable, searchable postings with original links when available.
- About the Data: sample limitations and methodology.

All sections use the filtered sample. Selecting one role in the sidebar excludes
other roles from comparisons; excluded roles show zero postings. The minimum
salary filter keeps postings whose **estimated maximum** meets the threshold.
Title and location searches match literal text, ignoring case.

## Setup and run

Use Python 3.11 or newer. Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local `.env` file with your own `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` values.
Never commit credentials. Ingestion loads this file from the repository root;
existing environment variables take precedence.

```bash
python src/ingest.py
streamlit run app/app.py
```

Stop the dashboard before running ingestion or reclassification, then restart it.
This avoids DuckDB locks between separate reader and writer processes. The
project-local Streamlit theme is loaded when launching from the repository root.
Database paths are resolved relative to the project, regardless of the working directory.

## Ingestion and storage

`src/ingest.py` requests **up to 10 pages per search, with 50 results per page**,
for Data Scientist, Data Engineer, Data Analyst, Machine Learning Engineer, and
Analytics Engineer. It stops a search early if a page has fewer than 50 results.
Page count, page size, location, and search terms are defined at the top of the module.

Each posting is normalized and classified from its title. Unmatched titles become
`Other`. DuckDB stores the records in `data/careerlens.duckdb`, with the Adzuna
job ID as the primary key. Inserts explicitly map source fields to destination
columns, including `job_url` and `role_category`.

Repeated source IDs are ignored: the first stored record is retained. Ingestion
does not update existing rows, track revisions, remove expired postings, or create
historical snapshots. A zero-result fetch safely inserts nothing.

## Project structure

```text
.streamlit/config.toml   Light theme
app/app.py              Dashboard, filters, charts, and presentation helpers
src/database.py         Shared database path, schema, and explicit inserts
src/ingest.py           Adzuna retrieval, normalization, and pipeline entry point
src/roles.py            Shared career paths, classification, optional reclassification
src/analysis.py         Optional read-only command-line summary
tests/test_database.py  Column-mapping and deduplication regression tests
tests/test_ingest.py    Mocked ingestion, pagination, and classification tests
tests/test_app.py       Dashboard and global-filter regression tests
requirements.txt       Pinned direct application dependencies
.gitignore             Credentials, databases, backups, and local artifacts
README.md              Setup, workflow, and methodology
```

The local `.env`, `.venv/`, `data/`, and optional `backups/` are not source files
and are excluded from Git as appropriate.

## Optional utilities

```bash
python src/analysis.py
```

Prints total postings, top employers, and estimated average/median salaries using
the same complete-range midpoint definition as the dashboard. It opens DuckDB read-only.

```bash
python src/roles.py
```

Reclassifies existing rows using the current title rules. This is **not a normal
ingestion step**: ingestion already calls `classify_role()`. Use it after changing
classification rules or to repair old role labels. It does not modify job URLs.
Back up the database before manually changing stored data.

## Validation

```bash
python -m unittest discover -s tests -v
```

Tests use in-memory or temporary databases and mocked API calls. They do not
read credentials, contact Adzuna, or modify the local dataset.

## Data limitations

- This is a sampled Adzuna dataset, not a complete census of the labor market.
- Search terms, API ranking, pagination, and collection time affect the sample.
- Titles are classified with simple rules, not a trained model.
- Salaries are estimates and may differ from employer-posted compensation.
  Average and median use `(salary_min + salary_max) / 2`, excluding postings
  missing either endpoint. They are not guaranteed offers or market-wide benchmarks.
- Source-ID deduplication does not detect equivalent listings with different IDs.
- Stored postings can become stale or expire. Posting dates are source dates,
  not collection timestamps. Original links may become unavailable.
- Repeated ingestion accumulates unseen IDs; it does not measure hiring trends.

## Future work

Historical snapshots and trend tracking are future work, not implemented functionality.
