"""Numerology (Indian ank-jyotish style): moolank, bhagyank, namank, Lo Shu grid, personal year.

Interpretations are in data/knowledge/numbers.json (draft, own wording).
Latin-script names only for now; Devanagari names need a transliteration step.
"""
from __future__ import annotations

from datetime import date

NUMBER_PLANET = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury",
                 6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}

PYTHAGOREAN = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
CHALDEAN = {}
for _n, _letters in {1: "AIJQY", 2: "BKR", 3: "CGLS", 4: "DMT", 5: "EHNX",
                     6: "UVW", 7: "OZ", 8: "FP"}.items():
    for _c in _letters:
        CHALDEAN[_c] = _n

# Lo Shu magic-square layout (rows top to bottom)
LO_SHU_LAYOUT = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]


def digit_sum(n: int) -> int:
    return sum(int(c) for c in str(abs(n)))


def reduce(n: int, keep_master: bool = False) -> int:
    """Reduce to a single digit (optionally stopping at master numbers 11, 22, 33)."""
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = digit_sum(n)
    return n


def name_value(name: str, system: str = "chaldean") -> dict:
    table = CHALDEAN if system == "chaldean" else PYTHAGOREAN
    letters = [c for c in name.upper() if c in table]
    total = sum(table[c] for c in letters)
    return {"system": system, "letters": len(letters), "compound": total,
            "number": reduce(total) if total else 0}


def lo_shu(day: int, month: int, year: int, moolank: int, bhagyank: int) -> dict:
    digits = [int(c) for c in f"{day:02d}{month:02d}{year:04d}" if c != "0"]
    digits += [moolank, bhagyank]
    counts = {n: digits.count(n) for n in range(1, 10)}
    grid = [[str(n) * counts[n] if counts[n] else "" for n in row] for row in LO_SHU_LAYOUT]
    return {"layout": LO_SHU_LAYOUT, "counts": counts, "grid": grid,
            "missing": [n for n in range(1, 10) if counts[n] == 0],
            "repeated": [n for n in range(1, 10) if counts[n] > 1]}


def analyse(birth: date, name: str | None = None, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    moolank = reduce(birth.day)
    bhagyank = reduce(digit_sum(birth.day) + digit_sum(birth.month) + digit_sum(birth.year))
    py = reduce(digit_sum(birth.day) + digit_sum(birth.month) + digit_sum(as_of.year))
    out = {
        "moolank": {"number": moolank, "planet": NUMBER_PLANET[moolank],
                    "how": f"Day of birth {birth.day} reduced to a single digit."},
        "bhagyank": {"number": bhagyank, "planet": NUMBER_PLANET[bhagyank],
                     "how": f"All digits of {birth.isoformat()} added and reduced."},
        "personal_year": {"year": as_of.year, "number": py, "planet": NUMBER_PLANET[py],
                          "how": "Birth day + birth month + current year, reduced."},
        "lo_shu": lo_shu(birth.day, birth.month, birth.year, moolank, bhagyank),
        "compatibility_note": "Moolank and bhagyank relationships are read from the planets of the numbers.",
    }
    if name and any(c.isalpha() for c in name):
        ch, py_ = name_value(name, "chaldean"), name_value(name, "pythagorean")
        for v in (ch, py_):
            if v["number"]:
                v["planet"] = NUMBER_PLANET[v["number"]]
        out["namank"] = {"chaldean": ch, "pythagorean": py_}
    return out
