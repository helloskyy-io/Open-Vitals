"""
Placeholder activity so the worker can start and accept Genesis workflow.
Will be replaced/expanded with real Genesis activities (ensure Postgres, migrate, etc.).
"""

from temporalio import activity


@activity.defn(name="genesis_heartbeat")
async def genesis_heartbeat() -> str:
    """Placeholder activity; worker is ready for Genesis."""
    return "genesis_worker_ready"
