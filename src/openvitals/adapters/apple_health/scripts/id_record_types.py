from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import io
import xml.etree.ElementTree as ET


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


class AppleHealthXMLStream(io.RawIOBase):
    """
    Streaming wrapper that removes:
      - UTF-8 BOM (if present)
      - DOCTYPE declaration (including internal subset: <!DOCTYPE ... [ ... ]>)

    It does this only near the top of the file (where Apple Health puts it),
    and then becomes a simple pass-through stream.

    Compatible with xml.etree.ElementTree.iterparse (binary stream).
    """

    def __init__(self, path: Path, chunk_size: int = 64 * 1024):
        self._f = open(path, "rb")
        self._chunk_size = chunk_size
        self._outbuf = bytearray()
        self._header_processed = False
        self._closed = False

    def readable(self) -> bool:  # required by io base classes
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

        # We only need to buffer the "top" of the file until we've handled DOCTYPE.
        # Apple Health's internal subset is large, but still typically near the top.
        # We'll keep reading until we can confidently remove/skip it.
        max_header_bytes = 8 * 1024 * 1024  # 8MB safety cap for pathological cases

        while True:
            chunk = self._f.read(self._chunk_size)
            if not chunk:
                # EOF while processing header; just finalize whatever we have
                break

            buf += chunk

            # 1) Strip UTF-8 BOM if present at very start
            if len(buf) >= 3 and buf[:3] == b"\xef\xbb\xbf":
                del buf[:3]

            # 2) Look for DOCTYPE
            doctype_start = buf.find(b"<!DOCTYPE")
            if doctype_start != -1:
                # We found the start of DOCTYPE. Now find its end.
                # With internal subset, end looks like "]>".
                end_internal = buf.find(b"]>", doctype_start)
                if end_internal != -1:
                    doctype_end = end_internal + 2  # include ]>
                    # Remove the entire doctype block
                    del buf[doctype_start:doctype_end]
                    # Also remove trailing whitespace/newlines immediately after it
                    while doctype_start < len(buf) and buf[doctype_start:doctype_start + 1] in (b" ", b"\n", b"\r", b"\t"):
                        del buf[doctype_start:doctype_start + 1]
                    self._outbuf += buf
                    self._header_processed = True
                    return

                # No internal subset end yet; might be a simple doctype ending in ">"
                end_simple = buf.find(b">", doctype_start)
                if end_simple != -1:
                    doctype_end = end_simple + 1
                    del buf[doctype_start:doctype_end]
                    while doctype_start < len(buf) and buf[doctype_start:doctype_start + 1] in (b" ", b"\n", b"\r", b"\t"):
                        del buf[doctype_start:doctype_start + 1]
                    self._outbuf += buf
                    self._header_processed = True
                    return

                # Still waiting for the end of DOCTYPE; keep reading
            else:
                # No DOCTYPE found (yet). If we can see the root element start,
                # we can stop buffering and start passing through.
                # This is a decent "go signal" for Apple Health exports.
                if b"<HealthData" in buf:
                    self._outbuf += buf
                    self._header_processed = True
                    return

            if len(buf) > max_header_bytes:
                # Failsafe: give up on stripping DOCTYPE to avoid unbounded memory.
                # At this point, the file is unusual; we pass through raw bytes.
                self._outbuf += buf
                self._header_processed = True
                return

        # EOF reached during header processing
        self._outbuf += buf
        self._header_processed = True

    def readinto(self, b) -> int:
        """
        RawIOBase hook: fill the preallocated bytes-like object `b` and return number of bytes read.
        """
        if self._closed:
            return 0

        self._process_header_if_needed()

        mv = memoryview(b).cast("B")
        want = len(mv)

        # Serve from out buffer first
        if self._outbuf:
            n = min(want, len(self._outbuf))
            mv[:n] = self._outbuf[:n]
            del self._outbuf[:n]
            return n

        # Then pass-through from underlying file
        data = self._f.read(want)
        if not data:
            return 0
        mv[:len(data)] = data
        return len(data)


def summarize_records(xml_path: Path) -> dict:
    """
    Summarize <Record> entries:
      - unique Record @type values
      - which attributes appear per type
      - which child tags appear per type (e.g., MetadataEntry)
    """
    attrs_by_type: dict[str, set[str]] = defaultdict(set)
    child_tags_by_type: dict[str, set[str]] = defaultdict(set)

    stream = AppleHealthXMLStream(xml_path)

    try:
        for _, elem in ET.iterparse(stream, events=("end",)):
            if strip_ns(elem.tag) != "Record":
                continue

            rec_type = elem.attrib.get("type")
            if not rec_type:
                elem.clear()
                continue

            for a in elem.attrib.keys():
                attrs_by_type[rec_type].add(a)

            for child in list(elem):
                child_tags_by_type[rec_type].add(strip_ns(child.tag))

            elem.clear()
    finally:
        stream.close()

    return {
        "record_type_count": len(attrs_by_type),
        "record_types": sorted(attrs_by_type.keys()),
        "attributes_by_record_type": {k: sorted(v) for k, v in attrs_by_type.items()},
        "child_tags_by_record_type": {k: sorted(v) for k, v in child_tags_by_type.items()},
    }


def write_summary(summary: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    xml_path = Path("src/openvitals/adapters/apple_health/sample_data/export.xml")  # <-- set your path
    out_path = Path("src/openvitals/adapters/apple_health/sample_data/record_type_field_summary.json")

    summary = summarize_records(xml_path)
    write_summary(summary, out_path)

    print(f"Wrote {out_path}")
    print(f"Found {summary['record_type_count']} unique Record types")