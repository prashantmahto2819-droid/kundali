"""Framework-independent request handling (shared by FastAPI app and dev server)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import ENGINE_VERSION, compute_chart
from . import numerology
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
