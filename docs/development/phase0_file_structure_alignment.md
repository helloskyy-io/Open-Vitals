# Phase 0 vs File Structure — Alignment Notes

**Canonical layout:** `docs/file_structure.txt`  
**Checklist / plan:** `docs/development/Phase0_research_project.md`

---

## Discrepancies Identified

### 1. Python package path: `src/` vs `src/openvitals/`

| Phase0 says | File structure has | Resolution |
|-------------|--------------------|------------|
| `src/adapters/`, `src/analytics/`, `src/workflows/`, `src/activities/` | All under `src/openvitals/` (e.g. `src/openvitals/adapters/`) | **Phase0:** Use full path `src/openvitals/...` everywhere. |

Phase0 treats “src” as the package root; the repo uses a nested package `src/openvitals/`. Phase0 should reference `src/openvitals/...` so paths match the file structure and imports.

---

### 2. Temporal: flat workflows/activities vs orchestration/temporal

| Phase0 says | File structure has | Resolution |
|-------------|--------------------|------------|
| `src/workflows/` (e.g. `initialize_openvitals.py`, `ingest_exports.py`) | `src/openvitals/orchestration/temporal/modules/{bootstrap,ingestion,analytics}/workflows.py` | **Phase0:** Point to orchestration/temporal modules and activities. |
| `src/activities/` | `src/openvitals/orchestration/temporal/activities/` (shared activities) | **Phase0:** Use `.../orchestration/temporal/activities/`. |

Stage 8 deliverables and any “workflows/activities” bullets in Phase0 should use the orchestration/temporal layout (modules + activities).

---

### 3. Docker and env config location

| Phase0 says | File structure has | Resolution |
|-------------|--------------------|------------|
| Create `docker-compose.yml` at repo root | `docker/docker-compose.yml` | **Phase0:** Say “Create `docker/docker-compose.yml`” (or “in `docker/`”). |
| Copy `.env.example` → `.env` | Root `.env.example` + `templates/.env.template` | **Phase0:** Optionally note “or copy from `templates/.env.template`”. |

---

### 4. Repo skeleton (Stage 0.1)

| Phase0 lists | File structure adds | Resolution |
|--------------|--------------------|------------|
| `src/`, `sql/`, `data/raw/`, `data/processed/`, `reports/`, `docs/` | `docker/`, `notebooks/`, `scripts/`, `templates/`, `tests/`, `services/` | **Phase0:** Extend 0.1 to include these dirs and use `src/openvitals/` with subpackages (adapters, analytics, analysis, models, orchestration/temporal). Remove flat `src/workflows/` and `src/activities/`. |

---

### 5. File structure doc missing from its own tree

| Observation | Resolution |
|-------------|------------|
| `docs/development/Phase0_research_project.md` exists but file_structure has no `docs/development/` | **File structure:** Add `docs/development/` with `Phase0_research_project.md` (and this alignment doc if desired). |
| File structure lists `phase0_execution_checklist.md` in `docs/` root | Either keep as-is (short checklist in root) or move under `docs/development/`; align naming with Phase0 doc. |

---

### 6. Services naming in Notes

| File structure Notes say | Actual structure | Resolution |
|--------------------------|------------------|------------|
| “Phase 1 adds services/web (Django API…)” | `services/backend/` (Django), `services/temporal-workers/` | **File structure:** Change “services/web” to “services/backend” in Notes. |

---

## Which doc to edit

| Doc | Edits |
|-----|--------|
| **Phase0_research_project.md** | Update all path references to match file_structure: `src/openvitals/...`, `docker/`, orchestration/temporal (modules + activities), and expanded Stage 0.1 skeleton. |
| **file_structure.txt** | Add `docs/development/` and `Phase0_research_project.md`; fix Notes to say `services/backend` instead of `services/web`. |

Result: Phase0 checklist and file structure doc stay in sync; file structure is the single source of truth for layout.
