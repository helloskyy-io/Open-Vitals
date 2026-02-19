# Reclaiming Wearable Health Data

## Class Project Proposal (CSCI/DASC 6010)

### Title

**Reclaiming Wearable Health Data: An Empirical Analysis of Vendor Lock-In and Reproducible Health Analytics**

---

### 1. Introduction and Motivation

Consumer wearable devices such as smartwatches and fitness trackers generate continuous, high-volume streams of personal health data. These data increasingly influence individual fitness decisions and, in some cases, clinical discussions. Despite this, most wearable data is stored and interpreted within proprietary ecosystems (e.g., Google Fit, Apple Health), where the vendor controls both the storage of raw data and the computation of higher-level health metrics.

This project is motivated by a central question in modern data analytics and data management: **to what extent can meaningful health analytics be reproduced from raw wearable data outside of proprietary platforms?** If users export their own data and store it independently, can they recover the same insights that vendors provide, or do proprietary transformations fundamentally limit transparency and portability?

This problem is not only technical but also representative of broader issues in big data systems, including data ownership, reproducibility, and vendor lock-in. By focusing on real-world wearable datasets, this project aims to analyze these issues empirically.

---

### 2. Research Questions

**Primary Research Question**
Which wearable health analytics can be reproduced from raw user data outside proprietary vendor platforms?

**Secondary Research Question**
What information is lost, altered, or obscured when wearable health data is migrated across vendor ecosystems?

---

### 3. Data

The dataset for this project is constructed from real-world wearable health data exported from multiple consumer platforms:

* Google Fit data exported from a Pixel phone and Pixel Watch
* Apple Health data exported from an Apple Watch

These datasets include longitudinal, time-series measurements such as:

* Daily step counts
* Heart rate samples
* Sleep sessions and total sleep duration

The data exhibits key big data characteristics, including high temporal resolution, heterogeneous schemas, missing values, and platform-specific representations. Dataset documentation will follow the *Datasheets for Datasets* framework, detailing data provenance, structure, known limitations, and ethical considerations. All data used in the project is voluntarily provided by the data subjects and used solely for academic analysis.

---

### 4. Method

The project implements a reproducible analytics pipeline consisting of the following stages:

1. **Data Export and Ingestion**
   Raw wearable data is exported from Google Fit and Apple Health and ingested into a local analysis environment.

2. **Normalization and Storage**
   Vendor-specific schemas are transformed into a unified, vendor-agnostic data model and stored in a database designed for time-series analytics.

3. **Metric Reproduction**
   Selected health metrics are recomputed using transparent, open methods. For this project, the focus is on three core metrics:

   * Daily step count
   * Total sleep duration per day
   * Resting heart rate (derived from heart rate samples)

4. **Comparison and Evaluation**
   Reproduced metrics are compared quantitatively against vendor-provided summaries to assess agreement, divergence, and loss of information.

To ensure reproducibility and reliability of the ingestion process, workflow orchestration is implemented using Temporal. Temporal provides deterministic execution, retry safety, and an auditable history of ingestion and transformation steps, supporting scientific repeatability.

---

### 5. Results

Results are evaluated using:

* Correlation and error analysis between vendor-reported and reproduced metrics
* Cross-platform comparisons for equivalent metrics
* Visualizations highlighting discrepancies, missing data, and alignment over time

All figures include labeled axes, descriptive captions, and are selected to clearly communicate empirical findings without redundancy.

---

### 6. Discussion and Future Work

The discussion analyzes which wearable health insights are transparently reproducible and which rely on proprietary transformations. The implications of these findings are discussed in the context of data ownership, reproducibility, and user trust in large-scale health analytics systems.

Future work includes expanding the dataset to additional users and devices, incorporating more advanced analytics, and exploring open-source platforms that enable individuals to maintain full ownership and control of their wearable health data.

---

### 7. Action items:
1. Develop plan of attack flush out more detail of each above step, with a check list of items to completion
2. Develop an initial component stack of OS components that are needed
3. Develop an initial folder structure for the repo
4. Develop a division of responsibilities for each team member
5. Start a Temporal based automated deployment and configuration of the VM.
6. Agree on how to manage data for end of class presentation (all on one machine? or switch between machines for Apple vs. Google?) 




# Phase 0 Implementation Checklist (v3)

**Project:** OpenVitals  
**Phase:** 0 — Research Prototype (Class Project)  
**Canonical layout:** Paths in this checklist follow `docs/file_structure.txt` (single source of truth for repo layout).

**Core Metrics (Set A):** Steps/day, Sleep duration/day, Resting heart rate (derived)  
**Packaging:** Docker Compose (containerized stack; see `docker/`)  
**Databases:** Postgres (OpenVitals data) + Postgres (Temporal data)  
**Orchestration Target:** Temporal (bonus in Phase 0; required in Phase 1+)  
**Phase 0 UI:** **None** (plots generated via scripts/notebooks; figures used in report/presentation)

---

## Phase 0 Goals

* Build a reproducible dataset from wearable exports (Google Fit via Takeout, Apple Health export)
* Normalize into a canonical schema (v0)
* Reproduce Set A metrics via transparent methods
* Compare reproduced metrics against vendor-provided values where available
* Generate figures + empirical findings aligned to course rubric

---

## Team Split (recommended)

* **Member A (Google):** Google Takeout / Fit ingestion adapter
* **Member B (Apple):** Apple Health ingestion adapter
* **Member C (Analytics):** Metrics, comparison, plots, report/presentation

All members:

* Review and agree on canonical schema v0 and metric definitions

---

# Stage 0 — Repo + Stack Bootstrap (Day 0)

**Deployment flow:** Bootstrap brings up Temporal (DB, server, UI); then Genesis workflow (via `genesis.sh`) deploys OpenVitals Postgres and runs migrations. Standards: `docs/standards/temporal_standards.md`, `docs/standards/temporal_deployment.md`.

### 0.1 Repo baseline

* [x] Create / confirm repo skeleton directories (see `docs/file_structure.txt` for full tree):

  * [x] `src/openvitals/` (Python package: adapters, analytics, analysis, models, orchestration/temporal)
  * [x] `src/openvitals/adapters/` (vendor adapters: apple_health, google_fit)
  * [x] `src/openvitals/analytics/` (metrics + evaluation)
  * [x] `src/openvitals/orchestration/temporal/` (Temporal: activities/ + modules/bootstrap; worker + stub Genesis)
  * [x] `docker/` — `docker/compose/` with numbered base files + overrides (see `docs/standards/docker_compose_layout.md`)
  * [x] `sql/` (schema + migrations)
  * [x] `data/raw/`, `data/processed/` (gitignored)
  * [x] `reports/` (figures + writeups)
  * [x] `docs/` (project docs; `docs/development/` for Phase 0 checklist)
  * [x] `notebooks/`, [x] `scripts/`, [x] `templates/`, [x] `tests/`

* [x] Add `.gitignore` entries:

  * [x] `data/`
  * [x] `.env`
  * [x] `__pycache__/`
  * [x] `*.ipynb_checkpoints`

### 0.2 Docker Compose (Phase 0)

Layout: `docker/compose/00-networks.yml`, `10-temporal.yml`, and env overrides (`dev.override.yml`, `test.override.yml`, `prod.override.yml`). Override chosen via `config.yaml` → `temporal.deployment_env`. See `docs/standards/docker_compose_layout.md`.

* [x] Temporal stack (in `docker/compose/10-temporal.yml`):

  * [x] `temporal-db` (Postgres for Temporal)
  * [x] `temporal-server`
  * [x] `temporal-ui` (host port 8234 to avoid 8080)
  * [x] `temporal-worker` (Python worker in `docker/compose/20-workers.yml`; started by bootstrap)
  * [ ] `jupyter` (dev-only, optional; e.g. in `dev.override.yml`)

* [x] OpenVitals Postgres: `docker/compose/25-openvitals-db.yml` (service `openvitals-db`; port 5433, user/db from env or defaults). Started by Genesis workflow or manually; bootstrap only brings up Temporal.

* [x] Config: `config.yaml` from `templates/.config.template` (non-secret settings); `.env` from `templates/.env.template` (secrets only). See `docs/standards/env_and_config.md`.

  * [x] `.env`: `TEMPORAL_POSTGRES_PASSWORD` and `OPENVITALS_DB_PASSWORD` (both auto-generated by bootstrap when creating from template)
  * [x] `config.yaml`: `temporal.deployment_env` (dev | test | prod), `openvitals.project_root` (set by bootstrap to repo path), ports, hostnames, OpenVitals DB host/port/user/name (password in `.env`)

* [x] **Host env (venv):** Single `requirements.txt` at repo root (shared by host venv, worker image, future Jupyter). Bootstrap creates `.venv` at repo root and installs from `requirements.txt`; script uses venv Python for config edit and project_root update. On Debian/Ubuntu, bootstrap installs version-specific `python3.X-venv` (e.g. `python3.12-venv`) so venv has pip. See README Deployment for user options (use `.venv` or conda with same requirements).

### 0.3 Day-0 bootstrap script (curl-friendly)

* [x] Create `scripts/bootstrap.linux.sh` (run from repo root; requires sudo) that:

  * [x] verifies Docker + Docker Compose available (installs via apt if missing on Linux)
  * [x] ensures Python venv at `.venv` (installs `python3.X-venv` on Debian/Ubuntu if needed), installs from `requirements.txt`; uses venv Python for all config edits
  * [x] creates `config.yaml` and `.env` from templates if missing (auto-generates `TEMPORAL_POSTGRES_PASSWORD` and `OPENVITALS_DB_PASSWORD`)
  * [x] accepts `--env` / `-e` dev|test|prod and `--yes` / `-y`; persists `temporal.deployment_env` via `scripts/lib/config_edit.py` (venv Python)
  * [x] updates `openvitals.project_root` in config to actual repo path (ruamel.yaml via venv)
  * [x] optional pause to edit Temporal password/port (when config was just created); default is continue; `-y` skips pause
  * [x] reads `temporal.deployment_env` from `config.yaml` and uses matching compose override
  * [x] runs `docker compose` for temporal-db, temporal-server, temporal-ui; then ensures namespace `openvitals-${ENV}`, starts `temporal-worker` (20-workers.yml), health-checks worker
  * [x] prints Temporal UI URL and next step (`scripts/genesis.sh`)

* [x] Create `scripts/bootstrap.linux.remote.sh` (VM/curl install): creates install dir, clones repo, runs `bootstrap.linux.sh` and passes through flags (e.g. `--env prod -y`).

* [x] **Worker** in bootstrap: creates Temporal namespace, starts `temporal-worker` via `20-workers.yml`, health-checks worker (tested; idempotent). Worker image uses repo-root `requirements.txt` (same deps as host venv).

* [x] Create `scripts/doctor.sh` — **on-demand health check** (run anytime to verify the stack without re-running bootstrap; e.g. after a reboot or to debug connectivity).
  * [x] Postgres (Temporal) reachable
  * [x] Temporal server reachable
  * [x] temporal-worker container running
  * [x] OpenVitals DB checked if container is running (will fail till Genesis deploys it)

* [x] Create `scripts/reset.env.sh` — **reset deployment env** (dev/test): four-step confirm (containers, Temporal volume, OpenVitals volume, `.env` + `config.yaml`); type YES to perform each step, NO/Enter to skip. Never touches `templates/`.

* [x] Create `scripts/lib/config_edit.py` — **generic config editor** (dot-notation keys); used by bootstrap to persist `temporal.deployment_env`. Requires ruamel.yaml (in `requirements.txt`).

**Standards:** `docs/standards/temporal_standards.md` (three-layer, layout, patterns), `docs/standards/temporal_deployment.md` (deployment summary).

**Deliverables:**

* [x] `docker/compose/00-networks.yml`, `10-temporal.yml`, `20-workers.yml`, `25-openvitals-db.yml`, `dev.override.yml`, `test.override.yml`, `prod.override.yml`
* [x] `templates/.config.template`, `templates/.env.template`
* [x] `requirements.txt` (repo root; temporalio, ruamel.yaml, pyyaml)
* [x] `scripts/bootstrap.linux.sh`, `scripts/bootstrap.linux.remote.sh`, `scripts/doctor.sh`, `scripts/reset.env.sh`
* [x] `scripts/lib/config_edit.py`
* [x] Worker: `docker/images/workers/temporal/` (Dockerfile uses repo-root `requirements.txt`), `src/openvitals/orchestration/temporal/` (worker.py, activities, modules/bootstrap stub)

### 0.4 Genesis (post-bootstrap, Temporal-driven)

**Status:** Genesis workflow runs end-to-end: load config/secrets → validate → compile plan → execute plan (Postgres up + verified). Remaining: create_db_user, run_migrations, ensure_jupyter (dev).

**Stack to deploy (from `docs/architecture/Tech_Stack.md`):**

- **Postgres (OpenVitals DB):** Genesis ensures container is up, creates DB/user, runs migrations. No volume deletion.
- **Python + pip packages (Tech Stack):** pandas, numpy, sqlalchemy, psycopg, typer, matplotlib/plotly. These live in **`requirements.txt`** and are **not** installed by Genesis — they are already present in the host venv (bootstrap), worker image (built from `requirements.txt`), and (when added) Jupyter image. Ensure `requirements.txt` includes all Phase 0 app deps from Tech_Stack so worker and Jupyter share the same stack; bootstrap and image builds handle install.
- **Jupyter container (dev-only):** Genesis can ensure the Jupyter service is up when `deployment_env` is dev (e.g. activity `ensure_jupyter_up` or `ensure_dev_services`). Jupyter service lives in compose (e.g. `dev.override.yml` or a numbered file); same `requirements.txt` so notebooks run with the same deps as worker.
- **Config + secrets:** `.env`, `config.yaml`; loaded by activities (load_config, load_secrets) so workflow has access.

**Genesis workflow pattern:**

- **Step 1 — Load config:** First activity reads `config.yaml` (generic `load_config`). Workflow gets raw config so helper can validate and compile execution plan. See `docs/standards/temporal_standards.md` (Configuration and secrets pattern).
- **Step 2 — Load secrets (when needed):** Separate activity reads `.env` (e.g. `load_secrets`). Never pass secrets as workflow input; activities receive only what they need as typed params.
- **Helper:** Pure validation and execution-plan compilation (Genesis-specific). Helper produces typed inputs for each activity.
- **Activities:** Generic, idempotent, receive fully-specified inputs from helper. List below.

**Activities (Temporal section — accomplished / remaining):**

| Order | Activity (domain) | Purpose | Status |
|-------|-------------------|---------|--------|
| 1 | `activities/config/load_config.py` | Read `config.yaml`; return raw config for helper. | [x] Done |
| 2 | `activities/secrets/load_secrets.py` | Read `.env`; return only what Genesis needs (e.g. OpenVitals DB password). | [x] Done |
| 3 | `activities/db/docker_compose_up.py` | Bring OpenVitals Postgres container up (`docker compose up -d openvitals-db`). | [x] Done |
| 3b | `activities/db/verify_postgres_up.py` | Verify Postgres is reachable (host/port/user/db/password). | [x] Done |
| 4 | `activities/db/create_db_user.py` | Create OpenVitals DB and user (from config + secrets). | [ ] Remaining |
| 5 | `activities/db/run_migrations.py` | Run `sql/migrations/` against OpenVitals DB. | [ ] Remaining |
| 6 | `activities/dev/ensure_jupyter_up.py` (or `ensure_dev_services`) | When `deployment_env` is dev, ensure Jupyter container is up. Skip when env is test/prod. | [ ] Remaining |

* [x] **requirements.txt:** Add all Phase 0 app deps from Tech_Stack (pandas, numpy, sqlalchemy, psycopg, typer, matplotlib, plotly) so host venv, worker, and Jupyter (when added) share the same stack. Bootstrap and image builds install from this; Genesis does not run pip.

* [ ] **Jupyter in compose:** Add Jupyter service (dev-only; e.g. in `dev.override.yml` or `30-jupyter.yml`). Image uses same `requirements.txt` so notebooks match worker/env.

* [x] **Genesis workflow** (Temporal): workflow calls `load_config` → `load_secrets` → helper validates/compiles plan → workflow runs plan activities via `execute_activity(..., args=activity_args)`. Implemented in `modules/bootstrap/workflows.py`; `genesis_helper.py` (validate_genesis_config, compile_execution_plan). Remaining: add create_db_user, run_migrations, ensure_jupyter to plan when implemented.

* [x] **Genesis activities (current):** `activities/config/load_config.py`, `activities/secrets/load_secrets.py`, `activities/db/docker_compose_up.py`, `activities/db/verify_postgres_up.py`; registered in worker. [ ] Remaining: `create_db_user`, `run_migrations`, `ensure_jupyter_up`.

* [x] **scripts/genesis.sh:** Trigger Genesis workflow (worker must be running); wait for success or surface failure. Working.

* [x] OpenVitals Postgres compose: `docker/compose/25-openvitals-db.yml` exists and is wired to `config.yaml` + `.env`; Genesis starts service if needed, then creates DB/user and runs migrations.

---

# Stage 1 — Export Acquisition + Dataset Datasheet

### 1.1 Google Takeout export captured

* [ ] Create Google Takeout export for Google Fit
* [ ] Store at `data/raw/google_fit/takeout_<YYYY-MM-DD>.zip`
* [ ] Record export metadata:

  * [ ] export date/time
  * [ ] approximate date range
  * [ ] device sources

### 1.2 Apple Health export captured

* [ ] Export Apple Health data
* [ ] Store at `data/raw/apple_health/apple_health_<YYYY-MM-DD>.zip`
* [ ] Record export metadata:

  * [ ] export date/time
  * [ ] approximate date range
  * [ ] device sources

### 1.3 Dataset datasheet (Phase 0)

* [ ] Create `docs/dataset_description.md` with:

  * [ ] provenance
  * [ ] time range
  * [ ] devices
  * [ ] known limitations
  * [ ] privacy/ethics handling

**Deliverables:**

* [ ] `docs/dataset_description.md`

---

# Stage 2 — Source Schema Recon (Google + Apple)

### 2.1 Google Fit export mapping

* [ ] Unzip and document key directories/files for:

  * [ ] steps
  * [ ] sleep
  * [ ] heart rate
  * [ ] daily summaries (if present)

* [ ] Create `docs/source_schemas/google_fit.md`

### 2.2 Apple Health export mapping

* [ ] Identify XML structure and record types for:

  * [ ] steps
  * [ ] sleep sessions
  * [ ] heart rate

* [ ] Create `docs/source_schemas/apple_health.md`

**Deliverables:**

* [ ] `docs/source_schemas/google_fit.md`
* [ ] `docs/source_schemas/apple_health.md`

---

# Stage 3 — Canonical Schema v0 (Set A only)

### 3.1 Define schema (document)

* [ ] Create `docs/canonical_schema_v0.md` defining:

  * [ ] `heart_rate_samples`
  * [ ] `sleep_sessions`
  * [ ] `step_events` *or* `daily_steps_raw`
  * [ ] `vendor_daily_metrics` (baseline values)
  * [ ] `ingestion_runs` (provenance)
  * [ ] `data_sources` (vendor/device)

### 3.2 Implement schema (SQL)

* [ ] Create `sql/schema_v0.sql`
* [ ] Add idempotency keys / uniqueness strategy:

  * [ ] stable record IDs (hash of source+timestamp+type)
  * [ ] unique constraints per table

### 3.3 Apply schema

* [ ] Add script `scripts/migrate.sh` to apply schema to Postgres
* [ ] Validate tables created

**Deliverables:**

* [ ] `docs/canonical_schema_v0.md`
* [ ] `sql/schema_v0.sql`
* [ ] `scripts/migrate.sh`

---

# Stage 4 — Notebook-First Parsing (Visibility First)

> Goal: prove parsing works end-to-end before Temporalizing.

### 4.1 Jupyter environment (optional)

* [ ] Bring up `jupyter` service
* [ ] Create `notebooks/00_environment_check.ipynb`

  * [ ] test DB connection
  * [ ] confirm exports accessible

### 4.2 Google ingestion (Member A)

* [ ] Create adapter scaffolding:

  * [ ] `src/openvitals/adapters/google_fit/__init__.py`
  * [ ] `src/openvitals/adapters/google_fit/parse_steps.py`
  * [ ] `src/openvitals/adapters/google_fit/parse_sleep.py`
  * [ ] `src/openvitals/adapters/google_fit/parse_heart_rate.py`

* [ ] Create notebook `notebooks/10_google_fit_parse.ipynb`

  * [ ] load zip/unzipped folder
  * [ ] parse steps → canonical dataframe
  * [ ] parse sleep → canonical dataframe
  * [ ] parse HR → canonical dataframe
  * [ ] upsert into Postgres
  * [ ] validate counts + date range

### 4.3 Apple ingestion (Member B)

* [ ] Create adapter scaffolding:

  * [ ] `src/openvitals/adapters/apple_health/__init__.py`
  * [ ] `src/openvitals/adapters/apple_health/parse_steps.py`
  * [ ] `src/openvitals/adapters/apple_health/parse_sleep.py`
  * [ ] `src/openvitals/adapters/apple_health/parse_heart_rate.py`

* [ ] Create notebook `notebooks/11_apple_health_parse.ipynb`

  * [ ] parse XML
  * [ ] extract steps, sleep, HR
  * [ ] upsert into Postgres
  * [ ] validate counts + date range

**Deliverables:**

* [ ] `src/openvitals/adapters/google_fit/*`
* [ ] `src/openvitals/adapters/apple_health/*`
* [ ] `notebooks/10_google_fit_parse.ipynb`
* [ ] `notebooks/11_apple_health_parse.ipynb`

---

# Stage 5 — Metric Reproduction (Set A)

### 5.1 Define metric methods

* [ ] Create `docs/metrics/set_a_definitions.md` including:

  * [ ] steps/day method
  * [ ] sleep duration/day method
  * [ ] resting HR method (assumptions)

### 5.2 Implement metrics (Member C)

* [ ] Create `src/openvitals/analytics/set_a.py`:

  * [ ] `compute_daily_steps()`
  * [ ] `compute_daily_sleep_duration()`
  * [ ] `compute_daily_resting_hr()`

* [ ] Create notebook `notebooks/20_metrics_set_a.ipynb`:

  * [ ] compute and store derived metrics tables
  * [ ] export derived metrics CSV

**Deliverables:**

* [ ] `docs/metrics/set_a_definitions.md`
* [ ] `src/openvitals/analytics/set_a.py`
* [ ] `notebooks/20_metrics_set_a.ipynb`

---

# Stage 6 — Vendor Comparison + Empirical Evaluation

### 6.1 Vendor baseline values

* [ ] Identify vendor-provided daily metrics in exports (if available)

* [ ] If not available, choose one:

  * [ ] Manual capture sample from app UI (document method)
  * [ ] Treat cross-platform comparison as baseline (document)

* [ ] Store baseline into `vendor_daily_metrics`

### 6.2 Compute evaluation metrics

* [ ] Create `src/openvitals/analytics/evaluation.py`:

  * [ ] missingness/coverage
  * [ ] correlation (Pearson + Spearman)
  * [ ] error metrics (MAE, RMSE)

* [ ] Create notebook `notebooks/30_vendor_comparison.ipynb`

  * [ ] join vendor vs reproduced
  * [ ] compute evaluation
  * [ ] export `data/processed/comparison_results.csv`

**Deliverables:**

* [ ] `src/openvitals/analytics/evaluation.py`
* [ ] `notebooks/30_vendor_comparison.ipynb`
* [ ] `data/processed/comparison_results.csv` *(generated)*

---

# Stage 7 — Visuals + Reporting Assets (No UI)

### 7.1 Generate required figures (Member C)

* [ ] Create `src/openvitals/analysis/plots.py` or notebook `notebooks/40_plots.ipynb`
* [ ] Generate and save figures to `reports/figures/`:

  * [ ] `steps_vendor_vs_reproduced.png`
  * [ ] `sleep_vendor_vs_reproduced.png`
  * [ ] `rhr_vendor_vs_reproduced.png`
  * [ ] `data_coverage_missingness.png`

### 7.2 Captions and figure index

* [ ] Create `reports/figures/README.md` listing:

  * [ ] title
  * [ ] axes labels
  * [ ] caption
  * [ ] purpose of each figure

**Deliverables:**

* [ ] `reports/figures/*.png` *(generated)*
* [ ] `reports/figures/README.md`

---

# Stage 8 — Temporalization (Bonus, time-permitting)

> Goal: demonstrate Temporal's value without blocking Phase 0. Code lives under `src/openvitals/orchestration/temporal/` (see `docs/file_structure.txt`). **Deployment flow:** Bootstrap (Stage 0.3) brings up Temporal; Genesis (Stage 0.4) deploys OpenVitals Postgres and runs migrations. See `docs/standards/temporal_standards.md` and `docs/standards/temporal_deployment.md`.

### 8.1 Extract logic from notebooks

* [ ] Ensure parse + compute functions live in `src/openvitals/` modules (adapters, analytics)
* [ ] Ensure idempotent upserts

### 8.2 Implement minimal workflows and activities

* [x] **Genesis workflow** — Implemented in `modules/bootstrap/workflows.py`: load_config → load_secrets → helper validate/compile plan → execute plan (activities via `execute_activity(..., args=activity_args)`). Helper in `genesis_helper.py` (validate_genesis_config, compile_execution_plan). Activities implemented: load_config, load_secrets, docker_compose_up, verify_postgres_up. [ ] Remaining: create_db_user, run_migrations, ensure_jupyter (add to plan when implemented). See **Stage 0.4** for full activity list.

* [ ] **Ingestion module** — Create `src/openvitals/orchestration/temporal/modules/ingestion/workflows.py`:

  * [ ] `IngestExportsWorkflow`: ingest Google export, ingest Apple export, compute Set A metrics, produce run summary

* [ ] **Shared activities** — Implement (or stub) in `src/openvitals/orchestration/temporal/activities/`:

  * [x] Genesis (current): `config/load_config.py`, `secrets/load_secrets.py`, `db/docker_compose_up.py`, `db/verify_postgres_up.py`. [ ] Remaining: `db/create_db_user.py`, `db/run_migrations.py`, `dev/ensure_jupyter_up.py`.
  * [ ] `db_migrate.py`, `ingest_apple.py`, `ingest_google.py`, `compute_metrics.py`, `export_figures.py` (as needed for ingestion)

* [x] **Worker** — `src/openvitals/orchestration/temporal/worker.py`: starts worker, registers GenesisWorkflow and Genesis activities (load_config, load_secrets, docker_compose_up, verify_postgres_up). Started by bootstrap (Stage 0.3). Register additional activities when create_db_user, run_migrations, ingestion are implemented.

### 8.3 Demo artifacts

* [ ] Capture Temporal UI screenshots
* [ ] Record workflow history notes

**Deliverables:**

* [x] `src/openvitals/orchestration/temporal/modules/bootstrap/workflows.py` (Genesis workflow — full logic: load config/secrets, validate, compile plan, execute plan)
* [x] `src/openvitals/orchestration/temporal/modules/bootstrap/genesis_helper.py` (Genesis helper — validate config, compile execution plan)
* [x] `src/openvitals/orchestration/temporal/activities/config/`, `activities/secrets/`, `activities/db/` (Genesis activities: load_config, load_secrets, docker_compose_up, verify_postgres_up). [ ] Remaining: create_db_user, run_migrations, ensure_jupyter.
* [ ] `src/openvitals/orchestration/temporal/modules/ingestion/workflows.py` (IngestExportsWorkflow)
* [x] `src/openvitals/orchestration/temporal/worker.py` (Genesis workflow + activities registered)
* [ ] `reports/temporal_demo.md`

---

# Stage 9 — Final Class Deliverables

### 9.1 Report

* [ ] Create `reports/final_report.md` structured per rubric:

  * [ ] intro + motivation
  * [ ] related work
  * [ ] data (datasheet summary)
  * [ ] methods
  * [ ] results
  * [ ] discussion + future work

### 9.2 Presentation

* [ ] Create `reports/presentation_outline.md`
* [ ] Select only best figures
* [ ] Ensure every plot has title, labels, caption

**Deliverables:**

* [ ] `reports/final_report.md`
* [ ] `reports/presentation_outline.md`

---

## Phase 0 Done Definition

Phase 0 is complete when:

* Canonical schema v0 exists and is applied
* Both exports ingest successfully into Postgres
* Set A metrics are computed and stored
* Vendor comparison is completed (or baseline strategy documented)
* Figures are generated and usable in slides
* Final report and presentation materials exist

---

## Scope Guards (Phase 0)

* No mobile app
* No continuous sync
* No Django UI/backend
* Temporal integration is bonus (scaffold only is acceptable)
* Only Set A metrics


