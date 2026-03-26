#!/bin/bash
# NOTE: Production paths use /opt/omaha-cloud/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/sync_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

cd "$PROJECT_ROOT" || exit 1

echo "=== Sync started at $(date) ===" >> "$LOG_FILE"
python3 deployment/sync_tushare_data.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "=== Sync finished at $(date) with exit code $EXIT_CODE ===" >> "$LOG_FILE"

exit $EXIT_CODE
