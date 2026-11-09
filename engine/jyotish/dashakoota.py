"""Dashakoota — the ten-koota matching of the South Indian (Tamil / Telugu / Kannada) tradition, from the two Moon positions.

Kootas and the common scoring (max 36, boy's star counted from the girl's star where the tradition counts so):
 Dina (3): count of the boy's nakshatra from the girl's, mod 9 — 2, 4, 6, 8, 9 are good (0 = 9).
 Gana (6): deva/manushya/rakshasa of the two stars — same 6; deva–manushya 5; manushya–rakshasa 1; deva–rakshasa 0.
 Mahendra (2): boy's star 4, 7, 10, 13, 16, 19, 22, 25 from the girl's → 2.
 Stree Deergha (2): boy's star more than 13 from the girl's (some say > 7) → 2; 8–13 → 1.
 Yoni (4): animal of each star — same 4, friendly 3, neutral 2, enemy 0 (Vedic yoni table).
 Rasi (7): distance of the boy's sign from the girl's — 7th 7; 2/12 0 (if the girl's is 12th from boy's, 7 by some, here 2); 3/11 5; 4/10 4; 5/9 (girl's sign 5th from boy's) 0 but boy's 5th from girl's 7; 6/8 girl's 6th from boy's 0, boy's 6th from girl's 7 — simplified as: 7 (opposite) 7; same sign 7 if different stars; 2–12 pairs 0; 3–11 pairs 5; 4–10 pairs 4; 5–9 pairs 5; 6–8 pairs 0.
 Rasyadhipati (5): friendship of the two sign lords — same/friend 5, neutral 3, enemy 0.
 Vasya (2): the girl's sign is the boy's vasya (controlled) sign or vice-versa → 2; same group 1.
 Rajju (5): the star's rajju (pada, kati, nabhi, kantha, siro) — DIFFERENT rajju 5; same rajju 0 (the most weighted exclusion; same Siro rajju is the gravest).
 Vedha (0 = pass, else fail): the mutually obstructing star pairs (Ashwini–Jyeshtha, Bharani–Anuradha, …) → vedha dosha.
The ten add to 36 in this scheme; a match of 18+ is acceptable, with Rajju and Vedha treated as near-absolute. Texts and local
pañcāṅgas differ in details; this follows the commonly printed tables and is labelled draft.
"""
from __future__ import annotations

from .constants import NAKSHATRAS, NAKSHATRAS_HI, SIGN_LORDS, SIGNS, SIGNS_HI
from .matching import _GANA as GANA, _GANA_SCORE as GANA_SCORE, _NAK_YONI as YONI, _YONI_MATRIX, _YONI_ORDER, _relation, vashya_group  # shared tables

RAJJU = ["pada", "kati", "nabhi", "kantha", "siro", "kantha", "nabhi", "kati", "pada"]       # Ashwini..Ashlesha, repeating 3×
RAJJU_HI = {"pada": "पाद", "kati": "कटि", "nabhi": "नाभि", "kantha": "कंठ", "siro": "शिरो"}
RAJJU_WARN_HI = {"pada": "भ्रमण/अस्थिरता", "kati": "दरिद्रता", "nabhi": "संतान-कष्ट", "kantha": "पत्नी-हानि", "siro": "पति-हानि (सबसे गंभीर)"}
# Ashwini–Jyeshtha, Bharani–Anuradha, Krittika–Vishakha, Rohini–Swati, Mrigashira–Dhanishtha & Chitra, Ardra–Shravana, Punarvasu–U.Ashadha,
# Pushya–P.Ashadha, Ashlesha–Mula, Magha–Revati, P.Phalguni–U.Bhadra, U.Phalguni–P.Bhadra, Hasta–Shatabhisha
VEDHA_PAIRS = [(0, 17), (1, 16), (2, 15), (3, 14), (4, 22), (4, 13), (5, 21), (6, 20), (7, 19), (8, 18), (9, 26), (10, 25), (11, 24), (12, 23)]
MAHENDRA = {4, 7, 10, 13, 16, 19, 22, 25}
RASI_SCORE = {0: 7, 6: 7, 1: 0, 11: 0, 2: 5, 10: 5, 3: 4, 9: 4, 4: 5, 8: 5, 5: 0, 7: 0}
VASYA_OF = {0: {4, 7}, 1: {3, 6}, 2: {5}, 3: {7, 8}, 4: {6}, 5: {2, 11}, 6: {5, 9}, 7: {3}, 8: {11}, 9: {0, 10}, 10: {0}, 11: {9}}


def _nak(lon: float) -> int:
    return int(lon // (360.0 / 27.0)) % 27


def _yoni_score(a: int, b: int) -> int:
    return _YONI_MATRIX[_YONI_ORDER.index(YONI[a])][_YONI_ORDER.index(YONI[b])]


def dashakoota(boy_moon: float, girl_moon: float) -> dict:
    bn, gn = _nak(boy_moon), _nak(girl_moon)
    bs, gs = int(boy_moon // 30) % 12, int(girl_moon // 30) % 12
    count = (bn - gn) % 27 + 1                           # boy's star counted from the girl's (1..27)
    rows = []
    def row(key, hi, got, mx, det_hi, det_en):
        rows.append({"key": key, "name_hi": hi, "score": got, "max": mx, "detail_hi": det_hi, "detail_en": det_en})
    # Dina
    r = count % 9 or 9
    dina = 3 if r in (2, 4, 6, 8, 9) else 0
    row("dina", "दिन", dina, 3, f"कन्या के नक्षत्र से वर का {count}वाँ (शेष {r})", f"boy's star is {count} from the girl's (remainder {r})")
    # Gana
    g = GANA_SCORE[(GANA[bn], GANA[gn])]
    row("gana", "गण", g, 6, f"{GANA[bn]} – {GANA[gn]}", f"{GANA[bn]} – {GANA[gn]}")
    # Mahendra
    row("mahendra", "महेंद्र", 2 if count in MAHENDRA else 0, 2, f"गणना {count}", f"count {count}")
    # Stree deergha
    sd = 2 if count > 13 else (1 if count > 7 else 0)
    row("stree_deergha", "स्त्री-दीर्घ", sd, 2, f"गणना {count} (13 से अधिक उत्तम)", f"count {count} (over 13 is best)")
    # Yoni
    row("yoni", "योनि", _yoni_score(bn, gn), 4, f"{YONI[bn]} – {YONI[gn]}", f"{YONI[bn]} – {YONI[gn]}")
    # Rasi
    d = (bs - gs) % 12
    rasi = RASI_SCORE[d] if not (d == 0 and bn == gn) else 0
    row("rasi", "राशि", rasi, 7, f"{SIGNS_HI[bs]} – {SIGNS_HI[gs]} (अंतर {d})", f"{SIGNS[bs]} – {SIGNS[gs]} (distance {d})")
    # Rasyadhipati
    lb, lg = SIGN_LORDS[bs], SIGN_LORDS[gs]
    rel = "same" if lb == lg else _relation(lb, lg)
    ra = 5 if rel in ("same", "friend") else 3 if rel == "neutral" else 0
    row("rasyadhipati", "राश्यधिपति", ra, 5, f"{lb} – {lg}: {rel}", f"{lb} – {lg}: {rel}")
    # Vasya
    va = 2 if (gs in VASYA_OF.get(bs, set()) or bs in VASYA_OF.get(gs, set())) else (1 if vashya_group(boy_moon) == vashya_group(girl_moon) else 0)
    row("vasya", "वश्य", va, 2, f"{SIGNS_HI[bs]} / {SIGNS_HI[gs]}", f"{SIGNS[bs]} / {SIGNS[gs]}")
    # Rajju
    rb, rg = RAJJU[bn % 9], RAJJU[gn % 9]
    same_rajju = rb == rg
    row("rajju", "रज्जु", 0 if same_rajju else 5, 5, f"{RAJJU_HI[rb]} – {RAJJU_HI[rg]}" + (f" — समान रज्जु दोष ({RAJJU_WARN_HI[rb]})" if same_rajju else ""),
        f"{rb} – {rg}" + (" — same-rajju dosha" if same_rajju else ""))
    # Vedha
    vedha = any({bn, gn} == {a, b} for a, b in VEDHA_PAIRS)
    row("vedha", "वेध", 0 if vedha else 0, 0, "नक्षत्र-वेध दोष" if vedha else "वेध नहीं", "nakshatra vedha dosha" if vedha else "no vedha")
    total = sum(r["score"] for r in rows)
    mx = sum(r["max"] for r in rows)
    blockers = ([ "समान रज्जु" ] if same_rajju else []) + (["नक्षत्र-वेध"] if vedha else [])
    verdict = ("अस्वीकार्य (रज्जु/वेध दोष)" if blockers else "उत्तम" if total >= 28 else "स्वीकार्य" if total >= 18 else "निम्न")
    verdict_en = ("not advised (rajju/vedha)" if blockers else "excellent" if total >= 28 else "acceptable" if total >= 18 else "low")
    return {"system": "dashakoota", "total": total, "max": mx, "kootas": rows, "blockers_hi": blockers, "verdict_hi": verdict, "verdict_en": verdict_en,
            "boy": {"nakshatra_hi": NAKSHATRAS_HI[bn], "nakshatra": NAKSHATRAS[bn], "sign_hi": SIGNS_HI[bs], "rajju_hi": RAJJU_HI[rb]},
            "girl": {"nakshatra_hi": NAKSHATRAS_HI[gn], "nakshatra": NAKSHATRAS[gn], "sign_hi": SIGNS_HI[gs], "rajju_hi": RAJJU_HI[rg]},
            "review_status": "draft",
            "note_hi": "दक्षिण भारतीय दशकूट (दिन, गण, महेंद्र, स्त्री-दीर्घ, योनि, राशि, राश्यधिपति, वश्य, रज्जु, वेध) — 36 में अंक; 18+ स्वीकार्य, रज्जु-वेध दोष प्रायः निर्णायक। स्थानीय पंचांगों में तालिकाएँ थोड़ी भिन्न हैं।",
            "note_en": "South Indian ten-koota matching; 36 points, 18+ acceptable, rajju and vedha usually decisive. Local almanacs differ slightly in the tables."}
