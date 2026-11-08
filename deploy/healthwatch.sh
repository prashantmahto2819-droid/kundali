#!/usr/bin/env bash
# Every 5 minutes: check /health; on failure (or recovery) send one alert through a webhook you own
# (for example a Vivid Relay WhatsApp send endpoint, or any URL that accepts a POST with a "text" field).
# Cron:   */5 * * * *  /srv/kundali/deploy/healthwatch.sh
# Config in /srv/kundali/deploy/.env:  ALERT_URL=https://...   ALERT_TOKEN=...   ALERT_TO=91XXXXXXXXXX
set -uo pipefail
cd "$(dirname "$0")"; [ -f .env ] && set -a && . ./.env && set +a
BASE="${KUNDALI_URL:-https://kundali.vividbrandify.com}"
STATE=/var/tmp/kundali-health.state
ok=0
if curl -fsS --max-time 20 "$BASE/health" | grep -q '"status":"ok"'; then ok=1; fi
prev=$(cat "$STATE" 2>/dev/null || echo 1)
echo "$ok" > "$STATE"
[ "$ok" = "$prev" ] && exit 0                      # alert only on change (down -> up, up -> down)
msg="Kundali $BASE is $([ "$ok" = 1 ] && echo 'UP again' || echo 'DOWN') at $(date -u +%FT%TZ)"
logger -t kundali-health "$msg" || true
if [ -n "${ALERT_URL:-}" ]; then
  curl -fsS --max-time 20 -X POST "$ALERT_URL" -H "Authorization: Bearer ${ALERT_TOKEN:-}" -H 'Content-Type: application/json' \
       -d "{\"to\":\"${ALERT_TO:-}\",\"text\":\"$msg\"}" >/dev/null || echo "alert send failed"
fi
echo "$msg"
