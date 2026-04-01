# Apple ETL scripts (explore + load)

This folder contains three Apple Health ETL scripts:

1. `id_record_types.py` *(exploratory)*
  - Scans `export.xml`
  - Lists all `<Record type="...">` values
  - Summarizes attributes and child tags by record type
  - Output: `data/apple/record_type_field_summary.json`

2. `fetch_relevant_fields.py` *(exploratory)*
  - Scans `export.xml`
  - Filters for heart-rate, steps, and sleep-related record types
  - Summarizes counts/fields/tags for those filtered records
  - Output: `data/apple/hr_steps_sleep_record_types.json`

3. `load_hr_steps_sleep.py` *(parse + load)*
  - Parses relevant Apple records (HR/steps/sleep)
  - Loads data into Postgres tables
  - Sleep loading is restricted to `HKCategoryTypeIdentifierSleepAnalysis`

## Input file (local only)

- Place Apple Health `export.xml` at `data/apple/export.xml`.
- This file is local-only and should not be committed.

---

## Prerequisites

---

### 1) Create a local virtual environment

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Use that local venv when running the Apple ETL scripts.


### 2) Start test Postgres container

Use the test compose file at repo root:

```bash
docker compose -f test.compose.yaml up -d
```

This starts Postgres, pgAdmin, and Jupyter.


### 3) Open pgAdmin

- Open `http://localhost:5050`
- Log in with:
  - Email: `admin@example.com`
  - Password: `openvitals`


### 3b) Open Jupyter (optional for visualization notebooks)

- Open `http://localhost:8888`


### 4) Register the Postgres server in pgAdmin

Create a new server connection with:

- Name: `openvitals-test`
- Host: `postgres`
- Port: `5432`
- Maintenance DB: `openvitals`
- Username: `openvitals`
- Password: `openvitals`


### 5) Create tables manually in pgAdmin

Use test SQL only.

Open [sql/test/example_tables.sql](sql/test/example_tables.sql), copy the SQL, then paste it into the pgAdmin Query Tool for the `openvitals` database and run it.

Notes:
- Keep schema creation manual for now.
- Do **not** use `sql/migrations` for this workflow.

---

## Run sequence

From repo root:

- Exploratory record inventory: `python etl/apple/id_record_types.py`
- Exploratory filtered summary (HR/steps/sleep): `python etl/apple/fetch_relevant_fields.py`
- Parse + load relevant Apple data: `python etl/apple/load_hr_steps_sleep.py --only all`

For notebook visualization, use `--only all` so all required test data is loaded (steps, sleep, and resting heart rate).

If your venv is not already activated, use `.venv/bin/python` instead of `python`.

Depending on how large `data/apple/export.xml` is, the load step may take a while to finish.

Optional loader filters:

- `python etl/apple/load_hr_steps_sleep.py --only heart_rate`
- `python etl/apple/load_hr_steps_sleep.py --only steps`
- `python etl/apple/load_hr_steps_sleep.py --only sleep`

---

## Connection details

`load_hr_steps_sleep.py` currently uses:

- `host=localhost`
- `port=5432`
- `user=openvitals`
- `dbname=openvitals`
- `password=openvitals`

These should match your `test.compose.yaml` container settings.

---

## Validate data and run notebooks (test only)

After loading, you can validate either way:

### Option A) Validate in pgAdmin Query Tool

Run each split query file in pgAdmin:

- [sql/test/queries/01_steps_merged_daily.sql](sql/test/queries/01_steps_merged_daily.sql)
- [sql/test/queries/02_sleep_by_stage_night_of.sql](sql/test/queries/02_sleep_by_stage_night_of.sql)
- [sql/test/queries/03_total_sleep_per_night.sql](sql/test/queries/03_total_sleep_per_night.sql)
- [sql/test/queries/04_resting_hr_daily.sql](sql/test/queries/04_resting_hr_daily.sql)

### Option B) Validate by running notebooks

Open Jupyter at `http://localhost:8888` and run these notebooks in order (Cell 1, then Cell 2):

- `notebooks/01_steps_merged_daily.ipynb`
- `notebooks/02_sleep_by_stage_night_of.ipynb`
- `notebooks/03_total_sleep_per_night.ipynb`
- `notebooks/04_resting_hr_daily.ipynb`

Notebook connection is set to:

- `postgresql+psycopg://openvitals:openvitals@postgres:5432/openvitals`


