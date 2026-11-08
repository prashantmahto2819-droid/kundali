"""Palmistry v1: a guided checklist. The person (or, later, a vision model) reports what is seen;
this module turns the choices into a reading. It never predicts lifespan, illness or death."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "palm.json"


@lru_cache(maxsize=1)
def knowledge() -> dict:
    return json.loads(_DATA.read_text(encoding="utf-8"))


def catalog() -> dict:
    k = knowledge()
    return {"features": [{"key": f["key"], "group": f["group"], "hi": f["hi"], "where_hi": f["where_hi"],
                          "options": [{"key": ok, "hi": o["hi"]} for ok, o in f["options"].items()]}
                         for f in k["features"]], "general_hi": k["general_hi"]}


def read(choices: dict) -> dict:
    k = knowledge()
    by_key = {f["key"]: f for f in k["features"]}
    if not isinstance(choices, dict) or not choices:
        raise ValueError("choices must be an object like {\"life_length\": \"long\"}")
    traits = []
    for key, opt in choices.items():
        f = by_key.get(key)
        if f is None:
            raise ValueError(f"unknown feature '{key}'")
        o = f["options"].get(opt)
        if o is None:
            raise ValueError(f"unknown option '{opt}' for '{key}' (choose {', '.join(f['options'])})")
        traits.append({"feature": key, "group": f["group"], "feature_hi": f["hi"], "choice": opt,
                       "choice_hi": o["hi"], "meaning_hi": o["meaning_hi"]})
    order = {f["key"]: i for i, f in enumerate(k["features"])}
    traits.sort(key=lambda t: order[t["feature"]])
    groups: dict[str, list] = {}
    for t in traits:
        groups.setdefault(t["group"], []).append(t)
    return {"traits": traits, "groups": groups, "count": len(traits), "confidence": "draft",
            "general_hi": k["general_hi"], "disclaimer_hi": k["disclaimer_hi"]}
