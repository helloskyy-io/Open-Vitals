# Phase 1 — Automated Ingestion (Planning Capture)

**Phase:** 1 — Deterministic Ingestion Engine (see `docs/ROADMAP.md`).  
**Purpose:** Capture ideas and decisions from planning discussions for Phase 1 (no implementation yet). The mobile helper app that feeds this pipeline is Phase 5 (mobile companion) scope but is designed to feed Phase 1 ingestion.

---

## Where This Fits in the ROADMAP

| Idea | Phase | ROADMAP scope it matches |
|------|--------|---------------------------|
| Automated data pipeline (scheduled ingest, incremental, idempotent) | **Phase 1** | Temporal-scheduled ingestion, incremental data updates, vendor adapter interfaces |
| Mobile helper app (Health Connect → our cloud) | **Phase 5** | Mobile companion — feeds Phase 1 pipeline |

Phase 0 uses manual export (Takeout, Apple). Phase 1 adds *automated* ingestion; the mobile app is the on-device piece that feeds that pipeline for Android/Health Connect.

---

## Data Source Reality (Android / Google Ecosystem)

- **Health Connect** = on-device DB on Android. No cloud API; reading requires an app on the device or the built-in scheduled export (Android 14+) to Drive.
- **Fitbit** = cloud. Fitbit Web API + OAuth can be called from a server; no phone required for Fitbit-sourced data.
- **Google Fit** (legacy) = was cloud; API deprecated (e.g. mid-2025). Going forward, Google/Pixel data flows through **Health Connect** on the device.
- **Takeout** = one-off, slow (hours/days); suitable for research/testing only, not continuous sync.

**Implication:** For continuous Android/Pixel data we need either (1) a **helper app** that reads Health Connect and pushes to our backend, or (2) Health Connect **scheduled export to Drive** and a backend job that pulls the zip from Drive. For maximum coverage (including metrics Fitbit doesn’t write to Health Connect), combine **Health Connect (device)** + **Fitbit API (cloud)**.

---

## Mobile Helper App — High-Level Approach (Phase 5, feeds Phase 1)

- **What:** Small Android app using the **Health Connect SDK** to read data and send it to **our cloud** (OpenVitals ingest API).
- **Why:** Health Connect has no server-side API; the only way to get its data off the device programmatically is an app on the device (or the OS’s scheduled export to Drive).
- **Goal:** Regular sync (e.g. every 15–30 min) of *new* data only — no “send everything and dedupe” as datasets grow.

---

## Incremental Sync — Best Practices (Capture)

- **Avoid:** Sending full history every run and filtering duplicates on the server (inefficient, cumbersome as data grows).
- **Do:** Time-window incremental sync + idempotent upsert on server.

### Client (phone app)

- [ ] Persist **last synced end time** per data type (e.g. steps, sleep, heart rate) in local storage (SharedPreferences or local DB).
- [ ] Each run (e.g. every 15–30 min): for each type, call Health Connect with **time range filter** `TimeRangeFilter.between(start, end)` where `start = lastSyncedEndTime - overlap`, `end = now()`. Overlap (e.g. 15–30 min) catches late-arriving data from watch sync.
- [ ] Upload only the **batch** returned for that window to our ingest API.
- [ ] Update `lastSyncedEndTime` to `end` (or max record time in response).
- [ ] Respect Health Connect **request quotas** (e.g. 15–30 min interval; sync only needed data types).

### Server (Phase 1 pipeline)

- [ ] **Idempotent upsert** per record: stable ID (e.g. `user_id + data_type + record_id` or hash of content). Duplicate uploads overwrite or no-op; no duplicate rows.
- [ ] Ingest API accepts batches from the helper app and writes into canonical schema (Phase 1 pipeline).

### Late-arriving data

- Health Connect records use **event time** (when the step/sleep happened), not “when written.” Watches can sync later and backfill. Using a small **overlap** window on the client + upsert on server avoids missing data without re-sending full history.

---

## Alternative: Health Connect Scheduled Export (No Custom App)

- **Android 14+:** Health Connect can **scheduled export** (daily/weekly/monthly) to Google Drive (or other cloud). Device produces an encrypted zip.
- **Our backend (Phase 1):** Temporal (or cron) job that **pulls the zip from Drive** on a schedule and runs existing ingestion. No custom phone app; less frequent (daily/weekly), but simpler.
- **When to use:** If we don’t need 15–30 min granularity, scheduled export + Drive pull may be enough before investing in a mobile app.

---

## Fitbit Cloud + Health Connect

- Health Connect does **not** have “all” data; only what apps write into it (per data type, user permissions). Fitbit writes a subset (e.g. steps, exercise, distance, floors, calories; sleep/HR depending on app).
- For **fullest** coverage: **Health Connect (device)** for what’s there + **Fitbit Web API (cloud)** for the rest. Document which metrics come from which source in dataset/schema docs.

---

## Open Wearables as Optional Complement

- **Open Wearables** = self-hosted “one API for many wearables” (Garmin, Polar, Suunto, Apple export, etc.). Database-driven, normalized schema, sync via Celery. **Does not** (as of our research) cover Health Connect / Google; focused on other providers.
- **OpenVitals** = analytics, visualizations, AI interpretation on top of data. Natural **complement**: use Open Wearables (or similar) as aggregation layer where it fits; OpenVitals consumes and does metrics, comparison, viz, AI.
- **Our pipeline (Phase 1):** Can be fed by (a) our own helper app + Fitbit API, or (b) Open Wearables API when we want to add more sources, or (c) both.

---

## Action Items (Checklist for Later)

- [ ] **Phase 1:** Design ingest API and idempotent upsert schema for records pushed by mobile app (and/or Drive zip). Ensure canonical schema supports source attribution (Health Connect vs Fitbit cloud).
- [ ] **Phase 1:** Temporal workflow (or equivalent) for scheduled pull of Health Connect export zip from Drive (if using built-in export instead of/in addition to helper app).
- [ ] **Phase 5:** Scope mobile companion: minimal “Health Connect → our backend” helper app with time-window incremental sync, quota-aware (15–30 min), per–data-type last-sync cursor.
- [ ] **Docs:** Document in `docs/data/extraction/` (e.g. automated README) the two paths: (1) Health Connect scheduled export → Drive → our pipeline, (2) Helper app → ingest API. Note Fitbit cloud as optional second source for full coverage.
- [ ] **Optional:** Evaluate Open Wearables (or similar) as aggregation layer for non-Google sources; document how OpenVitals would consume from it (analytics/viz/AI on top).

---

*This doc is a planning capture for Phase 1 (and the Phase 5 app that feeds it). It is not a full implementation plan. Update as decisions and designs solidify.*
