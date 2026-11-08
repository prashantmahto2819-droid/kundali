"""Tarot: 78-card deck, three spreads, deterministic when a seed is given.

Card meanings live in data/knowledge/tarot.json (own wording, draft). Minor arcana
meanings are composed from rank x suit themes. Tarot here is a reflection tool,
not a prediction engine; the output says so.
"""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "tarot.json"

DISCLAIMER_HI = "टैरो आत्म-चिंतन का साधन है, भविष्यवाणी की गारंटी नहीं। बड़े फ़ैसले (स्वास्थ्य, धन, क़ानून) विशेषज्ञ की सलाह से लीजिए।"


@lru_cache(maxsize=1)
def _knowledge() -> dict:
    return json.loads(_DATA.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def deck() -> list[dict]:
    k = _knowledge()
    cards = []
    for i, m in enumerate(k["majors"]):
        cards.append({"id": f"major-{i:02d}", "name": m["name"], "name_hi": m["hi"], "arcana": "major",
                      "suit": None, "number": i, "element": None,
                      "upright": m["up"], "reversed": m["rev"],
                      "upright_hi": m["up_hi"], "reversed_hi": m["rev_hi"], "confidence": "draft"})
    for suit, s in k["suits"].items():
        for n, r in enumerate(k["ranks"]):
            cid = f"{suit.lower()}-{n + 1:02d}"
            own = k.get("minors", {}).get(cid)                       # per-card text; rank x suit is the fallback
            cards.append({
                "id": cid, "name": f"{r['name']} of {suit}",
                "name_hi": f"{s['hi_obl']} {r.get('gen', 'का')} {r['hi']}", "arcana": "minor", "suit": suit,
                "number": n + 1, "element": s["element"],
                "upright": own["up"] if own else f"{r['up'].capitalize()}, in matters of {s['domain']}.",
                "reversed": own["rev"] if own else f"{r['rev'].capitalize()}, in matters of {s['domain']}.",
                "upright_hi": own["up_hi"] if own else f"{s['domain_hi']} के क्षेत्र में: {r['up_hi']}।",
                "reversed_hi": own["rev_hi"] if own else f"{s['domain_hi']} के क्षेत्र में: {r['rev_hi']}।",
                "theme": f"{r['up']}; {s['domain']}", "theme_hi": f"{r['up_hi']}; {s['domain_hi']}",
                "confidence": "draft"})
    return cards


def spreads() -> dict:
    return _knowledge()["spreads"]


def draw(spread: str = "three", seed: int | str | None = None, reversals: bool = True,
         question: str | None = None) -> dict:
    sp = spreads().get(spread)
    if sp is None:
        raise ValueError(f"unknown spread '{spread}' (choose {', '.join(spreads())})")
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    cards = deck()
    picks = rng.sample(cards, len(sp["positions"]))
    out = []
    for pos, c in zip(sp["positions"], picks):
        rev = bool(reversals and rng.random() < 0.5)
        out.append({"position": pos["key"], "position_hi": pos["hi"], "position_en": pos["en"],
                    "card": {k: c[k] for k in ("id", "name", "name_hi", "arcana", "suit", "number", "element")},
                    "reversed": rev,
                    "meaning": c["reversed"] if rev else c["upright"],
                    "meaning_hi": c["reversed_hi"] if rev else c["upright_hi"],
                    "confidence": c["confidence"]})
    majors = sum(1 for x in out if x["card"]["arcana"] == "major")
    suit_count: dict[str, int] = {}
    for x in out:
        if x["card"]["suit"]:
            suit_count[x["card"]["suit"]] = suit_count.get(x["card"]["suit"], 0) + 1
    notes = []
    if len(out) > 1 and majors * 2 >= len(out):
        notes.append("बहुत से बड़े अर्काना: बड़े जीवन-विषय या मोड़ का संकेत माना जाता है।")
    if suit_count:
        top = max(suit_count.items(), key=lambda kv: kv[1])
        if top[1] >= 3:
            notes.append(f"{top[0]} की प्रधानता ({top[1]} कार्ड): {_knowledge()['suits'][top[0]]['domain_hi']} पर ज़ोर।")
    return {"spread": spread, "spread_name": sp["name"], "spread_name_hi": sp["hi"],
            "question": question, "seed": seed, "reversals": reversals, "cards": out,
            "notes_hi": notes, "disclaimer_hi": DISCLAIMER_HI}
