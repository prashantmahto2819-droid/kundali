"""A few classical yogas/doshas, each with its 'why' so the UI can teach it.

All entries are DRAFT until reviewed by a scholar (see data/rules/README.md);
they are flagged ``review_status: draft``.
"""
from __future__ import annotations

KENDRA = {1, 4, 7, 10}


def _p(chart: dict) -> dict:
    return {p["name"]: p for p in chart["planets"]}


def _house_from(a: int, b: int) -> int:
    """House number of b counted from a (1..12)."""
    return (b - a) % 12 + 1


def detect_yogas(chart: dict) -> list[dict]:
    p = _p(chart)
    out = []

    def add(yid, name, name_hi, present, why):
        out.append({"id": yid, "name": name, "name_hi": name_hi, "present": bool(present),
                    "why": why, "review_status": "draft"})

    # Gajakesari: Jupiter in a kendra (1,4,7,10) from the Moon
    gk = _house_from(p["Moon"]["house"], p["Jupiter"]["house"]) in KENDRA
    add("gajakesari", "Gajakesari Yoga", "गजकेसरी योग", gk,
        "Jupiter sits in a kendra (1/4/7/10th house) counted from the Moon. "
        f"Here Jupiter is in house {_house_from(p['Moon']['house'], p['Jupiter']['house'])} from the Moon.")

    # Budhaditya: Sun and Mercury in the same sign
    ba = p["Sun"]["sign"] == p["Mercury"]["sign"]
    add("budhaditya", "Budhaditya Yoga", "बुधादित्य योग", ba,
        "Sun and Mercury occupy the same sign (Mercury is never far from the Sun, so this is common).")

    # Chandra-Mangala
    cm = p["Moon"]["sign"] == p["Mars"]["sign"]
    add("chandra_mangala", "Chandra-Mangala Yoga", "चंद्र-मंगल योग", cm,
        "Moon and Mars occupy the same sign.")

    # Mangal dosha (Kuja dosha) from lagna: Mars in 1,4,7,8,12
    md = p["Mars"]["house"] in {1, 4, 7, 8, 12}
    add("mangal_dosha", "Mangal Dosha (from Lagna)", "मंगल दोष (लग्न से)", md,
        f"Mars is in house {p['Mars']['house']} from the Lagna. Schools differ: some include the 2nd house, "
        "and many also check from the Moon and Venus; cancellations (parihara) exist and must be weighed.")

    # Pancha Mahapurusha
    mahapurusha = {"Mars": ("ruchaka", "Ruchaka", "रुचक"), "Mercury": ("bhadra", "Bhadra", "भद्र"),
                   "Jupiter": ("hamsa", "Hamsa", "हंस"), "Venus": ("malavya", "Malavya", "मालव्य"),
                   "Saturn": ("shasha", "Shasha", "शश")}
    for planet, (yid, en, hi) in mahapurusha.items():
        pl = p[planet]
        present = pl["dignity"] in ("own", "exalted") and pl["house"] in KENDRA
        add(yid, f"{en} Yoga (Pancha Mahapurusha)", f"{hi} योग (पंच महापुरुष)", present,
            f"{planet} must be in its own or exalted sign and in a kendra from the Lagna. "
            f"Here: dignity={pl['dignity']}, house={pl['house']}.")

    # Kala Sarpa: all seven planets on one side of the Rahu-Ketu axis
    rahu = p["Rahu"]["longitude"]
    seven = [p[n]["longitude"] for n in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")]
    arcs = [((x - rahu) % 360) for x in seven]
    ks = all(a < 180 for a in arcs) or all(a > 180 for a in arcs)
    add("kala_sarpa", "Kala Sarpa Dosha", "कालसर्प दोष", ks,
        "All seven planets (Sun to Saturn) lie between Rahu and Ketu on one side of the axis. "
        "Opinions on its effect vary widely between traditions.")
    return out
