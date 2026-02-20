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
    jupyter_cfg = openvitals.get("jupyter") or {}
    validated["jupyter"] = {"port": jupyter_cfg.get("port") or 8888}

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
    project_root = validated_config.get("project_root") or ""

    # env_vars for any compose run that loads dev.override.yml must include REPO_ROOT so jupyter volume parses
    db_env_vars = {
        "OPENVITALS_DB_USER": db_user,
        "OPENVITALS_DB_NAME": db_name,
        "OPENVITALS_DB_PORT": str(db_port_host),
    }
    if project_root:
        db_env_vars["REPO_ROOT"] = project_root

    steps = [
        {
            "activity": "docker_compose_up",
            "args": {
                "compose_dir": compose_dir,
                "compose_files": compose_files,
                "env_file": env_file,
                "service_name": "openvitals-db",
                "env_vars": db_env_vars,
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

    # Dev only: bring up Jupyter and verify it is up (defined only in dev.override.yml; port from config)
    jupyter_cfg = validated_config.get("jupyter") or {}
    jupyter_port = jupyter_cfg.get("port") or 8888
    if env == "dev" and project_root:
        steps.append(
            {
                "activity": "docker_compose_up",
                "args": {
                    "compose_dir": compose_dir,
                    "compose_files": compose_files,
                    "env_file": env_file,
                    "service_name": "jupyter",
                    "env_vars": {"REPO_ROOT": project_root, "JUPYTER_PORT": str(jupyter_port)},
                    "timeout_seconds": 360,
                },
                "timeout_seconds": 360,
            }
        )
        steps.append(
            {
                "activity": "verify_jupyter_up",
                "args": {"host": "jupyter", "port": jupyter_port},
                "timeout_seconds": 15,
            }
        )

    return {"steps": steps}
