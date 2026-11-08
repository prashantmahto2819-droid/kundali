#!/usr/bin/env bash
# Daily backup of the Kundali access database (orgs, API keys, usage, saved people) on the Relay server.
# The DB is SQLite inside the Docker volume "kundali-data" (/srv/data/access.sqlite in the container).
# Cron (as root):   25 2 * * *  /srv/kundali/deploy/backup-relay.sh >> /var/log/kundali-backup.log 2>&1
# Optional off-site copy: set R2_BUCKET and configure an rclone remote named "r2" (Cloudflare R2).
set -euo pipefail
DEST="${BACKUP_DIR:-/srv/backups/kundali}"
KEEP_DAYS="${KEEP_DAYS:-30}"
mkdir -p "$DEST"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
out="$DEST/access-${stamp}.sqlite"
# consistent snapshot via SQLite's online backup API (safe while the app is running)
docker exec kundali-api python -c "import sqlite3; s=sqlite3.connect('/srv/data/access.sqlite'); d=sqlite3.connect('/tmp/backup.sqlite'); s.backup(d); d.close()"
docker cp kundali-api:/tmp/backup.sqlite "$out"
docker exec kundali-api rm -f /tmp/backup.sqlite
gzip -f "$out"
find "$DEST" -name 'access-*.sqlite.gz' -mtime +"$KEEP_DAYS" -delete
if [ -n "${R2_BUCKET:-}" ] && command -v rclone >/dev/null; then
  rclone copy "$out.gz" "r2:${R2_BUCKET}/kundali/" && rclone delete "r2:${R2_BUCKET}/kundali" --min-age "${KEEP_DAYS}d"
fi
echo "backup ok: $out.gz ($(du -h "$out.gz" | cut -f1))"
