#!/usr/bin/env python3
"""
OpenVitals Temporal worker.

Connects to Temporal and runs workflows/activities (Genesis, ingestion, etc.).
Single worker for now; workflows are organized by modules for future splitting.
"""

import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

from pathlib import Path

# Ensure repo root (or install) is on path for openvitals
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from temporalio.client import Client
from temporalio.worker import Worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "temporal-server")
TEMPORAL_PORT = os.getenv("TEMPORAL_PORT", "7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = os.getenv("TASK_QUEUE", "bootstrap-dev")

TEMPORAL_ADDRESS = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"

shutdown_requested = False


def _signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Received signal %s, initiating graceful shutdown...", signum)
    shutdown_requested = True


async def run_worker() -> None:
    logger.info("Connecting to Temporal at %s (namespace=%s)...", TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE)
    client = await Client.connect(
        target_host=TEMPORAL_ADDRESS,
        namespace=TEMPORAL_NAMESPACE,
    )
    logger.info("Successfully connected to Temporal")

    from openvitals.orchestration.temporal.activities import (
        genesis_heartbeat,
        load_config,
        load_secrets,
    )
    from openvitals.orchestration.temporal.activities.db import docker_compose_up, verify_postgres_up
    from openvitals.orchestration.temporal.activities.dev import verify_jupyter_up
    from openvitals.orchestration.temporal.modules.bootstrap.workflows import GenesisWorkflow

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GenesisWorkflow],
        activities=[
            genesis_heartbeat,
            load_config,
            load_secrets,
            docker_compose_up,
            verify_postgres_up,
            verify_jupyter_up,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=4),
    ):
        logger.info("Worker started successfully (task_queue=%s)", TASK_QUEUE)
        logger.info("Waiting for work... (Ctrl+C to stop)")

        while not shutdown_requested:
            await asyncio.sleep(1)

    logger.info("Worker stopped gracefully")


def main() -> None:
    logger.info("OpenVitals Temporal worker starting")
    logger.info("  Temporal: %s", TEMPORAL_ADDRESS)
    logger.info("  Namespace: %s", TEMPORAL_NAMESPACE)
    logger.info("  Task queue: %s", TASK_QUEUE)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Interrupt received, shutting down...")
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
