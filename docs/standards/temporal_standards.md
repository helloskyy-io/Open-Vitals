# Temporal standards

This document defines how OpenVitals uses **Temporal** for deployment and workflow orchestration: layout (modules, workflows, helpers, activities), three-layer architecture, deployment flow (bootstrap, Genesis, env), and design patterns. It aligns with the micro-data-center approach so both projects share the same conceptual model.

---

## Mission and principles

**Mission:** Workflows describe intent; helpers compile intent into an execution plan; activities execute.

**Principles:**

- **Same workflow, different target:** One orchestrated path (e.g. Genesis) parameterized by **deployment environment** (dev / test / prod). Activities read config and `.env`; they do not hardcode targets.
- **Single source of truth:** Stack and steps are defined in code (workflows, activities, compose, config). Dev and prod differ only by **configuration** (override file, namespace, secrets), not by different scripts or steps.
- **No destructive automation:** Deployment workflows create and upgrade only. They do not delete database volumes or data. Any full reset is an explicit, user-confirmed operation (e.g. `scripts/reset.env.sh`).
- **Activities as reusable library:** Activities live **outside** the modules directory so they can be shared across workflows and stay generic within the OpenVitals domain.

---

## Three-layer architecture

Temporal workflows follow a three-layer architecture:

| Layer | Role | Rules |
|-------|------|--------|
| **1. Workflow** | Orchestration only | Describes high-level steps and intent. Calls helpers and activities. No external I/O. Deterministic (no randomness, no direct I/O, no network calls). |
| **2. Helper** | Compiler | Pure and deterministic (no I/O, no side effects). Validates and normalizes inputs. Produces typed activity inputs and/or execution plan. Workflow-specific naming/IDs/defaults live here. Lives next to the workflow in the module. |
| **3. Activities** | Execution | External I/O and side effects. Generic within the OpenVitals domain. Idempotent / retry-safe where possible. Accept fully-specified typed inputs (no hidden context). Single responsibility. Live under `activities/` by domain. |

**Core rule:** Workflows and helpers never perform I/O; all I/O happens in activities. Helpers never perform I/O or have side effects; they only validate and compile intent into execution plans.

---

## Directory structure

Layout under **`src/openvitals/orchestration/temporal/`**:

```
temporal/
├── worker.py                    # Worker entrypoint; registers workflows and activities
├── modules/                     # Workflow modules (by purpose)
│   ├── bootstrap/               # Bootstrap / deployment (e.g. Genesis)
│   │   ├── genesis_workflow.py  # Genesis workflow (orchestration)
│   │   └── genesis_helper.py    # Helper: validation & execution plan (pure)
│   └── ...                      # Future: ingestion, analytics, etc.
└── activities/                  # Reusable activities (outside modules)
    ├── config/                  # Config loading (first activity in most workflows)
    ├── secrets/                 # Secrets loading (.env, etc.)
    ├── db/                      # Database: ensure Postgres, run migrations
    └── ...                      # Other domains as needed
```

- **Modules** are named by **what they do** (e.g. `bootstrap` for deployment). Each workflow has its own folder or files: `{workflow_name}_workflow.py` and `{workflow_name}_helper.py`.
- **Workflow folders** are only created when workflows are implemented (no placeholder-only folders).
- **Activities** are grouped by **domain** (config, secrets, db, docker, etc.). Each activity file does one thing; activities are workflow-agnostic and reusable.

---

## Deployment environment (dev / test / prod)

| Concept | OpenVitals |
|--------|-------------|
| **Config source** | `config.yaml` → `temporal.deployment_env` |
| **Namespaces** | `openvitals-dev`, `openvitals-test`, `openvitals-prod` |
| **Task queues** | `bootstrap-dev`, `bootstrap-test`, `bootstrap-prod` (env-scoped) |
| **Compose** | Base files + `{env}.override.yml` — see [docker_compose_layout.md](docker_compose_layout.md) |

Deployment env can be set at bootstrap via **`--env`** / **`-e`** or **`OPENVITALS_DEPLOYMENT_ENV`**; it is persisted to `config.yaml` so the worker and Genesis use the correct namespace and override.

---

## Configuration and secrets pattern

**Config:** Workflow input is minimal or empty (e.g. start from UI or script with `{}`).

1. **First activity:** Load configuration from `config.yaml` (generic `load_config`-style activity).
2. **Helper:** Validate and structure config for the workflow (e.g. `genesis_helper.validate_genesis_config(raw_config)`).
3. **Helper:** Compile execution plan (list of steps with fully-specified typed inputs for activities).
4. **Workflow:** Execute plan by calling activities with the typed inputs from the plan.

**Secrets:** Loaded by a **separate activity** (e.g. `load_secrets` reading `.env`). Never passed as workflow input (so they are not stored in workflow history). Helpers can validate or transform secret usage; activities receive only what they need as parameters.

**Benefits:** UI start and script start behave the same; secrets stay out of history; config is single source of truth; activities stay generic (receive params, do not read config files directly).

---

## Activity design patterns

1. **Idempotency:** Activities should be idempotent where possible (safe to retry). Check current state; if already done, return "skipped" instead of failing or duplicating work.
2. **Structured results:** Return a consistent result type (e.g. `ActivityResult` with `status`, `details`, optional `artifacts` / `error_code`), not just a bool.
3. **Self-validation:** After an operation, verify it succeeded (e.g. check final state). Return a failed status if validation does not pass; do not fail silently.
4. **Fully-specified inputs:** All data passed as parameters. No hardcoded paths, URLs, or config keys inside the activity; workflow/helper provide them.
5. **Single responsibility:** One external concern per activity (e.g. "ensure Postgres is up", "run migrations"). No workflow-specific activities—activities are generic within the OpenVitals domain.
6. **No workflow starts:** Activities do not start other workflows; they only do external work. Starting child workflows is done from workflow code via child workflow APIs.

---

## Workflow design patterns

1. **Three-layer pattern:** Every workflow: (1) call config activity, (2) call helper to validate config, (3) call helper to compile execution plan, (4) iterate plan and execute activities with the plan’s typed inputs.
2. **Helpers are pure:** Helper functions take inputs and return validated config or execution plan. No I/O, no side effects, no Temporal SDK calls.
3. **Child workflows:** To start another workflow, use **child workflow APIs** from workflow code (e.g. `workflow.start_child_workflow(...)`). Do **not** instantiate Temporal clients in workflow code.
4. **Retries:** Define retry policies per activity (e.g. network: more retries with backoff; DB: fewer retries). Idempotent activities can allow more retries.

---

## Bootstrap and Genesis (deployment)

- **Bootstrap** brings up the Temporal stack (DB, server, UI), ensures namespace `openvitals-${ENV}`, and starts the **temporal-worker**. It does not start the OpenVitals application database; that is the job of the Genesis workflow.
- **Genesis workflow** ensures the OpenVitals Postgres service is up (e.g. via compose), creates database and user if needed, and runs SQL migrations. It does not delete or truncate data.
- **Invocation:** User runs **`scripts/genesis.sh`** after bootstrap; the script starts the Genesis workflow and waits for success or reports failure. Secrets and config come from `.env` and `config.yaml` (loaded by activities), not from workflow input.
- **Manual steps:** Run bootstrap → optionally edit `.env` / `config.yaml` → run Genesis. Full reset is explicit: **`scripts/reset.env.sh`** (per-step confirmation).

---

## Best practices

**Do:**

- Keep activities small and focused; make them idempotent.
- Use the three-layer pattern: Workflow → Helper → Activity.
- Load config with a generic activity; validate and compile in the helper.
- Give activities fully-specified typed inputs (no hidden context).
- Organize activities by domain; organize workflows by purpose in modules.
- Return structured results (e.g. `ActivityResult`); validate success inside the activity.
- Use child workflow APIs to start other workflows from workflow code.

**Do not:**

- Put I/O or external calls in workflows or helpers.
- Hardcode paths, URLs, or config values in activities.
- Create workflow-specific activities (activities must be generic).
- Pass secrets as workflow input.
- Start workflows from activities.
- Instantiate Temporal clients in workflow code.
- Fail silently—always validate and report.

---

## File locations (OpenVitals)

| Purpose | Location |
|--------|----------|
| Non-secret settings | Repo root `config.yaml` (see [env_and_config.md](env_and_config.md)) |
| Secrets | Repo root `.env` |
| Generic config-loading activity | `activities/config/load_config.py` (or similar) |
| Workflow + helper | `modules/{module}/{workflow_name}_workflow.py`, `{workflow_name}_helper.py` |
| Secrets-loading activity | `activities/secrets/load_secrets.py` |
| Worker | `temporal/worker.py` |

Paths are relative to `src/openvitals/orchestration/temporal/` unless stated otherwise. Repo root is the directory containing `config.yaml` and `.env` (e.g. set via `openvitals.project_root` in config or `REPO_ROOT` in compose).

---

*This standard aligns with the micro-data-center Temporal component standards. When the Genesis workflow and helpers are fully implemented, this doc should be updated to match; the principles and structure above are intended to stay stable.*
