# OpenVitals Jupyter (dev-only)
# Build from repo root: docker build -f docker/images/jupyter/Dockerfile .
# Same requirements.txt as worker; runs Jupyter Lab with no token/password (dev, localhost only).

FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /workspace

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy package so openvitals is importable in notebooks
COPY src /workspace/src
ENV PYTHONPATH=/workspace/src

# Jupyter Lab: no token, no password (safe only when bound to 127.0.0.1 and dev-only)
# --allow-root is required (we run as root); without it Jupyter exits with "Running as root is not recommended".
# If you changed CMD, rebuild with: docker compose -f docker/compose/... build --no-cache jupyter
ENV JUPYTER_PORT=8888
EXPOSE 8888
CMD ["sh", "-c", "jupyter lab --ip=0.0.0.0 --port=${JUPYTER_PORT:-8888} --ServerApp.token= --ServerApp.password= --no-browser --allow-root"]
