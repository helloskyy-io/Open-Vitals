"""
Bootstrap / Genesis workflows.

Genesis: deploy OpenVitals Postgres, create DB/user, run migrations.
Stub for now; will be expanded to run activities.
"""

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from openvitals.orchestration.temporal.activities.genesis_heartbeat import genesis_heartbeat


@workflow.defn(name="GenesisWorkflow")
class GenesisWorkflow:
    """
    One-time setup: ensure OpenVitals Postgres is up, create DB/user, run migrations.
    Stub implementation for now.
    """

    @workflow.run
    async def run(self) -> str:
        result = await workflow.execute_activity(
            genesis_heartbeat,
            start_to_close_timeout=workflow.Duration(seconds=30),
        )
        return result
