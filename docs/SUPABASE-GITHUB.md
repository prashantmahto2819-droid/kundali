# Supabase ↔ GitHub (no manual SQL after setup)

Database changes live in `supabase/migrations/*.sql`. Once one of the two options below is on, pushing a new
migration file to GitHub applies it to Supabase automatically. `0001_init.sql` is idempotent, so it is safe even if
it was already pasted into the SQL editor by hand.

## Option A — Supabase's own GitHub integration (no tokens to copy)
1. Open https://supabase.com/dashboard → your Kundali project → **Project Settings → Integrations**.
2. **GitHub Integration → Authorize GitHub**, then on GitHub click **Authorize Supabase** (allow repo `prashantmahto2819-droid/kundali`).
3. Choose the repository `prashantmahto2819-droid/kundali`.
4. **Working directory**: `.`  (the `supabase/` folder is at the repo root).
5. Turn on **Deploy to production**. Leave **Automatic branching** off unless you are on a paid plan and want preview databases.
6. Set the production branch to `phase-0-engine` if the form offers it; otherwise migrations deploy when work is merged to `main`.
7. **Enable integration**.
Docs: https://supabase.com/docs/guides/deployment/branching/github-integration

## Option B — GitHub Actions (works on every plan, deploys from `phase-0-engine` and `main`)
1. Create a token: https://supabase.com/dashboard/account/tokens → **Generate new token** (name it `github-kundali`).
2. Note the project ref (Project Settings → General → Project ID) and the database password (Project Settings → Database; reset it there if forgotten).
3. On GitHub: https://github.com/prashantmahto2819-droid/kundali/settings/secrets/actions → **New repository secret**, three times:
   `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_ID`, `SUPABASE_DB_PASSWORD`.
4. Run it once by hand: https://github.com/prashantmahto2819-droid/kundali/actions/workflows/supabase-migrate.yml → **Run workflow**.
   After that it runs by itself on every push that touches `supabase/`.

## Adding a change later
Create `supabase/migrations/0002_<what>.sql` (next number), write idempotent SQL (`if not exists`, `drop policy if exists …`), commit and push. Nothing to do in the Supabase dashboard.

Auth settings (site URL, redirect URLs, Google login) are not pushed by either option — set them once in the dashboard
(Authentication → URL Configuration). The server only needs `SUPABASE_URL` and the publishable key; never put the
service-role key in GitHub.
