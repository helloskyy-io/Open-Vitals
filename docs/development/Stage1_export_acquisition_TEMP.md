# Stage 1 — Export Acquisition + Dataset Datasheet (TEMP)

**Purpose:** What is required to complete Stage 1.  
**Source:** Phase 0 checklist § Stage 1.  
**When done:** Delete or fold into Phase0_research_project.md.

---

## Overview

| Section | Owner | Required |
|--------|--------|----------|
| **1.1** | Member A (Google) | Acquire Google Takeout export, place in repo with correct path and name |
| **1.2** | Member B (Apple) | Acquire Apple Health export, place in repo with correct path and name |
| **1.3** | Team (or Member C) | Create dataset datasheet at `docs/data/dataset_description.md` |

**Stage 1 deliverables:** Raw exports in the correct directories with correct naming; dataset datasheet. The raw exports log (JSON, per-export metadata) and date range are produced in Stage 2 from the Jupyter notebook. Bronze ingestion (dedup into `data/bronze/`) is Stage 3.

**Doc layout:** See `docs/file_structure.txt`. Dataset datasheet → `docs/data/dataset_description.md`. Source schemas and manual extraction procedures → `docs/data/source_schemas/`, `docs/data/extraction/manual/`.

---

## 1.1 Google Takeout Export (Member A — Google)

**Full procedure:** `docs/data/extraction/manual/google_fit_export.md` (authoritative). Below is the checklist.

### Prerequisites

- Google account with Fit data (e.g. Pixel phone + Pixel Watch linked)
- Enough Google Drive / export destination space
- Repo with `data/raw/google_fit/` present (gitignored)

### Required steps

1. **Request the export**  
   [Google Takeout](https://takeout.google.com/) → select Fit (and Fitbit if desired) → choose format (zip), size, delivery → submit. Wait for email (can take hours).

2. **Download the archive**  
   Use the link from the email (or Drive). Do not commit the zip.

3. **Place the file**  
   Move/copy to:  
   `data/raw/google_fit/takeout_<YYYY-MM-DD>.zip`  
   Use the download date or export date; pick one convention and stick to it.

Optional: unzip and explore manually. No metadata file to create in Stage 1.

### Checklist (1.1)

- [x] Takeout requested (Fit, and Fitbit if desired)
- [x] Zip downloaded
- [x] Zip (or unzipped folder) at `data/raw/google_fit/takeout_<YYYY-MM-DD>.zip` (or `takeout_<YYYY-MM-DD>/`)

---

## 1.2 Apple Health Export (Member B — Apple)

**Full procedure:** `docs/data/extraction/manual/apple_health_export.md` (authoritative). Below is the checklist.

### Prerequisites

- iPhone with Health app and Apple Watch data
- Repo with `data/raw/apple_health/` present (gitignored)

### Required steps

1. **Export from Health app**  
   Health → profile (top right) → Export All Health Data. Wait; share/save the zip (e.g. AirDrop to laptop).

2. **Place the file**  
   Copy to:  
   `data/raw/apple_health/apple_health_<YYYY-MM-DD>.zip`

No metadata file to create in Stage 1.

### Checklist (1.2)

- [ ] Health data exported
- [ ] Zip at `data/raw/apple_health/apple_health_<YYYY-MM-DD>.zip`

---

## 1.3 Dataset Datasheet (Phase 0): Defines the datasets used for the class project

**Owner:** Team or Member C (Analytics).

**Required:** Create `docs/data/dataset_description.md` with:

- **Provenance** — where the data came from (e.g. Google Takeout Fit + Fitbit, Apple Health export), who exported, export date(s)
- **Time range** — approximate start/end dates covered by the dataset (can be filled in when Stage 2 recon is done)
- **Source** — e.g. "Google (Fit + Fitbit)", "Apple Health"
- **Known limitations** — e.g. what the export does or does not include
- **Privacy/ethics** — voluntary participation, academic use only, no PII in repo (Datasheets for Datasets)

Can be drafted once at least one export exists; update when both exist and when Stage 2 provides date range and other details.

### Checklist (1.3)

- [ ] Create `docs/data/dataset_description.md` with the sections above
- [ ] Fill in provenance, source; add time range when known from Stage 2; update when second export is available

---

## Stage 2 — Source Schema Recon (reference)

Stage 2 produces: `docs/data/source_schemas/google_fit.md`, `apple_health.md`, and a **raw exports log** in JSON (e.g. `data/raw/google_fit/raw_exports.json`) — one entry per export with metadata (export folder, export date, source, data date range, counts). All generated from the Jupyter notebook. Full checklist: Phase 0 § Stage 2 (folder structure, data headers+paths, Set A mapping, date range, raw exports log, deliverables). Stage 3 (Bronze) then ingests the raw files into the deduplicated Bronze store.

---

## Tooling

| Task | Tool |
|------|------|
| Request / download / place export | Manual (browser, phone, file manager) |
| Optional validation | Script or single Jupyter cell (e.g. check path, `zipfile.is_zipfile()`) |
| Metadata, schema recon | Stage 2 — Jupyter notebook |

---

## Dependencies and order

- 1.1 and 1.2 can be done in parallel.
- 1.3 can start once at least one export exists; refine when Stage 2 recon is done and when both exports exist.
- Stage 2 starts once the export(s) are in place.

---

## Branch strategy

- Work on a feature branch (e.g. `feature/stage1-google-export`).
- Do not commit raw data; only code, docs, and (from Stage 2) the raw exports log (in data/, gitignored) and dataset datasheet.
- Merge to `main` via PR.
