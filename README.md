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

`/v1/chart` also returns `strength`: a partial Shadbala (uccha, dig, kendradi, naisargika, in virupas) with a rank among the seven planets. It is flagged `complete: false`; do not compare it with full-Shadbala minimum tables.

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
