"""Divisional charts (Parashari rules). Returns the varga sign of a longitude.

Implemented: D1, D2 (hora), D3 (drekkana), D4 (chaturthamsha), D7 (saptamsha),
D9 (navamsha), D10 (dashamsha), D12 (dwadashamsha). The remaining Shodashavarga
(D16, D20, D24, D27, D30, D40, D45, D60) come later, after rule verification.
Integer-friendly arithmetic is used so exact boundaries do not misbehave.
"""
from __future__ import annotations

NAMES = {
    "D1": ("Rashi", "राशि"), "D2": ("Hora", "होरा"), "D3": ("Drekkana", "द्रेष्काण"),
    "D4": ("Chaturthamsha", "चतुर्थांश"), "D7": ("Saptamsha", "सप्तमांश"),
    "D9": ("Navamsha", "नवांश"), "D10": ("Dashamsha", "दशमांश"),
    "D12": ("Dwadashamsha", "द्वादशांश"), "D16": ("Shodashamsha", "षोडशांश"), "D20": ("Vimshamsha", "विंशांश"),
    "D24": ("Chaturvimshamsha", "चतुर्विंशांश"), "D27": ("Bhamsha", "भांश"), "D30": ("Trimshamsha", "त्रिंशांश"),
    "D40": ("Khavedamsha", "खवेदांश"), "D45": ("Akshavedamsha", "अक्षवेदांश"), "D60": ("Shashtiamsha", "षष्ट्यंश"),
}
MEANING_EN = {
    "D1": "overall life and body", "D2": "wealth and assets", "D3": "siblings and courage",
    "D4": "fortune and fixed property", "D7": "children", "D9": "marriage and dharma, the inner strength of a planet",
    "D10": "career and profession", "D12": "parents", "D16": "vehicles, comforts and happiness", "D20": "spiritual practice and devotion",
    "D24": "education and learning", "D27": "strength and vitality", "D30": "misfortunes and character (trimsamsa)",
    "D40": "auspicious and inauspicious effects (maternal line)", "D45": "overall conduct (paternal line)", "D60": "past-life karma; the finest division",
}
MEANING_HI = {
    "D1": "समग्र जीवन और शरीर", "D2": "धन और संपत्ति", "D3": "भाई-बहन और साहस",
    "D4": "भाग्य और अचल संपत्ति", "D7": "संतान", "D9": "विवाह और धर्म, ग्रह का भीतरी बल",
    "D10": "कर्म और व्यवसाय", "D12": "माता-पिता", "D16": "वाहन, सुख और आराम", "D20": "साधना और भक्ति",
    "D24": "विद्या और शिक्षा", "D27": "बल और जीवन-शक्ति", "D30": "अरिष्ट और चरित्र (त्रिंशांश)",
    "D40": "शुभ-अशुभ फल (मातृ पक्ष)", "D45": "समग्र आचरण (पितृ पक्ष)", "D60": "पूर्व-जन्म कर्म; सबसे सूक्ष्म वर्ग",
}


def _part(lon: float, n: int) -> tuple[int, int]:
    """(sign index 0-11, part index 0..n-1 inside that sign)."""
    lon = lon % 360.0
    sign = int(lon // 30) % 12
    within = lon - sign * 30
    return sign, min(int(within * n // 30), n - 1)


def varga_sign(lon: float, varga: str) -> int:
    if varga == "D1":
        return int(lon % 360 // 30) % 12
    if varga == "D2":  # odd sign: first half Sun (Simha), second Moon (Karka); even: reverse
        s, k = _part(lon, 2)
        odd = s % 2 == 0
        return 4 if (k == 0) == odd else 3
    if varga == "D3":
        s, k = _part(lon, 3)
        return (s + 4 * k) % 12            # same, 5th, 9th
    if varga == "D4":
        s, k = _part(lon, 4)
        return (s + 3 * k) % 12            # same, 4th, 7th, 10th
    if varga == "D7":
        s, k = _part(lon, 7)
        start = s if s % 2 == 0 else (s + 6) % 12   # odd sign: itself, even sign: 7th from it
        return (start + k) % 12
    if varga == "D9":
        return int((lon % 360) * 9 // 30) % 12
    if varga == "D10":
        s, k = _part(lon, 10)
        start = s if s % 2 == 0 else (s + 8) % 12   # odd sign: itself, even sign: 9th from it
        return (start + k) % 12
    if varga == "D12":
        s, k = _part(lon, 12)
        return (s + k) % 12
    if varga in ("D16", "D45"):             # movable from Mesha, fixed from Simha, dual from Dhanu
        s, k = _part(lon, int(varga[1:]))
        return ((0, 4, 8)[s % 3] + k) % 12
    if varga == "D20":                      # movable from Mesha, fixed from Dhanu, dual from Simha
        s, k = _part(lon, 20)
        return ((0, 8, 4)[s % 3] + k) % 12
    if varga == "D24":                      # odd from Simha, even from Karka
        s, k = _part(lon, 24)
        return ((4 if s % 2 == 0 else 3) + k) % 12
    if varga == "D27":                      # fire from Mesha, earth from Karka, air from Tula, water from Makara
        s, k = _part(lon, 27)
        return ((0, 3, 6, 9)[s % 4] + k) % 12
    if varga == "D30":                      # unequal trimsamsa (Mars 5, Saturn 5, Jupiter 8, Mercury 7, Venus 5; reversed in even signs)
        s = int(lon % 360 // 30) % 12
        d = lon % 30
        if s % 2 == 0:
            bands = ((5, 0), (10, 10), (18, 8), (25, 2), (30, 6))      # Mesha, Kumbha, Dhanu, Mithuna, Tula
        else:
            bands = ((5, 1), (12, 5), (20, 11), (25, 9), (30, 7))      # Vrishabha, Kanya, Meena, Makara, Vrishchika
        return next(sign for limit, sign in bands if d < limit)
    if varga == "D40":                      # odd from Mesha, even from Tula
        s, k = _part(lon, 40)
        return ((0 if s % 2 == 0 else 6) + k) % 12
    if varga == "D60":                      # count from the sign itself
        s, k = _part(lon, 60)
        return (s + k) % 12
    raise ValueError(f"Unsupported varga {varga}")


def varga_chart(asc_lon: float, planets: list[dict], varga: str) -> dict:
    lagna = varga_sign(asc_lon, varga)
    signs = {p["name"]: varga_sign(p["longitude"], varga) for p in planets}
    houses = []
    for h in range(1, 13):
        sign = (lagna + h - 1) % 12
        houses.append({"house": h, "sign": sign,
                       "planets": [n for n, s in signs.items() if s == sign]})
    return {"name": NAMES[varga][0], "name_hi": NAMES[varga][1], "meaning_hi": MEANING_HI[varga], "meaning_en": MEANING_EN[varga],
            "lagna_sign": lagna, "planet_signs": signs, "houses": houses}


def all_vargas(asc_lon: float, planets: list[dict]) -> dict:
    return {v: varga_chart(asc_lon, planets, v) for v in NAMES}
