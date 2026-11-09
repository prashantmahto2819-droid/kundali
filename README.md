# kundali

A commercial-grade Vedic astrology platform: birth chart (kundali), dasha, panchang, numerology, tarot, palmistry and vastu, with a learning layer that explains the *what, why and how* of every result.

Status: **Phase 0/1**: calculation engine v0.2 (chart, dasha, panchang, sunrise-based muhurta, vargas D2-D12, numerology, ashtakoota matching) + dev web page. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Principles
- **Calculation is astronomy; interpretation is tradition.** Every interpretation carries a source and a review status; the UI says "according to the śāstra", never "will happen".
- **No AGPL in the product.** Positions come from NASA JPL data via Skyfield (production) – not Swiss Ephemeris.
- **Rules are data** (`data/rules/*.json`), so scholars can improve them without code.
- **Multi-tenant** from the start (`supabase/migrations/0001_init.sql`).

## Layout
```
engine/      Python calculation engine (jyotish/), API (app.py), dev server, tests
data/        knowledge base (planets, houses) and rules
web/         dev web page (North-Indian chart, click-to-learn)
supabase/    database schema with Row Level Security
deploy/      Dockerfile, docker-compose (Cloudflare Tunnel), backup script
docs/        ROADMAP, OPS (how to deploy on one VPS)
```

## Run locally (no installs needed)
```bash
cd engine
KUNDALI_BACKEND=analytic python devserver.py 8000   # open http://127.0.0.1:8000
python -m pytest                                    # tests
```
The `analytic` backend is for development only (≈0.01° Sun/Moon, up to ~0.3° outer planets).
For production use the JPL backend: `pip install -r requirements.txt` (it downloads `de440s.bsp`).

## API
`POST /v1/chart` with `{"date":"1990-05-17","time":"06:45","tz":"Asia/Kolkata","lat":23.1815,"lon":79.9864}`
returns lagna, planets (sign, degree, house, nakshatra, pada, retrograde, dignity), houses, navamsa, panchang,
Vimshottari dasha (to antardasha) with the running period, yogas with their *why*, and matched rules with their sources.
`POST /v1/numerology` with `{"date":"1990-05-17","name":"Prashant Mahto"}` returns moolank, bhagyank, namank (Chaldean and Pythagorean), Lo Shu grid and personal year.
The chart response also carries `day` (sunrise/sunset, Vedic vara, Rahu Kaal, Yamaganda, Gulika, Abhijit, Choghadiya) and `vargas` (D1, D2, D3, D4, D7, D9, D10, D12).
`/v1/chart` also returns `ashtakavarga` (BAV per planet and SAV by house, with strong/medium/weak bands; tables self-checked to the classical 337 total).

`/v1/chart` also returns `gochara` for `as_of` (default now): current sidereal positions, house from Moon and Lagna, classical favourable-house check combined with ashtakavarga points, and Sade Sati / Ashtama Shani. Vedha is not applied yet.

`POST /v1/report` (same body as `/v1/chart`) returns a printable Hindi HTML report (charts as inline SVG, planets, panchang, dasha, ashtakavarga, gochara, yogas). The web page has a button that opens it; print to PDF from the browser, or run `python tools/make_pdf.py DATE TIME TZ LAT LON out.pdf [NAME]` where Playwright/Chromium is installed (Chromium shapes Devanagari correctly).

`POST /v1/vastu` with `{"items":[{"room":"kitchen","direction":"SE"}]}` (or `degrees` instead of `direction`) rates each room against traditional direction guidance and suggests simple, non-structural fixes; `GET /v1/vastu/catalog` lists rooms and directions. Draft, original wording; schools differ.

`POST /v1/palm` with `{"choices":{"life_length":"long","hand_shape":"water"}}` turns a guided palm checklist into a Hindi reading; `GET /v1/palm/catalog` lists the 16 features, where to look and the options. It never predicts lifespan or illness. Photo analysis (vision model, with consent) is a later step.

`/v1/chart` also returns `lalkitab` (draft; two house views, traditional remedies with disclaimer). It also returns `relations` (neecha-bhanga with the exact conditions met, conjunctions, combustion, aspects by planet and by house; draft). It also returns `strength`: most of Shadbala in virupas (sthana incl. saptavargaja/ojayugma/drekkana, dig, kala: natonnata/paksha/tribhaga/vara/hora/ayana, naisargika, drik; cheshta only for Sun and Moon). Missing: cheshta of the five planets, abda, masa, yuddha. It is flagged `complete: false` and lists `assumptions`; rank excludes cheshta; do not compare totals with the classical minimum tables.

`POST /v1/varshaphal` (chart fields plus `year`, optional `return_lat/return_lon/return_tz`) returns the solar-return chart and muntha for that year.

`POST /v1/match` with `{"boy": {...}, "girl": {...}}` (same birth fields as `/v1/chart`) returns the 36-point ashtakoota score with per-koota detail and confidence, plus a manglik comparison.

`POST /v1/tarot` with `{"spread": "single|three|celtic", "question": "...", "seed": 7, "reversals": true}` draws from the 78-card deck (own wording, draft, Hindi + English). Omit `seed` for a random draw; the same seed gives the same draw.

`GET /v1/places?q=bombay&limit=8` searches 151 curated cities (English, Hindi, old names) and returns lat/lon/tz. Coordinates are hand-entered and approximate (~1 km); small towns need manual lat/lon. The web form uses the same list (`data/places.json`).
`GET /health` reports the active backend and whether it is production-ready.

## Known limitations (v0.1)
- Lahiri ayanamsa only; the constant is a development value to be verified against a reference.
- Whole-sign houses only; mean node for Rahu/Ketu. Sunrise/sunset use the NOAA equations (about +-1 minute, no altitude correction).
- Vargas implemented: D1, D2, D3, D4, D7, D9, D10, D12 (Parashari rules); D16-D60 later. Numerology takes Latin-script names only.
- Matching: Varna, Tara, Graha Maitri, Bhakoot and Nadi follow widely agreed rules; **Vashya, Yoni and Gana tables are drafts** (sources differ) and are flagged in the output. Parihara (cancellation) is not applied automatically.
- Rule library is a tiny **sample**; all rules are `draft` until a scholar reviews them.
- The JPL backend code path is written but was not run in the build environment (no network); run `engine/tools/compare_backends.py` on a connected machine.

License: not decided yet (proprietary by default).

## Deploying
- Test on the Vivid Relay server behind its Caddy: `docs/OPS-relay.md` (ordered steps) with `deploy/docker-compose.relay.yml`, `deploy/Caddyfile.snippet`, `deploy/smoke.sh`.
- Standalone VPS with Cloudflare Tunnel: `docs/OPS.md`.
- The FastAPI app also serves `web/` and `data/` (set `KUNDALI_SERVE_WEB=0` to turn off). The FastAPI/Docker path has not been run yet (no network here); the dev server and `smoke.sh` have.

## Access control & API keys (multi-tenant core)
Every `/v1/*` request can be tied to an **organisation** with a plan and a daily limit.

| Env var | Meaning |
|---|---|
| `KUNDALI_AUTH` | `off` (default, dev) · `optional` (public web page works anonymously, a bad key is rejected) · `required` (API customers) |
| `KUNDALI_DB` | SQLite file for orgs/keys/usage (default `kundali_access.db`; Postgres/Supabase later) |

Send the key as `X-API-Key: kd_...`. Responses carry `X-RateLimit-Limit` / `X-RateLimit-Remaining`; over the limit gives `429` + `Retry-After`. Keys are stored only as SHA-256 hashes (shown once at creation). `/health` is never guarded.

```bash
cd engine
python tools/admin.py create-org "Acme"
python tools/admin.py create-key <org_id>      # prints the key once
python tools/admin.py usage <org_id>
python tools/admin.py set-plan <org_id> pro    # free 200/day, pro 20000/day, unlimited
python tools/admin.py revoke <key_prefix>
```

## Saved people (per organisation)
Needs a valid API key (even with `KUNDALI_AUTH=off`). Only birth data is stored; charts are recomputed on demand. Each org sees only its own records (max 500).

| Call | What |
|---|---|
| `POST /v1/people` | `{name, date, time, tz, lat, lon, place?, note?}` → 201 + id |
| `GET /v1/people` | list |
| `GET /v1/people/{id}` · `DELETE /v1/people/{id}` | read / remove |
| `GET /v1/people/{id}/chart` | full chart of the saved person |

### Astrologer tools
`PUT /v1/people/{id}` updates `name`, `place` or the private `note` (2000 chars). `GET/PUT /v1/me` reads/sets the org's profile (`brand_name`, `phone`, `website`, `address`, `line`); when a signed-in user or API key calls `POST /v1/report`, that profile is printed at the top of the report. The web page shows a note box per saved person and a profile form under "मेरी कुंडलियाँ".

`POST /v1/rectify` (birth-time rectification aid): body = birth details + `range_min` (5–720, default 120), `step_min` (1–10, default 2), optional `events: [{type, year, month?}]` with type in marriage / child / job / property / travel / education. Returns the stretches around the given time within which Lagna, navamsa Lagna and Moon nakshatra stay the same, and, with events, a score per stretch (running dasha/antardasha lords at the event connected to the event's houses) plus the top 5. Draft rule set (`docs/REVIEW.md` A.17); it narrows a time, it does not prove it. Web: card under the sensitivity table in the summary sub-tab.

## Vastu from a floor plan
`POST /v1/vastu/plan` `{filename, content_b64}` converts an uploaded plan to a PNG: PDF page 1 (pypdfium2), AutoCAD **DXF** (built-in reader for LINE / LWPOLYLINE / POLYLINE / CIRCLE / ARC, rendered with Pillow; DWG must be saved as DXF or PDF first), or PNG/JPG. `POST /v1/vastu/zones` `{polygon: [[x,y]…], north_angle, rooms: [{room, x, y}], lat?, lon?, place?}` returns, per marked room, the compass bearing from the plot centre, the 16-zone (22.5°) placement, the 8-direction, the 81-pada Vastu Purusha Mandala cell and devata, a rating and suggestions; plus the degree wheel for drawing, cut-corner detection on the north-aligned bounding box (skipped for skewed plots), and a printable page at `POST /v1/vastu/plan/report`. `GET /v1/vastu/plan/catalog` lists rooms, zones and devatas. The web card draws the plan on a canvas (plot boundary, rooms, north arrow by click or phone compass, 16-zone wheel with degree ticks, 81-pada grid) and shows the location on an OpenStreetMap map (Leaflet, loaded on demand) with the 16 sectors and the plan's orientation. Zone data: `data/knowledge/vastu_zones.json` (draft; `docs/REVIEW.md` E).

## Palmistry from a photo (traced)
`POST /v1/palm/trace` `{landmarks: {wrist, index, middle, ring, little, thumb: [x,y]}, lines: {life, head, heart, fate?, sun?: [[x,y]…]}, marks?: [{line, type, x, y}], extras?: {union_lines, bracelets, travel_lines, girdle_of_venus: n}, choices?: {…}}`. The photo never leaves the browser; only points arrive. The engine (`engine/jyotish/palm_trace.py`) measures the lines as ratios of the palm frame (life-line reach and sweep, head-line span and drop, heart-line end position and curvature, fate/sun presence), turns them into the checklist choices of `/v1/palm`, reads marks on lines (island, break, chain, cross, star, fork, square, triangle, branches) and counted lines (union, bracelets, travel, girdle of Venus) from `data/knowledge/palm.json`, and never predicts health or lifespan. `GET /v1/palm/trace/catalog`, printable `POST /v1/palm/trace/report`. Thresholds are draft (`docs/REVIEW.md` F).

## Rashifal
`GET /v1/rashifal?date&period=daily|weekly|monthly&tz` — for the twelve Moon signs, the transiting planets' houses read with the gochara rule library (favourable houses, vedha), a 0–100 score, a summary and the weekday's lucky colour/number; printable `POST /v1/rashifal/report`; card in the muhurta tab; optional monthly rashifal page in the calendar studio. Tendency language only (`engine/jyotish/rashifal.py`).

## Lagna shuddhi (muhurta lagna)
`POST /v1/muhurta/lagna {date, lat, lon, tz, activity?, groom_moon_sign?, bride_moon_sign?}` → the day's twelve ascendant windows with a chart at each middle and the almanac rules for a muhurta lagna (7th and 8th empty, no malefic in the 12th, lagna lord not in 6/8/12, Moon not in 1/6/8/12, for marriage Mars-8 and Venus-6 avoided, fixed/dual preferred, lagna not 6/8/12 from the bride's or groom's Moon sign), with Abhijit, Rahu kaal and good choghadiya. A "लग्न-शुद्धि" button on every day in the muhurta tab. Draft (`docs/REVIEW.md` A.19).

## Moonrise / moonset
`engine/jyotish/moon.py`: Moon latitude (30 Meeus terms), parallax, standard altitude 0.7275π − 34′, 10-minute scan + bisection; Delhi values match published almanac times within a minute (Karva Chauth 2025 moonrise 20:13). Shown in the panchang card, the birth-day table and printed reports; used by the festival calendar for Sharad Purnima.

## Calendar design studio
New top tab **कैलेंडर**. `GET /v1/panchang/month?year&month&lat&lon&tz` gives every day's sunrise panchang with tithi / nakshatra / yoga / karana end times, both month systems, Vikram samvat, sunrise/sunset, moonrise/moonset, Rahu kaal / Yamaganda / Gulika / Abhijit, good choghadiya windows, Moon sign, disha shool, special yogas (Sarvartha Siddhi, Amrita Siddhi, Gand Mool, Panchak, Bhadra), sankranti flag and the day's festivals, plus the month's planetary ingresses and almanac-level auspicious dates per activity. `POST /v1/panchang/calendar/report` renders print-ready pages (one month or all twelve, optional cover page) from a design: five templates (classic grid, modern with hero image, poster list, full panchang almanac page with festival / muhurta / ingress boxes, two months per page), eight palettes or fully custom colours (accent, festival, Sunday, paper, ink, band text), three font pairings (Google Fonts online, system fallbacks), five backgrounds incl. dark, top / bottom / vertical side advertisement bands (image as data URL or text), logo, per-month hero images, business footer, bilingual month names, Monday/Sunday start, notes and holidays. The web studio has a fitted live preview, several named saved designs on the device, print (Save as PDF) and HTML download. `engine/jyotish/panchang_month.py`, `engine/jyotish/calendar_design.py`.

## Festival calendar
`GET /v1/festivals?year=2026&lat=..&lon=..&tz=Asia/Kolkata` — 32 festivals (Makar Sankranti by solar ingress; the rest by amanta month + tithi at sunrise, or at midnight / sunset / approximate moonrise / midday where the tradition does so), all Ekadashis with names, Purnima and Amavasya days (kshaya tithis handled), and adhika-masa spans. Card in the muhurta tab, grouped by month. Draft: regional conventions can differ by a day (`engine/jyotish/festivals.py`).

## Learn tab
Ten lessons (planets, signs, houses, nakshatras, dasha, yogas, transits, vargas, matching, panchang) rendered from the knowledge files, a searchable 54-term glossary (`data/knowledge/glossary.json`) and quizzes generated in the browser from the same data (sign lords, exaltations, nakshatra lords/deities/symbols, house meanings, term definitions). Everything is bilingual and the glossary is part of the Ask corpus.

## Login (Supabase Auth)
Signed-in users send `Authorization: Bearer <access_token>`; the token is verified locally and mapped to a personal organisation (created on first login). Quota and saved people then work exactly as for API keys.

| Env var | Meaning |
|---|---|
| `SUPABASE_URL` | `https://<ref>.supabase.co` (new projects: tokens verified via the project's JWKS, ES256/RS256) |
| `SUPABASE_JWT_SECRET` | only for legacy projects that still sign with HS256 |

Web page: fill `web/config.js` with the project URL and the **publishable** key (public by design; never a secret key). The "मेरी कुंडलियाँ" card (email-link login, save / open / delete) appears only when both are set.

## Hindi / English
The web page has a language button; the report accepts `"lang": "en"` (`POST /v1/report`). English is produced by a dictionary (`data/i18n_en.json`, rebuilt with `python engine/tools/build_i18n.py`) with **all-or-nothing** matching: a text is shown in English only if it can be translated completely, so a sentence is never half Hindi, half English. The report and the web page are fully English (checked in a browser); Vastu and palmistry data now carry English fields (`why`, `fix`, `meaning`, ...) next to the Hindi ones. New Hindi text should always be added together with its English, and `build_i18n.py` re-run. Rules (`readings`) carry both `text_hi` and `text_en`.

## Muhurta finder
`POST /v1/muhurta` `{activity: general|travel|business|griha_pravesh|vehicle|education, lat, lon, tz, start?, days? (1-60), chart?}` scores each day from the panchang at sunrise (rikta tithi, amavasya, bad yogas, Vishti karana, nakshatras suited/avoided for the activity, weekday) and, when a birth payload is given, tarabala and chandrabala. Each day carries its good choghadiya windows, abhijit and Rahu kaal. Draft rules; see docs/REVIEW.md.

## Prashna (KP horary)
`POST /v1/prashna` `{topic: general|marriage|job|business|money|property|education|children|travel|lost_item, lat, lon, tz, when? ('YYYY-MM-DD HH:MM' local), kp_number? (1-249)}` casts the chart of the moment (or anchors the Lagna at the KP number's sub) with Placidus cusps and KP ayanamsa, reads the sub-lord of the topic's cusp against the favouring/denying house groups, the Moon's sub-lord and the ruling planets, and returns a tendency verdict (favourable / unfavourable / mixed / unclear) with reasons. Health, legal and lifespan topics are not offered. Draft rules.

## Ask (RAG chat)
`POST /v1/ask` with `{"question": "...", "lang": "hi|en" (optional), "chart": {birth payload} (optional)}` answers from the project's own content only (rules, Vastu, palm, tarot, numerology knowledge and, if a chart is sent, that person's chart facts and readings). Retrieval is BM25 (no installs). Answers are **extractive** (the best passages, with source ids) unless `ANTHROPIC_API_KEY` is set, in which case the model writes a short answer from those passages only (`KUNDALI_LLM_MODEL` overrides the model; the model call is untested offline and falls back to extractive on any error). Questions about death/lifespan, illness, money/lottery or legal outcomes are refused before any retrieval or model call, in both languages. Yoga passages count only when the question is about yogas/doshas. Numerology is covered too: number passages are labelled ("Number 5 / Moolank / Bhagyank"), and with a chart the person's own Moolank, Bhagyank, personal year and (if a name was given) Chaldean name number are answerable. Limit: 500 characters per question. The web page has a "पूछिए / Ask" card that calls this route, sending the current chart's birth details when one has been made, and shows the answer, its sources and the disclaimer in the chosen language.

## Install as an app (PWA)
The web page is a Progressive Web App: `web/manifest.webmanifest`, `web/sw.js` (app shell and knowledge files cached, API always live) and icons in `web/icons/`. On HTTPS, Chrome/Edge (Android, desktop) show an "ऐप इंस्टॉल करें" button; on iPhone use Share → "Add to Home Screen". The service-worker cache version is the git commit (set at Docker build via `GIT_SHA`), so each deploy refreshes the shell. Making a chart still needs the server; the learning material opens offline.

## WhatsApp daily updates (Vivid Relay)
`engine/jyotish/notify.py` — subscriptions (`wa_subs` in the access SQLite), message composers (daily panchang with tithi windows,
personal rashifal, day-before vrat alert, weekly list), sender (`POST {RELAY_URL}/api/sessions/{RELAY_SESSION}/send`, Bearer
`RELAY_API_KEY`) and a once-a-minute worker (`KUNDALI_NOTIFY=1`). Routes: `POST /v1/notify/{subscribe,verify,unsubscribe,status,preview}`.
Setup: `docs/OPS-relay.md` §12.
