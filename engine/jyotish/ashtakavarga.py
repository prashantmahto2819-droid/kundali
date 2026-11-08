"""Ashtakavarga: Bhinnashtakavarga (BAV) per planet and Sarvashtakavarga (SAV).

Each of the seven planets gets 0-8 points ("bindus") in every sign, contributed by the
seven planets and the Lagna. A contributor gives a point when the sign is counted
(1..12, contributor's own sign = 1) in the list below. The tables follow the classical
Parashari scheme; their per-planet totals (48, 49, 39, 54, 56, 52, 39 = 337) are
checked by tests, which catches any typing error in a row.
"""
from __future__ import annotations

# TABLES[receiver][contributor] = houses (counted from the contributor) that give a bindu
TABLES: dict[str, dict[str, tuple[int, ...]]] = {
    "Sun": {"Sun": (1, 2, 4, 7, 8, 9, 10, 11), "Moon": (3, 6, 10, 11), "Mars": (1, 2, 4, 7, 8, 9, 10, 11),
            "Mercury": (3, 5, 6, 9, 10, 11, 12), "Jupiter": (5, 6, 9, 11), "Venus": (6, 7, 12),
            "Saturn": (1, 2, 4, 7, 8, 9, 10, 11), "Lagna": (3, 4, 6, 10, 11, 12)},
    "Moon": {"Sun": (3, 6, 7, 8, 10, 11), "Moon": (1, 3, 6, 7, 10, 11), "Mars": (2, 3, 5, 6, 9, 10, 11),
             "Mercury": (1, 3, 4, 5, 7, 8, 10, 11), "Jupiter": (1, 4, 7, 8, 10, 11, 12),
             "Venus": (3, 4, 5, 7, 9, 10, 11), "Saturn": (3, 5, 6, 11), "Lagna": (3, 6, 10, 11)},
    "Mars": {"Sun": (3, 5, 6, 10, 11), "Moon": (3, 6, 11), "Mars": (1, 2, 4, 7, 8, 10, 11),
             "Mercury": (3, 5, 6, 11), "Jupiter": (6, 10, 11, 12), "Venus": (6, 8, 11, 12),
             "Saturn": (1, 4, 7, 8, 9, 10, 11), "Lagna": (1, 3, 6, 10, 11)},
    "Mercury": {"Sun": (5, 6, 9, 11, 12), "Moon": (2, 4, 6, 8, 10, 11), "Mars": (1, 2, 4, 7, 8, 9, 10, 11),
                "Mercury": (1, 3, 5, 6, 9, 10, 11, 12), "Jupiter": (6, 8, 11, 12),
                "Venus": (1, 2, 3, 4, 5, 8, 9, 11), "Saturn": (1, 2, 4, 7, 8, 9, 10, 11),
                "Lagna": (1, 2, 4, 6, 8, 10, 11)},
    "Jupiter": {"Sun": (1, 2, 3, 4, 7, 8, 9, 10, 11), "Moon": (2, 5, 7, 9, 11),
                "Mars": (1, 2, 4, 7, 8, 10, 11), "Mercury": (1, 2, 4, 5, 6, 9, 10, 11),
                "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11), "Venus": (2, 5, 6, 9, 10, 11),
                "Saturn": (3, 5, 6, 12), "Lagna": (1, 2, 4, 5, 6, 7, 9, 10, 11)},
    "Venus": {"Sun": (8, 11, 12), "Moon": (1, 2, 3, 4, 5, 8, 9, 11, 12), "Mars": (3, 5, 6, 9, 11, 12),
              "Mercury": (3, 5, 6, 9, 11), "Jupiter": (5, 8, 9, 10, 11),
              "Venus": (1, 2, 3, 4, 5, 8, 9, 10, 11), "Saturn": (3, 4, 5, 8, 9, 10, 11),
              "Lagna": (1, 2, 3, 4, 5, 8, 9, 11)},
    "Saturn": {"Sun": (1, 2, 4, 7, 8, 10, 11), "Moon": (3, 6, 11), "Mars": (3, 5, 6, 10, 11, 12),
               "Mercury": (6, 8, 9, 10, 11, 12), "Jupiter": (5, 6, 11, 12), "Venus": (6, 11, 12),
               "Saturn": (3, 5, 6, 11), "Lagna": (1, 3, 4, 6, 10, 11)},
}
EXPECTED_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54, "Jupiter": 56, "Venus": 52, "Saturn": 39}
PLANETS = tuple(TABLES)

# Rule-of-thumb bands for a house's SAV total (average is 337/12, about 28). Draft, not a verdict.
STRONG, WEAK = 30, 25


def band(points: int) -> str:
    return "strong" if points >= STRONG else ("weak" if points < WEAK else "medium")


def bav(receiver: str, signs: dict[str, int]) -> list[int]:
    """Points in each of the 12 signs for one receiver. `signs` maps Sun..Saturn and 'Lagna' to sign index 0-11."""
    out = [0] * 12
    for contributor, houses in TABLES[receiver].items():
        base = signs[contributor]
        for h in houses:
            out[(base + h - 1) % 12] += 1
    return out


def ashtakavarga(signs: dict[str, int], lagna_sign: int) -> dict:
    per, sav = {}, [0] * 12
    for pl in PLANETS:
        row = bav(pl, signs)
        per[pl] = {"by_sign": row, "total": sum(row),
                   "by_house": [row[(lagna_sign + h) % 12] for h in range(12)],
                   "in_own_sign": row[signs[pl]]}
        sav = [a + b for a, b in zip(sav, row)]
    by_house = [sav[(lagna_sign + h) % 12] for h in range(12)]
    return {
        "bav": per,
        "sav": {"by_sign": sav, "by_house": by_house, "total": sum(sav),
                "bands": [band(p) for p in by_house]},
        "thresholds": {"strong_at_least": STRONG, "weak_below": WEAK},
        "why_hi": ("अष्टकवर्ग में हर ग्रह को हर राशि में 0 से 8 बिंदु मिलते हैं (सात ग्रह और लग्न बिंदु देते हैं)। "
                   "किसी भाव के सर्व-अष्टकवर्ग (SAV) का कुल जितना ऊँचा, उस भाव के फल उतने सहज माने जाते हैं। "
                   "औसत लगभग 28 है; 30+ मज़बूत और 25 से कम कमज़ोर, यह अंगूठे का नियम है, अंतिम फ़ैसला नहीं।"),
        "confidence": "firm-tables, draft-interpretation",
    }
