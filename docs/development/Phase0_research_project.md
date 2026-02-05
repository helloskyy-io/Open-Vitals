# Reclaiming Wearable Health Data

## Class Project Proposal (CSCI/DASC 6010)

### Title

**Reclaiming Wearable Health Data: An Empirical Analysis of Vendor Lock-In and Reproducible Health Analytics**

---

### 1. Introduction and Motivation

Consumer wearable devices such as smartwatches and fitness trackers generate continuous, high-volume streams of personal health data. These data increasingly influence individual fitness decisions and, in some cases, clinical discussions. Despite this, most wearable data is stored and interpreted within proprietary ecosystems (e.g., Google Fit, Apple Health), where the vendor controls both the storage of raw data and the computation of higher-level health metrics.

This project is motivated by a central question in modern data analytics and data management: **to what extent can meaningful health analytics be reproduced from raw wearable data outside of proprietary platforms?** If users export their own data and store it independently, can they recover the same insights that vendors provide, or do proprietary transformations fundamentally limit transparency and portability?

This problem is not only technical but also representative of broader issues in big data systems, including data ownership, reproducibility, and vendor lock-in. By focusing on real-world wearable datasets, this project aims to analyze these issues empirically.

---

### 2. Research Questions

**Primary Research Question**
Which wearable health analytics can be reproduced from raw user data outside proprietary vendor platforms?

**Secondary Research Question**
What information is lost, altered, or obscured when wearable health data is migrated across vendor ecosystems?

---

### 3. Data

The dataset for this project is constructed from real-world wearable health data exported from multiple consumer platforms:

* Google Fit data exported from a Pixel phone and Pixel Watch
* Apple Health data exported from an Apple Watch

These datasets include longitudinal, time-series measurements such as:

* Daily step counts
* Heart rate samples
* Sleep sessions and total sleep duration

The data exhibits key big data characteristics, including high temporal resolution, heterogeneous schemas, missing values, and platform-specific representations. Dataset documentation will follow the *Datasheets for Datasets* framework, detailing data provenance, structure, known limitations, and ethical considerations. All data used in the project is voluntarily provided by the data subjects and used solely for academic analysis.

---

### 4. Method

The project implements a reproducible analytics pipeline consisting of the following stages:

1. **Data Export and Ingestion**
   Raw wearable data is exported from Google Fit and Apple Health and ingested into a local analysis environment.

2. **Normalization and Storage**
   Vendor-specific schemas are transformed into a unified, vendor-agnostic data model and stored in a database designed for time-series analytics.

3. **Metric Reproduction**
   Selected health metrics are recomputed using transparent, open methods. For this project, the focus is on three core metrics:

   * Daily step count
   * Total sleep duration per day
   * Resting heart rate (derived from heart rate samples)

4. **Comparison and Evaluation**
   Reproduced metrics are compared quantitatively against vendor-provided summaries to assess agreement, divergence, and loss of information.

To ensure reproducibility and reliability of the ingestion process, workflow orchestration is implemented using Temporal. Temporal provides deterministic execution, retry safety, and an auditable history of ingestion and transformation steps, supporting scientific repeatability.

---

### 5. Results

Results are evaluated using:

* Correlation and error analysis between vendor-reported and reproduced metrics
* Cross-platform comparisons for equivalent metrics
* Visualizations highlighting discrepancies, missing data, and alignment over time

All figures include labeled axes, descriptive captions, and are selected to clearly communicate empirical findings without redundancy.

---

### 6. Discussion and Future Work

The discussion analyzes which wearable health insights are transparently reproducible and which rely on proprietary transformations. The implications of these findings are discussed in the context of data ownership, reproducibility, and user trust in large-scale health analytics systems.

Future work includes expanding the dataset to additional users and devices, incorporating more advanced analytics, and exploring open-source platforms that enable individuals to maintain full ownership and control of their wearable health data.

---
