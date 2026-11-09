# Test deployment on the Vivid Relay server (ordered steps for you)

Goal: run the Kundali app on the server where Vivid Relay already runs, at its own sub-domain, without touching Relay.
The Kundali container publishes no ports; the Caddy that Relay already uses forwards the new sub-domain to it.

> I could not look at your Relay server, so steps 2 and 3 tell you what to read there. Paste me the outputs and I will adjust the files.

## Values found on your server (2026-11-08)
Relay folder `/root/wa-gateway`, Caddyfile `/root/wa-gateway/Caddyfile`, Caddy container `wa-gateway-caddy-1`, network `wa-gateway_default`, 3.7 GB RAM (3 GB available), 19 GB free disk. Steps 2 and 3 are therefore done; use these values below.

## 1. Choose the sub-domain
For example `kundali.vividbrandify.com`. Replace it everywhere below if you pick another.

## 2. Log in and look at how Relay runs
```bash
ssh <user>@<relay server ip>
cd /srv/studio/app          # where Relay's docker-compose.yml was (adjust if different)
docker compose ps           # note the caddy container name
docker network ls           # note the network Relay's containers use
free -h; df -h /            # check free RAM and disk (Kundali needs about 1 GB RAM and 2 GB disk)
```
Docs: <https://docs.docker.com/engine/install/ubuntu/> (Docker), <https://docs.docker.com/compose/>

## 3. Find the Caddy network name
```bash
docker inspect <caddy-container-name> --format '{{json .NetworkSettings.Networks}}'
```
The key in that JSON is the network name (often something like `app_default`). Write it down.

## 4. DNS in Cloudflare
Cloudflare dashboard → your domain → DNS → add an **A** record: name `kundali`, value = the server's IP, proxied (orange cloud) the same way `relay` is set up.
Guide: <https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/>

## 5. Get the code onto the server
```bash
cd /srv
git clone -b phase-0-engine https://github.com/prashantmahto2819-droid/kundali.git
cd kundali/deploy
```
(If the repo is private, use a GitHub deploy key or a personal access token: <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys>)

## 6. Create `deploy/.env`
```
CADDY_NETWORK=wa-gateway_default
CORS_ORIGINS=
SUPABASE_URL=https://feipwckrdzkslgbenxtv.supabase.co
# optional: KUNDALI_AUTH=optional|required (default optional)
```
API keys and usage live in a Docker volume (`kundali-data`), so they survive rebuilds. Create a customer key with
`docker exec kundali-api python tools/admin.py create-org "<name>"` then `docker exec kundali-api python tools/admin.py create-key <org_id>` (see README "Access control").

## 7. Start it
```bash
docker compose -f docker-compose.relay.yml up -d --build
docker compose -f docker-compose.relay.yml ps       # wait until it says "healthy"
```
The first build downloads NASA's DE440s ephemeris (about 32 MB), so the server needs outbound internet access.

## 8. Tell Caddy about the sub-domain
Open the Caddyfile Relay uses, append the block from `deploy/Caddyfile.snippet` (with your sub-domain), then:
```bash
docker exec <caddy-container-name> caddy reload --config /etc/caddy/Caddyfile
```
Caddy docs: <https://caddyserver.com/docs/caddyfile/directives/reverse_proxy>
If your Caddyfile is mounted from another path, reload with that path.

## 9. Check
```bash
cd /srv/kundali && ./deploy/smoke.sh https://kundali.vividbrandify.com
```
It must end with `ALL OK`. Open the sub-domain in a browser too. `/health` should say `"backend": "jpl-de440s"`.
Send me the output, especially any `FAIL`/`WARN` line.

## Updating after a new push (run all three every time)
```bash
cd /srv/kundali && git pull && cd deploy && GIT_SHA=$(git rev-parse --short HEAD) docker compose -f docker-compose.relay.yml up -d --build
docker compose -f docker-compose.relay.yml ps          # wait for "healthy"
cd /srv/kundali && ./deploy/smoke.sh https://kundali.vividbrandify.com   # must end with ALL OK
```
If smoke prints FAIL, send `docker logs kundali-api --tail 60`. Roll back with `git checkout <previous commit>` and rebuild.

## 10. Backup, restore test and uptime alert (do this before sharing the link)
The only state on the server is the access database (orgs, API keys, usage, saved people) in the Docker volume `kundali-data`.
1. Daily backup (keeps 30 days in `/srv/backups/kundali`):
   ```bash
   chmod +x /srv/kundali/deploy/*.sh
   /srv/kundali/deploy/backup-relay.sh                      # run once by hand; prints "backup ok: ..."
   (crontab -l 2>/dev/null; echo "25 2 * * * /srv/kundali/deploy/backup-relay.sh >> /var/log/kundali-backup.log 2>&1") | crontab -
   ```
   Off-site copy (optional): create an R2 bucket (<https://developers.cloudflare.com/r2/>), install rclone, configure a remote named `r2`
   (<https://rclone.org/s3/#cloudflare-r2>) and add `R2_BUCKET=<bucket>` to the cron line's environment.
2. Restore test (a backup you never restored is not a backup):
   ```bash
   ls /srv/backups/kundali/
   /srv/kundali/deploy/restore-relay.sh /srv/backups/kundali/<newest file>
   ./deploy/smoke.sh https://kundali.vividbrandify.com
   ```
3. Uptime alert every 5 minutes, sent through a webhook you own (e.g. your Vivid Relay WhatsApp send endpoint).
   Add to `deploy/.env`: `ALERT_URL=...`, `ALERT_TOKEN=...`, `ALERT_TO=91XXXXXXXXXX` (the script POSTs JSON `{"to","text"}`;
   adjust the curl line in `healthwatch.sh` if your endpoint expects other fields). Then:
   ```bash
   /srv/kundali/deploy/healthwatch.sh                       # prints nothing when healthy and unchanged
   (crontab -l 2>/dev/null; echo "*/5 * * * * /srv/kundali/deploy/healthwatch.sh") | crontab -
   ```
   An external monitor is still worth adding (UptimeRobot <https://uptimerobot.com>, free): it alerts even if the whole server is down.

## Rolling back
```bash
cd /srv/kundali/deploy && docker compose -f docker-compose.relay.yml down
```
and remove the Caddy block. Relay is unaffected.


## 11. Build fails with "Temporary failure in name resolution" (pip inside docker build)
The build container could not resolve PyPI. `deploy/docker-compose.relay.yml` now builds with `network: host`
(the build shares the host's network and DNS). If a plain `docker build` still fails, give Docker public DNS:

```bash
cat > /etc/docker/daemon.json <<'EOF2'
{ "dns": ["1.1.1.1", "8.8.8.8"] }
EOF2
systemctl restart docker
```
(BuildKit does not allow `network: host` in compose without an entitlement, so the daemon DNS setting is the fix; the build then resolves PyPI through the daemon's resolver.)
`smoke.sh` needs curl on the host: `apt-get install -y curl`.


## 12. WhatsApp daily updates (panchang / rashifal / vrat alerts) through Vivid Relay

The app sends through Relay's HTTP API: `POST http://gateway:8080/api/sessions/<session>/send` with `Authorization: Bearer <key>` and
`{"to": "91xxxxxxxxxx", "text": "..."}`. Both containers are on `wa-gateway_default`, so the service name `gateway` resolves without
exposing anything. Subscribers verify their number with a 6-digit code sent over WhatsApp; Relay's own STOP keyword also opts them out.

1. In Relay, note the **session name** that is linked to the business WhatsApp number (Sessions page; e.g. `main`).
2. Create an API key: Relay → Developer → API keys → New key (a `vr_…` key); or use the master `API_KEY` from `/root/wa-gateway/.env`.
   Never paste the key into chat or commit it.
3. Add to `/srv/kundali/deploy/.env` (one line each, no quotes):
   ```
   RELAY_URL=http://gateway:8080
   RELAY_SESSION=main
   RELAY_API_KEY=vr_xxxxxxxxxxxxxxxxx
   KUNDALI_NOTIFY=1
   ```
4. Restart: `cd /srv/kundali/deploy && docker compose -f docker-compose.relay.yml up -d` (no rebuild needed for env changes).
5. Check: `docker compose -f docker-compose.relay.yml logs --tail 5 kundali-api` should show `WhatsApp notify worker running`.
   Test from the site: Kundali tab → "WhatsApp पर रोज़ का अपडेट" → your number → "कोड भेजिए"; the code must arrive within a few seconds.
   If it does not: `docker exec kundali-api python -c "import urllib.request;print(urllib.request.urlopen('http://gateway:8080/health').read())"`
   shows whether the gateway is reachable; a 401 in the card means the key is wrong, a 404 means the session name is wrong.
6. Subscribers live in the same SQLite file as the access store (`/srv/data/access.sqlite`, tables `wa_subs`, `wa_log`), so the
   existing backup covers them. The worker checks every minute, sends once per subscriber per local day (and the weekly list on the
   chosen weekday), retries next minute on a failed send, and records the last error on the row.


## 13. Two-way WhatsApp bot (people message the number and get panchang / rashifal / kundali back)

Relay forwards every inbound message to the app, the app answers through the same Relay session. Commands: पंचांग [शहर], राशिफल [राशि],
कुंडली DD-MM-YYYY HH:MM शहर, व्रत, मुहूर्त विवाह, शुरू, बंद, मदद (English equivalents work too).

1. Relay → Developer → **Webhooks** → New webhook:
   - URL: `https://kundali.vividbrandify.com/v1/notify/webhook` (the public URL — Relay refuses private docker addresses for user webhooks)
   - Events: `message` only
   - Copy the **secret** Relay shows.
2. Add to `/srv/kundali/deploy/.env`: `RELAY_WEBHOOK_SECRET=<that secret>` (the sender settings from §12 must also be present).
3. `cd /srv/kundali/deploy && docker compose -f docker-compose.relay.yml up -d`
4. Test: send "मदद" to the business number from any phone; the menu must come back within a few seconds.
   `docker exec kundali-api python -c "import sqlite3;print(sqlite3.connect('/srv/data/access.sqlite').execute('select * from wa_inbox order by at desc limit 5').fetchall())"` lists handled messages.
   A 401 in Relay's webhook log means the secret differs; "duplicate" entries are Relay retries and are expected.
5. Keep Relay's own STOP keyword on; the bot also honours बंद/stop, and "शुरू"/"start" turns the daily message on (06:30, Delhi — the
   person refines city/time/birth details on the website).


## 14. AI providers (chat, palm photo) — free tiers first, any mix, automatic fallback

The app tries providers in `AI_PROVIDERS` order and falls back to the next on error/quota; without any key it still answers from
its own material (retrieval). Put the keys in `/srv/kundali/deploy/.env` and `docker compose -f docker-compose.relay.yml up -d`.

| Provider | Free? | Key | .env lines |
|---|---|---|---|
| Google Gemini | free tier (daily limit), vision ✓ | https://aistudio.google.com/apikey | `GEMINI_API_KEY=…` (model `GEMINI_MODEL=gemini-2.0-flash`) |
| Groq | free tier, very fast | https://console.groq.com/keys | `GROQ_API_KEY=gsk_…` (`GROQ_MODEL=llama-3.3-70b-versatile`; vision: `GROQ_VISION_MODEL=llama-3.2-11b-vision-preview` if still offered) |
| OpenRouter (DeepSeek, Llama, Qwen `:free`) | free models | https://openrouter.ai/keys | `OPENROUTER_API_KEY=sk-or-…` (`OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free`) |
| DeepSeek direct | paid, cheap | https://platform.deepseek.com/api_keys | `DEEPSEEK_API_KEY=…` |
| Ollama (your own PC/server) | free, unlimited | — | `OLLAMA_URL=http://<tailscale-ip>:11434` `OLLAMA_MODEL=qwen2.5:7b` `OLLAMA_VISION_MODEL=llama3.2-vision:11b` |
| OpenAI / Anthropic | paid | platform.openai.com / console.anthropic.com | `OPENAI_API_KEY=…` / `ANTHROPIC_API_KEY=…` |
| any OpenAI-compatible | — | — | `AI_BASE_URL=https://…/v1` `AI_API_KEY=…` `AI_MODEL=…` |

Order example (free first, paid last): `AI_PROVIDERS=gemini,groq,openrouter,ollama,deepseek`. Quota per user per day: `AI_DAILY_QUOTA=30`
(palm photo counts 2). Check: `GET /v1/ai/status` lists the active providers; the "पूछिए" tab shows the chain. The WhatsApp bot also
answers free-text questions through the same chain when a provider is configured.

Ollama on the Z440: `curl -fsSL https://ollama.com/install.sh | sh`, `ollama pull qwen2.5:7b`, run with `OLLAMA_HOST=0.0.0.0`, reach it from
Hetzner over Tailscale (do not expose port 11434 publicly). CPU-only 7B is slow (30–60 s per answer) — keep Gemini/Groq first and Ollama last.

### 14a. OpenAI as the primary provider (what the owner chose) + Groq
1. https://platform.openai.com/api-keys → Create new secret key (billing must be enabled; gpt-4o-mini costs about ₹0.02–0.05 per answer).
2. https://console.groq.com/keys → Create API Key (free tier; fast fallback).
3. `/srv/kundali/deploy/.env`:
   ```
   OPENAI_API_KEY=sk-...
   GROQ_API_KEY=gsk_...
   AI_PROVIDERS=openai,groq
   OPENAI_MODEL=gpt-4o-mini            # or gpt-4.1-mini / gpt-4o for better Hindi
   EMBED_PROVIDER=openai               # semantic search for पूछिए / AI chat (text-embedding-3-small)
   AI_WA_SUMMARY=1                     # one AI line in each subscriber's daily WhatsApp (one call per subscriber per day)
   ```
4. Semantic search index (once, and after editing knowledge/rules): `docker exec -e OPENAI_API_KEY=sk-... kundali-api python tools/build_embeddings.py` (≈ ₹1–2),
   then `docker cp kundali-api:/srv/data/embeddings.json /srv/kundali/data/` and rebuild — or run it on your PC inside the repo and commit `data/embeddings.json`.
5. UI in another language (draft, AI-translated; review by a speaker): `python3 tools/ai_translate.py te` (te kn mr gu bn ta ml …) → `data/i18n_te.json`;
   commit and rebuild — a language dropdown appears beside the English button when any pack exists.
6. Admin rule extraction from a text passage: `POST /v1/ai/extract_rules` with `X-Admin-Key`, `{"text": "...", "source": "BPHS 24.3", "save": true}` → `data/rules/drafts/`.

## 15. Astrologer consultation and wallet

`KUNDALI_PAID=0` (default) keeps everything free: seekers send requests, astrologers get a WhatsApp ping (Relay) and answer in the thread.
Admin calls use header `X-Admin-Key: $KUNDALI_ADMIN_KEY` (set it in .env). Add an astrologer:
```
curl -s -X POST https://kundali.vividbrandify.com/v1/consult/admin -H "Content-Type: application/json" -H "X-Admin-Key: $KUNDALI_ADMIN_KEY" \
  -d '{"action":"astrologer","astrologer":{"name":"Pt. Ramesh Sharma","name_hi":"पं. रमेश शर्मा","phone":"91XXXXXXXXXX","languages":["हिंदी","English"],"specialities":["विवाह","करियर"],"experience_years":15,"bio_hi":"…","price_chat":199,"price_call":499,"price_report":999}}'
```
To charge: `KUNDALI_PAID=1`, `KUNDALI_UPI_ID=yourname@upi`; seekers pay by UPI and send the reference; you credit it:
`{"action":"topup","phone":"91…","amount":500,"ref":"UPI-ref","note":"verified"}`. Requests debit the wallet on creation. `{"action":"overview"}` lists open requests and top-ups.


## 16. Owner admin panel

`https://kundali.vividbrandify.com/admin.html` — enter `KUNDALI_ADMIN_KEY` (from deploy/.env; it stays in that browser's localStorage).
Tabs: summary KPIs + test WhatsApp send; subscribers (stop/start, mark verified, last error); sent/received message logs; astrologers
(add/edit) + open consultations (read, reply as the astrologer, close); wallet top-ups; AI providers and usage, rule extraction from a
text passage; festival overrides per year (add / move / remove). Owner edits are written next to the SQLite file
(`/srv/data/overrides/`, `/srv/data/rules_drafts/`) so they survive rebuilds; the repo's `data/overrides/` stays the default.
