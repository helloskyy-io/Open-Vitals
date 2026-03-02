# Apple Health Export Notes + Record-Type Exploration Script

## What Apple Health exports and why we use `export.xml`

When you export data from Apple Health, you’ll typically see two XML files:

### `export.xml` (primary / HealthKit-native export)
- This is the main HealthKit export format produced by Apple Health.
- It contains the full set of HealthKit entities (most importantly `<Record>` elements) and includes rich metadata:
  - HealthKit `type` identifiers (e.g., `HKQuantityTypeIdentifierHeartRate`)
  - units and values
  - sources (app/device), timestamps, and optional metadata entries
  - other element families such as workouts, correlations, activity summaries, etc.
- This file is the best “source of truth” for exploratory analysis and ingestion because it is the most complete representation of your Health data in Apple’s native model.

### `export_cda.xml` (CDA / clinical document format)
- This is a standards-oriented export formatted as an HL7 CDA (Clinical Document Architecture) document.
- It is structured like a clinical report and uses healthcare coding systems (e.g., LOINC, SNOMED CT).
- This file is useful for interoperability with healthcare systems, but it is often a curated/clinical subset and is less convenient for extracting the full breadth of HealthKit record types.

**We use `export.xml` in this directory because we want the most complete and direct representation of HealthKit data (all record types, attributes, sources, and metadata).**

---

## What this script does

This directory contains an exploration script that scans `export.xml` and answers two questions:

1. **What unique HealthKit record types are present?**
   - Example: `HKQuantityTypeIdentifierHeartRate`, `HKQuantityTypeIdentifierBodyMass`, etc.

2. **For each unique record type, what fields (attributes) appear?**
   - These fields come from the XML attributes on each `<Record ...>` element, such as:
     - `type`, `unit`, `value`, `sourceName`, `sourceVersion`, `device`, `creationDate`, `startDate`, `endDate`

Additionally, the script captures:
- **Child element tags under each `<Record>`**, such as:
  - `MetadataEntry`
  - `HeartRateVariabilityMetadataList` (when present)

### Why this is useful
- Apple Health exports are large and heterogeneous.
- This script gives you a quick inventory of:
  - what you actually have in a given export
  - how record “shapes” differ by type
- It’s a helpful first step before writing parsers, building schemas, or designing ingestion pipelines.

---

## Streaming-safe parsing (important)

Apple’s `export.xml` includes a large `<!DOCTYPE ... [ ... ]>` block (DTD/internal subset) at the top of the file.
Some parsers can be picky about this, and large exports also need to be handled efficiently.

This script wraps the file stream to:
- safely ignore/remove the DOCTYPE block while reading
- avoid loading the entire XML into memory
- stream through the file using `xml.etree.ElementTree.iterparse`

---

## Output file created

Running the script produces:

### `record_type_field_summary.json`
A JSON summary containing:
- `record_type_count`: number of unique `<Record type="...">` values found
- `record_types`: sorted list of unique record types
- `attributes_by_record_type`: mapping of record type → list of observed attribute names
- `child_tags_by_record_type`: mapping of record type → list of observed child tags

This JSON is intentionally easy to consume in follow-on scripts or notebooks.

---

## How to run

1. Export your Apple Health data.
2. Copy the main export file into the sample data directory:
