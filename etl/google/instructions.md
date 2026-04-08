# Google / Fitbit ETL scripts (explore + load)

This folder contains three Google Takeout ETL scripts, mirroring the Apple ETL pipeline.

1. `id_record_types.py` *(exploratory)*
   - Walks the entire Takeout directory tree
   - Inventories all vendors (Google Fit, Fitbit), file types, and data schemas
   - For Google Fit JSON files, reads the `Data Source` field to extract data types
   - Output: `data/google/record_type_field_summary.json`

2. `fetch_relevant_fields.py` *(exploratory)*
   - Filters the Takeout data down to heart rate, steps, and sleep sources
   - Maps where each data type lives across Google Fit and Fitbit directories
   - Reports record counts per source
   - Output: `data/google/hr_steps_sleep_record_types.json`

3. `load_hr_steps_sleep.py` *(parse + load)*
   - Parses Google Fit JSON and Fitbit JSON files
   - Loads data into the same vendor-agnostic Postgres tables used by the Apple pipeline
   - Supports `--only` flag to load heart_rate, steps, or sleep individually

## Input data (local only)

- Place Google Takeout export (unzipped) at `data/google/Takeout/`.
- Expected structure: `Takeout/Fit/` and `Takeout/Fitbit/` directories.
- This data is local-only and should not be committed.

---

## Prerequisites

Same as Apple ETL — see `etl/apple/instructions.md` for venv and Docker setup.

---

## Run sequence

From repo root:

```bash
python etl/google/id_record_types.py
python etl/google/fetch_relevant_fields.py
python etl/google/load_hr_steps_sleep.py --only all
```

The load step processes ~7M+ records and takes several minutes.
Heart rate is the largest dataset (~7M records from Fitbit alone).

Optional loader filters:

- `python etl/google/load_hr_steps_sleep.py --only heart_rate`
- `python etl/google/load_hr_steps_sleep.py --only steps`
- `python etl/google/load_hr_steps_sleep.py --only sleep`

---

## Connection details

Same as Apple ETL:

- `host=localhost`, `port=5432`, `user=openvitals`, `dbname=openvitals`, `password=openvitals`

---

## Data source decisions and known issues

### Timestamps

Fitbit exports timestamps in the user's local time with **no timezone offset**.
When loaded into Postgres (which stores `timestamptz` as UTC), these are treated
as UTC — but they are actually local time. This means:

- **Do NOT apply `AT TIME ZONE` conversion** in queries for Fitbit data.
- Google Fit timestamps (nanosecond epoch) are true UTC and may need conversion,
  but for daily aggregation the difference is negligible.

### Resting Heart Rate (`04_resting_hr_daily_google.sql`)

- **Source:** Fitbit daily resting HR (`fitbit.resting_heart_rate` vendor_type).
- Fitbit provides one pre-computed value per day — no averaging needed.
- Values are within ~1 BPM of what the Fitbit app shows. The minor difference
  is likely Fitbit's proprietary smoothing algorithm.

### Sleep (`02` and `03` Google queries)

- **Source:** Fitbit sleep logs only (`vendor = 'fitbit'`).
- Google Fit sleep data is excluded — it's synced from Fitbit with degraded
  stage info (no "core" stage, everything mapped to asleep/deep/rem).
- **Night windowing:** Queries use an **8PM–8AM window** per night to exclude
  daytime naps and only count nighttime sleep. Sleep stages are clipped to the
  window boundaries using `LEAST`/`GREATEST`.
- Stages are mapped: Fitbit wake→awake, light→core, deep→deep, rem→rem.
- Total sleep = sum of core + deep + rem stages (excludes awake and legacy "asleep").
- Values are within 5–37 minutes of Fitbit app. Differences are due to Fitbit's
  proprietary calculation which likely handles brief awakenings differently.

### Duplicate sleep sessions at monthly file boundaries

Fitbit Takeout exports split sleep data into monthly JSON files
(`sleep-YYYY-MM-DD.json`). Sessions that fall near month boundaries appear in
**both** adjacent files — identical `startTime`/`endTime` and stage data.

- **Affected:** 5 out of ~180 nights (Nov 6, Dec 6, Jan 5, Feb 4, Mar 7) — all
  exactly 2x duplicated.
- **Loader fix:** `load_fitbit_sleep()` now checks for an existing session with
  the same `source_id + start_ts + end_ts` before inserting. Duplicates are skipped.
- **Query fix:** Sleep notebooks use a `unique_sessions` CTE with
  `DISTINCT ON (start_ts, end_ts)` as a defensive dedup in case existing data
  was loaded before the loader fix.

### Steps (`01_steps_daily_google.sql`)

- **Primary source:** Fitbit watch (`vendor = 'fitbit'`, `product = 'Fitbit'`).
- **Fallback source:** Pixel phone (`vendor = 'google'`, `product = 'Pixel 8 Pro'`)
  — used only when Fitbit watch has < 500 steps (watch was on charger).
- Google Fit `FitbitMobile` source is **excluded** — it contains double-counted
  data (watch + phone steps merged without proper dedup, often 2x the real value).
- Fitbit raw export runs ~5-10% higher than Fitbit app values due to app-side
  post-processing/smoothing that cannot be reproduced.
- The 500-step threshold was validated against 180 days of data: only 1 day
  (a known charger day) fell below this threshold.

### Overlap between Google Fit and Fitbit

The same underlying data often appears in both `Fit/` and `Fitbit/` directories
because Fitbit syncs to Google Fit. For all metrics, Fitbit is the authoritative
source because:

1. The watch is the primary sensor (worn all day vs. phone on desk).
2. Fitbit's per-second/per-minute data is more granular.
3. Google Fit's synced data often introduces artifacts (phantom steps, degraded sleep stages).

---

## Validate data and run notebooks

After loading, validate using Google query variants in pgAdmin:

- `sql/test/queries/01_steps_daily_google.sql`
- `sql/test/queries/02_sleep_by_stage_night_of_google.sql`
- `sql/test/queries/03_total_sleep_per_night_google.sql`
- `sql/test/queries/04_resting_hr_daily_google.sql`

Or run the Google notebooks in Jupyter at `http://localhost:8888`:

- `notebooks/05_steps_daily_google.ipynb`
- `notebooks/06_sleep_by_stage_google.ipynb`
- `notebooks/07_total_sleep_google.ipynb`
- `notebooks/08_resting_hr_google.ipynb`
