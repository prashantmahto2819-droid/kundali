"""Offline city search over data/places.json (curated, approximate coordinates)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "places.json"


@lru_cache(maxsize=1)
def _places() -> list[dict]:
    return json.loads(_DATA.read_text(encoding="utf-8"))["places"]


def search(q: str, limit: int = 8) -> list[dict]:
    q = (q or "").strip().casefold()
    if not q:
        return []
    scored = []
    for p in _places():
        names = [p["name"], p["hi"], *p["aka"]]
        best = None
        for n in names:
            n = n.casefold()
            if n == q:
                best = 0
            elif n.startswith(q):
                best = min(best if best is not None else 9, 1)
            elif q in n:
                best = min(best if best is not None else 9, 2)
        if best is not None:
            scored.append((best, p["name"], p))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in scored[:max(1, min(limit, 25))]]
