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
# optional: KUNDALI_AUTH=optional|required (default optional), SUPABASE_URL=https://<project>.supabase.co
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

## 10. Later (before real customers)
Daily backup and uptime alert: steps 8 and 9 in `docs/OPS.md`. Restore test before the first paying customer.

## Rolling back
```bash
cd /srv/kundali/deploy && docker compose -f docker-compose.relay.yml down
```
and remove the Caddy block. Relay is unaffected.
