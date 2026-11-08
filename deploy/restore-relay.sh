#!/usr/bin/env bash
# Restore the access database from a backup made by backup-relay.sh:
#   /srv/kundali/deploy/restore-relay.sh /srv/backups/kundali/access-20261108T022500Z.sqlite.gz
# Stops the API, replaces the file in the volume, starts the API. The current DB is kept as access.sqlite.before-restore.
set -euo pipefail
f="${1:?usage: restore-relay.sh <backup.sqlite.gz>}"
cd "$(dirname "$0")"
tmp=$(mktemp); gunzip -c "$f" > "$tmp"
python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); assert c.execute('pragma integrity_check').fetchone()[0]=='ok'; print('backup integrity ok')" "$tmp"
docker compose -f docker-compose.relay.yml stop kundali-api
docker run --rm -v kundali-data:/data -v "$tmp":/restore.sqlite alpine sh -c 'cp /data/access.sqlite /data/access.sqlite.before-restore 2>/dev/null; cp /restore.sqlite /data/access.sqlite'
docker compose -f docker-compose.relay.yml start kundali-api
rm -f "$tmp"
echo "restored from $f"
