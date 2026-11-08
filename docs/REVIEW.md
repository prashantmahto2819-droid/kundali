# Scholar / reader review list (समीक्षा सूची)

Everything the app *interprets* is marked `review_status: draft` and written in tendency language.
The *calculations* are tested against one real printed patri (Korba 1991) and NASA DE440s; the
*interpretations* have not been reviewed by a jyotish scholar, a tarot reader, a vastu or palmistry
practitioner yet. This file lists what needs whose eyes, in priority order, with the exact file to edit.
When an item is approved, change its `review_status` to `reviewed` and add `reviewed_by` + date.

## A. Jyotish (ज्योतिष) — a traditional jyotishi
| # | What | File | Count | Notes |
|---|------|------|-------|-------|
| 1 | Planet-in-house readings (Hindi + English) | `data/rules/planet_in_house.json` | 108 | tendency language; cite BPHS/Phaladeepika chapter where possible |
| 2a | Gochara (transit) texts 9 x 12 from the Moon | `data/rules/gochara.json` | 108 | favourable lists per Phaladeepika tradition; vedha not applied |
| 2 | Dignity / retrograde readings | `data/rules/dignity_retrograde.json` | 26 | neecha-bhanga conditions are computed; text needs check |
| 3 | Yoga definitions and texts | `engine/jyotish/yogas.py` | — | which yogas count, cancellation rules |
| 4 | Ghata chakra table (11 of 12 rows unverified) | `engine/jyotish/patri.py` (`GHATA`) | 12 rows | Dhanu row matches a printed patri; check the rest against Muhurta Chintamani |
| 5 | Shadbala conventions | `engine/jyotish/strength.py` (`assumptions`) | — | abda/masa lords from Kali ahargana; yuddha winner by disc; cheshta half-sum kendra |
| 6 | Ashtakavarga reductions, gochara verdicts | `engine/jyotish/ashtakavarga.py`, `transit.py` | — | shodhana method, Sade Sati phases |
| 7 | Matching: vashya matrix, parihara | `engine/jyotish/matching.py` | — | vashya and yoni matrices are from memory; add nadi/bhakoot cancellations |
| 8 | Timeline themes per dasha lord | `engine/jyotish/timeline.py` | — | which houses/themes a dasha activates |
| 9 | Varshaphal (Tajika) | `engine/jyotish/varshaphal.py` | — | muntha, year lord rules |
| 10a | Lal Kitab varshphal table: enter the original 35-year house table (12 rows x 35) | `data/lalkitab_varshphal.json` (`table`) | 420 cells | one column verified from a published example; needs the book page |
| 10 | Lal Kitab planet/house texts and upay | `data/lalkitab.json` | 9×12 | marked draft; pakka-ghar logic |
| 11 | Nakshatra/sign/house/planet teaching texts | `data/knowledge/*.json` | — | learn panel; Hindi and English |
| 13 | KP layer: ayanamsa constant, Placidus cusps vs a KP program, sub-lord table, significator levels | `engine/jyotish/kp.py` | — | draft; compare one chart with a KP software |
| 14 | Jaimini: karaka scheme (7 vs 8), arudha exception rule, karakamsa | `engine/jyotish/jaimini.py` | — | draft |
| 15 | Muhurta finder: activity nakshatra/weekday lists, scoring weights | `engine/jyotish/muhurta_find.py` (`ACTIVITIES`) | 6 | draft |
| 16 | Prashna: topic house groups (favour/deny), verdict rule | `engine/jyotish/prashna.py` (`TOPICS`) | 10 | draft |
| 12 | Name syllables per pada | `engine/jyotish/patri.py` (`SYLLABLES`) | 108 | standard almanac table; verify spelling |

## B. Calculations — compare against trusted software (JHora / AstroSage, Lahiri, mean node, whole sign)
| # | What | How to verify |
|---|------|---------------|
| 1 | Planet degrees | add 2–3 reference charts with degrees to `engine/tests/reference/` (format in its README) |
| 2 | Sunrise convention | printouts use disc-centre/no-refraction; both are shown; confirm which the app should default to |
| 3 | Lunar month, adhika masa, samvat | spot-check 5 dates incl. one in Phalguna/Chaitra and one adhika month |
| 4 | Dasha balance | year length 365.25 vs 360 days; confirm the preferred convention |
| 5 | Lagna near sign boundary | one chart with lagna within 0.5° of a boundary |

## C. Numerology — a numerologist
| # | What | File |
|---|------|------|
| 1 | Number traits 1–9 (Hindi + English) | `data/knowledge/numbers.json` |
| 2 | Chaldean / Pythagorean letter values, master numbers | `engine/jyotish/numerology.py` |
| 3 | Lo Shu reading of missing / repeated numbers | `engine/jyotish/numerology.py` (`annotations`) |

## D. Tarot — an experienced reader
| # | What | File | Count |
|---|------|------|-------|
| 1 | Major arcana upright/reversed (Hindi + English) | `data/knowledge/tarot.json` (`majors`) | 22 |
| 2 | Minor arcana per-card texts | `data/knowledge/tarot.json` (`minors`) | 56 |
| 3 | Spread positions and wording | `data/knowledge/tarot.json` (`spreads`) | 3 |

## E. Vastu — a vastu practitioner
| # | What | File |
|---|------|------|
| 1 | Room × direction ratings, why/fix texts | `data/knowledge/vastu.json` (16 rooms × 8 directions) |
| 2 | 16-zone model (not built yet) | — |

## F. Palmistry — a palmist
| # | What | File |
|---|------|------|
| 1 | 16 features, their options and meanings | `data/knowledge/palm.json` |

## G. Safety wording (any reviewer)
- Guardrail topics for the ask route: `engine/jyotish/ask.py` (`BLOCKED`) — death, medical, money, legal.
- Disclaimers: report footer, tarot, patri note, Lal Kitab, ask disclaimer.
- Tests enforce "no death/illness/lifespan predictions" in rule texts: `engine/tests/test_rules_library.py`.

## How to review (for the reviewer)
1. Open the file named above (GitHub web editor is fine).
2. For each entry: keep, reword, or delete. Keep tendency language ("प्रवृत्ति", "tends to"); never predict death, illness, lifespan, lottery or legal outcomes.
3. Change `review_status` to `reviewed`, add `reviewed_by: "<name>"` and `reviewed_on: "YYYY-MM-DD"` at the top of the file.
4. Run `cd engine && python -m pytest -q` (or ask the developer to) — the tests check the wording rules.
