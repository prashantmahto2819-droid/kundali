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
- [x] Access core: orgs, hashed API keys, daily quotas (KUNDALI_AUTH)
- [x] Saved people per org (API + web card)
- [x] Supabase login: token verification, user->org, web card (needs the real project keys to go live)
- [x] Dev web page with North-Indian charts and click-to-learn
- [ ] **Gate:** 50 test charts compared against a trusted reference (planet degrees, lagna, dasha dates) with JPL backend
- [ ] Decide and verify Lahiri ayanamsa constant against a published reference (`core.LAHIRI_J2000`)
- [ ] Run `engine/tools/compare_backends.py` on the VPS to quantify dev-backend error

## Operations
- [x] Relay server: backup-relay.sh (SQLite online backup, 30-day retention, optional R2), restore-relay.sh, healthwatch.sh (webhook alert on state change); steps in OPS-relay.md §10.

## Patri header
- [x] Traditional janma-patri header (vara, tithi, nakshatra-pada-lord, yoga, karana, sunrise/sunset, ishta kaal, masa, ritu, ayana, Vikram/Shaka samvat, tropical Sun sign) + Avakahada chakra (varna, vashya, yoni, gana, nadi, tattva, name syllable) on the web summary and in the report; checked against the Korba printout. Done since: adhika masa from real lunations, disc-centre sunrise + ishta kaal, ghata chakra (draft table). Purnimanta month name shown alongside amanta. Pending: ghata-chakra scholar check.
- [x] Learn panel (planet/house/varga click) rendered directly in Hindi or English; nakshatra and sign knowledge carry English deity/symbol/traits.
- [x] City list: 242 places incl. all Chhattisgarh districts/towns and neighbouring MP/Odisha/Jharkhand towns.

## Accuracy gate
- [x] First real reference chart (Korba 1991, family printout, N.C. Lahiri): lagna sign, Moon sign/nakshatra/pada, ayanamsa (−0.2′), tithi, paksha, yoga, Ketu balance (−2.2 days), avakahada all match. Pending: a reference with planet degrees (Jagannatha Hora export) and one more birth year/place.

## Next
1. Phase 1 (in progress): [x] sunrise/sunset, sunrise-based vara, Rahu Kaal, Choghadiya, Abhijit; [x] D2/D3/D4/D7/D10/D12; [x] numerology; [x] D16/D20/D24/D27/D30/D40/D45/D60 vargas; [x] bhava-chalit (Sripati cusps, MC, planets that move house); [ ] geocoding + timezone lookup, rectification warnings.
2. Phase 2: remaining vargas, aspects/strengths (shadbala), [x] ashtakavarga v1 (BAV/SAV; shodhana reductions + transit use done in gochara v1), [x] kundali matching (v2: Bhakoot/Nadi parihara conditions + total with parihara; Vashya/Yoni/Gana tables to verify), [x] numerology, [x] tarot (v2: all 78 cards hand-written, upright/reversed, Hindi+English; reader review pending), [x] report v1 (HTML/print-PDF, Hindi), accounts, [x] city search v1 (151 cities, offline; full geocoder later).
3. Phase 3: [x] RAG chat v1 (`/v1/ask`: BM25 retrieval + guardrails + optional LLM + web Ask card; LLM path untested; FastAPI route verified on the Relay server), [ ] course content, [x] numerology passages in retrieval, [ ] retrieval quality evaluation set.
4. Phase 4: palmistry (needs a labelled palm dataset) and vastu overlay.
5. Phase 5: Lal Kitab, KP, Jaimini, astrologer tools, mobile app.

- [x] Vastu v1 (room x direction rating, 16 rooms, Hindi). Pending: floor-plan/plot analysis, 16-zone model, scholar review.
- [x] Palmistry v1 (guided checklist, 16 features). Pending: photo analysis with consent, line-crossing/marks, scholar review.
- [x] Shadbala v2: cheshta bala now for all seven (BPHS half-sum kendra with Meeus mean longitudes); ranking by full total. Abda, masa (ahargana lords) and yuddha (planetary war) added: Shadbala v1 complete; ishta/kashta phala added; pending scholar check of conventions.
- [x] Rule library v1: 9 planets x 12 houses (Hindi, draft, tendency language). Pending: English text, sign/dignity/aspect rules, classical citations, scholar sign-off.
- [x] Dignity (exalted/debilitated/own) and retrograde rules v1 (26, Hindi, draft). Pending: neecha-bhanga, sign/aspect/conjunction rules, English text.
- [x] Hindi/English toggle (web page + report + vastu + palmistry data; dictionary-based, all-or-nothing)
- [x] Lal Kitab v1 (draft): permanent and exaltation/debilitation houses in two views (lagna, Aries-fixed), harmless traditional remedies, disclaimer. Pending: planet-in-house texts, relationships between planets, scholar review.
- [x] Relations v1: neecha-bhanga (6 classical conditions, each listed), conjunctions, combustion, whole-sign aspects (draft; report section added)
- [x] Shadbala v2 (sthana, dig, kala except abda/masa/yuddha, naisargika, drik; cheshta for Sun/Moon only; draft). Pending: cheshta of Mars..Saturn (needs planetary motion), abda, masa, yuddha, true bhava cusps, check against a reference program.
- [x] Learning layer: 27 nakshatras + 12 rashis (lord, deity, symbol, traits) in the click-to-learn panel; Hindi planet explanations. Pending: house x sign lessons, glossary, quizzes.
- [x] Life timeline v1: every Vimshottari period read via the dasha lord (placement, lordship, dignity, ashtakavarga) with a transparent strength tag; past/running/future; themes only, no event predictions. Pending: transit overlay, yoga/aspect effects, scholar review.
- [x] Varshaphal v1: solar-return chart (solved numerically, error under 1 arc-second against the same backend) + muntha. Pending: varshesha, sahams, muddha dasha, Tajika aspects.
- [x] Input safety: warnings for DST gap/fold times, polar latitudes and dates outside 1900-2100 (shown in UI and report); history (war-time IST, BST) verified. Typical chart takes ~2.5 ms on the dev backend.
