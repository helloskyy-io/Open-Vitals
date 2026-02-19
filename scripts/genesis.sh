#!/usr/bin/env bash
#
# OpenVitals — Start Genesis workflow (next step after bootstrap)
#
# Triggers the Genesis workflow and waits for success or surfaces failure.
# Requires: Temporal up, temporal-worker running, config.yaml and .env present.
# Reads deployment env from config.yaml (namespace openvitals-${ENV}, task queue bootstrap-${ENV}).
#
# Usage (from repo root):
#   ./scripts/genesis.sh
#   sudo ./scripts/genesis.sh   # if .venv or config need root access

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [[ -n "${OPENVITALS_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$OPENVITALS_REPO_ROOT"
fi

CONFIG_FILE="$REPO_ROOT/config.yaml"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
HELPER="$REPO_ROOT/scripts/lib/start_genesis_workflow.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Read deployment env from config ---
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

# --- Main ---
main() {
  log_info "OpenVitals — Genesis workflow"
  echo ""

  ENV=$(get_deployment_env) || exit 1
  export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-127.0.0.1:7233}"
  export TEMPORAL_NAMESPACE="openvitals-${ENV}"
  export TASK_QUEUE="bootstrap-${ENV}"

  log_info "Namespace: $TEMPORAL_NAMESPACE  Task queue: $TASK_QUEUE"
  log_info "Starting Genesis workflow..."
  echo ""

  if [[ ! -f "$HELPER" ]]; then
    log_error "Helper not found: $HELPER"
    exit 1
  fi

  if [[ -x "$VENV_PYTHON" ]]; then
    "$VENV_PYTHON" "$HELPER" || exit 1
  else
    log_error "Venv not found at $REPO_ROOT/.venv. Run bootstrap first."
    exit 1
  fi

  echo ""
  log_info "Done."
}

main "$@"
