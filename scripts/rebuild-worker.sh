#!/usr/bin/env bash
#
# OpenVitals — Rebuild and restart the Temporal worker
#
# After changing workflow or activity code, the worker must be rebuilt and
# restarted so it runs the new code. (Workflows and activities execute inside
# the worker; the client only sends tasks.) Use this script to rebuild the
# worker image and bring the container up.
#
# Usage (from repo root):
#   ./scripts/rebuild-worker.sh
#   ./scripts/rebuild-worker.sh --no-cache   # force full rebuild

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [[ -n "${OPENVITALS_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$OPENVITALS_REPO_ROOT"
fi

CONFIG_FILE="$REPO_ROOT/config.yaml"
ENV_FILE="$REPO_ROOT/.env"
COMPOSE_DIR="$REPO_ROOT/docker/compose"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

get_deployment_env() {
  if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "config.yaml not found at $CONFIG_FILE. Run bootstrap first."
    return 1
  fi
  local env_value="dev"
  if [[ -x "$VENV_PYTHON" ]]; then
    env_value=$("$VENV_PYTHON" -c "
try:
    import yaml
    with open('$CONFIG_FILE') as f:
        c = yaml.safe_load(f)
    e = (c or {}).get('temporal', {}).get('deployment_env') or 'dev'
    if e not in ('dev', 'test', 'prod'):
        e = 'dev'
    print(e)
except Exception:
    print('dev')
" 2>/dev/null) || env_value="dev"
  else
    env_value=$(grep -E 'deployment_env' "$CONFIG_FILE" 2>/dev/null | head -1 | sed -n 's/.*deployment_env:\s*\(dev\|test\|prod\).*/\1/p') || true
    env_value="${env_value:-dev}"
  fi
  echo "$env_value"
}

main() {
  local build_opts=()
  if [[ "${1:-}" == "--no-cache" ]]; then
    build_opts=(--no-cache)
  fi

  log_info "OpenVitals — Rebuild Temporal worker"
  echo ""

  if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env not found at $ENV_FILE. Run bootstrap first."
    exit 1
  fi

  ENV=$(get_deployment_env) || exit 1
  export REPO_ROOT
  export ENV
  OVERRIDE_FILE="$COMPOSE_DIR/${ENV}.override.yml"
  if [[ ! -f "$OVERRIDE_FILE" ]]; then
    log_error "Override file not found: $OVERRIDE_FILE (expected for deployment_env=$ENV)"
    exit 1
  fi

  log_info "Deployment env: $ENV"
  log_info "Rebuilding worker image..."
  cd "$REPO_ROOT" || { log_error "Could not cd to $REPO_ROOT"; exit 1; }

  docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_DIR/00-networks.yml" \
    -f "$COMPOSE_DIR/10-temporal.yml" \
    -f "$COMPOSE_DIR/20-workers.yml" \
    -f "$OVERRIDE_FILE" \
    build "${build_opts[@]}" temporal-worker

  log_info "Restarting temporal-worker..."
  docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_DIR/00-networks.yml" \
    -f "$COMPOSE_DIR/10-temporal.yml" \
    -f "$COMPOSE_DIR/20-workers.yml" \
    -f "$OVERRIDE_FILE" \
    up -d temporal-worker

  echo ""
  log_info "Done. Run ./scripts/genesis.sh to test."
}

main "$@"
