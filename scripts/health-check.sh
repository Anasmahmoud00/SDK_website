#!/usr/bin/env bash
# =============================================================================
# NARRATIVE AI - System Health Monitoring Script
# =============================================================================

set -euo pipefail

# Configuration
LOG_FILE="${LOG_FILE:-./logs/health.log}"
BASE_URL="${1:-${BASE_URL:-http://localhost:8000}}"
mkdir -p "./logs"

# Unified API topology on DigitalOcean compose stack
SERVICES=(
    "API Health:${BASE_URL}/health"
    "API Dependencies:${BASE_URL}/health/dependencies"
)

echo "--- Health Check: $(date) ---" | tee -a "$LOG_FILE"

FAILED=0

for service_item in "${SERVICES[@]}"; do
    NAME="${service_item%%:*}"
    URL="${service_item#*:}"
    
    echo -n "Checking $NAME ($URL)... " | tee -a "$LOG_FILE"
    
    # Use curl with timeout
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$URL")
    
    if [ "$STATUS" == "200" ]; then
        echo " [OK]" | tee -a "$LOG_FILE"
    else
        echo " [FAILED] Status: $STATUS" | tee -a "$LOG_FILE"
        FAILED=$((FAILED + 1))
    fi
done

# Check Redis (if redis-cli is available)
if command -v redis-cli >/dev/null 2>&1; then
    echo -n "Checking Redis... " | tee -a "$LOG_FILE"
    REDIS_HOST="${REDIS_HOST:-localhost}"
    REDIS_PORT="${REDIS_PORT:-6379}"
    REDIS_PING=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null || true)
    if [ "$REDIS_PING" == "PONG" ]; then
        echo " [OK]" | tee -a "$LOG_FILE"
    else
        echo " [FAILED]" | tee -a "$LOG_FILE"
        FAILED=$((FAILED + 1))
    fi
fi

echo "--- Summary: $FAILED services failed ---" | tee -a "$LOG_FILE"

if [ $FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
