# Feature list (as built) — कुंडली super-app

All interpretations are tendency-level and marked `review_status: draft` until a scholar reviews them (`docs/REVIEW.md`). Calculations use NASA JPL DE440s (Skyfield) in production and an analytic backend in tests; Lahiri ayanamsa, whole-sign houses, mean node.

## कुंडली (chart)
- Birth chart with 9 planets, lagna, 16 vargas (D1–D60), Sripati bhava chalit, dignities, combustion, retrogression, planetary war, aspects, friendships.
- Vimshottari dasha to 3 levels with the running chain; year overlay (dasha × Saturn/Jupiter double transit per year of life); life timeline with themes.
- 70 yogas: classical (Gajakesari, Budhaditya, Chandra yogas, Viparita, Parivartana, Dhana, Raja…), Pancha Mahapurusha, 32 Nabhasa pattern yogas, conjunction yogas.
- Shadbala (six-fold strength) complete, Ashtakavarga with reductions, gochara from the Moon with vedha, Sade Sati lifetime windows (1900–2100), transit calendar (ingresses, retrogrades).
- Varshaphal (solar return) with muntha; Tajika layer: panchavargiya bala, panchadhikaris & varshesha, 12 sahams, mudda dasha, ithasala/ishrafa aspects, 12 Tajika yogas.
- KP (Placidus cusps, sub/sub-sub lords, significators, ruling planets, horary 1–249), Jaimini (chara karakas, arudha padas, karakamsa, chara dasha), Lal Kitab (fixed chart, pakka ghar, 120-year varshphal table, upay).
- Birth-time sensitivity and rectification aid (constant-signature stretches, event scoring by dasha lords).
- Panchang of the birth day (tithi, nakshatra, yoga, karana, sunrise conventions, moonrise/moonset, Rahu kaal, Yamaganda, Gulika, Abhijit, choghadiya, hora), printed patri page (ghata chakra, name syllables).
- Printable reports (Hindi/English), saved people (Supabase login), share links, PWA.

## मिलान (matching)
Ashtakoota 36 points with nadi/bhakoot/gana parihara, Mangal dosha with cancellations, both charts' notes.

## मुहूर्त (muhurta)
- Day table: sunrise/sunset (two conventions), moonrise/moonset, Rahu kaal, Yamaganda, Gulika, Abhijit, choghadiya (day/night), **hora** (24 planetary hours), Vedic weekday.
- Muhurta finder for 13 activities (general, marriage, griha pravesh, bhoomi pujan, property, vehicle, business, travel, education, mundan, namakaran, annaprashan, upanayana): tithi, nakshatra, yoga, Bhadra, weekday, preferred months; period blocks (Kharmas, Chaturmas, Holashtak, adhika masa, Pitru paksha, Jupiter/Venus combust); tarabala/chandrabala from a chart.
- **Lagna table and lagna shuddhi** per day (Jamitra, Ashtama, 12th malefic, lagna lord, Moon, Mars-8/Venus-6, fixed/dual, bride/groom rashi relation) + bride/groom chandrabala and tarabala.
- **Festival and vrat calendar** per year and place: 32 festivals, Ekadashis (named), Purnima/Amavasya, Pradosh, Vinayaka/Sankashti Chaturthi, Masik Shivaratri, adhika masa; regional festivals (Pongal, Lohri, Baisakhi, Tamil/Bengali/Malayalam new year, Onam, Karthigai Deepam, Durga Puja, Kali Puja, Nuakhai, Raja, Varalakshmi, Ugadi, Pola, Jitiya…), national days, Easter/Good Friday/Christmas, Islamic observances by crescent-visibility estimate.
- **Rashifal** daily/weekly/monthly for the 12 Moon signs from the gochara rules (score, summary, per-planet text, lucky colour/number).

## Navigation
Five sections — **आज** (home: today's panchang tiles, today's and tomorrow's vrats with tithi windows, good/bad hours incl. good choghadiya, rashifal for all 12 signs, quick links), **मेरी कुंडली** (kundali, matching, saved charts), **पंचांग-मुहूर्त** (muhurta, calendar studio), **अन्य विद्याएँ** (tarot, vastu, palm, prashna), **सीखिए-पूछिए** (lessons, ask). Each section's pages appear as a second row; on phones the sections form a bottom bar. The app shell is served no-cache and the service worker reloads once when a new build takes over.

## WhatsApp daily updates (Vivid Relay)
Free subscription from the Kundali tab: a 6-digit code over WhatsApp verifies the number; then every day at the chosen time (subscriber's own time zone and place) a message with the panchang — weekday, month, **the tithi window** (from when to when, and which tithi follows, so two-tithi days are explicit), nakshatra end, sunrise/sunset/moonrise, Rahu kaal, Abhijit, disha shool, special yogas, today's vrats/festivals — the subscriber's own daily rashifal (Moon sign from the chart), and a **day-before alert** for tomorrow's vrat/festival with its tithi start/end, sunrise/sunset, Ekadashi parana and Pradosha window; a **weekly list** on the chosen weekday. Kinds are selectable (festival, Ekadashi, Purnima, Amavasya, Pradosh, Chaturthi, Masik Shivaratri, regional, national). Hindi or English. Sending goes through the owner's Vivid Relay gateway (`RELAY_URL`, `RELAY_API_KEY`, `RELAY_SESSION`, `KUNDALI_NOTIFY=1`); Relay's STOP keyword and the card's "बंद करें" both opt out.

## कैलेंडर (calendar design studio)
Monthly panchang data (tithi/nakshatra/yoga/karana end times, both month systems, Vikram/Shaka/Gujarati samvat, Tamil/Bengali/Malayalam months, special yogas, planetary ingresses, muhurta dates). Print-ready pages: 6 templates (classic, modern, poster, full panchang almanac, two and three months per page), cover page, yearly auspicious-dates page, monthly rashifal page; 8 palettes or custom colours, 3 font pairings, 5 backgrounds, top/bottom/side advertisement bands, logo, hero images, notes/holidays, saved designs, print/PDF and HTML download.

## प्रश्न (prashna), पूछिए (ask), सीखिए (learn)
KP horary with 1–249 numbers; retrieval-based Q&A over the app's own knowledge (rules, glossary, yogas, palm marks) with guardrails; ten lessons, 54-term glossary, generated quizzes.

## टैरो, वास्तु, हस्तरेखा, अंक
Tarot (78 cards, 3 spreads), numerology (moolank, bhagyank, name numbers, Lo Shu), vastu (room × 8 directions, and from a floor plan: PDF/DXF/image upload, 16-zone degree wheel, 81-pada mandala, map), palmistry (guided checklist, and photo tracing with measured lines, marks, counted lines).
