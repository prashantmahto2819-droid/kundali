#!/usr/bin/env bash
# Nightly backup of the kundali data volume (SQLite + owner overrides + rule drafts) to /srv/backups/kundali/<date>.tar.gz
# Keeps the last 30. Install:  (crontab -l; echo "20 3 * * * /srv/kundali/deploy/backup.sh >> /var/log/kundali-backup.log 2>&1") | crontab -
set -euo pipefail
OUT=${1:-/srv/backups/kundali}
mkdir -p "$OUT"
STAMP=$(date +%F)
# consistent SQLite copy via the container's python (sqlite backup API), then the rest of the volume
docker exec kundali-api python - <<'PY'
import sqlite3, os
src = sqlite3.connect(os.environ.get("KUNDALI_DB", "/srv/data/access.sqlite"))
dst = sqlite3.connect("/srv/data/access.backup.sqlite")
src.backup(dst); dst.close(); src.close()
PY
docker run --rm -v kundali-data:/data -v "$OUT":/out alpine sh -c "cd /data && tar czf /out/kundali-$STAMP.tar.gz access.backup.sqlite overrides rules_drafts 2>/dev/null || tar czf /out/kundali-$STAMP.tar.gz access.backup.sqlite"
ls -1t "$OUT"/kundali-*.tar.gz | tail -n +31 | xargs -r rm -f
echo "$(date -Is) backup ok: $OUT/kundali-$STAMP.tar.gz ($(du -h "$OUT/kundali-$STAMP.tar.gz" | cut -f1))"
