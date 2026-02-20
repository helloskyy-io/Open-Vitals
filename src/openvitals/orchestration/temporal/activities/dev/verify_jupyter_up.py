"""
Verify Jupyter (Lab/Server) is up and responding (generic).

Hits the Jupyter API or root and checks for HTTP 200. Used after docker_compose_up jupyter.
When worker runs in Docker (temporal-worker), host=jupyter resolves on the same network.
When worker runs on host (e.g. debugging), use 127.0.0.1 so the check still works.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

from temporalio import activity


def _result(status: str, details: str, error_code: str | None = None) -> dict:
    out: dict = {"status": status, "details": details}
    if error_code is not None:
        out["error_code"] = error_code
    return out


def _effective_host(host: str) -> str:
    """Use 127.0.0.1 when worker runs on host so 'jupyter' hostname resolves (port is published)."""
    if host == "jupyter" and not os.path.exists("/.dockerenv"):
        return "127.0.0.1"
    return host


@activity.defn(name="verify_jupyter_up")
def verify_jupyter_up(host: str, port: int) -> dict:
    """
    Verify Jupyter is up by requesting its API or root (sync; runs in worker thread).

    Args:
        host: Jupyter host (e.g. jupyter when worker is on same Docker network).
        port: Jupyter port (e.g. 8888).

    Returns:
        Activity result dict: status ok/failed, details.
    """
    host = _effective_host(host)
    base = f"http://{host}:{port}"
    for path in ("/api/status", "/"):
        url = base + path
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return _result("ok", "Jupyter up (HTTP 200)")
                if path == "/":
                    return _result(
                        "failed",
                        f"Jupyter returned HTTP {resp.status}",
                        error_code="JUPYTER_CHECK_FAILED",
                    )
        except urllib.error.HTTPError as e:
            if e.code == 404 and path == "/api/status":
                continue
            return _result("failed", f"Jupyter check failed: {e}", error_code="JUPYTER_CHECK_FAILED")
        except (urllib.error.URLError, OSError) as e:
            return _result("failed", f"Jupyter check failed: {e}", error_code="JUPYTER_CHECK_FAILED")
    return _result("failed", "Jupyter did not respond with 200", error_code="JUPYTER_CHECK_FAILED")
