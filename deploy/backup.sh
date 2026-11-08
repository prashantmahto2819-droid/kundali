#!/usr/bin/env bash
# Daily Postgres backup to Cloudflare R2 (via rclone). Run from cron, e.g.:
#   30 2 * * *  /opt/kundali/deploy/backup.sh >> /var/log/kundali-backup.log 2>&1
# Needs: DATABASE_URL (Supabase connection string), an rclone remote named "r2"
# pointing to your R2 account, and R2_BUCKET.
set -euo pipefail
: "${DATABASE_URL:?set DATABASE_URL}" "${R2_BUCKET:?set R2_BUCKET}"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
pg_dump --no-owner --format=custom "$DATABASE_URL" | rclone rcat "r2:${R2_BUCKET}/db/kundali-${stamp}.dump"
# keep 30 days
rclone delete "r2:${R2_BUCKET}/db" --min-age 30d
echo "backup ok: kundali-${stamp}.dump"
