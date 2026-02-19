# Docker Compose layout and standard

OpenVitals uses a **numbered base files + environment overrides** layout. This keeps a single source of truth for each concern and lets you switch environments (dev/test/prod) via config without editing base compose files.

## Layout

Compose files live under **`docker/compose/`**:

- **Base files (load order):**
  - **`00-networks.yml`** — shared networks (e.g. `openvitals`). Load first so all services can attach.
  - **`10-temporal.yml`** — Temporal stack (temporal-db, temporal-server, temporal-ui).
  - **`20-workers.yml`** — Temporal worker (Genesis, etc.). The worker container has the host **Docker socket** and **compose files** mounted so Genesis activities can run `docker compose` (e.g. ensure OpenVitals Postgres is up). Treat the worker as a trusted orchestration component.
  - **`25-openvitals-db.yml`** — OpenVitals application Postgres (started by Genesis or manually).
  - **`30-*.yml`**, … — future stacks (backend, etc.) as they are added.
- **Override files (one per environment):**
  - **`dev.override.yml`** — dev overrides (selected when `temporal.deployment_env` is `dev`).
  - **`test.override.yml`** — test overrides.
  - **`prod.override.yml`** — prod overrides.

Base files define the default shape of the stack; override files change ports, env vars, or options per environment. Overrides can be empty (`services: {}`) if defaults are fine.

## How the deployment type is chosen

The **deployment environment** is read from **`config.yaml`**:

- **`temporal.deployment_env`** — one of `dev`, `test`, or `prod`.

The bootstrap/deploy script reads this value and passes the matching override file to `docker compose`, e.g.:

```bash
docker compose --env-file .env \
  -f docker/compose/00-networks.yml \
  -f docker/compose/10-temporal.yml \
  -f docker/compose/${ENV}.override.yml \
  up -d ...
```

So the same script and same base compose files work for dev, test, and prod; only the override file and `config.yaml` differ.

## Conventions

- **Secrets** stay in **`.env`** (never in compose or config.yaml). See `docs/standards/env_and_config.md`.
- **Non-secret settings** (ports, hostnames, feature flags) go in **`config.yaml`** or in the override YAML.
- **Numbered base files** — two digits and a short name (e.g. `10-temporal.yml`, `20-openvitals-db.yml`) so order is obvious and merge-friendly.
- **Override file names** — `{dev|test|prod}.override.yml` to match `temporal.deployment_env`.
