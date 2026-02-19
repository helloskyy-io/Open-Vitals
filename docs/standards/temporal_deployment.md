# Temporal as deployment mechanism

> **Full standard:** For the complete Temporal standard (three-layer architecture, directory layout, activities, helpers, patterns), see **[temporal_standards.md](temporal_standards.md)**. This doc summarizes deployment only.

OpenVitals uses **Temporal** to orchestrate deployment and environment setup so that the same workflow runs in dev, test, and prod with behavior controlled by configuration. This doc defines the **deployment** standard (bootstrap, Genesis, namespaces, worker).

## Principles

- **Same workflow, different target:** One orchestrated path (e.g. Genesis) parameterized by **deployment environment** (dev / test / prod). Activities read config and `.env`; they do not hardcode targets.
- **Single source of truth:** Stack and steps are defined in code (workflows, activities, compose, config). Dev and prod differ only by **configuration** (override file, namespace, secrets), not by different scripts or steps.
- **No destructive automation:** Deployment workflows create and upgrade only. They do not delete database volumes or data. Any full reset is an explicit, user-confirmed operation (e.g. `scripts/reset.env.sh`).

## Deployment environment (dev / test / prod)

- **Meaning:** The deployment environment selects which Docker Compose override is used, which **Temporal namespace** and task queue the worker uses, and how Genesis behaves (e.g. which DB host/port).
- **Where it is set:** In **`config.yaml`** as **`temporal.deployment_env`** (one of `dev`, `test`, `prod`). Bootstrap and other scripts read this value.
- **Setting it at deploy time:** Use bootstrap flags **`--env`** / **`-e`** (e.g. `--env prod`) so the value is written to `config.yaml` before Temporal starts; or set **`OPENVITALS_DEPLOYMENT_ENV`** (flags take precedence). Default is `dev`. See README Deployment section.
- **Temporal namespace:** One namespace per environment: **`openvitals-${ENV}`** (e.g. `openvitals-dev`, `openvitals-prod`). Bootstrap ensures this namespace exists and starts the worker in it. Task queues are environment-scoped (e.g. `bootstrap-${ENV}`) so workflows and activities run in the correct env.
- **Compose overrides:** Override file is **`docker/compose/${ENV}.override.yml`**; see [docker_compose_layout.md](docker_compose_layout.md). Secrets stay in `.env`; non-secret settings in `config.yaml`; see [env_and_config.md](env_and_config.md).

## Bootstrap and Temporal

- **Bootstrap** (e.g. `scripts/bootstrap.linux.sh` or `scripts/bootstrap.linux.remote.sh`) brings up the Temporal stack (temporal-db, temporal-server, temporal-ui), ensures the namespace for the chosen env, and starts the **temporal-worker**. It does not start the OpenVitals application database; that is the job of the Genesis workflow.
- **Config and secrets:** Bootstrap creates `config.yaml` and `.env` from templates if missing (with generated passwords). Deployment env can be set via `--env` and non-interactive mode via `--yes` / `-y`. The real place for optional manual configuration is **between bootstrap and Genesis** (edit `config.yaml` and `.env` if needed, then run Genesis).
- **Worker:** One worker is started by bootstrap so that when the user runs `genesis.sh`, the Genesis workflow can execute. The worker uses the namespace and task queue for the deployment env from config.

## Genesis workflow

- **Role:** Genesis deploys and configures the **OpenVitals** application database: ensure the OpenVitals Postgres service is up (e.g. via compose), create database and user if needed, run SQL migrations. It does not remove or truncate data.
- **Inputs:** Environment (or read from config); secrets come from `.env` (worker/compose have access). No secrets passed as workflow arguments.
- **Invocation:** User runs **`scripts/genesis.sh`** after bootstrap (and after any optional config edits). The script triggers the Genesis workflow and waits for success or reports failure.
- **Implementation:** Workflow and activities live in the codebase (e.g. under orchestration/temporal and modules/bootstrap); exact steps are documented in Phase 0 and README.

## Manual steps (summary)

| Step | When |
|------|------|
| Run bootstrap (`sudo ./scripts/bootstrap.linux.sh` or remote script; use `--env prod -y` for non-interactive prod) | First time or after a new machine/VM |
| Optionally edit `.env` and `config.yaml` (passwords, ports, `temporal.deployment_env`) | Between bootstrap and Genesis |
| Run Genesis (`sudo ./scripts/genesis.sh`) | After Temporal is up and config is set |
| (Dev) Use venv and `requirements.txt` for CLI/notebooks; (prod) worker already running from bootstrap | As needed |

We do **not** want deployment scripts or workflows to delete database volumes. Use **`scripts/reset.env.sh`** when you need a full reset (containers, volumes, `.env`, `config.yaml`); it prompts per step and requires explicit YES.

## Worker and Python environment

- **Single worker image** for deployment and Phase 0 workflows (Genesis, etc.). Same image can be used in dev and prod; only connection strings, namespace, and task queue change via config.
- **Python parity:** One `requirements.txt` (and optional `requirements-dev.txt`) in repo; worker image and dev venv use it so dev and prod behavior matches. See Phase 0 / Tech Stack for details.
- **Jupyter:** If used, it is a dev-only service in compose (e.g. in `dev.override.yml`), not started or managed by Temporal.

---

*This standard reflects the current implementation. When the Genesis workflow and `genesis.sh` are fully implemented, this doc should be updated to match; the principles and structure above are intended to stay stable.*
