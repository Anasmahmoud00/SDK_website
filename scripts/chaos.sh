#!/usr/bin/env bash
set -euo pipefail

# Safe failure simulation helper for local/staging.
# Usage:
#   ./scripts/chaos.sh redis
#   ./scripts/chaos.sh postgres
#   ./scripts/chaos.sh api-restart

MODE="${1:-}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.do.yml}"
BASE_URL="${BASE_URL:-http://localhost:8000}"

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 <redis|postgres|api-restart>"
  exit 1
fi

health() {
  echo "== /health =="
  curl -s "${BASE_URL}/health" || true
  echo
  echo "== /health/dependencies =="
  curl -s "${BASE_URL}/health/dependencies" || true
  echo
}

case "$MODE" in
  redis)
    echo "[chaos] stopping redis"
    docker stop narrative-ai-redis || true
    sleep 3
    health
    echo "[chaos] starting redis"
    docker start narrative-ai-redis || true
    ;;
  postgres)
    echo "[chaos] stopping postgres"
    docker stop narrative-ai-postgres || true
    sleep 3
    health
    echo "[chaos] starting postgres"
    docker start narrative-ai-postgres || true
    ;;
  api-restart)
    echo "[chaos] restarting narrative-api"
    docker compose -f "${COMPOSE_FILE}" restart narrative-api
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    echo "Valid: redis | postgres | api-restart"
    exit 1
    ;;
esac

echo "[chaos] waiting for recovery..."
sleep 5
health
echo "[chaos] done"

