# Stage 1 — Export Acquisition + Dataset Datasheet (TEMP)

**Purpose:** Temporary planning doc with finer-grained steps for Stage 1.  
**Source:** Phase 0 checklist § Stage 1; this doc adds detail and ownership.  
**Delete or fold into Phase0_research_project.md once Stage 1 is done.**

---

## Overview

Stage 1 has three parts:

| Section | Owner | Summary |
|--------|--------|---------|
| **1.1** | Member A (Google) | Google Takeout export + metadata |
| **1.2** | Member B (Apple) | Apple Health export + metadata |
| **1.3** | Team (or Member C) | Dataset datasheet (`docs/data/dataset_description.md`) |

**Deliverables:** Raw exports in `data/raw/{google_fit,apple_health}/`, export metadata recorded, and `docs/data/dataset_description.md`.

### Doc layout (Stage 1)

Canonical layout: `docs/file_structure.txt`. Data-related docs live under `docs/data/`:

| What | Path |
|------|------|
| Dataset datasheet (1.3) | `docs/data/dataset_description.md` |
| Source schemas (Stage 2) | `docs/data/source_schemas/google_fit.md`, `apple_health.md` |
| Manual export procedures | `docs/data/extraction/manual/google_fit_export.md`, `apple_health_export.md` — **authoritative** step-by-step; create these in Stage 1. |
| Automated ingestion (Phase 1+) | `docs/data/extraction/automated/` — README + vendor docs when Temporal workflows exist. |

Extraction overview (manual vs automated): `docs/data/extraction/README.md`. Stage 1 creates `docs/data/` stubs and the two manual procedure files; checklist items above are short versions; full procedures live in the extraction docs.

---

## 1.1 Google Takeout Export (Member A — Google)

**Authoritative procedure:** `docs/data/extraction/manual/google_fit_export.md` (create this file for the full step-by-step; this section is a short checklist only.)

### Prerequisites

- [ ] Google account with Fit data (e.g. Pixel phone + Pixel Watch linked)
- [ ] Enough Google Drive / export destination space for the Takeout zip
- [ ] Repo cloned and `data/raw/google_fit/` present (gitignored)

### Manual steps

1. **Request the export**
   - Go to [Google Takeout](https://takeout.google.com/)
   - Select **only** "Fit" (deselect all others, or select Fit plus any you need)
   - Choose export format (e.g. zip), size (e.g. 2 GB chunks), and delivery (download link or Drive)
   - Submit; wait for email (can take minutes to hours)

2. **Download the archive**
   - Use the link from the email to download the zip (or from Drive)
   - Do **not** commit the zip; store only under `data/raw/google_fit/`

3. **Place the file**
   - Move/copy the zip to:  
     `data/raw/google_fit/takeout_<YYYY-MM-DD>.zip`  
     (use the date you downloaded or the export date—pick one convention and stick to it)

### Metadata to record

Create a small metadata file or table (e.g. `data/raw/google_fit/README.md` or a JSON/YAML next to the zip) with:

- [ ] **Export date/time** — when the export was requested or completed
- [ ] **Approximate date range** — e.g. "2024-01-01 to 2025-02-15" (from Fit app or Takeout contents)
- [ ] **Device sources** — e.g. "Pixel 7, Pixel Watch 2"

These will be used in the dataset datasheet (1.3).

### Optional (can be Stage 2)

- [ ] Unzip locally and note top-level folders/files (for `docs/data/source_schemas/google_fit.md` later)

### Checklist (your part of Stage 1.1)

- [ ] Takeout requested with Fit selected only
- [ ] Zip downloaded
- [ ] Zip stored at `data/raw/google_fit/takeout_<YYYY-MM-DD>.zip`
- [ ] Export metadata recorded (date, date range, devices)

---

## 1.2 Apple Health Export (Member B — Apple)

**Authoritative procedure:** `docs/data/extraction/manual/apple_health_export.md` (create this file for the full step-by-step; this section is a short checklist only.)

### Prerequisites

- [ ] iPhone with Health app and Apple Watch data
- [ ] Repo cloned and `data/raw/apple_health/` present (gitignored)

### Manual steps

1. **Export from Health app**
   - Open Health → profile (top right) → Export All Health Data
   - Wait for export; share/save the zip (e.g. AirDrop to laptop, or save to Files and copy)

2. **Place the file**
   - Copy to:  
     `data/raw/apple_health/apple_health_<YYYY-MM-DD>.zip`

### Metadata to record

- [ ] Export date/time
- [ ] Approximate date range
- [ ] Device sources (e.g. iPhone 15, Apple Watch Series 9)

### Checklist (Member B)

- [ ] Health data exported
- [ ] Zip stored at `data/raw/apple_health/apple_health_<YYYY-MM-DD>.zip`
- [ ] Export metadata recorded

---

## 1.3 Dataset Datasheet (Phase 0)

**Owner:** Team or Member C (Analytics). Can be written once at least one export exists; update when both exist.

### Content (`docs/data/dataset_description.md`)

- [ ] **Provenance** — where the data came from (Google Takeout Fit, Apple Health export), who exported, when
- [ ] **Time range** — approximate start/end dates covered by the combined dataset
- [ ] **Devices** — e.g. Pixel phone + Pixel Watch; iPhone + Apple Watch
- [ ] **Known limitations** — e.g. "Fit export does not include X", "Health export is full dump only"
- [ ] **Privacy/ethics** — voluntary participation, academic use only, no PII in repo, etc. (align with Datasheets for Datasets)

### Checklist

- [ ] Create `docs/data/dataset_description.md` with the sections above
- [ ] Fill in from 1.1 and 1.2 metadata; update when second export is available

---

## Tooling: Manual vs Scripts vs Jupyter

| Task | Type | Tool |
|------|------|------|
| Request Takeout / Export Health | Manual | Browser / iPhone |
| Download and move zip | Manual (or script) | OS / file manager |
| Record metadata | Manual or script | Editor, or small script/notebook |
| Unzip and inspect (Stage 2) | Script / notebook | Jupyter or Python script |

**Stage 1** is mostly **manual**: export in the vendor UI, download, place file, write metadata. A small **script or Jupyter cell** can help with:

- Checking that `data/raw/google_fit/` exists and has the expected zip name
- Validating zip (e.g. `zipfile.is_zipfile()`)
- Template for metadata (YAML/JSON) that you fill in

**Jupyter** is appropriate for exploratory checks and for later stages (parsing, metrics). For Stage 1, a short script or a single notebook cell is enough if you want automation; otherwise, manual is fine.

---

## Dependencies and order

- **1.1 and 1.2** can be done in parallel by Member A and Member B (no shared code or shared files).
- **1.3** can start as soon as one export + metadata exist; update when both exist.
- **Stage 2** (schema recon) depends on having the zips; can start as soon as your export is in place.

---

## Branch strategy (reminder)

- Work on a feature branch (e.g. `feature/stage1-google-export`).
- Do not commit raw data; only paths, READMEs, and metadata (and later `docs/data/dataset_description.md`).
- Merge to `main` via PR after review.
