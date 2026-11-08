# kundali

A commercial-grade Vedic astrology platform: birth chart (kundali), dasha, panchang, numerology, tarot, palmistry and vastu, with a learning layer that explains the *what, why and how* of every result.

Status: **Phase 0**: calculation engine v0.1 + dev web page. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

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
`GET /health` reports the active backend and whether it is production-ready.

## Known limitations (v0.1)
- Lahiri ayanamsa only; the constant is a development value to be verified against a reference.
- Whole-sign houses only; mean node for Rahu/Ketu; vara is the civil weekday (sunrise-based vara comes later).
- Rule library is a tiny **sample**; all rules are `draft` until a scholar reviews them.
- The JPL backend code path is written but was not run in the build environment (no network); run `engine/tools/compare_backends.py` on a connected machine.

License: not decided yet (proprietary by default).
