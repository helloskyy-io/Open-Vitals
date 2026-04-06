# Code block 3: Scan date range. Run this after Block 1 and Block 2 to get global_date_range, valid_range, structured_folder_count.
# This process is too big and requires multi thread to complete in a reasonable time frame. (can run for over 45min without multi thread)
# Set the number of workers based on the system you are using to run this on. (more is faster)
# After editing date_range_scan.py, restart the kernel and re-run this cell to pick up changes.

import sys
from pathlib import Path

REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
ROOT = REPO_ROOT / "data/raw/google_fit/takeout_2026-02-21"
NUM_WORKERS = 16  # e.g. 12 on EPYC server, 6 on a modern work station, 2 on older laptop
# Debug: list of folder rel paths to scan only those; None = scan all.
DEBUG_FOLDERS = None

_script_dir = REPO_ROOT / "notebooks" / "scripts" / "02_google_fit_schema_recon"
sys.path.insert(0, str(_script_dir))
import date_range_scan as _drs

scan_result = _drs.run_date_range_parallel(
    ROOT, num_workers=NUM_WORKERS, folder_filter=DEBUG_FOLDERS
);  # semicolon suppresses Jupyter displaying the returned dict

# --- Vars for raw exports log (code block 4) ---
global_date_range = scan_result["global_date_range"]
valid_range = scan_result["valid_range"]
structured_folder_count = scan_result["structured_folder_count"]
