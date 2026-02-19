"""
Verify a Postgres instance is up (generic).

Connects to the given host/port with user/db_name/password and runs SELECT 1.
Reusable for any Postgres DB. Idempotent; retry-friendly.
"""

from __future__ import annotations

from temporalio import activity


def _result(status: str, details: str, error_code: str | None = None) -> dict:
    out: dict = {"status": status, "details": details}
    if error_code is not None:
        out["error_code"] = error_code
    return out


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

    try:
        with psycopg.connect(
            conninfo=f"host={host} port={port} user={user} dbname={db_name} password={password}",
            connect_timeout=10,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as e:
        return _result("failed", f"Postgres check failed: {e}", error_code="POSTGRES_CHECK_FAILED")

    return _result("ok", "Postgres up (SELECT 1 succeeded)")
