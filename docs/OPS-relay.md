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
`smoke.sh` needs curl on the host: `apt-get install -y curl`.
