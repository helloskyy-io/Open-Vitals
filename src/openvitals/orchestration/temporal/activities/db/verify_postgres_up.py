"""
Verify a Postgres instance is up (generic).

Connects to the given host/port with user/db_name/password and runs SELECT 1.
Reusable for any Postgres DB. Idempotent; retry-friendly.
Retries on "database system is starting up" so Genesis can run right after compose up.
"""

from __future__ import annotations

import time

from temporalio import activity

# Retry when Postgres is still starting (e.g. right after docker compose up)
_MAX_VERIFY_ATTEMPTS = 5
_VERIFY_RETRY_DELAY_SEC = 5


def _result(status: str, details: str, error_code: str | None = None) -> dict:
    out: dict = {"status": status, "details": details}
    if error_code is not None:
        out["error_code"] = error_code
    return out


def _is_starting_up(exc: Exception) -> bool:
    msg = (getattr(exc, "message", None) or str(exc)).lower()
    return "starting up" in msg or "connection refused" in msg


@activity.defn(name="verify_postgres_up")
def verify_postgres_up(
    host: str,
    port: int,
    user: str,
    db_name: str,
    password: str,
) -> dict:
    """
    Connect to Postgres and run SELECT 1 to verify it is up (sync; runs in worker thread).
    Retries on "database system is starting up" so Genesis can run immediately after compose up.

    Args:
        host: DB host (e.g. openvitals-db when worker is on Docker network).
        port: DB port (e.g. 5432).
        user: DB user.
        db_name: Database name.
        password: DB password.

    Returns:
        Activity result dict: status ok/failed, details.
    """
    try:
        import psycopg
    except ImportError:
        return _result("failed", "psycopg not installed", error_code="NO_PSYCOPG")

    conninfo = f"host={host} port={port} user={user} dbname={db_name} password={password}"
    last_error: Exception | None = None

    for attempt in range(1, _MAX_VERIFY_ATTEMPTS + 1):
        try:
            with psycopg.connect(
                conninfo=conninfo,
                connect_timeout=10,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return _result("ok", "Postgres up (SELECT 1 succeeded)")
        except Exception as e:
            last_error = e
            if attempt < _MAX_VERIFY_ATTEMPTS and _is_starting_up(e):
                time.sleep(_VERIFY_RETRY_DELAY_SEC)
                continue
            return _result("failed", f"Postgres check failed: {e}", error_code="POSTGRES_CHECK_FAILED")

    return _result(
        "failed",
        f"Postgres check failed after {_MAX_VERIFY_ATTEMPTS} attempts: {last_error!s}",
        error_code="POSTGRES_CHECK_FAILED",
    )
