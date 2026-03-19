from __future__ import annotations

import argparse
import io
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import psycopg


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


class AppleHealthXMLStream(io.RawIOBase):
    """
    Streaming wrapper that removes:
      - UTF-8 BOM (if present)
      - DOCTYPE declaration (including internal subset: <!DOCTYPE ... [ ... ]>)

    Compatible with xml.etree.ElementTree.iterparse (binary stream).
    """

    def __init__(self, path: Path, chunk_size: int = 64 * 1024):
        self._f = open(path, "rb")
        self._chunk_size = chunk_size
        self._outbuf = bytearray()
        self._header_processed = False
        self._closed = False

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        if not self._closed:
            try:
                self._f.close()
            finally:
                self._closed = True
        super().close()

    def _process_header_if_needed(self) -> None:
        if self._header_processed:
            return

        buf = bytearray()
        max_header_bytes = 8 * 1024 * 1024  # 8MB safety cap

        while True:
            chunk = self._f.read(self._chunk_size)
            if not chunk:
                break

            buf += chunk

            # Strip UTF-8 BOM if present at start
            if len(buf) >= 3 and buf[:3] == b"\xef\xbb\xbf":
                del buf[:3]

            doctype_start = buf.find(b"<!DOCTYPE")
            if doctype_start != -1:
                # Prefer internal subset end "]>"
                end_internal = buf.find(b"]>", doctype_start)
                if end_internal != -1:
                    doctype_end = end_internal + 2
                    del buf[doctype_start:doctype_end]
                    # strip whitespace immediately after removed block
                    while doctype_start < len(buf) and buf[doctype_start:doctype_start + 1] in (
                        b" ",
                        b"\n",
                        b"\r",
                        b"\t",
                    ):
                        del buf[doctype_start:doctype_start + 1]
                    self._outbuf += buf
                    self._header_processed = True
                    return

                # Fallback: simple doctype ending ">"
                end_simple = buf.find(b">", doctype_start)
                if end_simple != -1:
                    doctype_end = end_simple + 1
                    del buf[doctype_start:doctype_end]
                    while doctype_start < len(buf) and buf[doctype_start:doctype_start + 1] in (
                        b" ",
                        b"\n",
                        b"\r",
                        b"\t",
                    ):
                        del buf[doctype_start:doctype_start + 1]
                    self._outbuf += buf
                    self._header_processed = True
                    return

                # else: keep reading until we find end of doctype
            else:
                # If we can see root element start, we can stop buffering
                if b"<HealthData" in buf:
                    self._outbuf += buf
                    self._header_processed = True
                    return

            if len(buf) > max_header_bytes:
                # Failsafe: pass through raw bytes if header is unexpectedly huge
                self._outbuf += buf
                self._header_processed = True
                return

        self._outbuf += buf
        self._header_processed = True

    def readinto(self, b) -> int:
        if self._closed:
            return 0

        self._process_header_if_needed()

        mv = memoryview(b).cast("B")
        want = len(mv)

        if self._outbuf:
            n = min(want, len(self._outbuf))
            mv[:n] = self._outbuf[:n]
            del self._outbuf[:n]
            return n

        data = self._f.read(want)
        if not data:
            return 0
        mv[: len(data)] = data
        return len(data)


FILTERS = {
    "heart_rate": [
        "HKQuantityTypeIdentifierHeartRate",
        "HKQuantityTypeIdentifierRestingHeartRate",
        "HKQuantityTypeIdentifierWalkingHeartRateAverage",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "HKQuantityTypeIdentifierHeartRateRecoveryOneMinute",
    ],
    "steps": [
        "HKQuantityTypeIdentifierStepCount",
    ],
    "sleep": [
        "HKCategoryTypeIdentifierSleepAnalysis",
    ],
}

SUBSTRING_FILTERS = {
    "heart_rate": [
        "HeartRate",
        "HeartRateVariability",
        "HRV",
    ],
    "steps": [
        "StepCount",
        "Steps",
    ],
    "sleep": [
        "SleepAnalysis",
        "Sleep",
    ],
}


def classify_record_type(rec_type: str) -> set[str]:
    buckets: set[str] = set()

    for bucket, exact_list in FILTERS.items():
        if rec_type in exact_list:
            buckets.add(bucket)

    for bucket, subs in SUBSTRING_FILTERS.items():
        for s in subs:
            if s and s in rec_type:
                buckets.add(bucket)
                break

    return buckets


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        normalized = value.replace("T", " ")
        return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S %z")


NON_NUMERIC_VALUES = {
    "HKCategoryValueNotApplicable",
}


def parse_numeric(value: str | None) -> float | None:
    if value is None:
        return None
    if value in NON_NUMERIC_VALUES:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sleep_stage_from_value(value: str | None) -> str:
    if value is None:
        return "unknown"

    mapping = {
        # Legacy numeric
        "0": "in_bed",
        "1": "asleep",
        "2": "awake",

        # Legacy named
        "HKCategoryValueSleepAnalysisInBed": "in_bed",
        "HKCategoryValueSleepAnalysisAsleep": "asleep",
        "HKCategoryValueSleepAnalysisAwake": "awake",

        # iOS 16+ stages
        "HKCategoryValueSleepAnalysisAsleepUnspecified": "asleep",
        "HKCategoryValueSleepAnalysisAsleepCore": "core",
        "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
        "HKCategoryValueSleepAnalysisAsleepREM": "rem",
    }
    return mapping.get(value, "unknown")

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


def get_or_create_data_source(
    cur: psycopg.Cursor,
    source_name: str | None,
    source_version: str | None,
    device_raw: str | None,
) -> int | None:
    if not (source_name or source_version or device_raw):
        return None

    vendor = "apple"
    product = source_name
    device_model = None

    cur.execute(
        """
        SELECT source_id
        FROM data_source
        WHERE vendor = %s
          AND product IS NOT DISTINCT FROM %s
          AND device_raw IS NOT DISTINCT FROM %s
          AND device_model IS NOT DISTINCT FROM %s
          AND source_version IS NOT DISTINCT FROM %s
        """,
        (vendor, product, device_raw, device_model, source_version),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])

    cur.execute(
        """
        INSERT INTO data_source (vendor, product, device_model, device_raw, source_version)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING source_id
        """,
        (vendor, product, device_model, device_raw, source_version),
    )
    return int(cur.fetchone()[0])


def create_source_event(
    cur: psycopg.Cursor,
    source_id: int | None,
    vendor_type: str | None,
    vendor_id: str | None,
) -> int | None:
    if source_id is None and vendor_type is None and vendor_id is None:
        return None

    cur.execute(
        """
        INSERT INTO source_event (source_id, vendor_type, vendor_id)
        VALUES (%s, %s, %s)
        RETURNING source_event_id
        """,
        (source_id, vendor_type, vendor_id),
    )
    return int(cur.fetchone()[0])


def load_records(
    xml_path: Path,
    conninfo: str,
    person_key: str,
    init_schema: bool,
    schema_path: Path,
    commit_every: int,
    only: str,
) -> dict:
    stats = defaultdict(int)

    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            if init_schema:
                schema_sql = schema_path.read_text(encoding="utf-8")
                cur.execute(schema_sql)

            person_id = get_or_create_person(cur, person_key)

            stream = AppleHealthXMLStream(xml_path)
            processed = 0

            try:
                for _, elem in ET.iterparse(stream, events=("end",)):
                    if strip_ns(elem.tag) != "Record":
                        continue

                    rec_type = elem.attrib.get("type", "")
                    buckets = classify_record_type(rec_type)
                    if only != "all":
                        buckets = {only} & buckets
                    if not buckets:
                        elem.clear()
                        continue

                    source_name = elem.attrib.get("sourceName")
                    source_version = elem.attrib.get("sourceVersion")
                    device_raw = elem.attrib.get("device")
                    source_id = get_or_create_data_source(
                        cur,
                        source_name=source_name,
                        source_version=source_version,
                        device_raw=device_raw,
                    )
                    source_event_id = create_source_event(
                        cur,
                        source_id=source_id,
                        vendor_type=rec_type,
                        vendor_id=elem.attrib.get("uuid"),
                    )

                    start_raw = elem.attrib.get("startDate") or elem.attrib.get("creationDate")
                    end_raw = elem.attrib.get("endDate") or start_raw
                    value_raw = elem.attrib.get("value")
                    value_num = parse_numeric(value_raw)

                    if "heart_rate" in buckets and value_num is not None and end_raw:
                        bpm = int(round(value_num))
                        ts = parse_datetime(end_raw)
                        cur.execute(
                            """
                            INSERT INTO hr_sample (person_id, source_id, source_event_id, ts, bpm)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (person_id, source_id, source_event_id, ts, bpm),
                        )
                        stats["hr_sample"] += 1

                    if "steps" in buckets and value_num is not None and start_raw and end_raw:
                        steps = int(round(value_num))
                        start_ts = parse_datetime(start_raw)
                        end_ts = parse_datetime(end_raw)
                        cur.execute(
                            """
                            INSERT INTO steps_sample (person_id, source_id, source_event_id, start_ts, end_ts, steps)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (person_id, source_id, source_event_id, start_ts, end_ts, steps),
                        )
                        stats["steps_sample"] += 1

                    if "sleep" in buckets and start_raw and end_raw:
                        if rec_type != "HKCategoryTypeIdentifierSleepAnalysis":
                            elem.clear()
                            continue
                        start_ts = parse_datetime(start_raw)
                        end_ts = parse_datetime(end_raw)
                        cur.execute(
                            """
                            INSERT INTO sleep_session (person_id, source_id, source_event_id, start_ts, end_ts)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING sleep_session_id
                            """,
                            (person_id, source_id, source_event_id, start_ts, end_ts),
                        )
                        sleep_session_id = int(cur.fetchone()[0])
                        stage = sleep_stage_from_value(value_raw)
                        cur.execute(
                            """
                            INSERT INTO sleep_stage (sleep_session_id, start_ts, end_ts, stage)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (sleep_session_id, start_ts, end_ts, stage),
                        )
                        stats["sleep_session"] += 1
                        stats["sleep_stage"] += 1

                    processed += 1
                    if processed % commit_every == 0:
                        conn.commit()

                    elem.clear()
            finally:
                stream.close()

            conn.commit()

    stats["records_processed"] = processed
    return dict(stats)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Apple Health HR/steps/sleep records into Postgres tables."
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
    xml_path = Path("data/apple/export.xml")
    schema_path = Path("sql/test/example_tables.sql")
    person_key = "local"
    commit_every = 1000
    init_schema = False
    conninfo = "host=localhost port=5432 user=openvitals dbname=openvitals password=openvitals"

    stats = load_records(
        xml_path=xml_path,
        conninfo=conninfo,
        person_key=person_key,
        init_schema=init_schema,
        schema_path=schema_path,
        commit_every=commit_every,
        only=args.only,
    )

    print("Load complete")
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")


if __name__ == "__main__":
    main()
