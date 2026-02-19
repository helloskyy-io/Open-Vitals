"""
Run docker compose up -d for a service (generic).

Brings a service up; idempotent (no-op if already up). Uses host Docker via socket.
Secrets from --env-file; non-secret vars (e.g. user/name/port from config) via env_vars.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from temporalio import activity


def _result(status: str, details: str, error_code: str | None = None) -> dict:
    out: dict = {"status": status, "details": details}
    if error_code is not None:
        out["error_code"] = error_code
    return out


@activity.defn(name="docker_compose_up")
async def docker_compose_up(
    compose_dir: str,
    compose_files: list[str],
    env_file: str,
    service_name: str,
    env_vars: dict[str, str] | None = None,
) -> dict:
    """
    Run docker compose up -d for the given service.

    Args:
        compose_dir: Directory containing the compose files (e.g. /workspace/docker/compose).
        compose_files: List of compose file basenames.
        env_file: Path to .env (secrets only; e.g. OPENVITALS_DB_PASSWORD).
        service_name: Service to bring up (e.g. openvitals-db).
        env_vars: Optional env vars from config (e.g. OPENVITALS_DB_USER, OPENVITALS_DB_NAME, OPENVITALS_DB_PORT).
                  Merged with process env so compose sees them; non-secret settings belong in config, not .env.

    Returns:
        Activity result dict: status ok/failed, details.
    """
    cwd = Path(compose_dir)
    if not cwd.is_dir():
        return _result("failed", f"Compose dir not found: {compose_dir}", error_code="COMPOSE_DIR_NOT_FOUND")

    env_path = Path(env_file)
    if not env_path.is_file():
        return _result("failed", f"Env file not found: {env_file}", error_code="ENV_FILE_NOT_FOUND")

    if not compose_files:
        return _result("failed", "compose_files list is empty", error_code="NO_COMPOSE_FILES")

    cmd = ["docker", "compose"]
    for f in compose_files:
        cmd.extend(["-f", str(cwd / f)])
    cmd.extend(["--env-file", str(env_path), "up", "-d", service_name])

    run_env = {**os.environ}
    if env_vars:
        run_env.update(env_vars)

    try:
        proc = await asyncio_to_subprocess_run(cmd, cwd=cwd, env=run_env, capture_output=True, text=True, timeout=120)
    except Exception as e:
        return _result("failed", f"Failed to run docker compose: {e}", error_code="COMPOSE_RUN_ERROR")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        return _result("failed", f"docker compose up failed: {stderr}", error_code="COMPOSE_UP_FAILED")

    return _result("ok", f"Service {service_name} is up (or already running)")


async def asyncio_to_subprocess_run(
    cmd: list[str], cwd: Path, env: dict[str, str], capture_output: bool, text: bool, timeout: int
):
    """Run subprocess in executor so we don't block the event loop."""
    def _run():
        return subprocess.run(cmd, cwd=cwd, env=env, capture_output=capture_output, text=text, timeout=timeout)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)
