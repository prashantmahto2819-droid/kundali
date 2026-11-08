"""Vastu: rate where rooms sit against traditional direction guidance (draft, original wording)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "vastu.json"
SCORE = {"ideal": 2, "ok": 1, "neutral": 0, "avoid": -2}
LABEL_HI = {"ideal": "उत्तम", "ok": "ठीक", "neutral": "सामान्य", "avoid": "टालने योग्य"}


@lru_cache(maxsize=1)
def knowledge() -> dict:
    return json.loads(_DATA.read_text(encoding="utf-8"))


def direction_from_degrees(deg: float) -> str:
    """Compass bearing (0 = north, clockwise) to one of the 8 directions."""
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int(((deg % 360) + 22.5) // 45) % 8]


def rate(room: str, direction: str) -> str:
    r = knowledge()["rooms"][room]
    if direction in r["ideal"]:
        return "ideal"
    if direction in r["ok"]:
        return "ok"
    if direction in r["avoid"]:
        return "avoid"
    return "neutral"


def evaluate(items: list[dict]) -> dict:
    """items: [{"room": key, "direction": "SE" | None, "degrees": float | None}]"""
    k = knowledge()
    out, total, worst = [], 0, 0
    for it in items:
        room = it.get("room")
        if room not in k["rooms"]:
            raise ValueError(f"unknown room '{room}' (choose {', '.join(k['rooms'])})")
        d = it.get("direction")
        if d is None and it.get("degrees") is not None:
            d = direction_from_degrees(float(it["degrees"]))
        if d not in k["directions"]:
            raise ValueError(f"unknown direction '{d}' (choose {', '.join(k['directions'])})")
        r = k["rooms"][room]
        lvl = rate(room, d)
        total += SCORE[lvl]
        worst = min(worst, SCORE[lvl])
        row = {"room": room, "room_hi": r["hi"], "direction": d, "direction_hi": k["directions"][d]["hi"],
               "rating": lvl, "rating_hi": LABEL_HI[lvl], "ideal_hi": [k["directions"][x]["hi"] for x in r["ideal"]],
               "why_hi": r["why_hi"]}
        if lvl == "avoid":
            row["fix_hi"] = r["fix_hi"]
        out.append(row)
    n = len(out)
    return {"items": out, "score": total, "max": 2 * n, "avoid_count": sum(o["rating"] == "avoid" for o in out),
            "general_hi": k["general_hi"], "confidence": "draft",
            "disclaimer_hi": "यह परंपरागत वास्तु-मार्गदर्शन है, वैज्ञानिक या क़ानूनी सलाह नहीं। अलग-अलग परंपराओं में मतभेद हैं।"}
