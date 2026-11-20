# One-time owner setup (everything the code needs from you)

Do these in order. Never paste keys or passwords into chat — only into the places named here.

## 1. Server update (Hetzner, /srv/kundali)
```bash
cd /srv/kundali && git pull && cd deploy && GIT_SHA=$(git rev-parse --short HEAD) docker compose -f docker-compose.relay.yml up -d --build
cd /srv/kundali && ./deploy/smoke.sh https://kundali.vividbrandify.com      # must end with ALL OK
```

## 2. Automatic updates from GitHub (then step 1 is never needed again)
1. On the server: `ssh-keygen -t ed25519 -f ~/.ssh/gh_deploy -N "" && cat ~/.ssh/gh_deploy.pub >> ~/.ssh/authorized_keys`
2. `cat ~/.ssh/gh_deploy` → copy the private key.
3. https://github.com/prashantmahto2819-droid/kundali/settings/secrets/actions → New repository secret: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`.
4. https://github.com/prashantmahto2819-droid/kundali/actions/workflows/deploy.yml → Run workflow.

## 3. Keys and settings in /srv/kundali/deploy/.env (then update the server)
| Setting | Where to get it |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `GROQ_API_KEY` | https://console.groq.com/keys (free) |
| `GEMINI_API_KEY` (optional) | https://aistudio.google.com/apikey (free) |
| `AI_PROVIDERS=openai,groq` | order in which AI services are tried |
| `KUNDALI_ADMIN_KEY` | any long random text; opens /admin.html |
| `RELAY_SESSION`, `RELAY_API_KEY`, `KUNDALI_NOTIFY=1` | your Vivid Relay dashboard (session name + API key) |
| `RELAY_WEBHOOK_SECRET` | make a webhook in Relay pointing to `https://kundali.vividbrandify.com/v1/notify/webhook`, copy its secret |
| `KUNDALI_BRAND_NAME`, `KUNDALI_BRAND_TAGLINE` | text on the daily panchang image |
| `KUNDALI_CONTACT_EMAIL` | email shown on /privacy and /terms |
| `TWA_PACKAGE`, `TWA_SHA256` | after the Play Store step (docs/PLAY-STORE.md) |

## 4. Google Search
https://search.google.com/search-console → add the site → Sitemaps → `https://kundali.vividbrandify.com/sitemap.xml` → Submit.

## 5. Play Store
Follow docs/PLAY-STORE.md (PWABuilder → .aab → Play Console; privacy URL: https://kundali.vividbrandify.com/privacy).

## 6. Supabase
Already automatic: new files in `supabase/migrations/` apply on push (GitHub Action "Supabase migrations").
Once: Supabase dashboard → Authentication → URL Configuration → Site URL `https://kundali.vividbrandify.com`.
