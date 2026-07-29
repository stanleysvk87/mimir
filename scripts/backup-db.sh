#!/usr/bin/env bash
# Periodic SQLite backup for Mímir -- safe under WAL mode because it uses
# sqlite3's own ".backup" command (a proper online backup, not a raw file
# copy that could grab a half-written page) instead of copying the file
# straight off the live volume.
set -euo pipefail

BACKUP_DIR="${MIMIR_BACKUP_DIR:-$HOME/mimir-restore-points}"
KEEP=30
CONTAINER="mimir-backend-1"
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

# No standalone sqlite3 CLI in the python:3.12-slim image -- use the
# stdlib sqlite3 module's VACUUM INTO instead, same online-backup
# guarantee (safe under WAL, never grabs a half-written page).
docker exec "$CONTAINER" python3 -c "
import sqlite3
sqlite3.connect('/data/mimir.db').execute(\"VACUUM INTO '/data/backup-tmp.db'\")
"
docker cp "$CONTAINER:/data/backup-tmp.db" "$BACKUP_DIR/mimir-$STAMP.db"
docker exec "$CONTAINER" rm -f /data/backup-tmp.db

# Keep only the most recent $KEEP backups.
ls -1t "$BACKUP_DIR"/mimir-*.db 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f

echo "Backed up to $BACKUP_DIR/mimir-$STAMP.db"
