# OpenVitals Temporal worker
# Build from repo root: docker build -f docker/images/workers/temporal/Dockerfile .

FROM python:3.11-slim AS builder

WORKDIR /app

COPY docker/images/workers/temporal/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy worker and package code (compose build context is repo root)
COPY src /app/src
ENV PYTHONPATH=/app/src

# Worker entrypoint
ENTRYPOINT ["python3", "-m", "openvitals.orchestration.temporal.worker"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1
