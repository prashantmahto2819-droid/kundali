"""Framework-independent request handling (shared by FastAPI app and dev server)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import ENGINE_VERSION, compute_chart
from . import matching, numerology, palm, places, tarot, vastu, varshaphal
from .ephemeris import get_backend

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")

_backend = None


def backend():
    global _backend
    if _backend is None:
        _backend = get_backend()
    return _backend


class BadRequest(ValueError):
    pass


def health() -> dict:
    b = backend()
    return {"status": "ok", "engine_version": ENGINE_VERSION, "backend": b.name,
            "production_ready": b.name.startswith("jpl")}


def chart_from_payload(payload: dict) -> dict:
    try:
        date, time_, tz = payload["date"], payload["time"], payload["tz"]
        lat, lon = float(payload["lat"]), float(payload["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BadRequest("Required fields: date (YYYY-MM-DD), time (HH:MM), tz (IANA), lat, lon") from exc
    if not _DATE.match(str(date)) or not _TIME.match(str(time_)):
        raise BadRequest("date must be YYYY-MM-DD and time HH:MM[:SS]")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise BadRequest("lat must be within -90..90 and lon within -180..180 (east positive)")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BadRequest(f"Unknown time zone '{tz}'") from exc
    year_days = float(payload.get("year_days", 365.25))
    if year_days not in (360.0, 365.25, 365.2425):
        raise BadRequest("year_days must be 360, 365.25 or 365.2425")
    as_of = None
    if payload.get("as_of"):
        try:
            as_of = datetime.fromisoformat(str(payload["as_of"]).replace("Z", "+00:00"))
            if as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise BadRequest("as_of must be an ISO-8601 timestamp") from exc
    try:
        return compute_chart(date, time_, tz, lat, lon, name=payload.get("name"),
                             ayanamsa_system=payload.get("ayanamsa", "lahiri"),
                             year_days=year_days, as_of=as_of, backend=backend(),
                             dasha_level=int(payload.get("dasha_level", 2)))
    except ValueError as exc:  # e.g. impossible date like 1990-02-31
        raise BadRequest(str(exc)) from exc


def numerology_from_payload(payload: dict) -> dict:
    try:
        y, m, d = (int(x) for x in str(payload["date"]).split("-"))
        birth = datetime(y, m, d).date()
    except (KeyError, ValueError, TypeError) as exc:
        raise BadRequest("date (YYYY-MM-DD) is required and must be a real date") from exc
    as_of = None
    if payload.get("as_of"):
        try:
            as_of = datetime.fromisoformat(str(payload["as_of"]).replace("Z", "+00:00")).date()
        except ValueError as exc:
            raise BadRequest("as_of must be an ISO-8601 date") from exc
    name = payload.get("name")
    if name is not None and (not isinstance(name, str) or len(name) > 120):
        raise BadRequest("name must be text up to 120 characters")
    return numerology.analyse(birth, name, as_of)


def match_from_payload(payload: dict) -> dict:
    """payload = {"boy": {date,time,tz,lat,lon,name?}, "girl": {...}}"""
    people = {}
    for role in ("boy", "girl"):
        data = payload.get(role)
        if not isinstance(data, dict):
            raise BadRequest(f"'{role}' birth details are required")
        try:
            chart = chart_from_payload({**data, "dasha_level": 1})
        except BadRequest as exc:
            raise BadRequest(f"{role}: {exc}") from exc
        planets = {p["name"]: p for p in chart["planets"]}
        people[role] = {"chart": chart, "moon": planets["Moon"]["longitude"],
                        "manglik": matching.manglik_from(planets["Mars"]["house"], planets["Mars"]["sign"],
                                                         planets["Moon"]["sign"])}
    result = matching.ashtakoota(people["boy"]["moon"], people["girl"]["moon"])
    result["manglik"] = matching.compare_manglik(people["boy"]["manglik"], people["girl"]["manglik"])
    result["backend"] = people["boy"]["chart"]["backend"]
    result["backend_note"] = people["boy"]["chart"]["backend_note"]
    for role in ("boy", "girl"):
        result[role + "_name"] = people[role]["chart"]["input"].get("name")
    return result


def tarot_from_payload(payload: dict) -> dict:
    spread = payload.get("spread", "three")
    seed = payload.get("seed")
    if seed is not None and not isinstance(seed, (int, str)):
        raise BadRequest("seed must be an integer or a string")
    question = payload.get("question")
    if question is not None and (not isinstance(question, str) or len(question) > 300):
        raise BadRequest("question must be text of at most 300 characters")
    try:
        return tarot.draw(spread, seed=seed, reversals=bool(payload.get("reversals", True)),
                          question=question or None)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def places_from_query(q: str, limit: int = 8) -> dict:
    return {"results": places.search(q, limit)}


def report_from_payload(payload: dict) -> str:
    """Printable Hindi HTML report for the same payload as /v1/chart."""
    from . import report
    return report.render(chart_from_payload(payload))


def vastu_from_payload(payload: dict) -> dict:
    items = payload.get("items")
    if not isinstance(items, list) or not items or len(items) > 40:
        raise BadRequest("items must be a list of 1-40 entries like {room, direction}")
    try:
        return vastu.evaluate(items)
    except (ValueError, TypeError, AttributeError) as exc:
        raise BadRequest(str(exc)) from exc


def vastu_catalog() -> dict:
    k = vastu.knowledge()
    return {"rooms": {key: {"hi": r["hi"], "ideal": r["ideal"]} for key, r in k["rooms"].items()},
            "directions": {key: {"hi": d["hi"], "element_hi": d["element_hi"], "lord_hi": d["lord_hi"],
                                 "theme_hi": d["theme_hi"]} for key, d in k["directions"].items()}}


def palm_from_payload(payload: dict) -> dict:
    try:
        return palm.read(payload.get("choices"))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def varshaphal_from_payload(payload: dict) -> dict:
    """Solar-return chart. Body = /v1/chart fields plus `year`; optional return_lat, return_lon, return_tz."""
    natal = chart_from_payload({k: v for k, v in payload.items() if k not in ("year", "return_lat", "return_lon", "return_tz")})
    try:
        year = int(payload["year"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BadRequest("year (e.g. 2027) is required") from exc
    if not 1900 <= year <= 2100:
        raise BadRequest("year must be between 1900 and 2100")
    try:
        lat = float(payload["return_lat"]) if payload.get("return_lat") is not None else None
        lon = float(payload["return_lon"]) if payload.get("return_lon") is not None else None
    except (TypeError, ValueError) as exc:
        raise BadRequest("return_lat and return_lon must be numbers") from exc
    tz = payload.get("return_tz")
    if tz:
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise BadRequest(f"Unknown time zone '{tz}'") from exc
    try:
        return varshaphal.varshaphal(natal, year, lat, lon, tz, backend())
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
