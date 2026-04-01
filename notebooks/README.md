# Apple Test Notebooks

These notebooks visualize Apple ETL test data in Postgres.

## Prerequisites

From repo root:

1. Start services:
	- `docker compose -f test.compose.yaml up -d`
	- This launches Postgres, pgAdmin, and Jupyter.
2. Create local venv and install dependencies:
	- `python3 -m venv .venv`
	- `source .venv/bin/activate`
	- `pip install -r requirements.txt`
3. Place Apple Health export file at:
	- `data/apple/export.xml`

## Load data before viewing notebooks

1. Open pgAdmin at `http://localhost:5050`
2. Run schema SQL manually from:
	- `sql/test/example_tables.sql`
3. Run ETL scripts from repo root:
	- `python etl/apple/id_record_types.py`
	- `python etl/apple/fetch_relevant_fields.py`
	- `python etl/apple/load_hr_steps_sleep.py --only all`

## Open and run notebooks

1. Open Jupyter Lab at `http://localhost:8888`
2. Run notebooks in order (Cell 1 then Cell 2):
	1. `01_steps_merged_daily.ipynb`
	2. `02_sleep_by_stage_night_of.ipynb`
	3. `03_total_sleep_per_night.ipynb`
	4. `04_resting_hr_daily.ipynb`

## Connection and scope notes

- Notebooks use: `postgresql+psycopg://openvitals:openvitals@postgres:5432/openvitals`
- Schema setup is manual.
- No migrations are used in this test workflow.
