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

## AI (optional, multi-provider)
Chat grounded in the asker's chart, the rule/glossary corpus and today's panchang; providers Gemini / Groq / OpenRouter (DeepSeek etc.) / Ollama / DeepSeek / OpenAI / Anthropic / any OpenAI-compatible, tried in order with fallback; per-user daily quota; retrieval answer when no provider. Palm photo → the model fills the 16-feature checklist, the app interprets. The WhatsApp bot answers free-text questions through the same chain.

## Kundali image card
Shareable PNG of the birth chart (North or South style) with lagna, Moon sign/nakshatra, Sun sign, running dasha, yogas and branding — "कुंडली कार्ड साझा करें" on the summary, `POST /v1/chart/card.png`, and sent as an image by the WhatsApp bot's कुंडली command.

## Panchang image card
Shareable 1080×1350 PNG of the day's panchang (Pillow, Devanagari shaping) — "कार्ड साझा करें" on the Today tab (Web Share / download), `GET /v1/panchang/card.png`, and sent with the WhatsApp daily message as an image with the text as caption (per-subscriber toggle; falls back to text if media fails). Footer branding from `KUNDALI_BRAND_NAME/TAGLINE`.

## Dashakoota matching (South Indian)
Ten kootas (Dina, Gana, Mahendra, Stree Deergha, Yoni, Rasi, Rasyadhipati, Vasya, Rajju, Vedha) out of 36 alongside Ashtakoota; same-rajju and nakshatra-vedha flagged as blockers.

## Personal day score and year table
Transits scored against the natal Ashtakavarga (each planet's BAV bindus in its transit sign, SAV, chandra-bala, tara-bala) → a daily personal score line (Today card, WhatsApp); `/v1/chart/year_ahead` month-by-month table of Jupiter/Saturn/Rahu/Mars/Sun with house-from-Moon, bindus, MD/AD and change dates.

## Owner admin panel
`/admin.html` (admin key): KPIs, WhatsApp subscribers and logs, bot inbox, astrologers and consultation threads, wallet top-ups, AI providers/usage, rule extraction, festival overrides — edits persist on the data volume.

## AI tools (on the same provider chain)
AI summary of a chart / match / varshaphal (from computed facts only); calendar-studio month lines, festival notes and tagline; AI quiz on any topic grounded in the glossary/rules; astrologer's first-draft reply in a consultation thread; admin rule extraction from classical text to draft JSON; one daily AI line in the WhatsApp message (opt-in); semantic (embedding) search blended into keyword ranking when `data/embeddings.json` exists; UI translation packs via `tools/ai_translate.py` with a language dropdown.

## Consultation with astrologers
Astrologer profiles (admin), request → WhatsApp ping → in-app thread (+ WhatsApp copy of replies) → close & rate; wallet ledger with manual UPI top-ups; free by default (`KUNDALI_PAID`).

## Eclipses at a place
Local first/maximum/last contact, totality, magnitude, visibility (body above horizon) and the traditional **sutak** window (12 h solar / 9 h lunar; none for penumbral) for the chosen place — on the Today tab and the festival list.

## Outer planets and true node
Uranus, Neptune, Pluto shown separately (not used in dasha/yoga/strength); mean or true Rahu-Ketu selectable.

## Nadi (Bhrigu Nandi Nadi)
Planet-karaka reading (jeeva, karma, spouse, shadow planets), Saturn-based profession field, Jupiter transit year-clock, nadi kuta and nadi-amsha.

## Regional languages
Panchang vocabulary and labels in Telugu, Kannada, Marathi, Gujarati, Bengali (Today tab selector, `lang=` on `/v1/panchang/day`, WhatsApp daily message in the subscriber's language).

## Doshas and remedy pointers
Kaal Sarp (full/partial, 12 types by Rahu's house, direction), Pitru dosha indications (Sun/Moon with the nodes, 9th house and lord), Mangal dosha from Lagna/Moon/Venus with the classical cancellations and the 2nd-house (South) note, Sade Sati status; remedy pointers: gemstone of the lagna lord plus friendly 5th/9th lords (day, finger, planets to avoid), rudraksha mukhi, Ishta Devata from the karakamsa's 12th (Jaimini), lagna-lord mantra. All labelled draft/convention.

## Dasha systems
Vimshottari (up to 3 levels, pratyantars), **Yogini** (36-year cycle, 8 yoginis with antardashas and running period), Jaimini Chara dasha, Tajika mudda dasha (varshaphal).

## Ayanamsa options
Lahiri (Chitrapaksha, default), Raman, Krishnamurti (KP), Yukteshwar — selectable in the kundali form and API (`ayanamsa`).

## Chart views
Lagna, **Chandra kundali** and **Surya kundali** views of D1 (houses counted from the Moon or the Sun), in North or South Indian style.

## Almanac extras (Today tab, panchang month, calendar)
Varjyam, Amrit Kalam, Dur Muhurtam, Anandadi yoga (27), Ravi Pushya / Guru Pushya, Ravi yoga, Tripushkara / Dwipushkara (alongside Sarvartha/Amrita Siddhi, Gand Mool, Panchak, Bhadra); running-muhurta indicator with minutes left; **eclipses** (solar/lunar, from the syzygies and node distance; visibility not computed) as `grahan` events in the festival calendar, WhatsApp lists and the Today tab.

## Baby-name syllables
Nakshatra-pada syllable (avakahada) with seed name suggestions (boys/girls) from `data/knowledge/baby_names.json`.

## Personal alerts (dasha & transit changes)
Every chart carries `alerts`: today's changes for that chart — mahadasha/antardasha start, Sun/Mercury/Venus/Mars/Jupiter/Saturn/Rahu sign ingress with the house from the natal Moon and the gochara tendency text, Sade Sati / Ashtama Shani start, phase change or end, retrograde/direct stations — plus the week ahead. Shown in "आज क्या ख़ास है" and in the subscriber's daily WhatsApp message ("आपकी कुंडली में").

## Chart styles
North Indian (diamond) and South Indian (fixed 4×4, lagna marked with a diagonal) for D1, vargas, matching and the printed reports; the choice is remembered per browser.

## Festival overrides
`data/overrides/festivals_<year>.json` (add / move / remove) patches the computed calendar for government holidays or a local panchang's differing date; applied everywhere (calendar, panchang month, WhatsApp, Today tab).

## Navigation
Five sections — **आज** (home: today's panchang tiles, today's and tomorrow's vrats with tithi windows, good/bad hours incl. good choghadiya, rashifal for all 12 signs, quick links), **मेरी कुंडली** (kundali, matching, saved charts), **पंचांग-मुहूर्त** (muhurta, calendar studio), **अन्य विद्याएँ** (tarot, vastu, palm, prashna), **सीखिए-पूछिए** (lessons, ask). Each section's pages appear as a second row; on phones the sections form a bottom bar. The Today tab has its own city picker (remembered), and its panchang/rashifal calls are cached by the service worker so it opens offline with the last data. The app shell is served no-cache and the service worker reloads once when a new build takes over.

## WhatsApp daily updates (Vivid Relay)
Free subscription from the Kundali tab: a 6-digit code over WhatsApp verifies the number; then every day at the chosen time (subscriber's own time zone and place) a message with the panchang — weekday, month, **the tithi window** (from when to when, and which tithi follows, so two-tithi days are explicit), nakshatra end, sunrise/sunset/moonrise, Rahu kaal, Abhijit, disha shool, special yogas, today's vrats/festivals — the subscriber's own daily rashifal (Moon sign from the chart), and a **day-before alert** for tomorrow's vrat/festival with its tithi start/end, sunrise/sunset, Ekadashi parana and Pradosha window; a **weekly list** on the chosen weekday. Kinds are selectable (festival, Ekadashi, Purnima, Amavasya, Pradosh, Chaturthi, Masik Shivaratri, regional, national). Hindi or English. Sending goes through the owner's Vivid Relay gateway (`RELAY_URL`, `RELAY_API_KEY`, `RELAY_SESSION`, `KUNDALI_NOTIFY=1`); Relay's STOP keyword and the card's "बंद करें" both opt out.

## WhatsApp bot (two-way)
Message the business number: **पंचांग** [city], **राशिफल** [sign] (all 12 or one in detail), **कुंडली** DD-MM-YYYY HH:MM city (lagna, Moon sign/nakshatra, running dasha, link to the full chart), **व्रत** (this week), **मुहूर्त** विवाह/गृह प्रवेश/वाहन/यात्रा/व्यापार… (best dates with good hours), **शुरू**/**बंद**, **मदद**; Hindi or English, 242 Indian cities by Hindi/English name. Webhook `/v1/notify/webhook` verified with Relay's HMAC signature, retries de-duplicated. Interactive: the menu is a tap-to-open WhatsApp list (पंचांग, राशिफल, व्रत, मुहूर्त, सब्सक्राइब), rashifal offers a 12-sign picker; button/list replies are handled as commands, with plain-text fallback.

## कैलेंडर (calendar design studio)
Monthly panchang data (tithi/nakshatra/yoga/karana end times, both month systems, Vikram/Shaka/Gujarati samvat, Tamil/Bengali/Malayalam months, special yogas, planetary ingresses, muhurta dates). Print-ready pages: 6 templates (classic, modern, poster, full panchang almanac, two and three months per page), cover page, yearly auspicious-dates page, monthly rashifal page; 8 palettes or custom colours, 3 font pairings, 5 backgrounds, top/bottom/side advertisement bands, logo, hero images, notes/holidays, saved designs, print/PDF and HTML download.

## प्रश्न (prashna), पूछिए (ask), सीखिए (learn)
KP horary with 1–249 numbers; retrieval-based Q&A over the app's own knowledge (rules, glossary, yogas, palm marks) with guardrails; ten lessons, 54-term glossary, generated quizzes.

## टैरो, वास्तु, हस्तरेखा, अंक
Tarot (78 cards, 3 spreads), numerology (moolank, bhagyank, name numbers, Lo Shu), vastu (room × 8 directions, and from a floor plan: PDF/DXF/image upload, 16-zone degree wheel, 81-pada mandala, map), palmistry (guided checklist, and photo tracing with measured lines, marks, counted lines).
