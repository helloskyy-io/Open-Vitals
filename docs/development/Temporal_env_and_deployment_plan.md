# Temporal env setup and deployment plan

**Purpose:** Plan how Temporal is used to set up and configure the OpenVitals environment for **dev** (local) vs **production** (VM), and what **manual steps** sit between running the bootstrap script and running the Temporal-driven workflow (Genesis).

**Scope:** Phase 0 stack per [Tech_Stack.md](../architecture/Tech_Stack.md): Postgres (OpenVitals DB + Temporal DB), Python/pip (pandas, numpy, sqlalchemy, psycopg, typer, matplotlib/plotly), Jupyter (dev-only), Temporal (server + worker).

---

## Refined flow (agreed)

1. **Bootstrap script** gets us to: repo locally (or at `/opt/open-vitals` on a VM), Temporal up and running with its database, database password, user, and webserver available.
2. **User "manual input" pause is between the script and the Genesis workflow.** During that gap the user:
   - Sets or accepts the **OpenVitals** Postgres password (we should generate a default when creating `.env`, like we do for Temporal, so they can accept or override before Genesis).
   - Confirms **dev / test / prod** in `config.yaml` (e.g. `temporal.deployment_env`). That value drives what Genesis does next (which compose override, which resources, etc.).
3. **Genesis** deploys and starts the OpenVitals Postgres database, then creates DB/user and runs migrations (confirmed).
4. **Worker:** Bootstrap currently does **not** start a Temporal worker. We should align with how it's done in micro-data-center (worker in bootstrap so that when the user runs `genesis.sh`, something can execute the Genesis workflow). To be confirmed when we check micro-data-center.
5. **Script pause:** The in-script pause (edit config then press y) is **unnecessary by default** but should **remain an option** for anyone who wants to change the Temporal password or port before Temporal starts. So: default = continue with defaults and bring Temporal up; optional = pause to edit Temporal-related config first. The **real** place for manual input is **between bootstrap and Genesis**, not inside the script. Agreed.

---

## 1. Using Temporal to set up and configure dev vs production

### 1.1 Goal

- **Same workflow, different target:** One orchestrated "setup" path (e.g. Genesis) that can run in **dev** (local machine, optional Jupyter, local Postgres) or **prod** (VM, no Jupyter, containerized or host Postgres).
- **Single source of truth:** Stack and steps are defined in code (workflows + activities + compose/config), not in ad‑hoc runbooks.
- **Reproducibility:** Dev and prod differ only by **configuration** (env, config.yaml, compose overrides), not by a different sequence of steps.

### 1.2 What "env" means here

| Layer | Dev (local) | Production (VM) |
|-------|-------------|------------------|
| **Infra** | Docker Compose (Temporal already up via bootstrap) | Same; bootstrap runs on VM (e.g. via `bootstrap.linux.remote.sh`) |
| **OpenVitals DB** | Postgres in Docker (e.g. `20-openvitals-db.yml`) or host | Same; port/host from config |
| **Python / pip** | venv on host or in dev container: pandas, numpy, sqlalchemy, psycopg, typer, matplotlib, plotly | Same deps; in VM often in container (worker image) or venv |
| **Jupyter** | Optional; dev-only service in compose (e.g. `dev.override.yml`) | Not deployed in prod |
| **Temporal worker** | Can run on host (dev) or in container | Typically in container on VM |

So "env" = infra (Postgres, Temporal) + Python dependency set + optional Jupyter (dev only). Temporal **orchestrates** the setup (create DB, run migrations, seed if any); it doesn't replace the need for a defined Python env (venv or container image).

### 1.3 How other orgs typically solve this

- **Same workflow, parameterized by environment:**  
  One "bootstrap" or "provision" workflow that takes an **environment** (e.g. `dev` / `prod`) or a **config label**. Activities then branch or read config so that, for example:
  - Dev: create OpenVitals DB in local Postgres, run migrations, optionally start a dev-only worker or mark "Jupyter available."
  - Prod: same steps against VM Postgres, no Jupyter, stricter checks (e.g. migrations only, no seed data from fixtures).

- **Infra-as-code + env parity:**  
  Docker Compose defines the same **logical** services everywhere; **overrides** (e.g. `dev.override.yml` vs `prod.override.yml`) switch ports, resource limits, and which optional services (Jupyter) are included. So "what Temporal does" is the same; "where it runs" and "what's enabled" come from config.

- **Secrets and config:**  
  Secrets in `.env` (or a vault); non-secret settings in `config.yaml`. Bootstrap and Genesis read the same files so dev and prod only differ by the values (and by which override file is used), not by different scripts.

- **Worker image = app env:**  
  Many orgs build a **single worker image** that contains the Python env (pandas, numpy, sqlalchemy, psycopg, typer, matplotlib, plotly, Temporal SDK). That image runs in dev and prod; only connection strings and task queues (or namespaces) change. So "managing the env" for production = building and deploying that image; for dev, same image or a local venv that matches it.

### 1.4 Recommended approach for OpenVitals

1. **Bootstrap:** Brings up Temporal (DB, server, UI). No OpenVitals DB yet; no Jupyter. **Worker:** should be started in bootstrap (align with micro-data-center) so Genesis can run when the user invokes `genesis.sh`. Same script for dev and prod; override file chosen via `config.yaml` (`temporal.deployment_env`). In-script pause is optional (for editing Temporal password/port); default is to continue with defaults.
2. **Genesis workflow (Temporal):**  
   - **Inputs:** Environment (dev/prod) or read from config; no need to pass secrets (worker/compose use `.env`).  
   - **Activities (high level):**  
     - Ensure OpenVitals Postgres exists (create DB + user if not present; use `OPENVITALS_DB_PASSWORD` from env).  
     - Run SQL migrations (`sql/migrations/`) against OpenVitals DB.  
     - Optionally: register namespaces/task queues if we want env-specific queues.  
   - **No volume deletion:** Genesis only creates/upgrades; it never deletes DB volumes or data.
3. **Python env:**  
   - **Dev:** Either (a) host venv with `requirements.txt` (and optional `requirements-dev.txt` for Jupyter/notebooks), or (b) a dev compose service that builds the same image as the worker so the env matches.  
   - **Prod:** Worker runs in a container built from the same Dockerfile/requirements so the Python env is identical.  
   - **Best practice:** One `requirements.txt` (and optionally `requirements-dev.txt`) in repo; worker image and dev venv both use it so dev/prod parity is explicit.
4. **Jupyter:** In compose only in `dev.override.yml` (or equivalent); not in prod override. No Temporal activity "starts Jupyter"; it's just a dev-only service in the compose stack.
5. **Manual steps:** Limited to "edit `.env` and optionally `config.yaml` once, then run bootstrap; then run Genesis (e.g. via `genesis.sh`)." See Section 2.

This gives: **one bootstrap, one Genesis workflow, same activities in dev and prod**, with behavior and optional services (Jupyter) controlled by config and compose overrides.

---

## 2. Manual steps between bootstrap and the Temporal workflow

These are the steps a human must do **after** `bootstrap.linux.sh` has been run successfully (Temporal up and healthy) and **before or as part of** running the Temporal-driven setup (Genesis).

### 2.1 In the gap (before running Genesis)


1. **OpenVitals DB password:** Either accept the **default** (to be generated when we create `.env` from template, same pattern as `TEMPORAL_POSTGRES_PASSWORD`) or edit `.env` and set `OPENVITALS_DB_PASSWORD`. Today we are **missing** this default generation; we should add it so accept-defaults is possible without editing.
2. **Environment (dev / test / prod):** Set or confirm `temporal.deployment_env` in `config.yaml`. This drives which compose override and what Genesis does.
3. **Optional:** Edit `config.yaml` for ports, hostnames, etc.; edit `.env` only for secrets (see [env_and_config.md](../standards/env_and_config.md)).

Then run Genesis (e.g. `sudo ./scripts/genesis.sh`). No need to pause inside the bootstrap script for OpenVitals config; the script can proceed with defaults and the user configures the rest before Genesis.

### 2.2 What Genesis assumes

- **Genesis** deploys and starts the OpenVitals Postgres database (compose service), then creates the DB/user and runs migrations. So either:
  - Genesis workflow (or a script it calls) brings up the OpenVitals Postgres container (e.g. `docker compose up -d openvitals-db`), then the workflow creates the database and user and runs migrations; or
  - A compose file (e.g. `20-openvitals-db.yml`) is started by `genesis.sh` before the workflow runs, and the workflow only creates DB/user and runs migrations.
- **Worker:** Must be running so the Genesis workflow can execute (either started in bootstrap or by `genesis.sh` before triggering the workflow). To be aligned with micro-data-center.

### 2.3 Summary: manual steps checklist

| Step | When | Owner |
|------|------|--------|
| 1. Run bootstrap (`sudo ./scripts/bootstrap.linux.sh`) | First time (or after adding a new machine/VM) | Human |
| 2. (Optional) If you want to change Temporal password or port before Temporal starts: pause when script offers it, edit `.env` / `config.yaml`, then continue. Otherwise script continues with defaults. | Only if pausing in script | Human |
| 3. **Between bootstrap and Genesis:** Set or accept OpenVitals DB password in `.env`; set or confirm `temporal.deployment_env` (dev/test/prod) in `config.yaml`. | After Temporal is up, before Genesis | Human |
| 4. Run Genesis (e.g. `sudo ./scripts/genesis.sh`). Genesis deploys/starts OpenVitals Postgres, creates DB/user, runs migrations. | After step 3 | Human |
| 5. (Dev) Create/use Python venv and install deps from `requirements.txt` (and `requirements-dev.txt` for Jupyter) if running CLI/notebooks on host | Anytime for local dev | Human |
| 6. (Prod) Worker already running from bootstrap (or started by Genesis); ensure worker image is built and run for ongoing workflows. | After Genesis | Human / CI or compose |

We do **not** want scripting to delete database volumes; any "start from scratch" is an explicit, rare, manual operation (e.g. remove volume and re-run only when the user has decided to reset).

---

## 3. Next steps (implementation)

- **Bootstrap:** Add **worker** to bootstrap (align with micro-data-center) so Genesis can run when the user invokes `genesis.sh`. Make in-script pause **optional** (default = continue with defaults; option to pause to edit Temporal password/port). When creating `.env` from template, **generate default `OPENVITALS_DB_PASSWORD`** (same pattern as `TEMPORAL_POSTGRES_PASSWORD`) so the user can accept or override before Genesis.
- Implement **Genesis workflow** in Temporal: activities for "ensure OpenVitals DB + user," "run migrations," and optionally "create namespace/task queue." Genesis deploys and starts OpenVitals Postgres (compose), then creates DB/user and runs migrations.
- Add **OpenVitals Postgres** to Docker Compose (e.g. `20-openvitals-db.yml`) and wire it to `config.yaml` + `.env`; include in dev/prod overrides as needed.
- Implement **`genesis.sh`** to trigger the Genesis workflow (worker already running from bootstrap) and wait for success (or surface failure).
- Document **Python env** in README or Tech_Stack: one `requirements.txt` (and optional `requirements-dev.txt`) for parity; dev = venv or dev container; prod = worker image.
- Add **Jupyter** only in dev override compose so it's available locally but not in prod.

Once this is in place, "what to set up and configure in Temporal" is fully driven by the Genesis workflow and config; manual steps remain minimal and explicit as in the checklist above.
