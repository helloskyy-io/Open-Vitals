# Long-Term Platform Roadmap (Open-Source Vision)

## Guiding Principles

* User owns raw data at all times
* Analytics are transparent and reproducible
* No irreversible vendor lock-in
* GitOps-first development
* Each phase produces independently valuable artifacts

---

## Phase 0 – Research Prototype (Class Project)

**Goal:** Construct a real dataset and produce empirical findings using industry-standard Bronze/Silver/Gold data lake architecture from the start — no throwaway code.

**Scope:**

* Manual export of wearable data (landing zone → `data/raw/`)
* Bronze layer: deduplicated, content-addressed raw data store with manifest (`data/bronze/`)
* Silver layer: vendor-agnostic canonical schema in Postgres, incremental parsing adapters
* Gold layer: derived metrics (steps, sleep duration, resting heart rate), vendor comparison
* Visualization, analysis, and reporting

**Deliverables:**

* Bronze/Silver/Gold pipeline (code + docs)
* Documented dataset and canonical schema
* Reproducible ingestion from raw exports through metrics
* Empirical comparison results
* Academic presentation and report

---

## Phase 1 – Deterministic Ingestion Engine

**Goal:** Automate and harden the Bronze/Silver/Gold pipeline without changing data semantics.

**Scope:**

* Temporal-scheduled ingestion workflows (Bronze ingest → Silver parse → Gold compute)
* Idempotent, incremental ingestion logic (built on manifest from Phase 0)
* Automated new-export detection and processing
* Vendor adapter interfaces hardened for production

**Outcome:**

* Reliable, replayable, fully automated ingestion of wearable data

---

## Phase 2 – Vendor-Agnostic Data Model

**Goal:** Eliminate vendor-specific coupling at the data layer.

**Scope:**

* Canonical health event schemas
* Provenance and source metadata
* Explicit accounting of data loss during ingestion

**Outcome:**

* True data portability across wearable ecosystems

---

## Phase 3 – Open Analytics Layer

**Goal:** Replace opaque vendor metrics with transparent analytics.

**Scope:**

* Versioned metric definitions
* Feature engineering pipelines
* Statistical baselines and comparisons

**Outcome:**

* Inspectable and reproducible health analytics

---

## Phase 4 – AI Interpretation Layer

**Goal:** Provide intelligent insights without black-box scoring.

**Scope:**

* Trend detection and anomaly analysis
* Personalized baselines
* Explainable machine learning models

**Outcome:**

* Trustworthy AI-assisted health interpretation

---

## Phase 5 – User Platform and Ecosystem

**Goal:** Deliver a user-facing platform that competes ethically with proprietary ecosystems.

**Scope:**

* Web dashboard and mobile companion
* Self-hosted and managed deployments
* Open-core contribution model

**Outcome:**

* A sustainable, open-source ecosystem for personal health data ownership
