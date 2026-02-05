<img src="hs_logo.jpg" alt="HelloSkyy Logo" width="100%"/>

# OpenVitals

**Own your health data. Understand your body. On your terms.**

---

## What is OpenVitals?

OpenVitals is an open, vendor‑neutral platform for ingesting, storing, and analyzing personal wearable health data outside of proprietary ecosystems.

It allows individuals to take ownership of their raw health data and reproduce key health metrics using transparent, inspectable analytics.

---

## Why does OpenVitals exist?

Modern wearables generate massive amounts of personal health data, but that data is typically locked inside closed platforms controlled by large vendors. These platforms decide how data is stored, how metrics are computed, and which insights users are allowed to see.

OpenVitals exists to reverse that model.

**Not my storage, not my data.**

The goal is to give individuals full ownership over their health data, make analytics reproducible and transparent, and remove unnecessary vendor lock‑in — while still enabling advanced insights and AI‑driven interpretation on the user’s terms.

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

## Quickstart

🚧 **Coming soon**

OpenVitals will provide a simple bootstrap process that deploys a fully local, self‑hosted environment using automated workflows.

The planned quickstart will:

* Provision an empty VM or local environment
* Deploy required services automatically
* Ingest exported wearable data
* Launch a local analytics interface

No cloud account required. Your data stays on your machine.

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
