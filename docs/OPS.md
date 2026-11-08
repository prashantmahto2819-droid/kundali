# Operations: one VPS + Cloudflare + Supabase

Architecture: Cloudflare (website, CDN, R2 storage, Tunnel) → one VPS (engine API in Docker) → Supabase (Postgres, Auth).
The VPS publishes **no ports**; `cloudflared` makes an outbound tunnel to Cloudflare, so the server IP stays hidden.

## Steps you must do yourself (in order)

1. **VPS:** an India-region Ubuntu 22.04/24.04 VPS, about 4 vCPU / 8 GB RAM to start. Install Docker: <https://docs.docker.com/engine/install/ubuntu/>
2. **Cloudflare Tunnel:** Zero Trust → Networks → Tunnels → create a tunnel, copy the token, add a public hostname (e.g. `api.yourdomain.com` → `http://api:8000`). Guide: <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/>
3. **Supabase:** create a project in a nearby region, then run `supabase/migrations/0001_init.sql` in the SQL editor (staging project first). Docs: <https://supabase.com/docs/guides/database/overview>
4. **Copy the repo to the VPS**, create `deploy/.env`:
   ```
   TUNNEL_TOKEN=...your tunnel token...
   CORS_ORIGINS=https://yourdomain.com
   ```
5. **Start:** `cd deploy && docker compose up -d --build`
6. **Check:** open `https://api.yourdomain.com/health`. It must say `"backend": "jpl-de440s"` and `"production_ready": true`.
7. **Frontend:** deploy `web/` (and `data/knowledge/`) on Cloudflare Pages: <https://developers.cloudflare.com/pages/>. Open the page with `?api=https://api.yourdomain.com`.
8. **Daily backup:** create an R2 bucket (<https://developers.cloudflare.com/r2/>), install `rclone` and `postgresql-client`, configure an rclone remote named `r2` (<https://rclone.org/s3/#cloudflare-r2>), then add the cron line from `deploy/backup.sh`.
9. **Uptime alert:** add an HTTPS monitor on `/health` with e-mail/WhatsApp alert, e.g. UptimeRobot <https://uptimerobot.com> or Cloudflare Health Checks <https://developers.cloudflare.com/health-checks/>.

## Before the first paying customer
- Test a restore from backup (a backup you never restored is not a backup).
- Compare the engine against a trusted reference on the 50 test charts (see ROADMAP, Phase 0 gate).
- Have a lawyer review privacy policy and terms (India DPDP Act 2023; birth details and palm photos are personal data).
