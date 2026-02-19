#!/usr/bin/env bash
#
# OpenVitals — on-demand health check
#
# Verifies the deployed stack (Temporal + worker; optionally OpenVitals DB if running).
# Run anytime to confirm connectivity without re-running bootstrap (e.g. after a reboot).
#
# Best practice: one doctor script for the whole environment. Once Genesis is in place
# and openvitals-db is part of the stack, doctor already checks it if the container
# is running. Add more components here as the stack grows.
#
# Usage (from repo root or scripts/):
#   ./scripts/doctor.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [[ -n "${OPENVITALS_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$OPENVITALS_REPO_ROOT"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

FAILED=0

# Docker available
if command -v docker &>/dev/null; then
  ok "Docker available"
else
  fail "Docker not found"
  (( FAILED++ )) || true
fi

# Temporal Postgres
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-db$'; then
  if docker exec temporal-db pg_isready -U temporal -d temporal &>/dev/null; then
    ok "temporal-db reachable"
  else
    fail "temporal-db not ready (pg_isready failed)"
    (( FAILED++ )) || true
  fi
else
  fail "temporal-db container not running"
  (( FAILED++ )) || true
fi

# Temporal server (gRPC 7233)
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-server$'; then
  if docker exec temporal-server sh -c "ss -tln 2>/dev/null | grep -q ':7233' || netstat -tln 2>/dev/null | grep -q ':7233'" 2>/dev/null; then
    ok "temporal-server reachable (gRPC 7233)"
  else
    fail "temporal-server not listening on 7233"
    (( FAILED++ )) || true
  fi
else
  fail "temporal-server container not running"
  (( FAILED++ )) || true
fi

# Temporal UI (HTTP)
if curl -sf "http://127.0.0.1:8234" &>/dev/null; then
  ok "temporal-ui reachable (HTTP :8234)"
else
  fail "temporal-ui not responding on :8234"
  (( FAILED++ )) || true
fi

# Temporal worker
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^temporal-worker$'; then
  ok "temporal-worker container running"
else
  fail "temporal-worker container not running"
  (( FAILED++ )) || true
fi

# OpenVitals DB (optional — if container exists and is running, check it)
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^openvitals-db$'; then
  if docker exec openvitals-db pg_isready -U openvitals -d openvitals &>/dev/null; then
    ok "openvitals-db reachable"
  else
    fail "openvitals-db not ready (pg_isready failed)"
    (( FAILED++ )) || true
  fi
else
  warn "openvitals-db not running (start with Genesis, or manually)"
fi

echo ""
if [[ $FAILED -eq 0 ]]; then
  ok "All required checks passed"
  exit 0
else
  fail "$FAILED check(s) failed"
  exit 1
fi
