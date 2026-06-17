#!/usr/bin/env bash
# =============================================================================
# NARRATIVE AI - Automated Database Backup Script
# =============================================================================
# Usage: ./backup.sh [BACKUP_DIR] [RETENTION_DAYS]
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${2:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATABASE_URL="${DATABASE_URL:-}"

# Extract connection details if DATABASE_URL is present (basic parsing)
# Format: postgresql://user:password@host:port/dbname
if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:/]+):?([0-9]*)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]:-5432}"
    DB_NAME="${BASH_REMATCH[5]}"
else
    # Fallback to env vars if parsing fails or URL is local
    DB_USER="${POSTGRES_USER:-narrative}"
    DB_PASS="${POSTGRES_PASSWORD:-narrative_dev_password}"
    DB_HOST="${POSTGRES_HOST:-localhost}"
    DB_PORT="${POSTGRES_PORT:-5432}"
    DB_NAME="${POSTGRES_DB:-narrative_ai}"
fi

OUTPUT_FILE="${BACKUP_DIR}/narrative_ai_backup_${TIMESTAMP}.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "--- Starting Backup: $(date) ---"
echo "Target: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"

if ! command -v pg_dump >/dev/null 2>&1; then
    echo "[ERROR] pg_dump is required but not installed on PATH."
    exit 1
fi

# Export password for pg_dump to use
export PGPASSWORD="$DB_PASS"

# Run pg_dump and compress on the fly
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | gzip > "$OUTPUT_FILE"
echo "[OK] Backup successful: $OUTPUT_FILE"
echo "[OK] Size: $(du -h "$OUTPUT_FILE" | cut -f1)"

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -name "narrative_ai_backup_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "[OK] Cleanup complete."
echo "--- Backup Process Finished: $(date) ---"
