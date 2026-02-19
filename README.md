![Logo](docs/assets/hs_logo.jpg)

# OpenVitals

This repository is the core platform for **OpenVitals**: an open, vendor‑neutral system for ingesting, storing, and analyzing personal wearable health data outside of proprietary ecosystems.

---

## OpenVitals ecosystem

OpenVitals is a local-first platform that lets you own and analyze your wearable health data. It takes exports from vendor ecosystems (e.g. Google Fit, Apple Health), normalizes them into a single schema, and reproduces core health metrics using transparent, reproducible methods. Built for research and self‑hosting, it keeps your data on your machine and uses Temporal for orchestration so that deployment and pipelines can be automated incrementally.

### Purpose

OpenVitals empowers individuals and researchers to:

- **Own and store wearable health data** in a vendor-agnostic, local database  
- **Reproduce core health metrics** (steps, sleep, resting heart rate) with open methods  
- **Compare reproduced metrics to vendor-reported values** for transparency and research  
- **Run pipelines and deployment via Temporal** so workflows are auditable and retry-safe  

---

## What is OpenVitals?

OpenVitals is an open, vendor‑neutral platform for ingesting, storing, and analyzing personal wearable health data outside of proprietary ecosystems.

It allows individuals to take ownership of their raw health data and reproduce key health metrics using transparent, inspectable analytics.

---

## Why does OpenVitals exist?

Modern wearables generate massive amounts of personal health data, but that data is typically locked inside closed platforms controlled by large vendors. These platforms decide how data is stored, how metrics are computed, and which insights users are allowed to see.

OpenVitals exists to reverse that model.

**Not my storage, not my data.**

The goal is to give individuals full ownership over their health data, make analytics reproducible and transparent, and remove unnecessary vendor lock‑in — while still enabling advanced insights and AI‑driven interpretation on the user's terms.

---

## What can OpenVitals do today?

OpenVitals is currently in **Phase 0 (Research & Prototype)** as part of an academic big‑data analytics project.

At this stage, OpenVitals focuses on:

* Exporting wearable health data from vendor platforms (e.g. Google Fit, Apple Health)
* Normalizing heterogeneous data into a vendor‑agnostic schema
* Storing time‑series health data in a local database
* Reproducing a small set of core health metrics using transparent methods:

  * Daily step count
  * Total sleep duration
  * Resting heart rate
* Comparing reproduced metrics against vendor‑reported values
* Generating visualizations and empirical analysis

This phase is intentionally limited in scope to prioritize correctness, reproducibility, and research findings.

For detailed information about the Phase 0 research project, see [`docs/development/Phase0_research_project.md`](docs/development/Phase0_research_project.md).

---

## Deployment

Deployment starts with the **Temporal stack** (database, server, UI) and the **temporal-worker**. Bootstrap is idempotent and prepares the environment so that the Genesis workflow (via `genesis.sh`) can deploy the OpenVitals app DB and run migrations next.

**Environment for local work (optional):** To use the same Python packages on the host (notebooks, CLI), use the venv bootstrap creates: from repo root run **`source .venv/bin/activate`**. Or use conda: **`conda create -n openvitals python=3.11`** then **`pip install -r requirements.txt`**; then **`conda activate openvitals`**.

**Bootstrap scripts:** **`bootstrap.linux.remote.sh`** — production/VM install via curl (creates `/opt/open-vitals`, clones repo, runs bootstrap). **`bootstrap.linux.sh`** — run from repo root (dev or after remote clone). Both scripts accept the same **flags**; the remote script passes them through to the main bootstrap. Windows and macOS bootstrap scripts are planned for a future release.

#### Bootstrap flags (both entry points)

| Flag | Short | Description |
|------|--------|-------------|
| `--env dev\|test\|prod` | `-e` | Deployment environment. Written to `config.yaml` (`temporal.deployment_env`) so the correct Temporal namespace and compose override are used. Default is `dev`. |
| `--yes` | `-y` | Non-interactive: skip the config-review pause and continue with defaults. Use for CI or when config is already correct. |

**Optional env vars** (flags take precedence): `OPENVITALS_DEPLOYMENT_ENV` (same as `--env`), `OPENVITALS_YES` (non-empty = skip pause).

**Examples:**

- Dev, interactive (pause to review config):  
  `sudo ./scripts/bootstrap.linux.sh`
- Prod, non-interactive (no pause; env persisted to config):  
  `sudo ./scripts/bootstrap.linux.sh --env prod -y`
- Remote VM, prod, non-interactive (flags passed through):  
  `sudo ./scripts/bootstrap.linux.remote.sh --env prod -y`

---

### Production / VM install (remote)

Use this on a **fresh VM or server**. The script creates **`/opt/open-vitals`**, clones the repo there, then runs the main bootstrap from the clone. **Requires root (sudo).**

**One-liner (curl):**

```bash
curl -fsSL https://raw.githubusercontent.com/helloskyy-io/Open-Vitals/main/scripts/bootstrap.linux.remote.sh | sudo bash
```

**What it does (idempotent):**

1. Creates **`/opt/open-vitals`**.
2. Installs **git** if missing (Ubuntu/Debian, apt).
3. **Clones** the repo into `/opt/open-vitals` if not already there.
4. Runs **`scripts/bootstrap.linux.sh`** from the clone, passing through any flags you provide (e.g. `--env prod -y` for a non-interactive prod deploy).

Safe to run multiple times; if the repo is already present, it skips clone and runs bootstrap again. For a production deploy without the config-review pause, run with flags:  
`sudo ./scripts/bootstrap.linux.remote.sh --env prod -y`

---

### Dev install (local)

Use this when you **already cloned the repo** (e.g. on your laptop or in a custom path). Clone wherever you want, then run the bootstrap from the repo root. **Requires root (sudo).**

**Clone, then run bootstrap:**

```bash
git clone https://github.com/helloskyy-io/Open-Vitals.git open-vitals
cd open-vitals
sudo ./scripts/bootstrap.linux.sh
```

To set deployment environment and skip the config-review pause (e.g. for automation), add flags:  
`sudo ./scripts/bootstrap.linux.sh --env prod -y`

**Clone URLs:**

- **HTTPS:** `https://github.com/helloskyy-io/Open-Vitals`
- **SSH:** `git@github.com:helloskyy-io/Open-Vitals.git`

**One-liner (clone then bootstrap):**

```bash
git clone https://github.com/helloskyy-io/Open-Vitals.git open-vitals && cd open-vitals && sudo ./scripts/bootstrap.linux.sh
```

### What `bootstrap.linux.sh` does (idempotent)

**`bootstrap.linux.sh`** (run from repo root, or by the remote script from `/opt/open-vitals`):

1. **Requires sudo** — Must be run as root.
2. **Ensures Docker** — Installs Docker and Docker Compose (v2) on Linux (apt) if missing.
3. **Creates config files** if they don't exist:
   - `config.yaml` from `templates/.config.template` (sets `openvitals.project_root` to the actual repo path when possible).
   - `.env` from `templates/.env.template` and **auto-generates** both `TEMPORAL_POSTGRES_PASSWORD` and `OPENVITALS_DB_PASSWORD` when creating from template.
4. **Optional pause (only when config was just created):** the script stops and asks you to review—unless you passed **`-y`** or set `OPENVITALS_YES`. You can edit `.env` or `config.yaml` (e.g. Temporal password/port, deployment env), or press **y** to accept defaults and continue.
5. **Reads deployment env** from `config.yaml` (`temporal.deployment_env`: dev | test | prod) and uses the matching Docker Compose override (see `docs/standards/docker_compose_layout.md`). If you passed **`--env`** (or set `OPENVITALS_DEPLOYMENT_ENV`), that value is written to `config.yaml` before this step. This also determines the **Temporal namespace** (e.g. `openvitals-dev`, `openvitals-prod`) and task queue—that’s how dev and production are separated in one cluster. Default is `dev`; set to `prod` (or `test`) when deploying to that environment.
6. **Starts Temporal** (temporal-db, temporal-server, temporal-ui), creates that namespace if needed, then starts **temporal-worker** and runs health checks.
7. **Prints** the Temporal UI URL and the next step (`scripts/genesis.sh`).

Safe to run multiple times; existing `config.yaml` and `.env` are left unchanged.

### Manual steps (when and what to edit)

- **During first run:** If the script just created config, it pauses. You can edit `.env` (e.g. to change Temporal or OpenVitals DB passwords) and/or `config.yaml` (e.g. `temporal.deployment_env`, ports), or press **y** to accept defaults. Both passwords are already generated when `.env` is created from the template.
- **Between bootstrap and Genesis:** Before running `scripts/genesis.sh`, you can change `openvitals.project_root` or other settings in `config.yaml`, or secrets in `.env`, if needed. The real place for manual configuration is this gap; the in-script pause is optional.

### After deployment

- Open **Temporal UI** at the printed URL (e.g. `http://127.0.0.1:8234`).
- **Verify** that the Temporal UI is up and accessible in your browser before running the Genesis workflow.
- Containers: temporal-db, temporal-server, temporal-ui, **temporal-worker**.
- When ready for the next step (Genesis workflow to deploy OpenVitals DB and run migrations), run: **`sudo ./scripts/genesis.sh`**.
- For Temporal deployment, architecture, and workflow/activity standards, see [Temporal standards](docs/standards/temporal_standards.md).

### Resetting the environment (dev/test)

To remove containers, database volumes, and config for a clean start (e.g. before re-running bootstrap), use **`scripts/reset.env.sh`**. The script asks for confirmation before each step; type **YES** to perform that step, or **NO** / **Enter** to skip.

- Step 1: Stop and remove all containers (temporal-*, openvitals-db).
- Step 2: Delete Temporal database volume.
- Step 3: Delete OpenVitals database volume.
- Step 4: Delete `.env` and `config.yaml` in the repo root.

Requires root: **`sudo ./scripts/reset.env.sh`**. At the end it prints a summary of what was done.

---

## Contributing

🚧 **Coming soon**

OpenVitals is designed to be a community‑driven project. Contributions will be welcomed across:

* Data ingestion adapters (new vendors, formats)
* Canonical data models and migrations
* Analytics metrics and visualizations
* Documentation and examples

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for contribution guidelines. 🚧 **Coming soon** — labeled `good-first-issue` tasks will be added as the project stabilizes.

---

## Hosting & Sustainability

OpenVitals is designed to be fully self‑hosted and open.

For users who prefer not to run their own infrastructure, a **managed hosting option** may be offered via HelloSkyy Hosting at a minimal cost. This option will never be required to use OpenVitals, and self‑hosting will remain a first‑class path.

---

## License & Privacy

OpenVitals is released under a source‑available license based on the Business Source License (BUSL) 1.1.

This license allows individuals and organizations to view, modify, and self‑host the software freely for personal or internal use, while restricting the creation of directly competing commercial or SaaS offerings without a commercial license.

* **License:** See [`docs/LICENSE`](docs/LICENSE) for full license details
* **Privacy:** See [`docs/PRIVACY.md`](docs/PRIVACY.md) for privacy policy and data handling practices

---

## Project Status

For the complete long-term platform roadmap and development phases, see [`docs/ROADMAP.md`](docs/ROADMAP.md).


* Phase 0: Research & Prototype — **In Progress**

---

> OpenVitals is an open project focused on transparency, reproducibility, and user data ownership. If you have ideas, questions, or want to get involved, stay tuned — this is just the beginning.
