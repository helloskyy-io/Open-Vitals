"""
Bootstrap / Genesis workflows.

Genesis: deploy OpenVitals Postgres, create DB/user, run migrations.
Pattern: load_config → load_secrets → helper validate → helper compile → execute plan.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from openvitals.orchestration.temporal.activities.config.load_config import load_config
    from openvitals.orchestration.temporal.activities.secrets.load_secrets import load_secrets
    from openvitals.orchestration.temporal.activities.db.docker_compose_up import docker_compose_up
    from openvitals.orchestration.temporal.activities.db.verify_postgres_up import verify_postgres_up
    from openvitals.orchestration.temporal.activities.dev.verify_jupyter_up import verify_jupyter_up

from openvitals.orchestration.temporal.modules.bootstrap import genesis_helper

# Map plan step activity names to activity functions (for execute plan loop)
_PLAN_ACTIVITIES = {
    "docker_compose_up": docker_compose_up,
    "verify_postgres_up": verify_postgres_up,
    "verify_jupyter_up": verify_jupyter_up,
}

# Argument keys in the order each activity expects (for positional args to execute_activity)
_PLAN_ACTIVITY_ARG_ORDER = {
    "docker_compose_up": ("compose_dir", "compose_files", "env_file", "service_name", "env_vars", "timeout_seconds"),
    "verify_postgres_up": ("host", "port", "user", "db_name", "password"),
    "verify_jupyter_up": ("host", "port"),
}


@workflow.defn(name="GenesisWorkflow")
class GenesisWorkflow:
    """
    One-time setup: ensure OpenVitals Postgres is up, create DB/user, run migrations.
    Step 1: load config and secrets; validate and compile plan; (later) execute activities.
    """

    @workflow.run
    async def run(self, _input: dict | None = None) -> dict:
        # _input: optional workflow input (client can pass {}); we load config via activities
        # Step 1: Load config (Layer 3 — activity)
        config_result = await workflow.execute_activity(
            load_config,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        if config_result.get("status") == "failed":
            return {
                "status": "failed",
                "details": config_result.get("details", ""),
                "error_code": config_result.get("error_code"),
            }
        raw_config = (config_result.get("artifacts") or {}).get("config") or {}

        # Step 2: Load secrets (Layer 3 — activity)
        secrets_result = await workflow.execute_activity(
            load_secrets,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        if secrets_result.get("status") == "failed":
            return {
                "status": "failed",
                "details": secrets_result.get("details", ""),
                "error_code": secrets_result.get("error_code"),
            }
        secrets = (secrets_result.get("artifacts") or {}).get("secrets") or {}

        # Step 3: Validate config (Layer 2 — helper, pure)
        validated = genesis_helper.validate_genesis_config(raw_config)

        # Step 4: Compile execution plan (Layer 2 — helper, pure)
        plan = genesis_helper.compile_execution_plan(validated, secrets)
        steps = plan.get("steps") or []

        # Step 5: Execute plan
        for i, step in enumerate(steps):
            activity_name = step.get("activity") or ""
            activity_fn = _PLAN_ACTIVITIES.get(activity_name)
            if activity_fn is None:
                return {
                    "status": "failed",
                    "details": f"Unknown plan activity: {activity_name}",
                    "error_code": "UNKNOWN_ACTIVITY",
                }
            step_args = step.get("args") or {}
            timeout_seconds = step.get("timeout_seconds") or 60
            # Multiple activity args must be passed via args= list; execute_activity(activity, args=[...])
            arg_keys = _PLAN_ACTIVITY_ARG_ORDER.get(activity_name) or ()
            activity_args = [step_args.get(k) for k in arg_keys]
            result = await workflow.execute_activity(
                activity_fn,
                args=activity_args,
                start_to_close_timeout=timedelta(seconds=timeout_seconds),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            if result.get("status") == "failed":
                return {
                    "status": "failed",
                    "details": result.get("details", "Plan step failed"),
                    "error_code": result.get("error_code"),
                    "failed_step": activity_name,
                    "step_index": i,
                }

        return {
            "status": "ok",
            "details": "Config and secrets loaded; plan executed (Postgres up and verified)",
            "validated_config": validated,
            "plan_steps_count": len(steps),
        }


# Keep genesis_heartbeat import for backward compat if needed; workflow no longer calls it
__all__ = ["GenesisWorkflow"]
