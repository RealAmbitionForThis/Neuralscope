#!/usr/bin/env bash
# NeuralScope local launcher.
# Usage: bash scripts/launch.sh
# Env vars:
#   NEURALSCOPE_SKIP_INSTALL=1   skip pip/npm install
#   NEURALSCOPE_SKIP_BUILD=1     skip frontend build (use dev server)

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

echo -e "${CYAN}${BOLD}NeuralScope launcher${NC}"

require() {
  command -v "$1" >/dev/null 2>&1 || { echo -e "${RED}missing: $1${NC}"; exit 1; }
}

echo -e "\n${BOLD}[1/4] Checking prerequisites${NC}"
require python3
require node
require npm
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
else
  echo "  no CUDA GPU detected — CPU-only mode"
fi

if [ -z "${NEURALSCOPE_SKIP_INSTALL:-}" ]; then
  echo -e "\n${BOLD}[2/4] Installing backend deps${NC}"
  python3 -m pip install -r "${BACKEND_DIR}/requirements.txt"

  echo -e "\n${BOLD}[3/4] Installing frontend deps${NC}"
  (cd "${FRONTEND_DIR}" && npm install --silent)
else
  echo -e "\n  ${CYAN}[2-3/4] skipped (NEURALSCOPE_SKIP_INSTALL set)${NC}"
fi

echo -e "\n${BOLD}[4/4] Starting services${NC}"
cd "${ROOT_DIR}"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

if [ -z "${NEURALSCOPE_SKIP_BUILD:-}" ]; then
  (cd "${FRONTEND_DIR}" && npm run build >/dev/null 2>&1 && npm run start) &
else
  (cd "${FRONTEND_DIR}" && npm run dev) &
fi
FRONTEND_PID=$!

cleanup() {
  echo -e "\n${CYAN}shutting down${NC}"
  kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo -e "\n${GREEN}${BOLD}NeuralScope running${NC}"
echo -e "  ${GREEN}http://localhost:3000${NC}  (frontend)"
echo -e "  ${GREEN}http://localhost:8000${NC}  (backend + /docs)"
echo -e "\nCtrl+C to stop."
wait "${BACKEND_PID}" "${FRONTEND_PID}"
