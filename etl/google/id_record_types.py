from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path


def identify_vendor(rel_path: str) -> str:
    """Classify a file as 'google_fit' or 'fitbit' based on its top-level directory."""
    first_dir = rel_path.split("/")[0] if "/" in rel_path else ""
    if first_dir == "Fitbit":
        return "fitbit"
    return "google_fit"


def data_type_from_fit_json(path: Path) -> str | None:
    """
    Extract the Google Fit data type from the 'Data Source' field inside the JSON.

    Data Source looks like:
        'derived:com.google.heart_rate.bpm:com.google.android.gms:...'
        'raw:com.google.step_count.delta:Google:Pixel 8 Pro:...'

    Returns the data type portion, e.g. 'com.google.heart_rate.bpm'
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    source = data.get("Data Source", "")
    # Format: "derived:com.google.X.Y:source_package:..."
    #     or: "raw:com.google.X.Y:source:..."
    parts = source.split(":")
    if len(parts) >= 2:
        return parts[1]
    return None


def sample_json_structure(path: Path, max_points: int = 3) -> dict:
    """Read a JSON file and return structural info (top-level keys, data point schema)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"error": "could not parse JSON"}

    info: dict = {}

    if isinstance(data, dict):
        info["top_level_keys"] = sorted(data.keys())
        # Google Fit "All Data" files have {"Data Source": ..., "Data Points": [...]}
        if "Data Points" in data:
            points = data["Data Points"]
            info["data_point_count"] = len(points)
            if points:
                sample = points[0]
                info["data_point_keys"] = sorted(sample.keys()) if isinstance(sample, dict) else [type(sample).__name__]
        if "Data Source" in data:
            info["data_source"] = data["Data Source"]
    elif isinstance(data, list):
        info["top_level_type"] = "array"
        info["array_length"] = len(data)
        if data and isinstance(data[0], dict):
            info["element_keys"] = sorted(data[0].keys())

    return info


def sample_csv_structure(path: Path, max_rows: int = 3) -> dict:
    """Read a CSV file and return header + sample rows."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers is None:
                return {"error": "empty CSV"}
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)
    except (UnicodeDecodeError, csv.Error):
        return {"error": "could not parse CSV"}

    info: dict = {
        "headers": headers,
        "column_count": len(headers),
    }
    if rows:
        info["sample_row_count"] = len(rows)
    return info


def summarize_takeout(takeout_root: Path) -> dict:
    """
    Walk the Google Takeout directory and produce a structural inventory.

    Groups files by (vendor, category, extension) and samples schemas.
    """
    # Track groups: key = (vendor, category, extension)
    groups: dict[tuple[str, str, str], list[Path]] = defaultdict(list)

    for dirpath, _dirnames, filenames in os.walk(takeout_root):
        for fname in filenames:
            full_path = Path(dirpath) / fname
            rel_path = str(full_path.relative_to(takeout_root))
            vendor = identify_vendor(rel_path)

            # Category = the subdirectory under Fit/ or Fitbit/
            parts = rel_path.split("/")
            if len(parts) >= 2:
                category = parts[1]
            else:
                category = "(root)"

            ext = full_path.suffix.lower()
            groups[(vendor, category, ext)].append(full_path)

    # Build summary for each group
    group_summaries = []
    total_files = 0

    for (vendor, category, ext), files in sorted(groups.items()):
        total_files += len(files)
        entry: dict = {
            "vendor": vendor,
            "category": category,
            "format": ext.lstrip("."),
            "file_count": len(files),
        }

        # Sample one representative file for schema info
        sample_file = files[0]
        entry["example_file"] = str(sample_file.relative_to(takeout_root))

        if ext == ".json":
            entry["schema"] = sample_json_structure(sample_file)
            # For Google Fit "All Data" JSONs, extract the data type from the file
            if category == "All Data":
                data_type = data_type_from_fit_json(sample_file)
                if data_type:
                    entry["fit_data_type"] = data_type
        elif ext == ".csv":
            entry["schema"] = sample_csv_structure(sample_file)
        elif ext == ".txt":
            entry["schema"] = {"note": "text/readme file"}
        elif ext == ".tcx":
            entry["schema"] = {"note": "Garmin Training Center XML (activity/GPS data)"}

        group_summaries.append(entry)

    # Aggregate file counts by extension
    ext_counts: dict[str, int] = defaultdict(int)
    for (_, _, ext), files in groups.items():
        ext_counts[ext.lstrip(".")] = ext_counts.get(ext.lstrip("."), 0) + len(files)

    # For "All Data" directory, list all unique data types found (reads each JSON)
    fit_data_types: dict[str, list[str]] = defaultdict(list)
    for (vendor, category, ext), files in groups.items():
        if category == "All Data" and ext == ".json":
            for f in files:
                dt = data_type_from_fit_json(f)
                if dt and dt not in fit_data_types[vendor]:
                    fit_data_types[vendor].append(dt)

    for v in fit_data_types:
        fit_data_types[v] = sorted(fit_data_types[v])

    return {
        "source_directory": str(takeout_root),
        "total_files": total_files,
        "file_type_counts": dict(sorted(ext_counts.items())),
        "vendors_found": sorted(set(v for v, _, _ in groups.keys())),
        "fit_data_types": dict(fit_data_types),
        "group_count": len(group_summaries),
        "groups": group_summaries,
    }


def write_summary(summary: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    takeout_root = Path("data/google/Takeout")
    out_path = Path("data/google/record_type_field_summary.json")

    summary = summarize_takeout(takeout_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_summary(summary, out_path)

    print(f"Wrote {out_path}")
    print(f"Total files scanned: {summary['total_files']}")
    print(f"Vendors found: {', '.join(summary['vendors_found'])}")
    print(f"Data groups: {summary['group_count']}")
    print()
    print("File types:")
    for ext, count in summary["file_type_counts"].items():
        print(f"  .{ext}: {count}")
    print()
    if summary["fit_data_types"]:
        print("Google Fit data types (from All Data/):")
        for vendor, types in summary["fit_data_types"].items():
            for t in types:
                print(f"  {t}")
    print()
    print("Groups by vendor/category:")
    for g in summary["groups"]:
        print(f"  {g['vendor']}/{g['category']} — {g['file_count']} .{g['format']} files")
