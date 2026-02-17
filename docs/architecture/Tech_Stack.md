# OpenVitals Tech Stack

**Project:** OpenVitals
**Purpose:** Define the official technology stack for Phase 0 (class research prototype) and future platform phases.
**Guiding Principle:** Phase 0 prioritizes reproducible analytics and data pipeline correctness. Platform features (web UI, multi‑user, SaaS hosting) are intentionally deferred to later phases.

---

# Overview

OpenVitals is designed as a **containerized, reproducible data pipeline and analytics system** that evolves into a full self‑hosted health data platform.

The stack is divided into:

* Phase 0 — Research Prototype (class deliverable)
* Phase 1 — Platform Backend and Web Interface
* Phase 2+ — Full User Platform and Ecosystem

---

# Phase 0 — Research Prototype Stack

## Core Infrastructure

### Docker Compose

**Purpose:**

* Defines the entire runtime environment
* Ensures reproducibility across machines
* Enables self‑hosting and future deployment portability

**Justification:**

Docker serves as the single source of truth for environment configuration.

---

### PostgreSQL

**Purpose:**

Primary system database for:

* Canonical wearable data storage
* Metric storage
* Ingestion tracking and provenance

**Why PostgreSQL:**

* Industry standard
* Excellent time‑series support
* Fully compatible with future Django backend
* Strong reliability and tooling ecosystem

---

### Temporal (Workflow Orchestration)

**Components:**

* Temporal Server
* Temporal Worker (Python)

**Purpose:**

Provides deterministic, fault‑tolerant workflow orchestration for:

* Data ingestion pipelines
* Metric computation
* Future scheduled synchronization

**Phase 0 Role:**

Optional bonus implementation. Pipeline may initially run as CLI scripts and later migrate to Temporal.

**Future Role:**

Core orchestration engine for the platform.

---

## Application Layer

### Python (Primary Application Language)

**Purpose:**

Implements:

* Data ingestion adapters
* Analytics pipeline
* Metric reproduction
* CLI interface
* Temporal activities and workflows

**Key Libraries:**

* pandas
* numpy
* sqlalchemy
* psycopg
* typer
* matplotlib / plotly

---

### Python CLI Interface (Typer)

**Purpose:**

Provides stable command interface:

Examples:

```
openvitals ingest google <export>
openvitals ingest apple <export>
openvitals compute set‑a
openvitals report
```

**Why CLI First:**

* No web interface required
* Easily integrates into Temporal later
* Supports automation
* Simple for researchers and developers

---

## Development and Analysis Tools

### Jupyter Notebook

**Purpose:**

Used for:

* Exploratory data analysis
* Metric validation
* Visualization development

**Important Constraint:**

Notebooks are development tools only.

Final production pipeline exists as Python scripts.

---

### Matplotlib / Plotly

**Purpose:**

Visualization generation for:

* Research report
* Academic presentation
* Metric comparison analysis

Outputs saved to:

```
reports/figures/
```

---

## Database Schema Management

### Raw SQL Schema Files

**Purpose:**

Defines canonical database schema.

**Location:**

```
sql/migrations/
```

**Phase 0 Approach:**

Manual SQL migrations.

**Future Upgrade:**

Alembic or Django migrations.

---

## Configuration Management

### .env File

**Purpose:**

Stores:

* Database credentials
* Temporal configuration
* Environment settings

**Security Model:**

```
.env.example → committed
.env → not committed
```

**Vault not required for Phase 0.**

---

## Logging

### Python Logging

**Purpose:**

Tracks:

* Ingestion runs
* Errors
* Metric computation

Future Temporal integration provides workflow history.

---

# Phase 0 Stack Summary Diagram

Logical structure:

Docker Compose

├── Postgres
├── Temporal Server
├── Temporal Worker
├── OpenVitals Python Service
└── Jupyter (dev only)

---

# Phase 1 — Platform Backend Stack

These components are intentionally excluded from Phase 0.

---

## Django Backend

**Purpose:**

Provides:

* Web API
* User accounts
* Authentication
* Admin interface
* Upload management

**Why Django:**

* Mature ecosystem
* Excellent Postgres integration
* Rapid development
* Scalable architecture

---

## Web Frontend

**Initial Implementation:**

Django‑rendered frontend

**Future Option:**

Separate frontend framework

Examples:

* React
* Next.js

---

# Phase 2 — Mobile Integration

Future mobile application will provide:

* Automated data synchronization
* Direct integration with wearable ecosystems
* Secure upload to user‑owned OpenVitals instance

---

# Explicit Non‑Goals for Phase 0

The following are intentionally excluded:

* Web interface
* Django backend
* Authentication
* Multi‑user support
* Mobile apps
* SaaS deployment

These belong to later phases.

---

# Technology Decision Summary

Phase 0 Core:

* Docker Compose
* PostgreSQL
* Python
* Typer CLI
* Jupyter
* Matplotlib / Plotly
* Temporal (optional bonus)

Phase 1 Adds:

* Django
* Web frontend

Phase 2 Adds:

* Mobile applications

---

# Long‑Term Architecture Vision

OpenVitals evolves from:

Research Pipeline

→ Self‑Hosted Platform

→ Full Health Data Ecosystem

All Phase 0 decisions are made to support this evolution without rework.

---

**End of Document**
