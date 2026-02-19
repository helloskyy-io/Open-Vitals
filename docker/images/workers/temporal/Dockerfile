# OpenVitals Temporal worker
# Build from repo root: docker build -f docker/images/workers/temporal/Dockerfile .
# Uses repo-root requirements.txt (same deps as host venv and Jupyter).
# Includes Docker CLI + Compose plugin so activities can run docker compose (e.g. ensure_postgres_up).

FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Docker CLI + Compose plugin (worker uses host socket to run docker compose)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy worker and package code (compose build context is repo root)
COPY src /app/src
ENV PYTHONPATH=/app/src

# Worker entrypoint
ENTRYPOINT ["python3", "-m", "openvitals.orchestration.temporal.worker"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1
