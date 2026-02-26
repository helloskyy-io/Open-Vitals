# Code block 2: Map data headers with path. Run this after Block 1 to get headers_by_path, unique_header_groups.
import time
from pathlib import Path
import csv
import json

# Reuse repo root and export root (same as Block 1)
REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
ROOT = REPO_ROOT / "data/raw/google_fit/takeout_2026-02-21"

t0 = time.perf_counter()
print("Block 2: Mapping data headers with path")
print(f"ROOT = {ROOT.resolve()}")
if not ROOT.exists():
    raise FileNotFoundError(f"Export not found: {ROOT} (cwd={Path.cwd()})")
print("ROOT exists, scanning for .csv and .json ...")

STRUCTURED_EXTENSIONS = (".csv", ".json")

def get_csv_headers(path: Path) -> list[str] | None:
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            first = next(reader, None)
            return first if first else None
    except Exception as e:
        return [f"(error: {e})"]

def get_json_keys(path: Path) -> list[str] | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return list(data.keys())
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            return list(first.keys()) if isinstance(first, dict) else [f"(array of {type(first).__name__})"]
        if isinstance(data, list):
            return ["(empty array)"]
        return [f"(type: {type(data).__name__})"]
    except json.JSONDecodeError as e:
        return [f"(invalid JSON: {e})"]
    except Exception as e:
        return [f"(error: {e})"]

# Collect structured file paths first (so we see count immediately)
file_paths = []
for ext in STRUCTURED_EXTENSIONS:
    for path in ROOT.rglob(f"*{ext}"):
        if path.is_file():
            file_paths.append((path, ext))
file_paths.sort(key=lambda x: (str(x[0]), x[1]))

print(f"Found {len(file_paths)} structured files\n")

# Collect headers for each file
results = []
for i, (path, ext) in enumerate(file_paths):
    rel = path.relative_to(ROOT)
    if ext == ".csv":
        headers = get_csv_headers(path)
    else:
        headers = get_json_keys(path)
    results.append((rel, ext, headers))
    if (i + 1) % 100 == 0:
        print(f"  ... processed {i + 1}/{len(file_paths)}")

# Dedupe: same folder + same headers => one row (many files share structure, e.g. one CSV per date)
# Group key: (parent_dir, ext, tuple of sorted header names)
def signature(h):
    return tuple(sorted(h)) if h else ()

groups = {}  # (parent, ext, sig) -> (example_path, headers, count)
for rel, ext, headers in results:
    parent = str(rel.parent)
    sig = signature(headers)
    key = (parent, ext, sig)
    if key not in groups:
        groups[key] = [rel, headers, 0]
    groups[key][2] += 1

# Print unique (folder, headers) with one example path and file count — human-scannable
print("\nData headers (unique by folder + headers; one example path per group)\n" + "=" * 70)
for (parent, ext, _), (example_rel, headers, count) in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
    print(f"\n  {parent}/  [{ext}]  ({count} file{'s' if count != 1 else ''})")
    print(f"    example: {example_rel.name}")
    if headers:
        print(f"    headers: {headers}")
    else:
        print("    headers: (none)")

# For later use: full list and deduped summary
headers_by_path = {str(r[0]): r[2] for r in results}
unique_header_groups = list(groups.items())  # (parent, ext, sig) -> (example_rel, headers, count)

elapsed = time.perf_counter() - t0
if elapsed >= 60:
    mins, secs = divmod(elapsed, 60)
    print(f"\nTotal run time: {mins:.0f} m {secs:.1f} s")
else:
    print(f"\nTotal run time: {elapsed:.1f} s")

# (Block 4 raw exports log uses vars from Block 1 and Block 3 only.)