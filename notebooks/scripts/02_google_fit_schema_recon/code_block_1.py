# Code block 1: Map folder structure and file types. Run this first to get export_folder_name, export_date, source, structured_file_count.
import re
from pathlib import Path
from collections import defaultdict

# Repo root: Jupyter often runs with cwd = notebooks/, so go up one if needed
REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
ROOT = REPO_ROOT / "data/raw/google_fit/takeout_2026-02-21"

if not ROOT.exists():
    raise FileNotFoundError(f"Export not found: {ROOT} (cwd={Path.cwd()})")

# --- Vars for raw exports log (code block 4) ---
export_folder_name = ROOT.name
_export_date_match = re.match(r"takeout_(\d{4})[-_](\d{2})[-_](\d{2})", ROOT.name, re.I)
export_date = f"{_export_date_match.group(1)}-{_export_date_match.group(2)}-{_export_date_match.group(3)}" if _export_date_match else None
source = "Google Fit and Fitbit"

# Collect all directories and file extensions
dirs = []
ext_counts = defaultdict(int)
for path in ROOT.rglob("*"):
    if path.is_dir():
        dirs.append(path.relative_to(ROOT))
    else:
        ext = path.suffix.lower() or "(no ext)"
        ext_counts[ext] += 1

structured_file_count = ext_counts.get(".csv", 0) + ext_counts.get(".json", 0)

# Sort and print folder structure (one line per directory)
dirs_sorted = sorted(dirs, key=lambda p: (len(p.parts), str(p)))
print("Folders:")
for d in dirs_sorted:
    indent = "  " * (len(d.parts))
    print(f"{indent}{d.name}/")

# File types summary
print("\nFile types (extension -> count):")
for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
    print(f"  {ext}: {count}")