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

### 0.1 Repo baseline

* [ ] Create / confirm repo skeleton directories (see `docs/file_structure.txt` for full tree):

  * [ ] `src/openvitals/` (Python package: adapters, analytics, analysis, models, orchestration/temporal)
  * [ ] `src/openvitals/adapters/` (vendor adapters: apple_health, google_fit)
  * [ ] `src/openvitals/analytics/` (metrics + evaluation)
  * [ ] `src/openvitals/orchestration/temporal/` (Temporal: activities/ + modules/; may be stubbed)
  * [ ] `docker/` (docker-compose.yml, Dockerfile, .dockerignore)
  * [ ] `sql/` (schema + migrations)
  * [ ] `data/raw/`, `data/processed/` (gitignored)
  * [ ] `reports/` (figures + writeups)
  * [ ] `docs/` (project docs; `docs/development/` for Phase 0 checklist)
  * [ ] `notebooks/`, `scripts/`, `templates/`, `tests/`

* [ ] Add `.gitignore` entries:

  * [ ] `data/`
  * [ ] `.env`
  * [ ] `__pycache__/`
  * [ ] `*.ipynb_checkpoints`

### 0.2 Docker Compose (Phase 0)

* [ ] Create `docker/docker-compose.yml` with services:

  * [ ] `postgres_openvitals`
  * [ ] `postgres_temporal` *(or a single Postgres instance with two DBs)*
  * [ ] `temporal` (server)
  * [ ] `temporal-ui` (optional but helpful)
  * [ ] `worker` (python worker; can be idle initially)
  * [ ] `jupyter` (dev-only, optional)

* [ ] Create root `.env.example` (or copy from `templates/.env.template`) with:

  * [ ] `OPENVITALS_DB_URL=...`
  * [ ] `TEMPORAL_DB_URL=...`
  * [ ] `TEMPORAL_ADDRESS=...`

### 0.3 Day-0 bootstrap script (curl-friendly)

* [ ] Create `scripts/bootstrap.sh` that:

  * [ ] verifies docker + compose available
  * [ ] copies `templates/.env.template` or `.env.example` → `.env` if missing
  * [ ] runs `docker compose -f docker/docker-compose.yml up -d` (or equivalent from repo root)
  * [ ] runs health checks
  * [ ] prints next steps

* [ ] Create `scripts/doctor.sh` that checks:

  * [ ] Postgres reachable
  * [ ] Temporal reachable
  * [ ] worker container running

**Deliverables:**

* [ ] `docker/docker-compose.yml` (and optionally `docker/Dockerfile`, `docker/.dockerignore`)
* [ ] `.env.example` and/or `templates/.env.template`
* [ ] `scripts/bootstrap.sh`
* [ ] `scripts/doctor.sh`

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

> Goal: demonstrate Temporal’s value without blocking Phase 0. Code lives under `src/openvitals/orchestration/temporal/` (see `docs/file_structure.txt`).

### 8.1 Extract logic from notebooks

* [ ] Ensure parse + compute functions live in `src/openvitals/` modules (adapters, analytics)
* [ ] Ensure idempotent upserts

### 8.2 Implement minimal workflows and activities

* [ ] **Bootstrap module** — Create `src/openvitals/orchestration/temporal/modules/bootstrap/workflows.py`:

  * [ ] `InitializeOpenVitals` workflow: apply schema, register ingestion run

* [ ] **Ingestion module** — Create `src/openvitals/orchestration/temporal/modules/ingestion/workflows.py`:

  * [ ] `IngestExportsWorkflow`: ingest Google export, ingest Apple export, compute Set A metrics, produce run summary

* [ ] **Shared activities** — Implement (or stub) in `src/openvitals/orchestration/temporal/activities/`:

  * [ ] `db_migrate.py`, `ingest_apple.py`, `ingest_google.py`, `compute_metrics.py`, `export_figures.py` (as needed)

* [ ] **Worker** — Create `src/openvitals/orchestration/temporal/worker.py` that starts the worker and registers workflows/activities

### 8.3 Demo artifacts

* [ ] Capture Temporal UI screenshots
* [ ] Record workflow history notes

**Deliverables:**

* [ ] `src/openvitals/orchestration/temporal/modules/bootstrap/workflows.py` (InitializeOpenVitals)
* [ ] `src/openvitals/orchestration/temporal/modules/ingestion/workflows.py` (IngestExportsWorkflow)
* [ ] `src/openvitals/orchestration/temporal/activities/*`
* [ ] `src/openvitals/orchestration/temporal/worker.py`
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


