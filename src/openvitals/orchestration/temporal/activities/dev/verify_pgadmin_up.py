"""
Verify pgAdmin 4 is up and responding (generic).

Hits the pgAdmin login page and checks for HTTP 200. Used after docker_compose_up pgadmin.
When worker runs in Docker (temporal-worker), host=pgadmin resolves on the same network.
When worker runs on host (e.g. debugging), use 127.0.0.1 so the check still works.
Retries on connection refused so we wait for pgAdmin to finish starting (~1–2 min after container up).
"""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request

from temporalio import activity

# pgAdmin can take 1–2 min to become ready after container start; retry before failing
_MAX_VERIFY_ATTEMPTS = 18  # 18 * 10s = 3 min max wait
_VERIFY_RETRY_DELAY_SEC = 10


def _result(status: str, details: str, error_code: str | None = None) -> dict:
    out: dict = {"status": status, "details": details}
    if error_code is not None:
        out["error_code"] = error_code
    return out


def _effective_host(host: str) -> str:
    """Use 127.0.0.1 when worker runs on host so 'pgadmin' hostname resolves (port is published)."""
    if host == "pgadmin" and not os.path.exists("/.dockerenv"):
        return "127.0.0.1"
    return host


def _try_one_request(base: str) -> tuple[bool, str]:
    """Try /login then /. Return (True, '') on success, (False, error_detail) on failure."""
    for path in ("/login", "/"):
        url = base + path
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True, ""
                if path == "/":
                    return False, f"pgAdmin returned HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code == 404 and path == "/login":
                continue
            return False, str(e)
        except (urllib.error.URLError, OSError) as e:
            return False, str(e)
    return False, "pgAdmin did not respond with 200"


@activity.defn(name="verify_pgadmin_up")
def verify_pgadmin_up(host: str, port: int) -> dict:
    """
    Verify pgAdmin is up by requesting its login page (sync; runs in worker thread).
    Retries on connection refused so we wait for pgAdmin to finish starting after compose up.

    Args:
        host: pgAdmin host (e.g. pgadmin when worker is on same Docker network).
        port: pgAdmin port (e.g. 5050).

    Returns:
        Activity result dict: status ok/failed, details.
    """
    host = _effective_host(host)
    base = f"http://{host}:{port}"
    last_error = ""
    for attempt in range(1, _MAX_VERIFY_ATTEMPTS + 1):
        ok, err = _try_one_request(base)
        if ok:
            return _result("ok", "pgAdmin up (HTTP 200)")
        last_error = err
        if attempt < _MAX_VERIFY_ATTEMPTS:
            time.sleep(_VERIFY_RETRY_DELAY_SEC)
    return _result(
        "failed",
        f"pgAdmin check failed after {_MAX_VERIFY_ATTEMPTS} attempts: {last_error}",
        error_code="PGADMIN_CHECK_FAILED",
    )
