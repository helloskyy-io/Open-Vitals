"""
Load config.yaml (generic activity; first step in Genesis and other workflows).

Reads config from path (env OPENVITALS_REPO_ROOT + /config.yaml, or explicit path).
Returns raw config dict in ActivityResult.artifacts["config"] for helper to validate.
"""

from __future__ import annotations

import os
from pathlib import Path

from temporalio import activity

# In container, compose sets OPENVITALS_REPO_ROOT to mount path (e.g. /workspace)
_DEFAULT_REPO_ROOT = os.environ.get("OPENVITALS_REPO_ROOT", "/workspace")
_DEFAULT_CONFIG_PATH = Path(_DEFAULT_REPO_ROOT) / "config.yaml"


@activity.defn(name="load_config")
async def load_config(config_path: str | None = None) -> dict:
    """
    Read config.yaml and return raw config dict.

    Args:
        config_path: Optional path to config.yaml. If None, uses
            OPENVITALS_REPO_ROOT/config.yaml (in container, set by compose to mount path).

    Returns:
        ActivityResult with status, details, and artifacts["config"] = raw dict.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    path = path.resolve()

    def _result(status: str, details: str, artifacts: dict | None = None, error_code: str | None = None) -> dict:
        out: dict = {"status": status, "details": details}
        if artifacts is not None:
            out["artifacts"] = artifacts
        if error_code is not None:
            out["error_code"] = error_code
        return out

    if not path.is_file():
        return _result("failed", f"Config file not found: {path}", error_code="CONFIG_NOT_FOUND")

    try:
        import yaml
    except ImportError:
        return _result("failed", "PyYAML not available; cannot load config", error_code="NO_PYYAML")

    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except Exception as e:
        return _result("failed", f"Failed to read config: {e}", error_code="CONFIG_READ_ERROR")

    if raw is None:
        raw = {}

    return _result("ok", "Loaded config", artifacts={"config": raw})
