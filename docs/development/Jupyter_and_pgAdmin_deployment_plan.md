# Jupyter and pgAdmin deployment plan (Temporal / Genesis)

**Scope:** Add Jupyter (and later pgAdmin) as dev-only services, deployable via Genesis when `deployment_env` is `dev`. Local-friendly with minimal friction; safe defaults so accidental use in a public-facing environment does not expose them.

---

## 1. Jupyter — plan

### 1.1 Goals

- **Local-friendly:** Open browser, start working — no password/token drama when used on your own machine.
- **Safe default:** If the same stack is ever used in a public-facing or shared environment, Jupyter is not exposed by default.
- **Dev-only:** Jupyter appears only when `deployment_env` is `dev` (e.g. in `dev.override.yml` or a compose file loaded only for dev).
- **Stack parity:** Same Python env as worker (same `requirements.txt`) so notebooks and workflows use identical deps.

### 1.2 Best-practice approach

**Where Jupyter lives**

- Define the Jupyter service in a **dev-only** compose file:
  - **Option A:** `30-jupyter.yml` — only included when bootstrap/Genesis runs with `dev` override (e.g. `-f 30-jupyter.yml` only for dev). Prod/test never load this file.
  - **Option B:** Put the `jupyter` service definition directly in `dev.override.yml`. Prod/test overrides don’t define it, so it never runs.

Either way: **prod and test never start Jupyter.** No need to “turn off” Jupyter in prod — it simply isn’t there.

**Port exposure (your idea, done right)**

- **Do not publish a host port in the base service definition.**  
  If you ever add Jupyter to a shared/prod compose by mistake, “no ports” means the container is only reachable from other containers on the same Docker network — not from the host or the internet.
- **In dev only:** Publish the port **only in the dev override**, e.g. `ports: ["127.0.0.1:8888:8888"]`.
  - Binding to **127.0.0.1** on the host means only localhost can connect. Even if the machine has a public IP, nothing from the network can hit Jupyter.
- Result: On your laptop you open `http://127.0.0.1:8888` and work. If the same compose is used on a public VM without changing the override, Jupyter still isn’t exposed (no port in base; dev override with 127.0.0.1 is only for your local use).

**Authentication (“no drama” local)**

- Jupyter can run with:
  - **Token (default):** URL contains a token; no password. Fine for local.
  - **Password:** Set via env or config.
  - **No auth:** `--NotebookApp.token=''` and `--NotebookApp.password=''` — only safe if the server is not reachable from the network (e.g. only 127.0.0.1 on host).
- **Recommendation for dev:**  
  - Use **token from env** (e.g. `JUPYTER_TOKEN`) so you can paste the URL once and bookmark it, or  
  - Use **no token** when `JUPYTER_ALLOW_INSECURE_LOCAL=1` or similar in dev, **only** because the port is bound to 127.0.0.1. Document that this is for local use only.  
  This keeps “open browser and work” without opening the door on a public install.

**Summary table**

| Concern              | Approach                                                                 |
|----------------------|--------------------------------------------------------------------------|
| Who runs Jupyter     | Dev only (compose/override loaded only for dev)                         |
| Host port            | Not in base; in dev override only, e.g. `127.0.0.1:8888:8888`          |
| Auth                 | No token, no password (safe: dev-only + 127.0.0.1 only)                  |
| Image / deps         | Same Dockerfile/`requirements.txt` as worker (or shared base)           |
| How it’s started     | Genesis activity `ensure_jupyter_up` when `deployment_env` is dev      |

### 1.3 Implementation outline

1. **Compose**
   - Add `30-jupyter.yml` (or define `jupyter` in `dev.override.yml`):
     - Image built from same `requirements.txt` as worker (or a small Jupyter Dockerfile that extends worker base).
     - No `ports:` in the base service (or in a shared fragment). In **dev.override.yml** only: `jupyter.ports: ["127.0.0.1:8888:8888"]`.
     - Env: `JUPYTER_TOKEN` (optional), `OPENVITALS_*` for DB connection if needed; mount repo so notebooks see `notebooks/`, `data/`, etc.
   - Ensure `30-jupyter.yml` is **only** loaded when `temporal.deployment_env` is `dev` (bootstrap and Genesis already use the override; add this file to the compose stack only for dev).

2. **Genesis**
   - Add activity `ensure_jupyter_up` (e.g. in `activities/dev/ensure_jupyter_up.py`): same pattern as `docker_compose_up` — run `docker compose up -d jupyter` with the right compose set (dev override + 30-jupyter).
   - In `genesis_helper.compile_execution_plan`, when `deployment_env == "dev"`, append a step for `ensure_jupyter_up`; otherwise skip it.

3. **Docs**
   - README: “After Genesis (dev), Jupyter is at http://127.0.0.1:8888. Token in env or no auth when bound to localhost only.”
   - Note: “Jupyter is dev-only and not exposed in test/prod.”

### 1.4 Security / DevOps summary

- **No host port in base:** Safe default; accidental inclusion in a public stack does not expose Jupyter.
- **127.0.0.1 in dev:** Only localhost can connect; no network exposure.
- **Dev-only compose:** Prod/test never load Jupyter; no “switch” to turn off — it’s simply absent.
- **No token/password:** Acceptable when dev-only and 127.0.0.1-only; document and restrict to dev.

---

## 2. pgAdmin — plan (next)

- Same ideas: **dev-only** service, **no host port** in base, **127.0.0.1:port** in dev override only.
- pgAdmin will need OpenVitals DB connection (host: `openvitals-db`, port, user, db, password from config/secrets). We can wire that via env or a mounted config so “open browser and connect” works without re-typing credentials.
- Plan details (compose file name, port, Genesis step) to be added in a follow-up; this doc can be extended with a “pgAdmin” section when you’re ready.

---

## 3. References

- Phase 0: `docs/development/Phase0_research_project.md` — Stage 0.4 (Genesis), Stage 8 (Temporalization); Jupyter in compose and `ensure_jupyter_up` activity.
- Compose layout: `docs/standards/docker_compose_layout.md` — numbered base files, dev/test/prod overrides.
- Tech stack: `docs/architecture/Tech_Stack.md` — Jupyter as dev-only.
