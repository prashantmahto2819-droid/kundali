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

## Prashna
- [x] Prashna (KP horary) v1: 10 topics, cusp sub-lord vs house groups, Moon sub-lord, ruling planets, KP 1-249 number. Pending KP practitioner review.

## Muhurta
- [x] Muhurta finder v1 (6 activity types, panchang rules at sunrise, tarabala/chandrabala with a chart, choghadiya windows). Pending: scholar review of nakshatra lists, hora/lagna-level muhurta.

## Operations
- [x] Relay server: backup-relay.sh (SQLite online backup, 30-day retention, optional R2), restore-relay.sh, healthwatch.sh (webhook alert on state change); steps in OPS-relay.md §10.

## Yogas
- [x] Yoga batch 2: Sunapha/Anapha/Durudhara/Kemadruma, Vesi/Vasi/Ubhayachari, Adhi, Amala, Viparita Raja (Harsha/Sarala/Vimala), Parivartana, Dhana (2/11 with 5/9), Raja (kendra–trikona), Lakshmi, Saraswati. 27 yogas total, all draft.

## Panchang
- [x] Festival and vrat calendar (`festivals.py`, `/v1/festivals`): 32 festivals, 24+ Ekadashis, Purnima/Amavasya, adhika masa, per year and place. Pending: pradosha/sankashti chaturthi lists, regional variants (Tamil/Bengali/Gujarati calendars), moonrise by computation.

## Yogas (patterns)
- [x] Yoga batch 3 (`yogas_nabhasa.py`): Pancha Mahapurusha (Ruchaka, Bhadra, Hamsa, Malavya, Shasha), all 32 Nabhasa pattern yogas (Ashraya 3, Dala 2, Akriti 20, Sankhya 7 with Akriti precedence), Guru-Chandala, Grahana (Sun/Moon), Angaraka, Vish, Shakata (Moon–Jupiter). 70 yogas total; web lists the formed ones first.

## Dasha
- [x] Year overlay (`timeline.year_overlay`): per year of life the running MD/AD, Saturn/Jupiter houses, Sade Sati/Ashtama flags, double-transit houses (Saturn 3/7/10 + Jupiter 5/7/9 + occupation) and whether the running dasha lord links to them; table under the life timeline.
- [x] Running chain resolved to pratyantar (3rd level); pratyantars of the running antardasha listed on web and in the report.

## Patri header
- [x] Traditional janma-patri header (vara, tithi, nakshatra-pada-lord, yoga, karana, sunrise/sunset, ishta kaal, masa, ritu, ayana, Vikram/Shaka samvat, tropical Sun sign) + Avakahada chakra (varna, vashya, yoni, gana, nadi, tattva, name syllable) on the web summary and in the report; checked against the Korba printout. Done since: adhika masa from real lunations, disc-centre sunrise + ishta kaal, ghata chakra (draft table). Purnimanta month name shown alongside amanta. Pending: ghata-chakra scholar check.
- [x] Learn panel (planet/house/varga click) rendered directly in Hindi or English; nakshatra and sign knowledge carry English deity/symbol/traits.
- [x] City list: 242 places incl. all Chhattisgarh districts/towns and neighbouring MP/Odisha/Jharkhand towns.

## Accuracy gate
- [x] First real reference chart (Korba 1991, family printout, N.C. Lahiri): lagna sign, Moon sign/nakshatra/pada, ayanamsa (−0.2′), tithi, paksha, yoga, Ketu balance (−2.2 days), avakahada all match. Pending: a reference with planet degrees (Jagannatha Hora export) and one more birth year/place.

## Next
1. Phase 1 (in progress): [x] sunrise/sunset, sunrise-based vara, Rahu Kaal, Choghadiya, Abhijit; [x] D2/D3/D4/D7/D10/D12; [x] numerology; [x] D16/D20/D24/D27/D30/D40/D45/D60 vargas; [x] bhava-chalit (Sripati cusps, MC, planets that move house); [x] birth-time sensitivity (minutes until Lagna / navamsa Lagna / Moon sign / nakshatra change, with warnings); [x] 12-month transit calendar with slow-planet ingress dates; [x] lifetime Saturn/Jupiter periods (Sade Sati windows with phases, Ashtama, Kantaka, Jupiter by house; one cached 1900-2100 scan); [ ] geocoding + timezone lookup.
2. Phase 2: remaining vargas, aspects/strengths (shadbala), [x] ashtakavarga v1 (BAV/SAV; shodhana reductions + transit use done in gochara v1; vedha applied in gochara verdicts), [x] kundali matching (v2: Bhakoot/Nadi parihara conditions + total with parihara; Vashya/Yoni/Gana tables to verify), [x] numerology, [x] tarot (v2: all 78 cards hand-written, upright/reversed, Hindi+English; reader review pending), [x] report v1 (HTML/print-PDF, Hindi), accounts, [x] city search v1 (151 cities, offline; full geocoder later).
3. Phase 3: [x] course content v1 (Learn tab); [x] RAG chat v1 (`/v1/ask`: BM25 retrieval + guardrails + optional LLM + web Ask card; LLM path untested; FastAPI route verified on the Relay server), [ ] course content, [x] numerology passages in retrieval, [ ] retrieval quality evaluation set.
4. Phase 4: palmistry (needs a labelled palm dataset) and vastu overlay.
5. Phase 5: [x] Lal Kitab (draft; natal view sub-tab + varshphal engine on the 120-year Lal Kitab table (transcribed 2026-11-08 from the Astrostudents chart, 46th-year row verified against a published example; two source rows carry a printed duplicate and are flagged), [x] KP v1 (KP ayanamsa, Placidus cusps, star/sub/sub-sub lords, 4-level significators, ruling planets; draft), [x] Jaimini v1 (chara karakas 7/8, arudha padas, karakamsa, chara dasha K.N. Rao scheme; draft), [x] mobile: PWA (manifest, service worker, install button, offline shell); [x] astrologer tools v1 (private notes per saved person, profile branding on reports); native store apps later if needed.

- [x] Vastu v1 (room x direction rating, 16 rooms, Hindi). [x] Vastu v2 from a floor plan: PDF/DXF/image upload, plot boundary + rooms marked on a canvas, north angle (typed, drawn or phone compass), 16-zone degree wheel, 81-pada mandala with devatas, cut corners, map with location (Leaflet/OSM), printable report. Pending: automatic wall/room detection, scholar review of the zone lists.
- [x] Palmistry v1 (guided checklist, 16 features). [x] Palmistry v2: photo traced in the browser (6 landmarks + lines), measurements → checklist choices, 10 mark types on lines, counted lines (union, bracelets, travel, girdle of Venus), printable report. Pending: automatic line detection (needs a labelled dataset), palmist review of thresholds and texts.
- [x] Shadbala v2: cheshta bala now for all seven (BPHS half-sum kendra with Meeus mean longitudes); ranking by full total. Abda, masa (ahargana lords) and yuddha (planetary war) added: Shadbala v1 complete; ishta/kashta phala added; pending scholar check of conventions.
- [x] Rule library v1: 9 planets x 12 houses (Hindi+English, draft). Gochara texts 9 x 12 from the Moon (draft) shown under transits and in the report; all searchable in Ask. Pending: English text, sign/dignity/aspect rules, classical citations, scholar sign-off.
- [x] Dignity (exalted/debilitated/own) and retrograde rules v1 (26, Hindi, draft). Pending: neecha-bhanga, sign/aspect/conjunction rules, English text.
- [x] Hindi/English toggle (web page + report + vastu + palmistry data; dictionary-based, all-or-nothing)
- [x] Lal Kitab v1 (draft): permanent and exaltation/debilitation houses in two views (lagna, Aries-fixed), harmless traditional remedies, disclaimer. Pending: planet-in-house texts, relationships between planets, scholar review.
- [x] Relations v1: neecha-bhanga (6 classical conditions, each listed), conjunctions, combustion, whole-sign aspects (draft; report section added)
- [x] Shadbala v2 (sthana, dig, kala except abda/masa/yuddha, naisargika, drik; cheshta for Sun/Moon only; draft). Pending: cheshta of Mars..Saturn (needs planetary motion), abda, masa, yuddha, true bhava cusps, check against a reference program.
- [x] Learning layer: 27 nakshatras + 12 rashis (lord, deity, symbol, traits) in the click-to-learn panel; Hindi planet explanations. [x] Learn tab: ten-lesson course (planets → panchang) built from the knowledge files, 54-term glossary (`data/knowledge/glossary.json`) with search, generated quizzes (per lesson and mixed), bilingual; glossary and pattern yogas searchable in Ask. Pending: house x sign lessons, scholar review.
- [x] Life timeline v1: every Vimshottari period read via the dasha lord (placement, lordship, dignity, ashtakavarga) with a transparent strength tag; past/running/future; themes only, no event predictions. Pending: transit overlay, yoga/aspect effects, scholar review.
- [x] Varshaphal v1: solar-return chart (solved numerically, error under 1 arc-second against the same backend) + muntha. [x] Tajika v1 (`tajika.py`): panchavargiya bala (Egyptian hadda), panchadhikaris + varshesha, 12 sahams (day/night reversal, +30° rule), mudda dasha, ithasala/ishrafa aspects by deeptamsha. [x] 12 of the 16 Tajika yogas (Ikkavala, Induvara, Ithasala, Ishrafa, Nakta, Yamaya, Manau, Kambula, Radda, Kuttha, Durapha, Tambira) for the Lagna lord against each house lord. Pending: Khallasara, Duphali-Kuttha, Dutthotha-Davira, Gairi-Kambula; scholar check of conventions.
- [x] Birth-time rectification aid (`rectify.py`, `/v1/rectify`): constant-signature stretches around the given time, optional event scoring by dasha lords (draft).
- [x] Input safety: warnings for DST gap/fold times, polar latitudes and dates outside 1900-2100 (shown in UI and report); history (war-time IST, BST) verified. Typical chart takes ~2.5 ms on the dev backend.
