#!/usr/bin/env bash
#
# OpenVitals — Bootstrap / Deploy Temporal (idempotent)
#
# Single script that brings the environment up to a running Temporal stack
# (database, server, UI) for workstations and VMs.
# public-installer logic: install Docker/Compose if missing, then deploy Temporal.
#
# This script:
# - Installs Docker and Docker Compose (v2) if missing (Linux, apt; requires sudo)
# - Ensures a Python venv at .venv with requirements.txt (same deps as worker/Jupyter)
# - Creates config.yaml and .env from templates/ if they don't exist
#   (auto-generates Temporal Postgres password in .env)
# - Starts Temporal infrastructure via docker compose
# - Runs health checks and prints the Temporal UI URL
#
# Safe to run multiple times (idempotent). Run from repo root or any subdir.
#
# Usage (from repo root):
#   sudo ./scripts/bootstrap.linux.sh
#   sudo ./scripts/bootstrap.linux.sh --env prod --yes
#   sudo ./scripts/bootstrap.linux.sh -e prod -y
#
# Flags:
#   --env, -e dev|test|prod   Deployment environment (persisted to config.yaml). Overrides config and env var.
#   --yes, -y                 Non-interactive: skip the config-review pause and continue with defaults.
#
# Env vars (optional; flags take precedence):
#   OPENVITALS_DEPLOYMENT_ENV  Same as --env (dev|test|prod).
#   OPENVITALS_YES             Non-empty skips the pause (same as -y).

set -euo pipefail

# --- Configuration ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Allow override so curl-run can set REPO_ROOT to current dir
if [[ -n "${OPENVITALS_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$OPENVITALS_REPO_ROOT"
elif [[ -d "$REPO_ROOT/.git" ]]; then
  : # REPO_ROOT is repo root
else
  # When run via curl, current dir is repo root
  REPO_ROOT="${REPO_ROOT:-$(pwd)}"
fi

CONFIG_FILE="$REPO_ROOT/config.yaml"
ENV_FILE="$REPO_ROOT/.env"
CONFIG_TEMPLATE="$REPO_ROOT/templates/.config.template"
ENV_TEMPLATE="$REPO_ROOT/templates/.env.template"
COMPOSE_DIR="$REPO_ROOT/docker/compose"
REQUIREMENTS_FILE="$REPO_ROOT/requirements.txt"
VENV_DIR="$REPO_ROOT/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"

# --- Logging ---

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Require root (script installs Docker and runs compose; sudo required) ---

check_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (e.g. sudo ./scripts/bootstrap.linux.sh)"
    exit 1
  fi
}

# --- Docker: install if missing (Linux, apt; requires root) ---

install_docker() {
  log_info "Installing Docker using official repository (Ubuntu/Debian)..."

  apt-get update
  apt-get install -y ca-certificates curl gnupg lsb-release

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  . /etc/os-release 2>/dev/null || true
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$(lsb_release -cs 2>/dev/null)} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  systemctl enable docker 2>/dev/null || true
  systemctl start docker 2>/dev/null || true

  if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    log_info "Docker installed: $(docker --version); $(docker compose version --short)"
  else
    log_error "Docker install completed but docker/compose not found in PATH"
    return 1
  fi
}

# --- Prerequisites: ensure Docker (and Compose) available; install on Linux if missing ---

ensure_docker() {
  log_info "Checking Docker and Docker Compose..."

  if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    log_info "Docker: $(docker --version)"
    log_info "Docker Compose: $(docker compose version --short)"
    log_info "Prerequisites OK"
    return 0
  fi

  # Docker or Compose missing — install on Linux (apt); we are already root
  if [[ -f /etc/os-release ]] && grep -qEi 'ubuntu|debian' /etc/os-release 2>/dev/null; then
    if command -v apt-get &>/dev/null; then
      install_docker || return 1
      return 0
    fi
  fi

  log_error "Docker or Docker Compose is not installed and could not be installed automatically."
  log_error "On Linux (Ubuntu/Debian), run this script with sudo to install Docker."
  log_error "On other platforms, install Docker and Docker Compose (v2), then run this script again."
  log_error "See: https://docs.docker.com/engine/install/"
  return 1
}

verify_repo_files() {
  if [[ ! -f "$COMPOSE_DIR/00-networks.yml" ]] || [[ ! -f "$COMPOSE_DIR/10-temporal.yml" ]]; then
    log_error "Compose files not found in $COMPOSE_DIR (00-networks.yml, 10-temporal.yml)"
    return 1
  fi
  if [[ ! -f "$COMPOSE_DIR/20-workers.yml" ]]; then
    log_error "Compose file not found: $COMPOSE_DIR/20-workers.yml"
    return 1
  fi
  if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    log_error "requirements.txt not found at $REQUIREMENTS_FILE"
    return 1
  fi
  log_info "Compose dir: $COMPOSE_DIR"
}

# --- Ensure Python venv exists and has requirements (for config edit and parity with containers) ---
ensure_venv() {
  log_info "Ensuring Python venv and requirements..."

  if ! command -v python3 &>/dev/null; then
    log_error "python3 not found; install Python 3.9+ and run bootstrap again"
    return 1
  fi

  # On Debian/Ubuntu, venv needs the version-specific package (e.g. python3.12-venv) for ensurepip
  if [[ -f /etc/os-release ]] && grep -qEi 'ubuntu|debian' /etc/os-release 2>/dev/null && command -v apt-get &>/dev/null; then
    local py_ver
    py_ver=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || true
    if [[ -n "$py_ver" ]]; then
      local venv_pkg="python${py_ver}-venv"
      if ! dpkg -l "$venv_pkg" 2>/dev/null | grep -q '^ii'; then
        log_info "Installing $venv_pkg (apt) for venv + pip..."
        apt-get update -qq
        apt-get install -y "$venv_pkg"
      fi
    else
      apt-get update -qq
      apt-get install -y python3-venv 2>/dev/null || true
    fi
  fi

  # Remove broken venv (e.g. created without ensurepip) so we can recreate
  if [[ -d "$VENV_DIR" ]] && [[ ! -x "$VENV_DIR/bin/pip" ]]; then
    log_info "Removing broken venv (missing pip) at $VENV_DIR..."
    rm -rf "$VENV_DIR"
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    log_info "Creating venv at $VENV_DIR..."
    if ! python3 -m venv "$VENV_DIR"; then
      log_error "Failed to create venv. On Debian/Ubuntu install: apt install python3.X-venv (match your python3 version)"
      return 1
    fi
  else
    log_info "Venv already exists at $VENV_DIR (idempotent)"
  fi

  log_info "Installing requirements from $REQUIREMENTS_FILE..."
  if ! "$VENV_PYTHON" -m pip install -q --upgrade pip 2>/dev/null; then
    "$VENV_PYTHON" -m pip install --upgrade pip
  fi
  if ! "$VENV_PYTHON" -m pip install -q -r "$REQUIREMENTS_FILE"; then
    log_error "Failed to install requirements; check $REQUIREMENTS_FILE"
    return 1
  fi
  log_info "Venv ready: $VENV_PYTHON"
  log_info "Tip: After changing requirements.txt, run ./scripts/rebuild-worker.sh to update the worker image."
}

# --- Read deployment env from config.yaml (dev | test | prod); set OVERRIDE_FILE ---
# Optional first argument overrides config (e.g. from --env flag when persistence failed).
read_deployment_env() {
  local override_env="${1:-}"
  local env_value=""

  if [[ -n "$override_env" ]]; then
    env_value="$override_env"
    log_info "Using deployment environment from flag/env: $env_value"
  else
    log_info "Reading deployment environment from config.yaml..."
    if [[ ! -f "$CONFIG_FILE" ]]; then
      log_error "config.yaml not found at $CONFIG_FILE (run script once to create from template)"
      return 1
    fi
    if [[ -x "$VENV_PYTHON" ]]; then
      env_value=$("$VENV_PYTHON" -c "
try:
    import yaml
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    env = (config or {}).get('temporal', {}).get('deployment_env') or 'dev'
    if env not in ('dev', 'test', 'prod'):
        env = 'dev'
    print(env)
except Exception:
    print('dev')
" 2>/dev/null) || env_value="dev"
    elif command -v python3 &>/dev/null; then
      env_value=$(python3 -c "
try:
    import yaml
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    env = (config or {}).get('temporal', {}).get('deployment_env') or 'dev'
    if env not in ('dev', 'test', 'prod'):
        env = 'dev'
    print(env)
except Exception:
    print('dev')
" 2>/dev/null) || env_value="dev"
    else
      env_value=$(grep -E 'deployment_env' "$CONFIG_FILE" 2>/dev/null | head -1 | sed -n 's/.*deployment_env:\s*\(dev\|test\|prod\).*/\1/p') || true
      env_value="${env_value:-dev}"
    fi
  fi

  export ENV="${env_value}"
  export OVERRIDE_FILE="$COMPOSE_DIR/${ENV}.override.yml"

  if [[ ! -f "$OVERRIDE_FILE" ]]; then
    log_error "Override file not found: $OVERRIDE_FILE (expected for temporal.deployment_env=$ENV)"
    return 1
  fi
  log_info "Deployment env: $ENV; override: $OVERRIDE_FILE"
}

# --- Create config and .env from templates (idempotent) ---

# Set to true when we create .env or config.yaml so main can prompt for manual steps before starting Temporal
CREATED_CONFIG_FILES=false

create_config_files() {
  log_info "Ensuring config.yaml and .env exist..."

  local files_created=false

  if [[ -f "$CONFIG_FILE" ]]; then
    log_info "config.yaml already exists (idempotent: skipping)"
  else
    if [[ ! -f "$CONFIG_TEMPLATE" ]]; then
      log_error "Template not found: $CONFIG_TEMPLATE"
      return 1
    fi
    cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
    log_info "Created config.yaml from template"
    files_created=true
  fi

  if [[ -f "$ENV_FILE" ]]; then
    log_info ".env already exists (idempotent: skipping)"
  else
    if [[ ! -f "$ENV_TEMPLATE" ]]; then
      log_error "Template not found: $ENV_TEMPLATE"
      return 1
    fi
    cp "$ENV_TEMPLATE" "$ENV_FILE"

    # Auto-generate Temporal Postgres password if placeholder present
    if grep -q 'TEMPORAL_POSTGRES_PASSWORD="YOUR_SECURE_TEMPORAL_DB_PASSWORD_HERE"' "$ENV_FILE" 2>/dev/null; then
      local pwd
      pwd=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-25)
      if sed -i "s|TEMPORAL_POSTGRES_PASSWORD=\"YOUR_SECURE_TEMPORAL_DB_PASSWORD_HERE\"|TEMPORAL_POSTGRES_PASSWORD=\"$pwd\"|" "$ENV_FILE" 2>/dev/null; then
        log_info "Generated TEMPORAL_POSTGRES_PASSWORD and wrote to .env"
      else
        log_warn "Could not replace password placeholder; set TEMPORAL_POSTGRES_PASSWORD in .env manually"
      fi
    fi

    if grep -q 'OPENVITALS_DB_PASSWORD="YOUR_SECURE_OPENVITALS_DB_PASSWORD_HERE"' "$ENV_FILE" 2>/dev/null; then
      local ov_pwd
      ov_pwd=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-25)
      if sed -i "s|OPENVITALS_DB_PASSWORD=\"YOUR_SECURE_OPENVITALS_DB_PASSWORD_HERE\"|OPENVITALS_DB_PASSWORD=\"$ov_pwd\"|" "$ENV_FILE" 2>/dev/null; then
        log_info "Generated OPENVITALS_DB_PASSWORD and wrote to .env"
      else
        log_warn "Could not replace OPENVITALS_DB_PASSWORD placeholder; set it in .env manually"
      fi
    fi

    log_info "Created .env from template"
    log_warn "Review and update secrets in .env as needed"
    files_created=true
  fi

  if [[ "$files_created" == "true" ]]; then
    CREATED_CONFIG_FILES=true
    log_info "Configuration files created"
  else
    log_info "Configuration files already present (idempotent)"
  fi
}

# --- Update config.yaml project_root to actual repo path (preserves comments; uses venv) ---
update_config_project_root() {
  if [[ ! -f "$CONFIG_FILE" ]]; then
    return 0
  fi
  export OPENVITALS_REPO_ROOT_FOR_CONFIG="$REPO_ROOT"
  export OPENVITALS_CONFIG_PATH="$CONFIG_FILE"
  if "$VENV_PYTHON" -c '
import os
import ruamel.yaml
path = os.environ.get("OPENVITALS_REPO_ROOT_FOR_CONFIG", "")
config_path = os.environ.get("OPENVITALS_CONFIG_PATH", "")
if not path or not config_path:
    exit(1)
with open(config_path, "r") as f:
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    data = yaml.load(f)
if data is None:
    data = {}
if "openvitals" not in data:
    data["openvitals"] = {}
data["openvitals"]["project_root"] = path
with open(config_path, "w") as f:
    yaml.dump(data, f)
' 2>/dev/null; then
    log_info "Updated config.yaml openvitals.project_root to $REPO_ROOT"
  else
    log_warn "Could not update project_root in config.yaml (compose will use REPO_ROOT env)"
  fi
}

# Pause so user can edit .env and config.yaml; continue when they press y (only when config was just created)
prompt_edit_then_continue() {
  echo ""
  log_info "══════════════════════════════════════════════════════════════"
  log_info "Config files created — edit if desired, then continue"
  log_info "══════════════════════════════════════════════════════════════"
  echo ""
  log_info "Edit .env or config.yaml to change Temporal DB password or port — or press y to accept defaults and build Temporal."
  echo ""
  local response
  while true; do
    read -r -p "Continue and start Temporal? [y/N]: " response
    response="${response:-n}"
    if [[ "${response,,}" == "y" ]] || [[ "${response,,}" == "yes" ]]; then
      log_info "Continuing..."
      break
    fi
    log_info "Enter y when ready to continue, or Ctrl+C to exit."
  done
  echo ""
}

# --- Start Temporal infrastructure ---

start_temporal_infra() {
  log_info "Starting Temporal infrastructure..."

  if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env not found at $ENV_FILE (run create_config_files first)"
    return 1
  fi

  local db_running server_running ui_running
  db_running=false
  server_running=false
  ui_running=false

  docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-db$'     && db_running=true
  docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-server$' && server_running=true
  docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-ui$'    && ui_running=true

  if [[ "$db_running" == "true" ]] && [[ "$server_running" == "true" ]] && [[ "$ui_running" == "true" ]]; then
    log_info "All Temporal containers already running (idempotent: skipping start)"
    return 0
  fi

  cd "$REPO_ROOT" || { log_error "Could not cd to $REPO_ROOT"; return 1; }

  docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_DIR/00-networks.yml" \
    -f "$COMPOSE_DIR/10-temporal.yml" \
    -f "$OVERRIDE_FILE" \
    up -d temporal-db temporal-server temporal-ui

  log_info "Waiting for containers to be ready..."
  sleep 5
}

# --- Health checks ---

health_check() {
  log_info "Running health checks..."

  # temporal-db
  local i=1
  while [[ $i -le 30 ]]; do
    if docker exec temporal-db pg_isready -U temporal -d temporal &>/dev/null; then
      log_info "temporal-db: healthy"
      break
    fi
    [[ $i -eq 30 ]] && { log_error "temporal-db health check failed"; return 1; }
    log_info "Waiting for temporal-db... ($i/30)"
    sleep 2
    (( i++ )) || true
  done

  # temporal-server (process + port)
  i=1
  while [[ $i -le 30 ]]; do
    if docker exec temporal-server sh -c "ss -tln 2>/dev/null | grep -q ':7233' || netstat -tln 2>/dev/null | grep -q ':7233'" 2>/dev/null; then
      log_info "temporal-server: healthy (gRPC 7233)"
      break
    fi
    [[ $i -eq 30 ]] && { log_error "temporal-server health check failed"; return 1; }
    log_info "Waiting for temporal-server... ($i/30)"
    sleep 2
    (( i++ )) || true
  done

  # temporal-ui (HTTP; host port 8234 to avoid 8080 conflict with IDEs e.g. Cursor)
  i=1
  while [[ $i -le 30 ]]; do
    if curl -sf "http://127.0.0.1:8234" &>/dev/null; then
      log_info "temporal-ui: healthy (HTTP :8234)"
      break
    fi
    [[ $i -eq 30 ]] && { log_error "temporal-ui health check failed"; return 1; }
    log_info "Waiting for temporal-ui... ($i/30)"
    sleep 2
    (( i++ )) || true
  done

  log_info "All health checks passed"
}

# --- Ensure Temporal namespace exists (for worker) ---
ensure_temporal_namespace() {
  local namespace="openvitals-${ENV}"
  log_info "Ensuring Temporal namespace '$namespace' exists..."

  local create_out
  if create_out=$(docker run --rm \
    --network openvitals \
    --entrypoint temporal \
    temporalio/admin-tools:latest \
    operator namespace create \
    --address temporal-server:7233 \
    --namespace "$namespace" \
    --retention 7d 2>&1); then
    log_info "Namespace '$namespace' created"
  else
    if echo "$create_out" | grep -qi "already exists"; then
      log_info "Namespace '$namespace' already exists (idempotent)"
    else
      log_warn "Namespace create output: $create_out (may already exist)"
    fi
  fi
}

# --- Start temporal-worker ---
start_temporal_worker() {
  log_info "Starting temporal-worker..."

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-worker$'; then
    log_info "temporal-worker already running (idempotent: skipping)"
    return 0
  fi

  cd "$REPO_ROOT" || { log_error "Could not cd to $REPO_ROOT"; return 1; }
  export REPO_ROOT
  export ENV

  docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_DIR/00-networks.yml" \
    -f "$COMPOSE_DIR/10-temporal.yml" \
    -f "$COMPOSE_DIR/20-workers.yml" \
    -f "$OVERRIDE_FILE" \
    up -d --build temporal-worker

  log_info "Waiting for temporal-worker to start..."
  sleep 5
}

# --- Health check: temporal-worker ---
health_check_worker() {
  log_info "Checking temporal-worker..."

  local i=1
  while [[ $i -le 30 ]]; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-worker$'; then
      if docker exec temporal-worker python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
        log_info "temporal-worker: healthy"
        return 0
      fi
    fi
    [[ $i -eq 30 ]] && { log_error "temporal-worker health check failed"; return 1; }
    log_info "Waiting for temporal-worker... ($i/30)"
    sleep 2
    (( i++ )) || true
  done
}

# --- Print success and URL ---

print_success() {
  echo ""
  log_info "══════════════════════════════════════════════════════════════"
  log_info "Temporal deployment complete"
  log_info "══════════════════════════════════════════════════════════════"
  echo ""
  log_info "Temporal UI:  http://127.0.0.1:8234"
  log_info "Containers:   temporal-db, temporal-server, temporal-ui, temporal-worker"
  echo ""
  log_info "Check the Temporal webserver at the URL above."
  echo ""
  log_info "When ready to run the next deployment step (Genesis workflow), run:"
  log_info "  sudo ./scripts/genesis.sh"
  echo ""
  log_info "══════════════════════════════════════════════════════════════"
}

# --- Apply deployment env from flag/env to config.yaml (so read_deployment_env sees it) ---
apply_bootstrap_env_to_config() {
  local env_value="$1"
  if [[ -z "$env_value" ]]; then
    return 0
  fi
  if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "config.yaml not found; cannot set deployment_env"
    return 1
  fi
  local helper="$REPO_ROOT/scripts/lib/config_edit.py"
  if [[ ! -f "$helper" ]]; then
    log_error "Config helper not found: $helper"
    return 1
  fi
  if ! "$VENV_PYTHON" "$helper" --config "$CONFIG_FILE" --set temporal.deployment_env "$env_value"; then
    log_error "Failed to write temporal.deployment_env to config.yaml (venv: $VENV_PYTHON)"
    return 1
  fi
  log_info "Set temporal.deployment_env=$env_value in config.yaml"
  return 0
}

# --- Main ---

main() {
  # Parse flags: --env / -e dev|test|prod, --yes / -y (precedence: flag > env var)
  local BOOTSTRAP_ENV=""
  local BOOTSTRAP_YES=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --env|-e)
        if [[ $# -lt 2 ]]; then
          log_error "Missing value for $1 (use dev, test, or prod)"
          exit 1
        fi
        BOOTSTRAP_ENV="$2"
        shift 2
        ;;
      --yes|-y)
        BOOTSTRAP_YES=1
        shift
        ;;
      *)
        shift
        ;;
    esac
  done
  [[ -n "${BOOTSTRAP_ENV:-}" ]] || BOOTSTRAP_ENV="${OPENVITALS_DEPLOYMENT_ENV:-}"
  [[ -n "${BOOTSTRAP_YES:-}" ]] || [[ -z "${OPENVITALS_YES:-}" ]] || BOOTSTRAP_YES=1
  if [[ -n "$BOOTSTRAP_ENV" ]] && [[ "$BOOTSTRAP_ENV" != "dev" ]] && [[ "$BOOTSTRAP_ENV" != "test" ]] && [[ "$BOOTSTRAP_ENV" != "prod" ]]; then
    log_error "Invalid deployment env: $BOOTSTRAP_ENV (use dev, test, or prod)"
    exit 1
  fi

  log_info "OpenVitals — Bootstrap / Deploy Temporal (idempotent)"
  echo ""

  check_root
  log_info "Root access verified"
  echo ""

  ensure_docker || exit 1
  echo ""

  verify_repo_files || exit 1
  echo ""

  ensure_venv || exit 1
  echo ""

  create_config_files || exit 1
  echo ""

  if [[ -n "$BOOTSTRAP_ENV" ]]; then
    apply_bootstrap_env_to_config "$BOOTSTRAP_ENV" || exit 1
    echo ""
  fi

  if [[ "$CREATED_CONFIG_FILES" == "true" ]] && [[ "${BOOTSTRAP_YES:-0}" != "1" ]]; then
    prompt_edit_then_continue
  fi

  read_deployment_env "${BOOTSTRAP_ENV:-}" || exit 1
  echo ""

  update_config_project_root
  echo ""

  start_temporal_infra || exit 1
  echo ""

  health_check || exit 1
  echo ""

  ensure_temporal_namespace || true
  start_temporal_worker || exit 1
  echo ""

  health_check_worker || exit 1
  echo ""

  print_success
}

main "$@"
