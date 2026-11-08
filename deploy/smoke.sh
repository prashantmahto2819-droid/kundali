#!/usr/bin/env bash
# Smoke test a running instance:  deploy/smoke.sh https://kundali.example.com
set -euo pipefail
BASE="${1:?usage: smoke.sh BASE_URL}"
fail() { echo "FAIL: $*"; exit 1; }
j() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)"; }

h=$(curl -fsS "$BASE/health") || fail "health unreachable"
echo "health: $h"
echo "$h" | j "d['status']" | grep -qx ok || fail "status not ok"
echo "$h" | j "d['production_ready']" | grep -qx True || echo "WARN: backend is not the JPL production backend"

P='{"date":"1990-05-17","time":"06:45","tz":"Asia/Kolkata","lat":23.18,"lon":79.99}'
curl -fsS -XPOST "$BASE/v1/chart" -H 'Content-Type: application/json' -d "$P" | j "d['lagna']['sign_name']" | grep -qx Vrishabha || fail "chart lagna"
curl -fsS -XPOST "$BASE/v1/report" -H 'Content-Type: application/json' -d "$P" | grep -q "कुंडली रिपोर्ट" || fail "report"
curl -fsS -XPOST "$BASE/v1/tarot" -H 'Content-Type: application/json' -d '{"spread":"three","seed":1}' | j "len(d['cards'])" | grep -qx 3 || fail "tarot"
curl -fsS "$BASE/v1/places?q=jabalpur" | j "d['results'][0]['name']" | grep -qx Jabalpur || fail "places"
curl -fsS -o /dev/null "$BASE/" || fail "web page"
echo "ALL OK"
