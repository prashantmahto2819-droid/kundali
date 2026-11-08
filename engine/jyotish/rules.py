"""Tiny data-driven rule matcher.

Rules live in data/rules/*.json so scholars can add or correct them without
touching code. A rule looks like::

    {"id": "sun_in_10", "category": "planet_in_house",
     "when": {"planet": "Sun", "house": 10},
     "text_en": "...", "text_hi": "...",
     "source": {"text": "...", "chapter": null, "verse": null},
     "review_status": "draft"}

Supported ``when`` keys (all must match): planet, house, sign (0-11), dignity,
retrograde (bool).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

RULES_DIR = Path(os.environ.get("KUNDALI_RULES_DIR",
                                Path(__file__).resolve().parents[2] / "data" / "rules"))


@lru_cache(maxsize=1)
def load_rules() -> list[dict]:
    rules: list[dict] = []
    if RULES_DIR.is_dir():
        for path in sorted(RULES_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            rules.extend(data.get("rules", []))
    return rules


_NATAL_KEYS = {"planet", "house", "sign", "dignity", "retrograde"}


def _matches(when: dict, planet: dict) -> bool:
    if set(when) - _NATAL_KEYS:                       # e.g. gochara rules (house_from_moon) are not natal rules
        return False
    if "planet" in when and when["planet"] != planet["name"]:
        return False
    if "house" in when and when["house"] != planet["house"]:
        return False
    if "sign" in when and when["sign"] != planet["sign"]:
        return False
    if "dignity" in when and when["dignity"] != planet["dignity"]:
        return False
    if "retrograde" in when and when["retrograde"] != planet["retrograde"]:
        return False
    return True


def gochara_text(planet: str, house_from_moon: int) -> dict | None:
    for rule in load_rules():
        w = rule.get("when", {})
        if w.get("planet") == planet and w.get("house_from_moon") == house_from_moon:
            return {"rule_id": rule["id"], "text_hi": rule.get("text_hi"), "text_en": rule.get("text_en"), "favourable": rule.get("favourable")}
    return None


def match_rules(chart: dict) -> list[dict]:
    out = []
    for rule in load_rules():
        for planet in chart["planets"]:
            if _matches(rule["when"], planet):
                out.append({
                    "rule_id": rule["id"], "category": rule.get("category"),
                    "planet": planet["name"], "house": planet["house"],
                    "text_en": rule.get("text_en"), "text_hi": rule.get("text_hi"),
                    "source": rule.get("source"),
                    "review_status": rule.get("review_status", "draft"),
                    "because": {"planet": planet["name"], "house": planet["house"],
                                "sign": planet["sign_name"], "dignity": planet["dignity"]},
                })
    return out
