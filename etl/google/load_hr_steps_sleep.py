from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def nanos_to_dt(nanos: int) -> datetime:
    """Convert Google Fit nanosecond epoch to timezone-aware datetime (UTC)."""
    return datetime.fromtimestamp(nanos / 1e9, tz=timezone.utc)


def parse_fitbit_datetime(dt_str: str) -> datetime:
    """
    Parse Fitbit dateTime strings.
    Formats seen:
        '10/09/25 22:02:26'  (MM/DD/YY HH:MM:SS)
        '03/07/26 05:02:00'  (MM/DD/YY HH:MM:SS)
    Returns a naive datetime (Fitbit exports are in the user's local time).
    """
    return datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")


def parse_fitbit_sleep_datetime(dt_str: str) -> datetime:
    """
    Parse Fitbit sleep dateTime strings.
    Format: '2026-04-05T23:13:30.000' (ISO-ish, no timezone)
    """
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")


# ---------------------------------------------------------------------------
# Sleep stage mappings
# ---------------------------------------------------------------------------

GOOGLE_FIT_SLEEP_STAGE = {
    0: "awake",     # Awake (during sleep cycle)
    1: "asleep",    # Sleep (unspecified)
    2: "awake",     # Out of bed
    3: "core",      # Light sleep
    4: "deep",      # Deep sleep
    5: "rem",       # REM sleep
    6: "asleep",    # Sleep (sometimes used as generic)
}

FITBIT_SLEEP_STAGE = {
    "wake": "awake",
    "light": "core",
    "deep": "deep",
    "rem": "rem",
    "restless": "awake",
    "asleep": "asleep",
    "awake": "awake",
}


# ---------------------------------------------------------------------------
# Data source parsing helpers
# ---------------------------------------------------------------------------

def parse_data_source_string(data_source: str) -> dict:
    """
    Parse a Google Fit Data Source string into components.
    Format: 'derived:com.google.heart_rate.bpm:com.google.android.gms:resting_heart_rate<-...'
        or: 'raw:com.google.step_count.delta:Google:Pixel 8 Pro:...'
    """
    parts = data_source.split(":")
    result = {"raw": data_source}
    if len(parts) >= 2:
        result["origin"] = parts[0]       # derived / raw
        result["data_type"] = parts[1]    # com.google.heart_rate.bpm
    if len(parts) >= 3:
        result["package"] = parts[2]      # com.google.android.gms / Google
    if len(parts) >= 4:
        result["device"] = parts[3]       # Pixel 8 Pro / resting_heart_rate<-...
    return result


def product_from_origin_source(origin_source: str) -> str:
    """
    Extract a product name from an originDataSourceId.
    e.g. 'raw:com.google.step_count.cumulative:Google:Pixel 8 Pro:...' -> 'Pixel 8 Pro'
         'raw:com.google.sleep.segment:com.fitbit.FitbitMobile:...' -> 'FitbitMobile'
    """
    parts = origin_source.split(":")
    if len(parts) >= 4:
        # If package looks like a Java package, use last segment
        pkg = parts[2]
        device = parts[3]
        if pkg.startswith("com.fitbit"):
            return pkg.split(".")[-1]
        if device:
            return device
        return pkg
    return "unknown"


# ---------------------------------------------------------------------------
# DB helpers (mirrored from Apple loader for self-containment)
# ---------------------------------------------------------------------------

def get_or_create_person(cur: psycopg.Cursor, external_key: str) -> int:
    cur.execute("SELECT person_id FROM person WHERE external_key = %s", (external_key,))
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        "INSERT INTO person (external_key) VALUES (%s) RETURNING person_id",
        (external_key,),
    )
    return int(cur.fetchone()[0])


_source_cache: dict[str, int] = {}


def get_or_create_data_source(
    cur: psycopg.Cursor,
    vendor: str,
    product: str | None,
    device_raw: str | None = None,
) -> int:
    cache_key = f"{vendor}|{(product or '').lower()}"
    if cache_key in _source_cache:
        return _source_cache[cache_key]

    if product:
        cur.execute(
            """
            SELECT source_id FROM data_source
            WHERE vendor = %s AND lower(product) = lower(%s)
            ORDER BY source_id LIMIT 1
            """,
            (vendor, product),
        )
        row = cur.fetchone()
        if row:
            _source_cache[cache_key] = int(row[0])
            return int(row[0])

    cur.execute(
        """
        INSERT INTO data_source (vendor, product, device_raw)
        VALUES (%s, %s, %s)
        RETURNING source_id
        """,
        (vendor, product, device_raw),
    )
    source_id = int(cur.fetchone()[0])
    _source_cache[cache_key] = source_id
    return source_id


def create_source_event(
    cur: psycopg.Cursor,
    source_id: int,
    vendor_type: str | None,
) -> int:
    cur.execute(
        """
        INSERT INTO source_event (source_id, vendor_type)
        VALUES (%s, %s)
        RETURNING source_event_id
        """,
        (source_id, vendor_type),
    )
    return int(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# Loaders: Google Fit (JSON with nanosecond timestamps)
# ---------------------------------------------------------------------------

def load_fit_heart_rate(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    commit_every: int,
    stats: dict,
) -> None:
    all_data_dir = takeout_root / "Fit" / "All Data"
    if not all_data_dir.is_dir():
        return

    for json_file in sorted(all_data_dir.iterdir()):
        if json_file.suffix != ".json":
            continue
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue

        source_str = data.get("Data Source", "")
        if "com.google.heart_rate.bpm" not in source_str:
            continue

        parsed = parse_data_source_string(source_str)
        data_type = parsed.get("data_type", "com.google.heart_rate.bpm")

        # Determine if this is resting HR
        is_resting = "resting_heart_rate" in source_str

        source_id = get_or_create_data_source(
            cur,
            vendor="google",
            product=parsed.get("package", "Google Fit"),
        )

        vendor_type = "google.resting_heart_rate" if is_resting else data_type

        count = 0
        for pt in data.get("Data Points", []):
            fit_values = pt.get("fitValue", [])
            if not fit_values:
                continue
            bpm_raw = fit_values[0].get("value", {}).get("fpVal")
            if bpm_raw is None:
                continue
            bpm = int(round(bpm_raw))
            if bpm <= 0 or bpm > 300:
                continue

            end_nanos = pt.get("endTimeNanos")
            if not end_nanos:
                continue
            ts = nanos_to_dt(int(end_nanos))

            source_event_id = create_source_event(cur, source_id, vendor_type)
            cur.execute(
                """
                INSERT INTO hr_sample (person_id, source_id, source_event_id, ts, bpm)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (person_id, source_id, source_event_id, ts, bpm),
            )
            count += 1
            if count % commit_every == 0:
                conn.commit()
                print(f"    Google Fit HR: {count} records...", flush=True)

        conn.commit()
        stats["hr_sample_google_fit"] += count
        print(f"    Google Fit HR file done: {json_file.name} ({count} records)")


def load_fit_steps(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    commit_every: int,
    stats: dict,
) -> None:
    all_data_dir = takeout_root / "Fit" / "All Data"
    if not all_data_dir.is_dir():
        return

    for json_file in sorted(all_data_dir.iterdir()):
        if json_file.suffix != ".json":
            continue
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue

        source_str = data.get("Data Source", "")
        if "com.google.step_count.delta" not in source_str:
            continue

        parsed = parse_data_source_string(source_str)

        source_id = get_or_create_data_source(
            cur,
            vendor="google",
            product=parsed.get("device", parsed.get("package", "Google Fit")),
        )

        count = 0
        for pt in data.get("Data Points", []):
            fit_values = pt.get("fitValue", [])
            if not fit_values:
                continue
            steps_raw = fit_values[0].get("value", {}).get("intVal")
            if steps_raw is None:
                continue
            steps = int(steps_raw)
            if steps < 0:
                continue

            start_nanos = pt.get("startTimeNanos")
            end_nanos = pt.get("endTimeNanos")
            if not start_nanos or not end_nanos:
                continue

            start_ts = nanos_to_dt(int(start_nanos))
            end_ts = nanos_to_dt(int(end_nanos))

            # Derive product from originDataSourceId if available
            origin = pt.get("originDataSourceId", "")
            if origin and count == 0:
                prod = product_from_origin_source(origin)
                source_id = get_or_create_data_source(cur, vendor="google", product=prod)

            source_event_id = create_source_event(cur, source_id, "com.google.step_count.delta")
            cur.execute(
                """
                INSERT INTO steps_sample (person_id, source_id, source_event_id, start_ts, end_ts, steps)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (person_id, source_id, source_event_id, start_ts, end_ts, steps),
            )
            count += 1
            if count % commit_every == 0:
                conn.commit()
                print(f"    Google Fit steps: {count} records...", flush=True)

        conn.commit()
        stats["steps_sample_google_fit"] += count
        print(f"    Google Fit steps file done: {json_file.name} ({count} records)")


def load_fit_sleep(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    commit_every: int,
    stats: dict,
) -> None:
    all_data_dir = takeout_root / "Fit" / "All Data"
    if not all_data_dir.is_dir():
        return

    for json_file in sorted(all_data_dir.iterdir()):
        if json_file.suffix != ".json":
            continue
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue

        source_str = data.get("Data Source", "")
        if "com.google.sleep.segment" not in source_str:
            continue

        source_id = get_or_create_data_source(
            cur,
            vendor="google",
            product="Google Fit",
        )

        count = 0
        for pt in data.get("Data Points", []):
            fit_values = pt.get("fitValue", [])
            if not fit_values:
                continue
            stage_code = fit_values[0].get("value", {}).get("intVal")
            if stage_code is None:
                continue

            start_nanos = pt.get("startTimeNanos")
            end_nanos = pt.get("endTimeNanos")
            if not start_nanos or not end_nanos:
                continue

            start_ts = nanos_to_dt(int(start_nanos))
            end_ts = nanos_to_dt(int(end_nanos))
            stage = GOOGLE_FIT_SLEEP_STAGE.get(int(stage_code), "unknown")

            source_event_id = create_source_event(cur, source_id, "com.google.sleep.segment")
            cur.execute(
                """
                INSERT INTO sleep_session (person_id, source_id, source_event_id, start_ts, end_ts)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING sleep_session_id
                """,
                (person_id, source_id, source_event_id, start_ts, end_ts),
            )
            sleep_session_id = int(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO sleep_stage (sleep_session_id, start_ts, end_ts, stage)
                VALUES (%s, %s, %s, %s)
                """,
                (sleep_session_id, start_ts, end_ts, stage),
            )
            count += 1
            if count % commit_every == 0:
                conn.commit()
                print(f"    Google Fit sleep: {count} records...", flush=True)

        conn.commit()
        stats["sleep_session_google_fit"] += count
        print(f"    Google Fit sleep file done: {json_file.name} ({count} records)")


# ---------------------------------------------------------------------------
# Loaders: Fitbit (JSON with human-readable timestamps)
# ---------------------------------------------------------------------------

def load_fitbit_heart_rate(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    commit_every: int,
    stats: dict,
) -> None:
    hr_dir = takeout_root / "Fitbit" / "Global Export Data"
    if not hr_dir.is_dir():
        return

    source_id = get_or_create_data_source(cur, vendor="fitbit", product="Fitbit")

    total = 0
    for json_file in sorted(hr_dir.iterdir()):
        if not json_file.name.startswith("heart_rate-") or json_file.suffix != ".json":
            continue

        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue

        count = 0
        for entry in data:
            dt_str = entry.get("dateTime")
            value = entry.get("value", {})
            bpm = value.get("bpm") if isinstance(value, dict) else None
            if dt_str is None or bpm is None:
                continue
            bpm = int(bpm)
            if bpm <= 0 or bpm > 300:
                continue

            ts = parse_fitbit_datetime(dt_str)

            source_event_id = create_source_event(cur, source_id, "fitbit.heart_rate")
            cur.execute(
                """
                INSERT INTO hr_sample (person_id, source_id, source_event_id, ts, bpm)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (person_id, source_id, source_event_id, ts, bpm),
            )
            count += 1
            if count % commit_every == 0:
                conn.commit()

        total += count
        if total % (commit_every * 10) < count:
            print(f"    Fitbit HR: {total} records so far...", flush=True)

    stats["hr_sample_fitbit"] += total
    print(f"    Fitbit HR done: {total} records total")


def load_fitbit_resting_heart_rate(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    stats: dict,
) -> None:
    hr_dir = takeout_root / "Fitbit" / "Global Export Data"
    if not hr_dir.is_dir():
        return

    source_id = get_or_create_data_source(cur, vendor="fitbit", product="Fitbit")

    total = 0
    for json_file in sorted(hr_dir.iterdir()):
        if not json_file.name.startswith("resting_heart_rate-") or json_file.suffix != ".json":
            continue

        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue

        for entry in data:
            value = entry.get("value", {})
            if not isinstance(value, dict):
                continue
            rhr = value.get("value")
            date_str = value.get("date")
            if rhr is None or rhr == 0.0 or date_str is None:
                continue

            bpm = int(round(rhr))
            if bpm <= 0 or bpm > 200:
                continue

            ts = parse_fitbit_datetime(entry["dateTime"])

            source_event_id = create_source_event(cur, source_id, "fitbit.resting_heart_rate")
            cur.execute(
                """
                INSERT INTO hr_sample (person_id, source_id, source_event_id, ts, bpm)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (person_id, source_id, source_event_id, ts, bpm),
            )
            total += 1

    conn.commit()
    stats["hr_sample_fitbit_resting"] += total
    print(f"    Fitbit resting HR done: {total} records")


def load_fitbit_steps(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    commit_every: int,
    stats: dict,
) -> None:
    steps_dir = takeout_root / "Fitbit" / "Global Export Data"
    if not steps_dir.is_dir():
        return

    source_id = get_or_create_data_source(cur, vendor="fitbit", product="Fitbit")

    total = 0
    for json_file in sorted(steps_dir.iterdir()):
        if not json_file.name.startswith("steps-") or json_file.suffix != ".json":
            continue

        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue

        count = 0
        for entry in data:
            dt_str = entry.get("dateTime")
            val_str = entry.get("value")
            if dt_str is None or val_str is None:
                continue
            steps = int(val_str)
            if steps <= 0:
                continue

            start_ts = parse_fitbit_datetime(dt_str)
            # Fitbit steps are per-minute readings
            end_ts = start_ts.replace(second=0)
            end_ts = start_ts + timedelta(minutes=1)

            source_event_id = create_source_event(cur, source_id, "fitbit.steps")
            cur.execute(
                """
                INSERT INTO steps_sample (person_id, source_id, source_event_id, start_ts, end_ts, steps)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (person_id, source_id, source_event_id, start_ts, end_ts, steps),
            )
            count += 1
            if count % commit_every == 0:
                conn.commit()

        total += count

    conn.commit()
    stats["steps_sample_fitbit"] += total
    print(f"    Fitbit steps done: {total} records total")


def load_fitbit_sleep(
    cur: psycopg.Cursor,
    conn: psycopg.Connection,
    takeout_root: Path,
    person_id: int,
    commit_every: int,
    stats: dict,
) -> None:
    sleep_dir = takeout_root / "Fitbit" / "Global Export Data"
    if not sleep_dir.is_dir():
        return

    source_id = get_or_create_data_source(cur, vendor="fitbit", product="Fitbit")

    sessions_total = 0
    stages_total = 0

    for json_file in sorted(sleep_dir.iterdir()):
        if not json_file.name.startswith("sleep-") or json_file.suffix != ".json":
            continue

        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue

        for log in data:
            start_str = log.get("startTime")
            end_str = log.get("endTime")
            if not start_str or not end_str:
                continue

            session_start = parse_fitbit_sleep_datetime(start_str)
            session_end = parse_fitbit_sleep_datetime(end_str)

            # Skip if this session already exists (monthly files overlap at boundaries)
            cur.execute(
                """
                SELECT sleep_session_id FROM sleep_session
                WHERE source_id = %s AND start_ts = %s AND end_ts = %s
                """,
                (source_id, session_start, session_end),
            )
            existing = cur.fetchone()
            if existing:
                continue

            source_event_id = create_source_event(cur, source_id, "fitbit.sleep")
            cur.execute(
                """
                INSERT INTO sleep_session (person_id, source_id, source_event_id, start_ts, end_ts)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING sleep_session_id
                """,
                (person_id, source_id, source_event_id, session_start, session_end),
            )
            sleep_session_id = int(cur.fetchone()[0])
            sessions_total += 1

            # Load stage-level detail if available
            levels = log.get("levels", {})
            stage_data = levels.get("data", [])
            for stage_entry in stage_data:
                stage_dt_str = stage_entry.get("dateTime")
                level = stage_entry.get("level")
                seconds = stage_entry.get("seconds")
                if not stage_dt_str or not level or not seconds:
                    continue

                stage_start = parse_fitbit_sleep_datetime(stage_dt_str)
                stage_end = stage_start + timedelta(seconds=int(seconds))
                stage = FITBIT_SLEEP_STAGE.get(level, "unknown")

                cur.execute(
                    """
                    INSERT INTO sleep_stage (sleep_session_id, start_ts, end_ts, stage)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (sleep_session_id, stage_start, stage_end, stage),
                )
                stages_total += 1

            if sessions_total % commit_every == 0:
                conn.commit()

    conn.commit()
    stats["sleep_session_fitbit"] += sessions_total
    stats["sleep_stage_fitbit"] += stages_total
    print(f"    Fitbit sleep done: {sessions_total} sessions, {stages_total} stages")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def load_all(
    takeout_root: Path,
    conninfo: str,
    person_key: str,
    commit_every: int,
    only: str,
) -> dict:
    stats: dict[str, int] = defaultdict(int)
    _source_cache.clear()

    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            person_id = get_or_create_person(cur, person_key)
            conn.commit()

            if only in ("all", "heart_rate"):
                print("  Loading heart rate...", flush=True)
                load_fit_heart_rate(cur, conn, takeout_root, person_id, commit_every, stats)
                load_fitbit_heart_rate(cur, conn, takeout_root, person_id, commit_every, stats)
                load_fitbit_resting_heart_rate(cur, conn, takeout_root, person_id, stats)

            if only in ("all", "steps"):
                print("  Loading steps...", flush=True)
                load_fit_steps(cur, conn, takeout_root, person_id, commit_every, stats)
                load_fitbit_steps(cur, conn, takeout_root, person_id, commit_every, stats)

            if only in ("all", "sleep"):
                print("  Loading sleep...", flush=True)
                load_fit_sleep(cur, conn, takeout_root, person_id, commit_every, stats)
                load_fitbit_sleep(cur, conn, takeout_root, person_id, commit_every, stats)

    return dict(stats)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Google Takeout HR/steps/sleep records into Postgres tables."
    )
    parser.add_argument(
        "--only",
        choices=["all", "heart_rate", "steps", "sleep"],
        default="all",
        help="Load only a specific record type (default: all).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    takeout_root = Path("data/google/Takeout")
    person_key = "local"
    commit_every = 5000
    conninfo = "host=localhost port=5432 user=openvitals dbname=openvitals password=openvitals"

    print("Starting Google Takeout load...")
    stats = load_all(
        takeout_root=takeout_root,
        conninfo=conninfo,
        person_key=person_key,
        commit_every=commit_every,
        only=args.only,
    )

    print("\nLoad complete")
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")


if __name__ == "__main__":
    main()
