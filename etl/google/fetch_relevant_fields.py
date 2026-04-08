from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Source definitions: where HR, steps, and sleep data lives in a Takeout export.
#
# Each source has:
#   vendor   – "google_fit" or "fitbit"
#   path     – directory relative to Takeout root
#   format   – "json" or "csv"
#   match    – how to identify relevant files (prefix, glob, or data_source key)
#   notes    – what the data contains
# ---------------------------------------------------------------------------

SOURCES = {
    "heart_rate": [
        {
            "vendor": "google_fit",
            "path": "Fit/All Data",
            "format": "json",
            "data_source_contains": "com.google.heart_rate.bpm",
            "notes": "Google Fit heart rate BPM data points (nanosecond timestamps, fpVal BPM)",
        },
        {
            "vendor": "fitbit",
            "path": "Fitbit/Global Export Data",
            "format": "json",
            "filename_prefix": "heart_rate-",
            "notes": "Fitbit intraday HR (per-second BPM with confidence score)",
        },
        {
            "vendor": "fitbit",
            "path": "Fitbit/Global Export Data",
            "format": "json",
            "filename_prefix": "resting_heart_rate-",
            "notes": "Fitbit daily resting HR (computed by Fitbit, one value per day)",
        },
    ],
    "steps": [
        {
            "vendor": "google_fit",
            "path": "Fit/All Data",
            "format": "json",
            "data_source_contains": "com.google.step_count.delta",
            "notes": "Google Fit step deltas (nanosecond timestamps, intVal step count per interval)",
        },
        {
            "vendor": "fitbit",
            "path": "Fitbit/Global Export Data",
            "format": "json",
            "filename_prefix": "steps-",
            "notes": "Fitbit per-minute step counts (dateTime + string value)",
        },
    ],
    "sleep": [
        {
            "vendor": "google_fit",
            "path": "Fit/All Data",
            "format": "json",
            "data_source_contains": "com.google.sleep.segment",
            "notes": "Google Fit sleep segments (intVal stage code, nanosecond timestamps)",
        },
        {
            "vendor": "fitbit",
            "path": "Fitbit/Global Export Data",
            "format": "json",
            "filename_prefix": "sleep-",
            "notes": "Fitbit sleep logs with stage-level detail (wake/light/deep/rem, seconds per stage)",
        },
        {
            "vendor": "fitbit",
            "path": "Fitbit/Sleep Score",
            "format": "csv",
            "filename_prefix": "sleep_score",
            "notes": "Fitbit sleep score CSV (daily aggregate: overall score, deep minutes, resting HR)",
        },
    ],
}


def match_fit_all_data_files(
    all_data_dir: Path,
    data_source_contains: str,
) -> list[dict]:
    """
    Match Google Fit 'All Data' JSON files by reading the 'Data Source' field
    inside each file and checking if it contains the given substring.
    """
    matches = []
    if not all_data_dir.is_dir():
        return matches

    for f in sorted(all_data_dir.iterdir()):
        if f.suffix != ".json":
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if not isinstance(data, dict):
            continue

        source = data.get("Data Source", "")
        if data_source_contains in source:
            point_count = len(data.get("Data Points", []))
            matches.append({
                "file": str(f.name),
                "data_source": source,
                "data_point_count": point_count,
            })

    return matches


def match_prefix_files(directory: Path, prefix: str, ext: str) -> list[dict]:
    """Match files in a directory by filename prefix and extension."""
    matches = []
    if not directory.is_dir():
        return matches

    for f in sorted(directory.iterdir()):
        if f.name.startswith(prefix) and f.suffix == f".{ext}":
            size = f.stat().st_size
            matches.append({
                "file": str(f.name),
                "size_bytes": size,
            })

    return matches


def count_records_in_json_array(path: Path) -> int | None:
    """Count elements in a JSON file that contains a top-level array."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return None


def summarize_hr_steps_sleep(takeout_root: Path) -> dict:
    """
    Scan the Takeout directory for HR/steps/sleep data sources.
    For each source definition, find matching files and count records.
    """
    categories: dict[str, dict] = {}

    for category, source_defs in SOURCES.items():
        sources_found = []

        for src in source_defs:
            directory = takeout_root / src["path"]
            ext = src["format"]

            # Match files based on the source definition
            if "data_source_contains" in src:
                matched_files = match_fit_all_data_files(directory, src["data_source_contains"])
            elif "filename_prefix" in src:
                matched_files = match_prefix_files(directory, src["filename_prefix"], ext)
            else:
                continue

            if not matched_files:
                continue

            total_records = 0
            for mf in matched_files:
                file_path = directory / mf["file"]
                if "data_point_count" in mf:
                    total_records += mf["data_point_count"]
                else:
                    count = count_records_in_json_array(file_path)
                    if count is not None:
                        total_records += count
                        mf["record_count"] = count

            sources_found.append({
                "vendor": src["vendor"],
                "path": src["path"],
                "format": ext,
                "notes": src["notes"],
                "files_matched": len(matched_files),
                "total_records": total_records,
                "files": matched_files,
            })

        categories[category] = {
            "sources_found": len(sources_found),
            "total_records": sum(s["total_records"] for s in sources_found),
            "sources": sources_found,
        }

    # Grand totals
    total_sources = sum(c["sources_found"] for c in categories.values())
    total_records = sum(c["total_records"] for c in categories.values())

    return {
        "source_directory": str(takeout_root),
        "categories": categories,
        "total_source_groups": total_sources,
        "total_records_across_categories": total_records,
        "notes": {
            "filtering": "Sources are defined in SOURCES dict at top of script. "
                         "Google Fit files are matched by 'Data Source' field inside JSON. "
                         "Fitbit files are matched by filename prefix.",
            "edit_filters_here": "Update SOURCES dict to add/remove data sources.",
            "overlap_warning": "Google Fit and Fitbit may contain overlapping data "
                               "(e.g. Fitbit HR synced to Google Fit). "
                               "The loader must pick one authoritative source per data type.",
        },
    }


def write_json(data: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    takeout_root = Path("data/google/Takeout")
    out_path = Path("data/google/hr_steps_sleep_record_types.json")

    summary = summarize_hr_steps_sleep(takeout_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(summary, out_path)

    print(f"Wrote {out_path}")
    print(f"Total source groups found: {summary['total_source_groups']}")
    print(f"Total records across all categories: {summary['total_records_across_categories']}")
    print()
    for cat, info in summary["categories"].items():
        print(f"  {cat}: {info['sources_found']} sources, {info['total_records']} records")
        for src in info["sources"]:
            print(f"    {src['vendor']}/{src['path']} — {src['files_matched']} files, {src['total_records']} records")
            print(f"      {src['notes']}")
