#!/usr/bin/env bash
#
# OpenVitals — Reset deployment environment (dev/test)
#
# Stops and optionally removes containers, volumes, and config so you can
# run bootstrap again from a clean state. Each step is confirmed separately:
# type YES to perform that step, NO or Enter to skip.
#
# Requires root (sudo). Run from repo root.
#
# Usage:
#   sudo ./scripts/reset.env.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [[ -n "${OPENVITALS_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$OPENVITALS_REPO_ROOT"
fi

COMPOSE_DIR="$REPO_ROOT/docker/compose"
ENV_FILE="$REPO_ROOT/.env"
CONFIG_FILE="$REPO_ROOT/config.yaml"

# Use dev override so we can run compose down even when config.yaml is missing
OVERRIDE_FILE="$COMPOSE_DIR/dev.override.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

confirm_step() {
  local prompt="$1"
  echo ""
  read -r -p "$prompt " response
  response="${response:-no}"
  if [[ "${response,,}" == "yes" ]]; then
    return 0
  fi
  return 1
}

check_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (e.g. sudo ./scripts/reset.env.sh)"
    exit 1
  fi
}

# --- Step 1: Stop and remove containers ---
step_containers() {
  if ! command -v docker &>/dev/null || ! docker compose version &>/dev/null; then
    log_warn "Docker or Docker Compose not available; skipping containers"
    return 0
  fi
  if [[ ! -f "$OVERRIDE_FILE" ]] || [[ ! -f "$COMPOSE_DIR/00-networks.yml" ]]; then
    log_warn "Compose files not found; skipping containers"
    return 0
  fi
  log_info "Stopping and removing containers..."
  cd "$REPO_ROOT" || exit 1
  docker compose \
    -f "$COMPOSE_DIR/00-networks.yml" \
    -f "$COMPOSE_DIR/10-temporal.yml" \
    -f "$OVERRIDE_FILE" \
    -f "$COMPOSE_DIR/20-workers.yml" \
    -f "$COMPOSE_DIR/25-openvitals-db.yml" \
    down 2>/dev/null || true
  # Fallback: remove by name in case project name differs
  for c in temporal-db temporal-server temporal-ui temporal-worker openvitals-db; do
    docker rm -f "$c" 2>/dev/null || true
  done
  log_info "Containers removed"
}

# --- Step 2: Delete Temporal database volume ---
step_temporal_volume() {
  if ! command -v docker &>/dev/null; then
    log_warn "Docker not available; skipping Temporal volume"
    return 0
  fi
  local vol
  vol=$(docker volume ls -q 2>/dev/null | grep 'temporal_db_data' | head -1) || true
  if [[ -z "$vol" ]]; then
    log_info "No Temporal database volume found (nothing to delete)"
    return 0
  fi
  log_info "Removing Temporal database volume: $vol"
  docker volume rm "$vol" 2>/dev/null || true
  log_info "Temporal database volume removed"
}

# --- Step 3: Delete OpenVitals database volume ---
step_openvitals_volume() {
  if ! command -v docker &>/dev/null; then
    log_warn "Docker not available; skipping OpenVitals volume"
    return 0
  fi
  local vol
  vol=$(docker volume ls -q 2>/dev/null | grep 'openvitals_db_data' | head -1) || true
  if [[ -z "$vol" ]]; then
    log_info "No OpenVitals database volume found (nothing to delete)"
    return 0
  fi
  log_info "Removing OpenVitals database volume: $vol"
  docker volume rm "$vol" 2>/dev/null || true
  log_info "OpenVitals database volume removed"
}

# --- Step 4: Delete .env and config.yaml ---
step_config_files() {
  local removed=""
  if [[ -f "$ENV_FILE" ]]; then
    rm -f "$ENV_FILE"
    removed="${removed}.env "
  fi
  if [[ -f "$CONFIG_FILE" ]]; then
    rm -f "$CONFIG_FILE"
    removed="${removed}config.yaml "
  fi
  if [[ -n "$removed" ]]; then
    log_info "Removed: $removed"
  else
    log_info "No .env or config.yaml found (nothing to delete)"
  fi
}

# --- Summary and exit ---
print_summary() {
  echo ""
  log_info "══════════════════════════════════════════════════════════════"
  log_info "Reset summary"
  log_info "══════════════════════════════════════════════════════════════"
  echo ""
  if [[ -n "$DID_CONTAINERS" ]]; then
    log_info "  • Containers: stopped and removed"
  else
    log_info "  • Containers: skipped"
  fi
  if [[ -n "$DID_TEMPORAL_VOL" ]]; then
    log_info "  • Temporal database volume: deleted"
  else
    log_info "  • Temporal database volume: skipped"
  fi
  if [[ -n "$DID_OPENVITALS_VOL" ]]; then
    log_info "  • OpenVitals database volume: deleted"
  else
    log_info "  • OpenVitals database volume: skipped"
  fi
  if [[ -n "$DID_CONFIG_FILES" ]]; then
    log_info "  • .env and config.yaml: deleted"
  else
    log_info "  • .env and config.yaml: skipped"
  fi
  echo ""
  log_info "Run sudo ./scripts/bootstrap.linux.sh to start over."
  echo ""
}

# --- Main ---
main() {
  log_info "OpenVitals — Reset deployment environment"
  echo ""

  check_root

  DID_CONTAINERS=""
  DID_TEMPORAL_VOL=""
  DID_OPENVITALS_VOL=""
  DID_CONFIG_FILES=""

  if confirm_step "This will stop and remove all existing containers (temporal-db, temporal-server, temporal-ui, temporal-worker, openvitals-db). YES to continue, NO to skip:"; then
    step_containers
    DID_CONTAINERS=1
  fi

  if confirm_step "This will delete Temporal database data (volume). YES to continue, NO to skip:"; then
    step_temporal_volume
    DID_TEMPORAL_VOL=1
  fi

  if confirm_step "This will delete all OpenVitals database data (volume). YES to continue, NO to skip:"; then
    step_openvitals_volume
    DID_OPENVITALS_VOL=1
  fi

  if confirm_step "This will delete the .env and config.yaml files. YES to continue, NO to skip:"; then
    step_config_files
    DID_CONFIG_FILES=1
  fi

  print_summary
}

main "$@"
