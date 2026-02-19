"""
Genesis workflow helper (pure; no I/O, no Temporal SDK).

Validates raw config and compiles execution plan for Genesis activities.
"""

from __future__ import annotations


def validate_genesis_config(raw_config: dict) -> dict:
    """
    Validate and structure config for Genesis (pure function).

    Args:
        raw_config: Raw dict from load_config activity.

    Returns:
        Validated Genesis-specific config dict (e.g. temporal.deployment_env,
        openvitals.project_root, openvitals.database if present).
    """
    validated: dict = {}
    temporal = (raw_config or {}).get("temporal") or {}
    validated["deployment_env"] = temporal.get("deployment_env") or "dev"
    if validated["deployment_env"] not in ("dev", "test", "prod"):
        validated["deployment_env"] = "dev"

    openvitals = (raw_config or {}).get("openvitals") or {}
    validated["project_root"] = openvitals.get("project_root") or ""
    validated["database"] = openvitals.get("database") or {}

    return validated


def compile_execution_plan(validated_config: dict, secrets: dict) -> dict:
    """
    Compile execution plan for Genesis activities (pure function).

    Args:
        validated_config: Output of validate_genesis_config.
        secrets: Output of load_secrets activity (artifacts["secrets"]).

    Returns:
        Execution plan: {"steps": [{"activity": ..., "args": ..., "timeout_seconds": ...}, ...]}.
        Steps run in worker; paths use in-container /workspace (OPENVITALS_REPO_ROOT).
    """
    env = validated_config.get("deployment_env") or "dev"
    # In-container paths (worker has OPENVITALS_REPO_ROOT=/workspace and compose mounted at /workspace/docker/compose)
    compose_dir = "/workspace/docker/compose"
    env_file = "/workspace/.env"
    compose_files = [
        "00-networks.yml",
        "25-openvitals-db.yml",
        f"{env}.override.yml",
    ]
    # User/name/port from config only; password from .env (secrets)
    db_config = validated_config.get("database") or {}
    db_user = db_config.get("user") or "openvitals"
    db_name = db_config.get("name") or "openvitals"
    db_port_host = db_config.get("port") or 5433  # host port in config; compose uses OPENVITALS_DB_PORT
    db_password = (secrets or {}).get("OPENVITALS_DB_PASSWORD") or ""

    steps = [
        {
            "activity": "docker_compose_up",
            "args": {
                "compose_dir": compose_dir,
                "compose_files": compose_files,
                "env_file": env_file,
                "service_name": "openvitals-db",
                "env_vars": {
                    "OPENVITALS_DB_USER": db_user,
                    "OPENVITALS_DB_NAME": db_name,
                    "OPENVITALS_DB_PORT": str(db_port_host),
                },
            },
            "timeout_seconds": 120,
        },
        {
            "activity": "verify_postgres_up",
            "args": {
                "host": "openvitals-db",
                "port": 5432,
                "user": db_user,
                "db_name": db_name,
                "password": db_password,
            },
            "timeout_seconds": 15,
        },
    ]
    return {"steps": steps}
