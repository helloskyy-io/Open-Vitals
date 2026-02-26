# Parallel date-range scan for Google Fit Takeout (notebook-specific).
# Run from repo root: python -u notebooks/scripts/date_range_scan.py --root <path> [--workers N]
# Or from Jupyter: from scripts.date_range_scan import run_date_range_parallel; run_date_range_parallel(ROOT, num_workers=8)

import argparse
import json
import re
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd

# Column/key names that look like time, timestamp, or date (case-insensitive)
TIME_PATTERN = re.compile(
    r"time|timestamp|date|datetime|start\s*time|end\s*time|recorded|created|updated",
    re.I,
)

# Realistic date bounds: ignore parsed dates outside [min, max] so they never enter folder/global ranges.
DEFAULT_MIN_VALID_DATE = "2010-01-01"  # wearable/export data not meaningful before this
EXPORT_DATE_PATTERN = re.compile(r"takeout_(\d{4})[-_](\d{2})[-_](\d{2})", re.I)


def is_time_like(name):
    return bool(name and TIME_PATTERN.search(name))


def _normalize_ts(ts):
    """Convert to tz-naive for comparison (avoid tz-naive vs tz-aware TypeError)."""
    if ts is None or (isinstance(ts, float) and pd.isna(ts)):
        return None
    t = pd.Timestamp(ts)
    if t.tz is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    return t


def _in_range(t, min_valid, max_valid):
    """True if t is within [min_valid, max_valid] (None bound means no limit). Returns False if comparison overflows."""
    if t is None:
        return False
    try:
        if min_valid is not None and t < min_valid:
            return False
        if max_valid is not None and t > max_valid:
            return False
        return True
    except (OverflowError, Exception):
        return False


def parse_dates_from_values(values, path_hint="", min_valid=None, max_valid=None):
    """Parse iterable to datetimes; return (min, max) or (None, None). Only keeps dates in [min_valid, max_valid]."""
    try:
        vals = list(values)
    except TypeError:
        vals = [values]
    if len(vals) == 0:
        return None, None
    out = []
    for v in vals:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        if isinstance(v, (int, float)) and 1e9 < v < 2e10:
            try:
                t = pd.Timestamp(v, unit="s") if v < 2e9 else pd.Timestamp(v, unit="ms")
                t = _normalize_ts(t)
                if _in_range(t, min_valid, max_valid):
                    out.append(t)
            except Exception:
                continue
        else:
            try:
                t = pd.to_datetime(v, errors="coerce")
                if pd.notna(t):
                    t = _normalize_ts(t)
                    if _in_range(t, min_valid, max_valid):
                        out.append(t)
            except Exception:
                continue
    out = [x for x in out if x is not None]
    if not out:
        return None, None
    return min(out), max(out)


def date_range_csv(path: Path, rel_path, min_valid=None, max_valid=None) -> tuple:
    """Return (time_column_names, min_date, max_date). Only dates in [min_valid, max_valid] count."""
    try:
        df = pd.read_csv(path, nrows=50000)
    except Exception:
        return [], None, None
    time_cols = [c for c in df.columns if is_time_like(c)]
    if not time_cols:
        return [], None, None
    all_mins, all_maxs = [], []
    for c in time_cols:
        mn, mx = parse_dates_from_values(
            df[c].dropna().astype(str), min_valid=min_valid, max_valid=max_valid
        )
        if mn is not None:
            all_mins.append(mn)
            all_maxs.append(mx)
    if not all_mins and rel_path and len(rel_path.parts) >= 1:
        name = rel_path.name
        if re.match(r"\d{4}-\d{2}-\d{2}", name):
            try:
                d = _normalize_ts(pd.to_datetime(name[:10]))
                if _in_range(d, min_valid, max_valid):
                    return time_cols, d, d
            except Exception:
                pass
    if not all_mins:
        return time_cols, None, None
    all_mins_n = [_normalize_ts(t) for t in all_mins]
    all_maxs_n = [_normalize_ts(t) for t in all_maxs]
    return time_cols, min(all_mins_n), max(all_maxs_n)


def flatten_json_values(obj, key_filter, out: list):
    """Recursively collect scalar values for keys matching key_filter (callable)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if key_filter(k) and not isinstance(v, (dict, list)):
                out.append(v)
            flatten_json_values(v, key_filter, out)
    elif isinstance(obj, list):
        for item in obj:
            flatten_json_values(item, key_filter, out)


def date_range_json(path: Path, min_valid=None, max_valid=None) -> tuple:
    """Return (time_key_names, min_date, max_date). Only dates in [min_valid, max_valid] count."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return [], None, None
    keys_found = set()

    def collect(k):
        if is_time_like(k):
            keys_found.add(k)
            return True
        return False

    values = []
    flatten_json_values(data, collect, values)
    mn, mx = parse_dates_from_values(values, min_valid=min_valid, max_valid=max_valid)
    return list(keys_found), mn, mx


def parse_export_date_from_path(root: Path) -> str | None:
    """Extract export date from root path (e.g. takeout_2026-02-21 -> '2026-02-21'). Returns ISO date string or None."""
    name = root.name
    m = EXPORT_DATE_PATTERN.search(name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def process_one_file(
    root_str: str,
    file_rel_path: str,
    ext: str,
    min_valid_str: str | None = None,
    max_valid_str: str | None = None,
) -> tuple:
    """
    Process one .csv or .json file. Return (folder_rel_str, min_date, max_date).
    Must be top-level for pickling.
    """
    root = Path(root_str)
    path = root / file_rel_path
    if not path.is_file():
        return (str(Path(file_rel_path).parent) if Path(file_rel_path).parent != Path(".") else "", None, None)
    rel_path = Path(file_rel_path)
    min_valid = _normalize_ts(pd.Timestamp(min_valid_str)) if min_valid_str else None
    max_valid = _normalize_ts(pd.Timestamp(max_valid_str)) if max_valid_str else None
    try:
        if ext == ".csv":
            _, mn, mx = date_range_csv(path, rel_path, min_valid=min_valid, max_valid=max_valid)
        else:
            _, mn, mx = date_range_json(path, min_valid=min_valid, max_valid=max_valid)
    except Exception:
        mn, mx = None, None
    folder = str(rel_path.parent) if rel_path.parent != Path(".") else ""
    return (folder, mn, mx)


def get_all_files(root: Path, folder_filter: list | None = None) -> list[tuple[str, str, str]]:
    """Return list of (folder_rel_str, file_rel_path_str, ext) for every .csv and .json."""
    out = []
    for ext in (".csv", ".json"):
        for path in root.rglob(f"*{ext}"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root)
                folder = str(rel.parent) if rel.parent != Path(".") else ""
                if folder_filter is not None and folder not in folder_filter:
                    continue
                out.append((folder, str(rel), ext))
            except ValueError:
                continue
    return out


def run_date_range_parallel(root, num_workers=4, stream=None, min_valid_date=None, folder_filter=None):
    """
    Run parallel date-range scan and print progress + summary.
    root: Path or str to Takeout export (e.g. data/raw/google_fit/takeout_2026-02-21).
    num_workers: number of processes.
    stream: file-like for print (default sys.stdout); use flush=True on prints for Jupyter/subprocess.
    min_valid_date: lower bound for valid dates, ISO format (default DEFAULT_MIN_VALID_DATE, e.g. 2010-01-01).
    folder_filter: optional list of folder rel paths to scan (debug mode); None = scan all.
    """
    root = Path(root).resolve()
    if stream is None:
        stream = sys.stdout
    # Force line buffering so Jupyter shows output immediately (not after cell finishes)
    if stream is sys.stdout and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(line_buffering=True)
        except Exception:
            pass

    def log(msg, end="\n"):
        print(msg, end=end, file=stream, flush=True)

    from datetime import datetime as _dt
    t0 = time.perf_counter()
    log(f"[started at {_dt.now().isoformat()}] — streaming to Jupyter OK")
    log("Block 3 (parallel): Time/date columns and date range")
    log(f"ROOT = {root}")
    if not root.exists():
        raise FileNotFoundError(f"Export not found: {root}")

    min_valid_str = min_valid_date if min_valid_date is not None else DEFAULT_MIN_VALID_DATE
    max_valid_str = parse_export_date_from_path(root)
    if max_valid_str:
        log(f"Valid date range: {min_valid_str} .. {max_valid_str} (export date from path); dates outside ignored.")
    else:
        log(f"Valid date range: {min_valid_str} .. (no max; export date not found in path).")

    # Bounds for filtering in main process (defense in depth: never aggregate or display out-of-range dates).
    min_valid_ts = _normalize_ts(pd.Timestamp(min_valid_str)) if min_valid_str else None
    if max_valid_str:
        # End of export day so timestamps on that day are allowed.
        max_valid_ts = _normalize_ts(
            pd.Timestamp(max_valid_str) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        )
    else:
        max_valid_ts = None

    file_list = get_all_files(root, folder_filter)
    if folder_filter is not None:
        log(f"DEBUG MODE: filtering to folders {folder_filter}")
    n_files = len(file_list)
    expected_count = Counter(folder for folder, _, _ in file_list)
    n_folders = len(expected_count)
    log(f"Scanning {n_files} files in {n_folders} folders (one task per file) ...")
    log("(Logging each folder when complete.)\n")

    root_str = str(root)
    results_by_folder = defaultdict(list)  # folder -> list of (mn_f, mx_f)

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                process_one_file,
                root_str,
                file_rel_path,
                ext,
                min_valid_str,
                max_valid_str,
            ): (folder, file_rel_path, ext)
            for folder, file_rel_path, ext in file_list
        }
        for future in as_completed(futures):
            folder, file_rel_path, ext = futures[future]
            try:
                folder_rel, mn, mx = future.result()
                mn_f = mn if (mn is not None and _in_range(mn, min_valid_ts, max_valid_ts)) else None
                mx_f = mx if (mx is not None and _in_range(mx, min_valid_ts, max_valid_ts)) else None
                results_by_folder[folder_rel].append((mn_f, mx_f))
                # When this folder is complete, log it
                if len(results_by_folder[folder_rel]) == expected_count[folder_rel]:
                    mins = [m for m, _ in results_by_folder[folder_rel] if m is not None]
                    maxs = [x for _, x in results_by_folder[folder_rel] if x is not None]
                    earliest = min(mins) if mins else None
                    latest = max(maxs) if maxs else None
                    loc = folder_rel if folder_rel else "(root)"
                    log(f"  {loc}/")
                    log(f"    earliest: {earliest}")
                    log(f"    latest:   {latest}")
                    log("")
            except Exception as e:
                log(f"  (skip {file_rel_path}: {e})")

    # Build results and location_ranges for return (same shape as before)
    results = []
    location_ranges = {}
    for folder_rel in sorted(results_by_folder.keys()):
        pairs = results_by_folder[folder_rel]
        mins = [m for m, _ in pairs if m is not None]
        maxs = [x for _, x in pairs if x is not None]
        folder_min = min(mins) if mins else None
        folder_max = max(maxs) if maxs else None
        results.append((folder_rel, folder_min, folder_max))
        loc = folder_rel or "(root)"
        location_ranges[loc] = {"mins": mins, "maxs": maxs}

    all_mins = [r[1] for r in results if r[1] is not None]
    all_maxs = [r[2] for r in results if r[2] is not None]
    global_min = min(all_mins) if all_mins else None
    global_max = max(all_maxs) if all_maxs else None

    log("\n" + "=" * 70)
    log("Global date range (entire dataset)")
    # Note: some sources yield bogus dates (epoch 1970, year 1, far future); filtering/blacklisting is a separate task.
    if global_min is None and global_max is None:
        log("  (no dates parsed from time/date columns)")
    else:
        log(f"  oldest date: {global_min}")
        log(f"  newest date: {global_max}")
        if global_min and global_max:
            try:
                log(f"  span: {(global_max - global_min).days} days")
            except (OverflowError, Exception) as _e:
                err = type(_e).__name__
                log(f"  span: (not computed — {err}; dates may be out of pandas range)")

    elapsed = time.perf_counter() - t0
    if elapsed >= 60:
        mins, secs = divmod(elapsed, 60)
        log(f"\nTotal run time: {mins:.0f} m {secs:.1f} s")
    else:
        log(f"\nTotal run time: {elapsed:.1f} s")

    return {
        "results": results,
        "location_ranges": location_ranges,
        "global_date_range": (global_min, global_max),
        "valid_range": (min_valid_str, max_valid_str),
        "structured_folder_count": n_folders,
        "elapsed_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parallel date-range scan for Google Fit Takeout export (notebook script)."
    )
    parser.add_argument("--root", type=str, required=True, help="Path to Takeout export directory")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes")
    args = parser.parse_args()
    run_date_range_parallel(args.root, num_workers=args.workers)


if __name__ == "__main__":
    main()
