from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import io
import json
import xml.etree.ElementTree as ET


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
                    while doctype_start < len(buf) and buf[doctype_start:doctype_start + 1] in (b" ", b"\n", b"\r", b"\t"):
                        del buf[doctype_start:doctype_start + 1]
                    self._outbuf += buf
                    self._header_processed = True
                    return

                # Fallback: simple doctype ending ">"
                end_simple = buf.find(b">", doctype_start)
                if end_simple != -1:
                    doctype_end = end_simple + 1
                    del buf[doctype_start:doctype_end]
                    while doctype_start < len(buf) and buf[doctype_start:doctype_start + 1] in (b" ", b"\n", b"\r", b"\t"):
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
        mv[:len(data)] = data
        return len(data)


# ---- Filtering logic (edit these lists as you learn more about your own export) ----
FILTERS = {
    "heart_rate": [
        # common HR identifiers
        "HKQuantityTypeIdentifierHeartRate",
        "HKQuantityTypeIdentifierRestingHeartRate",
        "HKQuantityTypeIdentifierWalkingHeartRateAverage",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "HKQuantityTypeIdentifierHeartRateRecoveryOneMinute",
        # some exports include beat-to-beat / HRV variants; keep substring support below too
    ],
    "steps": [
        "HKQuantityTypeIdentifierStepCount",
    ],
    "sleep": [
        "HKCategoryTypeIdentifierSleepAnalysis",
    ],
}

# Optional substring matches (more forgiving / future-proof).
# If any substring is present in the Record @type, it will be included in that category.
SUBSTRING_FILTERS = {
    "heart_rate": [
        "HeartRate",          # catches HeartRate, RestingHeartRate, WalkingHeartRateAverage, etc.
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
    """
    Return one or more buckets that this record type belongs to.
    Buckets: heart_rate, steps, sleep
    """
    buckets: set[str] = set()

    # exact matches
    for bucket, exact_list in FILTERS.items():
        if rec_type in exact_list:
            buckets.add(bucket)

    # substring matches
    for bucket, subs in SUBSTRING_FILTERS.items():
        for s in subs:
            if s and s in rec_type:
                buckets.add(bucket)
                break

    return buckets


def summarize_hr_steps_sleep(xml_path: Path) -> dict:
    """
    Stream-parse Apple Health export.xml and keep only <Record> entries related to HR, steps, or sleep.
    Produces:
      - record types found per category
      - count per record type
      - observed attributes per record type
      - observed child tags per record type
    """
    count_by_type: dict[str, int] = defaultdict(int)
    attrs_by_type: dict[str, set[str]] = defaultdict(set)
    child_tags_by_type: dict[str, set[str]] = defaultdict(set)
    buckets_by_type: dict[str, set[str]] = defaultdict(set)

    stream = AppleHealthXMLStream(xml_path)
    try:
        for _, elem in ET.iterparse(stream, events=("end",)):
            if strip_ns(elem.tag) != "Record":
                continue

            rec_type = elem.attrib.get("type")
            if not rec_type:
                elem.clear()
                continue

            buckets = classify_record_type(rec_type)
            if not buckets:
                elem.clear()
                continue

            count_by_type[rec_type] += 1
            buckets_by_type[rec_type].update(buckets)

            for a in elem.attrib.keys():
                attrs_by_type[rec_type].add(a)

            for child in list(elem):
                child_tags_by_type[rec_type].add(strip_ns(child.tag))

            elem.clear()
    finally:
        stream.close()

    # Group types by bucket
    types_by_bucket: dict[str, list[str]] = {"heart_rate": [], "steps": [], "sleep": []}
    for t, bs in buckets_by_type.items():
        for b in bs:
            types_by_bucket[b].append(t)

    for b in types_by_bucket:
        types_by_bucket[b] = sorted(set(types_by_bucket[b]))

    # Build final output
    record_types_all = sorted(count_by_type.keys())

    return {
        "source_file": str(xml_path),
        "categories": {
            "heart_rate": {
                "record_types_found": types_by_bucket["heart_rate"],
            },
            "steps": {
                "record_types_found": types_by_bucket["steps"],
            },
            "sleep": {
                "record_types_found": types_by_bucket["sleep"],
            },
        },
        "record_type_count_total": len(record_types_all),
        "record_types_total": record_types_all,
        "counts_by_record_type": dict(sorted(count_by_type.items(), key=lambda kv: (-kv[1], kv[0]))),
        "attributes_by_record_type": {k: sorted(v) for k, v in attrs_by_type.items()},
        "child_tags_by_record_type": {k: sorted(v) for k, v in child_tags_by_type.items()},
        "buckets_by_record_type": {k: sorted(v) for k, v in buckets_by_type.items()},
        "notes": {
            "filtering": "Record @type is included if it matches an exact list OR contains a substring configured in SUBSTRING_FILTERS.",
            "edit_filters_here": "Update FILTERS / SUBSTRING_FILTERS at top of script to tune what 'HR/steps/sleep' means for your use-case.",
        },
    }


def write_json(data: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # Expected workflow:
    #   1) Drop export.xml into sample_data/
    #   2) Run this script
    xml_path = Path("src/openvitals/adapters/apple_health/sample_data/export.xml")
    out_path = Path("src/openvitals/adapters/apple_health/sample_data/hr_steps_sleep_record_types.json")

    summary = summarize_hr_steps_sleep(xml_path)
    write_json(summary, out_path)

    print(f"Wrote {out_path}")
    print(f"Found {summary['record_type_count_total']} total matching Record types")
    print("By category:")
    for cat, info in summary["categories"].items():
        print(f"  {cat}: {len(info['record_types_found'])} types")