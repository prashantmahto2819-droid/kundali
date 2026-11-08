# Roadmap (summary)

Full blueprint (in Hindi) lives in the Claude doc "कुंडली Super-App — ब्लूप्रिंट". Decisions so far:

| Decision | Choice |
| --- | --- |
| Commercial use | Yes, planned. No AGPL code in the product |
| Calculation engine | Our own, on NASA JPL data (Skyfield + DE440s). `engine/jyotish/ephemeris.py` also has a zero-dependency dev backend |
| Tenancy | Multi-tenant from day one (organizations, members, RLS) |
| Hosting | Cloudflare (web, R2, Tunnel) + Supabase (DB/Auth) + one VPS (engine API) |
| Payments | Later (plans table exists) |
| Content | Original (own wording, own tarot art) |

## Phase 0: foundation (this commit)
- [x] Repo layout, engine v0.1 (chart, nakshatra, navamsa, Vimshottari to antardasha, panchang, a few yogas)
- [x] Data-driven rule format with source field and review status
- [x] Multi-tenant SQL schema, deploy files, ops guide
- [x] Dev web page with North-Indian charts and click-to-learn
- [ ] **Gate:** 50 test charts compared against a trusted reference (planet degrees, lagna, dasha dates) with JPL backend
- [ ] Decide and verify Lahiri ayanamsa constant against a published reference (`core.LAHIRI_J2000`)
- [ ] Run `engine/tools/compare_backends.py` on the VPS to quantify dev-backend error

## Next
1. Phase 1 (in progress): [x] sunrise/sunset, sunrise-based vara, Rahu Kaal, Choghadiya, Abhijit; [x] D2/D3/D4/D7/D10/D12; [x] numerology; [ ] geocoding + timezone lookup, rectification warnings, bhava-chalit option, D16-D60.
2. Phase 2: remaining vargas, aspects/strengths (shadbala), [x] ashtakavarga v1 (BAV/SAV; shodhana reductions + transit use done in gochara v1), [x] kundali matching (v1: Vashya/Yoni/Gana to verify; parihara pending), [x] numerology, [x] tarot (v1: majors hand-written, minors composed from rank x suit; scholar/reader review pending), PDF report, accounts, [x] city search v1 (151 cities, offline; full geocoder later).
3. Phase 3: RAG chat and course content.
4. Phase 4: palmistry (needs a labelled palm dataset) and vastu overlay.
5. Phase 5: Lal Kitab, KP, Jaimini, astrologer tools, mobile app.
