#!/usr/bin/env bash
#
# OpenVitals — Remote / VM bootstrap (curl entrypoint)
#
# For production or VM installs: creates /opt/open-vitals, clones the repo
# there, then runs the real bootstrap (bootstrap.linux.sh) from the clone.
# Safe to run via curl or from disk; idempotent.
#
# Usage (from a fresh VM, as root):
#   curl -fsSL https://raw.githubusercontent.com/helloskyy-io/Open-Vitals/main/scripts/bootstrap.linux.remote.sh | sudo bash
#
# Or download and run:
#   sudo ./scripts/bootstrap.linux.remote.sh

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/open-vitals}"
REPO_URL="${REPO_URL:-https://github.com/helloskyy-io/Open-Vitals.git}"
BRANCH="${BRANCH:-main}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (e.g. sudo bash ...)"
    exit 1
  fi
}

setup_install_dir() {
  log_info "Ensuring install directory: $INSTALL_DIR"
  if [[ ! -d "$INSTALL_DIR" ]]; then
    mkdir -p "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    log_info "Created $INSTALL_DIR"
  else
    log_info "$INSTALL_DIR already exists (idempotent)"
  fi
}

ensure_git() {
  log_info "Checking for git..."
  if command -v git &>/dev/null; then
    log_info "Git: $(git --version)"
    return 0
  fi
  if [[ -f /etc/os-release ]] && grep -qEi 'ubuntu|debian' /etc/os-release 2>/dev/null; then
    log_info "Installing git (apt)..."
    apt-get update
    apt-get install -y git
    log_info "Git installed: $(git --version)"
    return 0
  fi
  log_error "Git is not installed and could not be installed automatically."
  log_error "Install git, then run this script again."
  exit 1
}

clone_or_skip() {
  log_info "Checking repository at $INSTALL_DIR..."
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log_info "Repository already present at $INSTALL_DIR (idempotent: skipping clone)"
    return 0
  fi
  if [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
    log_error "Directory $INSTALL_DIR exists but is not a git repo and is not empty."
  fi
  log_info "Cloning $REPO_URL into $INSTALL_DIR..."
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  log_info "Clone complete"
}

run_bootstrap() {
  local bootstrap="$INSTALL_DIR/scripts/bootstrap.linux.sh"
  if [[ ! -f "$bootstrap" ]]; then
    log_error "Bootstrap script not found: $bootstrap"
    exit 1
  fi
  if [[ ! -x "$bootstrap" ]]; then
    chmod +x "$bootstrap"
  fi
  log_info "Running bootstrap: $bootstrap"
  log_info "══════════════════════════════════════════════════════════════"
  "$bootstrap"
}

main() {
  log_info "OpenVitals — Remote / VM bootstrap"
  echo ""
  check_root
  log_info "Root verified"
  echo ""
  setup_install_dir
  echo ""
  ensure_git
  echo ""
  clone_or_skip
  echo ""
  run_bootstrap
}

main "$@"
