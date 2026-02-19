"""
Load secrets from .env (generic activity; used when workflow needs secrets).

Reads .env from path (env OPENVITALS_REPO_ROOT + /.env, or explicit path).
Returns only what the caller needs (e.g. Genesis: OPENVITALS_DB_PASSWORD).
Never pass secrets as workflow input; load via this activity so they are not in history.
"""

from __future__ import annotations

import os
from pathlib import Path

from temporalio import activity

_DEFAULT_REPO_ROOT = os.environ.get("OPENVITALS_REPO_ROOT", "/workspace")
_DEFAULT_ENV_PATH = Path(_DEFAULT_REPO_ROOT) / ".env"

# Keys Genesis (and other workflows) may need; only these are returned
GENESIS_SECRET_KEYS = frozenset({"OPENVITALS_DB_PASSWORD", "TEMPORAL_POSTGRES_PASSWORD"})


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a .env-style file (KEY=value, one per line; skip comments and empty)."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    out[key] = value
    return out


@activity.defn(name="load_secrets")
async def load_secrets(
    env_path: str | None = None,
    keys: list[str] | None = None,
) -> dict:
    """
    Read .env and return only the requested keys (or Genesis defaults).

    Args:
        env_path: Optional path to .env. If None, uses
            OPENVITALS_REPO_ROOT/.env (in container, set by compose to mount path).
        keys: Optional list of keys to return. If None, returns GENESIS_SECRET_KEYS
            (OPENVITALS_DB_PASSWORD, TEMPORAL_POSTGRES_PASSWORD).

    Returns:
        Dict with status, details, artifacts["secrets"] = dict of key -> value (serializable).
    """
    def _result(status: str, details: str, artifacts: dict | None = None, error_code: str | None = None) -> dict:
        out: dict = {"status": status, "details": details}
        if artifacts is not None:
            out["artifacts"] = artifacts
        if error_code is not None:
            out["error_code"] = error_code
        return out

    path = Path(env_path) if env_path else _DEFAULT_ENV_PATH
    path = path.resolve()

    if not path.is_file():
        return _result("failed", f".env not found: {path}", error_code="ENV_NOT_FOUND")

    try:
        all_vars = _parse_dotenv(path)
    except Exception as e:
        return _result("failed", f"Failed to read .env: {e}", error_code="ENV_READ_ERROR")

    requested = keys if keys is not None else list(GENESIS_SECRET_KEYS)
    secrets = {k: all_vars[k] for k in requested if k in all_vars}

    return _result("ok", f"Loaded {len(secrets)} secret(s)", artifacts={"secrets": secrets})
