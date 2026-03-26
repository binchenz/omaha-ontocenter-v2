#!/bin/bash
# NOTE: Production paths use /opt/omaha-cloud/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/omaha_backup_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL database
pg_dump -h localhost -U omaha_user omaha_db | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup successful: $BACKUP_FILE"
    # Keep only last 7 days
    find "$BACKUP_DIR" -name "omaha_backup_*.sql.gz" -mtime +7 -delete
else
    echo "Backup failed"
    exit 1
fi
