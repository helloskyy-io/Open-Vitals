#!/usr/bin/env bash
#
# OpenVitals — Update requirements and rebuild stack (no volume/config reset)
#
# Stops and removes all containers (temporal-*, openvitals-db), then re-runs the
# main bootstrap script. Bootstrap will:
#   - Update the local venv (pip install -r requirements.txt)
#   - Rebuild and start all containers (including the worker with new deps)
#
# Volumes and config/.env are NOT removed. Use scripts/reset.env.sh for a full reset.
#
# Usage (from repo root; sudo if bootstrap requires it):
#   ./scripts/update-requirements.sh
#   sudo ./scripts/update-requirements.sh
#   sudo ./scripts/update-requirements.sh -y   # pass -y to bootstrap (skip pause)

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
BOOTSTRAP_SCRIPT="$REPO_ROOT/scripts/bootstrap.linux.sh"

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
  log_info "OpenVitals — Update requirements and rebuild stack (containers only; volumes and config preserved)"
  echo ""

  if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env not found at $ENV_FILE. Run bootstrap first."
    exit 1
  fi

  ENV=$(get_deployment_env) || exit 1
  OVERRIDE_FILE="$COMPOSE_DIR/${ENV}.override.yml"
  if [[ ! -f "$OVERRIDE_FILE" ]]; then
    log_error "Override file not found: $OVERRIDE_FILE (expected for deployment_env=$ENV)"
    exit 1
  fi

  log_info "Deployment env: $ENV"
  log_info "Stopping and removing containers (volumes and config unchanged)..."
  cd "$REPO_ROOT" || { log_error "Could not cd to $REPO_ROOT"; exit 1; }

  docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_DIR/00-networks.yml" \
    -f "$COMPOSE_DIR/10-temporal.yml" \
    -f "$COMPOSE_DIR/20-workers.yml" \
    -f "$COMPOSE_DIR/25-openvitals-db.yml" \
    -f "$OVERRIDE_FILE" \
    down 2>/dev/null || true

  for c in temporal-db temporal-server temporal-ui temporal-worker openvitals-db; do
    docker rm -f "$c" 2>/dev/null || true
  done

  log_info "Containers removed. Re-running bootstrap..."
  echo ""

  exec "$BOOTSTRAP_SCRIPT" "$@"
}

main "$@"
