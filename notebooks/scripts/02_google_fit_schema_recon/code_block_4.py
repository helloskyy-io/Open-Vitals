# Raw exports log: create or update data/raw/google_fit/raw_exports.json (machine-readable).
# Uses vars from Block 1 (export_folder_name, export_date, source, structured_file_count)
# and Block 3 (global_date_range, valid_range, structured_folder_count). Run Block 1 and Block 3 first.

import json
from datetime import datetime, timezone
from pathlib import Path

# Reuse repo root (same as Block 1)
REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
RAW_GOOGLE_FIT_DIR = REPO_ROOT / "data/raw/google_fit"
LOG_FILE = RAW_GOOGLE_FIT_DIR / "raw_exports.json"

# Require Block 1 vars (when run in Jupyter they live in globals())
_g = globals()
for _name in ("export_folder_name", "export_date", "source", "structured_file_count"):
    if _name not in _g:
        raise NameError(f"Run Block 1 first (missing: {_name})")

# Build entry for current export (all values JSON-serializable)
data_start = None
data_end = None
valid_range_list = None
structured_folder_count_val = None
if "global_date_range" in _g and global_date_range is not None:
    gmin, gmax = global_date_range
    data_start = str(gmin) if gmin is not None else None
    data_end = str(gmax) if gmax is not None else None
if "valid_range" in _g and valid_range is not None:
    vmin, vmax = valid_range
    valid_range_list = [vmin, vmax] if vmax else [vmin]
if "structured_folder_count" in _g:
    structured_folder_count_val = structured_folder_count

log_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
new_entry = {
    "export_folder": export_folder_name,
    "export_date": export_date,
    "source": source,
    "data_start": data_start,
    "data_end": data_end,
    "valid_range": valid_range_list,
    "folders": structured_folder_count_val,
    "files": structured_file_count,
    "log_updated": log_updated,
}

# Load existing or start with empty list
RAW_GOOGLE_FIT_DIR.mkdir(parents=True, exist_ok=True)
if LOG_FILE.exists():
    data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
else:
    data = {"exports": []}
if "exports" not in data:
    data["exports"] = []

# Replace existing entry for this export or append
exports = data["exports"]
replaced = False
for i, e in enumerate(exports):
    if e.get("export_folder") == export_folder_name:
        exports[i] = new_entry
        replaced = True
        break
if not replaced:
    exports.append(new_entry)

LOG_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Updated {LOG_FILE.relative_to(REPO_ROOT)}")
