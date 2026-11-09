"""Framework-independent request handling (shared by FastAPI app and dev server)."""
from __future__ import annotations

import os
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
        chart = compute_chart(date, time_, tz, lat, lon, name=payload.get("name"),
                              ayanamsa_system=payload.get("ayanamsa", "lahiri"),
                              year_days=year_days, as_of=as_of, backend=backend(),
                              dasha_level=int(payload.get("dasha_level", 2)),
                              node_type="true" if str(payload.get("node_type", "mean")).lower() == "true" else "mean",
                              outer=bool(payload.get("outer", True)))
    except ValueError as exc:  # e.g. impossible date like 1990-02-31
        raise BadRequest(str(exc)) from exc
    try:                                             # today's and this week's dasha/transit changes for this chart
        from . import alerts
        local_day = (as_of or datetime.now(timezone.utc)).astimezone(ZoneInfo(tz)).date()
        chart["alerts"] = alerts.alerts(chart, local_day, tz)
        chart["alerts"]["personal_day"] = alerts.personal_day(chart, local_day, tz)
    except Exception:                                # never fail the chart for an alert
        chart["alerts"] = {"today": [], "upcoming": [], "personal_day": None}
    return chart


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
    from .dashakoota import dashakoota
    result["dashakoota"] = dashakoota(people["boy"]["moon"], people["girl"]["moon"])
    result["backend"] = people["boy"]["chart"]["backend"]
    result["backend_note"] = people["boy"]["chart"]["backend_note"]
    for role in ("boy", "girl"):
        ch = people[role]["chart"]
        result[role + "_name"] = ch["input"].get("name")
        result[role + "_chart"] = {"lagna": {k: ch["lagna"][k] for k in ("sign", "sign_name", "sign_name_hi", "dms")},
                                   "houses": [{"house": h["house"], "sign": h["sign"], "planets": h["planets"]} for h in ch["houses"]],
                                   "planets": [{k: p[k] for k in ("name", "name_hi", "short_hi", "sign", "sign_name_hi", "house", "degree_in_sign", "dms", "nakshatra_hi", "pada", "retrograde")} for p in ch["planets"]],
                                   "dasha_running": [{"level": d["level"], "lord": d["lord"], "end": d["end"]} for d in ch["dasha_running"]],
                                   "input": ch["input"]}
    return result


def match_report_from_payload(payload: dict) -> str:
    """POST /v1/match/report: printable Hindi HTML of the matching result (same payload as /v1/match, + lang)."""
    from . import i18n, report
    html = report.render_match(match_from_payload(payload), style="south" if str(payload.get("chart_style", "north")).lower() == "south" else "north")
    if str(payload.get("lang", "hi")).lower() == "en":
        html = i18n.translate_html(html.replace('<html lang="hi">', '<html lang="en">', 1))
    return html


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


def brand_for(headers) -> dict | None:
    """The astrologer profile of the signed-in org (API key or login token), or None for anonymous callers."""
    from . import access
    try:
        store = access.default_store()
        org, _err = access.resolve(headers, store)
        if not org:
            return None
        prof = store.get_profile(org["id"])
        return prof if prof.get("brand_name") else None
    except Exception:
        return None


def report_from_payload(payload: dict, brand: dict | None = None) -> str:
    """Printable Hindi HTML report for the same payload as /v1/chart. `brand` = astrologer profile for the header."""
    from . import i18n, report
    style = "south" if str(payload.get("chart_style", "north")).lower() == "south" else "north"
    html = report.render(chart_from_payload(payload), brand=brand, style=style)
    if str(payload.get("lang", "hi")).lower() == "en":
        html = i18n.translate_html(html.replace('<html lang="hi">', '<html lang="en">', 1))
    return html


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


def ask_from_payload(payload: dict) -> dict:
    """POST /v1/ask  {question, lang?, chart?: {date,time,tz,lat,lon}}"""
    from . import ask
    q = payload.get("question")
    if not isinstance(q, str):
        raise BadRequest("question (text, 1-500 characters) is required")
    chart = chart_from_payload(payload["chart"]) if payload.get("chart") else None
    try:
        return ask.ask(q, payload.get("lang"), chart)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def muhurta_from_payload(payload: dict) -> dict:
    """POST /v1/muhurta  {activity, lat, lon, tz, start?: YYYY-MM-DD, days?: 1-60, chart?: birth payload (adds tarabala/chandrabala)}"""
    from . import muhurta_find
    try:
        lat, lon = float(payload.get("lat")), float(payload.get("lon"))
    except (TypeError, ValueError):
        raise BadRequest("lat and lon are required numbers")
    tz = str(payload.get("tz") or "Asia/Kolkata")
    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        raise BadRequest(f"unknown time zone '{tz}'")
    moon = None
    if payload.get("chart"):
        ch = chart_from_payload(payload["chart"])
        moon = next(p for p in ch["planets"] if p["name"] == "Moon")["longitude"]
    start = payload.get("start")
    if start is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(start)):
        raise BadRequest("start must be YYYY-MM-DD")
    try:
        return muhurta_find.find(str(payload.get("activity", "general")), lat, lon, tz, start, int(payload.get("days", 30)), moon)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def prashna_from_payload(payload: dict) -> dict:
    """POST /v1/prashna  {topic, lat, lon, tz, when?: 'YYYY-MM-DD HH:MM' local (default now), kp_number?: 1-249}"""
    from . import prashna
    try:
        lat, lon = float(payload.get("lat")), float(payload.get("lon"))
    except (TypeError, ValueError):
        raise BadRequest("lat and lon are required numbers")
    tz = str(payload.get("tz") or "Asia/Kolkata")
    try:
        zone = ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        raise BadRequest(f"unknown time zone '{tz}'")
    when = payload.get("when")
    if when:
        try:
            when_utc = datetime.strptime(str(when)[:16].replace("T", " "), "%Y-%m-%d %H:%M").replace(tzinfo=zone).astimezone(timezone.utc)
        except ValueError:
            raise BadRequest("when must be 'YYYY-MM-DD HH:MM' (local time)")
    else:
        when_utc = datetime.now(timezone.utc)
    n = payload.get("kp_number")
    if n not in (None, "", 0):
        try:
            n = int(n)
        except (TypeError, ValueError):
            raise BadRequest("kp_number must be 1-249")
        if not 1 <= n <= 249:
            raise BadRequest("kp_number must be 1-249")
    else:
        n = None
    try:
        return prashna.prashna(str(payload.get("topic", "general")), when_utc, lat, lon, backend(), tz, n)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def lalkitab_varshphal_from_payload(payload: dict) -> dict:
    """POST /v1/lalkitab/varshphal  {birth payload..., year?}"""
    from . import lalkitab
    chart = chart_from_payload(payload)
    year = payload.get("year")
    try:
        return lalkitab.varshphal(chart, int(year) if year not in (None, "") else None)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def muhurta_report_from_payload(payload: dict) -> str:
    from . import i18n, report
    html = report.render_muhurta(muhurta_from_payload(payload))
    if str(payload.get("lang", "hi")).lower() == "en":
        html = i18n.translate_html(html.replace('<html lang="hi">', '<html lang="en">', 1))
    return html


def prashna_report_from_payload(payload: dict) -> str:
    from . import i18n, report
    html = report.render_prashna(prashna_from_payload(payload))
    if str(payload.get("lang", "hi")).lower() == "en":
        html = i18n.translate_html(html.replace('<html lang="hi">', '<html lang="en">', 1))
    return html


def _localize(html: str, payload: dict) -> str:
    from . import i18n
    if str(payload.get("lang", "hi")).lower() == "en":
        return i18n.translate_html(html.replace('<html lang="hi">', '<html lang="en">', 1))
    return html


def numerology_report_from_payload(payload: dict) -> str:
    import json as _json
    from pathlib import Path
    from . import report
    kb = _json.loads((Path(__file__).resolve().parents[2] / "data" / "knowledge" / "numbers.json").read_text(encoding="utf-8")).get("numbers", {})
    return _localize(report.render_numerology(numerology_from_payload(payload), payload.get("name"), str(payload.get("date", "")), kb), payload)


def tarot_report_from_payload(payload: dict) -> str:
    from . import report
    return _localize(report.render_tarot(tarot_from_payload(payload)), payload)


def vastu_report_from_payload(payload: dict) -> str:
    from . import report
    return _localize(report.render_vastu(vastu_from_payload(payload)), payload)


def palm_report_from_payload(payload: dict) -> str:
    from . import report
    return _localize(report.render_palm(palm_from_payload(payload)), payload)


REPORT_ROUTES = {"/v1/report": None, "/v1/match/report": "match_report_from_payload", "/v1/muhurta/report": "muhurta_report_from_payload",
                 "/v1/prashna/report": "prashna_report_from_payload", "/v1/numerology/report": "numerology_report_from_payload",
                 "/v1/tarot/report": "tarot_report_from_payload", "/v1/vastu/report": "vastu_report_from_payload", "/v1/vastu/plan/report": "vastu_plan_report_from_payload", "/v1/palm/report": "palm_report_from_payload",
                 "/v1/palm/trace/report": "palm_trace_report_from_payload", "/v1/panchang/calendar/report": "calendar_report_from_payload", "/v1/rashifal/report": "rashifal_report_from_payload"}


# ---- JSON safety net ------------------------------------------------------------------
def plain(obj):
    """Recursively turn numpy scalars/arrays (e.g. numpy.bool_ from the JPL backend) into plain Python."""
    if isinstance(obj, dict):
        return {k: plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    if hasattr(obj, "tolist") and not isinstance(obj, (str, bytes)):
        return plain(obj.tolist())
    if hasattr(obj, "item") and type(obj).__module__ == "numpy":
        return obj.item()
    return obj


def _wrap(fn):
    def inner(*a, **k):
        return plain(fn(*a, **k))
    inner.__name__, inner.__doc__ = fn.__name__, fn.__doc__
    return inner


for _n in [n for n in list(globals()) if n.endswith("_from_payload") or n.endswith("_from_query") or n in ("vastu_catalog",)]:
    globals()[_n] = _wrap(globals()[_n])


def rectify_from_payload(payload: dict) -> dict:
    """POST /v1/rectify  {date, time, tz, lat, lon, range_min?: 5-720, step_min?: 1-10, events?: [{type, year, month?}]}"""
    from . import rectify
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
    try:
        range_min = int(payload.get("range_min", 120)); step_min = int(payload.get("step_min", 2))
    except (TypeError, ValueError):
        raise BadRequest("range_min and step_min must be integers")
    if not 5 <= range_min <= 720 or not 1 <= step_min <= 10:
        raise BadRequest("range_min must be 5-720 and step_min 1-10")
    events = payload.get("events") or []
    if not isinstance(events, list) or len(events) > 12:
        raise BadRequest("events must be a list of up to 12 entries like {type, year}")
    clean = []
    for ev in events:
        if not isinstance(ev, dict) or ev.get("type") not in rectify.EVENT_HOUSES:
            raise BadRequest(f"event type must be one of {', '.join(rectify.EVENT_HOUSES)}")
        try:
            year = int(ev.get("year")); month = int(ev.get("month") or 7)
        except (TypeError, ValueError):
            raise BadRequest("event year must be an integer")
        if not 1900 <= year <= 2100 or not 1 <= month <= 12:
            raise BadRequest("event year must be 1900-2100 and month 1-12")
        clean.append({"type": ev["type"], "year": year, "month": month})
    try:
        return rectify.rectify(str(date), str(time_)[:5], tz, lat, lon, range_min, step_min, clean)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def vastu_plan_upload_from_payload(payload: dict) -> dict:
    """POST /v1/vastu/plan  {filename, content_b64}  → PNG of the plan (PDF page 1 / DXF drawing / image)."""
    import base64, binascii
    from . import vastu_plan
    b64 = payload.get("content_b64")
    if not isinstance(b64, str) or not b64:
        raise BadRequest("content_b64 (base64 of the file) is required")
    if "," in b64[:80] and b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    if len(b64) > 17 * 1024 * 1024:
        raise BadRequest("file is larger than 12 MB")
    try:
        data = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise BadRequest("content_b64 is not valid base64") from exc
    try:
        return vastu_plan.convert_upload(str(payload.get("filename") or ""), data)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    except Exception as exc:                      # a damaged PDF/image: say so instead of a 500
        raise BadRequest(f"could not read the file ({type(exc).__name__})") from exc


def vastu_plan_from_payload(payload: dict) -> dict:
    """POST /v1/vastu/zones  {polygon: [[x,y]...], north_angle, rooms: [{room, x, y}], lat?, lon?}"""
    from . import vastu_plan
    try:
        out = vastu_plan.evaluate_plan(payload)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    for k in ("lat", "lon", "place"):
        if payload.get(k) not in (None, ""):
            out[k] = payload[k]
    return out


def vastu_plan_catalog() -> dict:
    from . import vastu_plan
    z = vastu_plan.zones_data()
    return {"rooms": vastu_plan.room_catalog(), "zones": z["zones"], "mandala": z["mandala"], "review_status": z["review_status"]}


def vastu_plan_report_from_payload(payload: dict) -> str:
    from . import report
    return _localize(report.render_vastu_plan(vastu_plan_from_payload(payload)), payload)


def palm_trace_from_payload(payload: dict) -> dict:
    """POST /v1/palm/trace  {landmarks: {wrist,index,middle,ring,little,thumb: [x,y]}, lines: {life,head,heart,fate?,sun?: [[x,y]...]},
    marks?: [{line, type, x?, y?}], extras?: {union_lines, bracelets, travel_lines, girdle_of_venus: n}, choices?: {feature: option}}"""
    from . import palm_trace
    marks = payload.get("marks") or []
    if not isinstance(marks, list) or len(marks) > 30:
        raise BadRequest("marks must be a list of up to 30 entries")
    try:
        return palm_trace.trace(payload)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise BadRequest(str(exc) or "invalid tracing data") from exc


def palm_trace_catalog() -> dict:
    from . import palm, palm_trace
    k = palm.knowledge()
    return {"landmarks": [{"key": x, "hi": palm_trace.LANDMARK_HI[x], "en": palm_trace.LANDMARK_EN[x]} for x in palm_trace.LANDMARKS],
            "lines": k["lines"], "marks": {m: {"hi": v["hi"], "en": v["en"]} for m, v in k["marks"].items()},
            "extras": {e: {"hi": v["hi"], "en": v["en"]} for e, v in k["extras"].items()},
            "manual_features": [f["key"] for f in k["features"] if f["key"] in ("hand_shape", "life_depth") or f["key"].startswith("mount_")],
            "trace_note_hi": k["trace_note_hi"], "trace_note": k["trace_note"]}


def palm_trace_report_from_payload(payload: dict) -> str:
    from . import report
    return _localize(report.render_palm_trace(palm_trace_from_payload(payload)), payload)


def festivals_from_query(q: dict) -> dict:
    """GET /v1/festivals?year=2026&lat=..&lon=..&tz=Asia/Kolkata"""
    from . import festivals
    try:
        year = int(q.get("year") or datetime.now(timezone.utc).year)
        lat = float(q.get("lat") or 28.61); lon = float(q.get("lon") or 77.2)
    except (TypeError, ValueError):
        raise BadRequest("year, lat and lon must be numbers")
    tz = q.get("tz") or "Asia/Kolkata"
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BadRequest(f"Unknown time zone '{tz}'") from exc
    if not 1950 <= year <= 2099 or not (-66 <= lat <= 66) or not (-180 <= lon <= 180):
        raise BadRequest("year must be 1950-2099 and lat within -66..66")
    return festivals.calendar(year, lat, lon, tz)


def panchang_month_from_query(q: dict) -> dict:
    """GET /v1/panchang/month?year=2026&month=11&lat=..&lon=..&tz=Asia/Kolkata"""
    from . import panchang_month
    try:
        year = int(q.get("year") or datetime.now(timezone.utc).year); mon = int(q.get("month") or datetime.now(timezone.utc).month)
        lat = float(q.get("lat") or 28.61); lon = float(q.get("lon") or 77.2)
    except (TypeError, ValueError):
        raise BadRequest("year, month, lat and lon must be numbers")
    tz = q.get("tz") or "Asia/Kolkata"
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BadRequest(f"Unknown time zone '{tz}'") from exc
    if not 1950 <= year <= 2099 or not 1 <= mon <= 12 or not (-66 <= lat <= 66) or not (-180 <= lon <= 180):
        raise BadRequest("year 1950-2099, month 1-12, lat within -66..66")
    return panchang_month.month(year, mon, lat, lon, tz)


def calendar_report_from_payload(payload: dict) -> str:
    """POST /v1/panchang/calendar/report  {year, month?: 1-12 (omit or 'all' for twelve pages), lat, lon, tz, lang?, design: {...}}"""
    from . import calendar_design
    try:
        year = int(payload.get("year") or datetime.now(timezone.utc).year)
        lat = float(payload.get("lat") or 28.61); lon = float(payload.get("lon") or 77.2)
    except (TypeError, ValueError):
        raise BadRequest("year, lat and lon must be numbers")
    tz = payload.get("tz") or "Asia/Kolkata"
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BadRequest(f"Unknown time zone '{tz}'") from exc
    if not 1950 <= year <= 2099 or not (-66 <= lat <= 66):
        raise BadRequest("year 1950-2099, lat within -66..66")
    mon = payload.get("month")
    if mon in (None, "", "all", 0):
        months = list(range(1, 13))
    else:
        try:
            mon = int(mon)
        except (TypeError, ValueError):
            raise BadRequest("month must be 1-12 or 'all'")
        if not 1 <= mon <= 12:
            raise BadRequest("month must be 1-12 or 'all'")
        months = [mon]
    design = payload.get("design") or {}
    if not isinstance(design, dict):
        raise BadRequest("design must be an object")
    for k in ("notes", "holidays"):
        if design.get(k) and (not isinstance(design[k], list) or len(design[k]) > 400):
            raise BadRequest(f"design.{k} must be a list of up to 400 entries")
    lang = "en" if str(payload.get("lang", "hi")).lower() == "en" else "hi"
    return calendar_design.render_calendar(year, months, lat, lon, tz, design, lang)


def muhurta_lagna_from_payload(payload: dict) -> dict:
    """POST /v1/muhurta/lagna  {date: YYYY-MM-DD, lat, lon, tz, activity?: marriage|general, groom_moon_sign?: 0-11, bride_moon_sign?: 0-11}"""
    from . import muhurta_lagna
    try:
        lat, lon = float(payload.get("lat")), float(payload.get("lon"))
    except (TypeError, ValueError):
        raise BadRequest("lat and lon are required numbers")
    tz = str(payload.get("tz") or "Asia/Kolkata")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise BadRequest(f"unknown time zone '{tz}'")
    day = str(payload.get("date") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise BadRequest("date must be YYYY-MM-DD")
    signs = {}
    for k, top in (("groom_moon_sign", 11), ("bride_moon_sign", 11), ("groom_nakshatra", 26), ("bride_nakshatra", 26)):
        v = payload.get(k)
        if v in (None, ""):
            signs[k] = None; continue
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise BadRequest(f"{k} must be 0-{top}")
        if not 0 <= v <= top:
            raise BadRequest(f"{k} must be 0-{top}")
        signs[k] = v
    activity = str(payload.get("activity") or "marriage")
    try:
        return muhurta_lagna.lagna_muhurta(day, lat, lon, tz, activity, **signs)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def rashifal_from_query(q: dict) -> dict:
    """GET /v1/rashifal?date=YYYY-MM-DD&period=daily|weekly|monthly&tz=Asia/Kolkata"""
    from . import rashifal
    day = str(q.get("date") or datetime.now(timezone.utc).date().isoformat())
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise BadRequest("date must be YYYY-MM-DD")
    period = str(q.get("period") or "daily")
    if period not in ("daily", "weekly", "monthly"):
        raise BadRequest("period must be daily, weekly or monthly")
    tz = str(q.get("tz") or "Asia/Kolkata")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise BadRequest(f"unknown time zone '{tz}'")
    try:
        return rashifal.rashifal(day, tz, period)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def rashifal_report_from_payload(payload: dict) -> str:
    from . import report
    return _localize(report.render_rashifal(rashifal_from_query(payload)), payload)


def panchang_today_from_query(q: dict) -> dict:
    """GET /v1/panchang/day?date=YYYY-MM-DD&lat&lon&tz — one day's sunrise panchang with end times, festivals and kaal."""
    from . import panchang_month
    day = str(q.get("date") or datetime.now(ZoneInfo(str(q.get("tz") or "Asia/Kolkata"))).date().isoformat()) if _tz_ok(q.get("tz")) else None
    if not day or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise BadRequest("date must be YYYY-MM-DD and tz a valid zone")
    try:
        lat = float(q.get("lat") or 28.61); lon = float(q.get("lon") or 77.2)
        y, m, d = (int(x) for x in day.split("-"))
    except (TypeError, ValueError):
        raise BadRequest("lat, lon and date must be valid")
    if not 1950 <= y <= 2099 or not (-66 <= lat <= 66):
        raise BadRequest("year 1950-2099, lat within -66..66")
    out = panchang_month.month(y, m, lat, lon, str(q.get("tz") or "Asia/Kolkata"), only_day=d)
    if not out["days"]:
        raise BadRequest("no sunrise on that date at this latitude")
    row = {**out["days"][0], "tz": out["tz"], "lat": lat, "lon": lon}
    lang = str(q.get("lang") or "")
    if lang in ("te", "kn", "mr", "gu", "bn"):
        from . import regional
        row = regional.localize_day(row, lang)
    return row


def _tz_ok(tz) -> bool:
    try:
        ZoneInfo(str(tz or "Asia/Kolkata")); return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


# ---------------------------------------------------------------- WhatsApp updates (Vivid Relay)
def _notify_call(fn, payload: dict) -> dict:
    from . import notify
    try:
        return getattr(notify, fn)(payload if isinstance(payload, dict) else {})
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def notify_subscribe_from_payload(payload: dict) -> dict:
    """POST /v1/notify/subscribe — save the subscription and send a one-time code over WhatsApp."""
    return _notify_call("start_subscription", payload)


def notify_verify_from_payload(payload: dict) -> dict:
    return _notify_call("verify", payload)


def notify_unsubscribe_from_payload(payload: dict) -> dict:
    return _notify_call("unsubscribe", payload)


def notify_status_from_payload(payload: dict) -> dict:
    return _notify_call("status", payload)


def notify_preview_from_payload(payload: dict) -> dict:
    """POST /v1/notify/preview — today's daily and weekly texts for these settings, nothing sent."""
    return _notify_call("preview", payload)


def start_notify_worker_if_enabled() -> bool:
    """Start the once-a-minute sender thread when KUNDALI_NOTIFY=1 (and only once per process)."""
    if os.environ.get("KUNDALI_NOTIFY", "") not in ("1", "true", "yes"):
        return False
    from . import notify
    if getattr(notify, "_worker_started", False):
        return True
    notify.start_worker()
    notify._worker_started = True
    return True


def notify_webhook(body: bytes, headers: dict) -> dict:
    """POST /v1/notify/webhook — Vivid Relay delivers inbound WhatsApp messages here; the bot answers through Relay."""
    from . import wa_bot
    return wa_bot.handle_webhook(body, headers)


# ---------------------------------------------------------------- AI (multi-provider chat, palm photo)
def _ai_who(payload: dict) -> str:
    return str(payload.get("user_id") or payload.get("phone") or payload.get("client_id") or "anon")[:80]


def ai_status_from_payload(payload: dict | None = None) -> dict:
    from . import llm
    provs = llm.configured()
    return {"available": bool(provs), "providers": [{"name": p["name"], "model": p["model"], "vision": bool(p.get("vision"))} for p in provs],
            "daily_quota": int(os.environ.get("AI_DAILY_QUOTA", "30"))}


def ai_chat_from_payload(payload: dict) -> dict:
    """POST /v1/ai/chat  {messages:[{role,content}], lang?, birth?|chart?, lat?, lon?, tz?, user_id?|phone?|client_id?}"""
    from . import ai, access
    try:
        return ai.chat(payload, store=access.default_store(), who=_ai_who(payload))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def ai_palm_from_payload(payload: dict) -> dict:
    """POST /v1/ai/palm  {content_b64, mime?, hand?, lang?}"""
    import base64
    from . import ai, access
    b64 = payload.get("content_b64")
    if not isinstance(b64, str) or not b64:
        raise BadRequest("content_b64 (base64 of the photo) is required")
    mime = "image/jpeg"
    if b64.startswith("data:"):
        head, b64 = b64.split(",", 1)
        mime = head[5:].split(";")[0] or mime
    try:
        data = base64.b64decode(b64, validate=False)
    except Exception as exc:
        raise BadRequest("content_b64 is not valid base64") from exc
    try:
        return ai.palm_scan(data, mime=str(payload.get("mime") or mime), lang=payload.get("lang") or "hi", hand=str(payload.get("hand") or "right"),
                            store=access.default_store(), who=_ai_who(payload))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


# ---------------------------------------------------------------- consultation with astrologers + wallet
def _consult_call(fn, *args, **kw):
    from . import consult
    try:
        return getattr(consult, fn)(*args, **kw)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def consult_astrologers_from_query(_q: dict | None = None) -> dict:
    from . import consult
    return {"astrologers": consult.list_astrologers(), "paid": consult.paid(), "modes": {k: {"hi": v[0], "en": v[1]} for k, v in consult.MODES.items()}}


def consult_request_from_payload(payload: dict) -> dict:
    return _consult_call("create_request", payload)


def consult_get_from_payload(payload: dict, headers: dict | None = None) -> dict:
    from . import consult
    return _consult_call("get_request", str(payload.get("id") or ""), payload.get("phone"), admin=consult.is_admin(headers or {}))


def consult_mine_from_payload(payload: dict) -> dict:
    return {"requests": _consult_call("my_requests", payload.get("phone"))}


def consult_message_from_payload(payload: dict, headers: dict | None = None) -> dict:
    from . import consult
    return _consult_call("post_message", str(payload.get("id") or ""), str(payload.get("sender") or "seeker"), str(payload.get("text") or ""), payload.get("phone"), admin=consult.is_admin(headers or {}))


def consult_close_from_payload(payload: dict, headers: dict | None = None) -> dict:
    from . import consult
    return _consult_call("close_request", str(payload.get("id") or ""), payload.get("phone"), payload.get("rating"), admin=consult.is_admin(headers or {}))


def wallet_from_payload(payload: dict) -> dict:
    return _consult_call("wallet_view", payload.get("phone"))


def consult_admin_from_payload(payload: dict, headers: dict | None = None) -> dict:
    """POST /v1/consult/admin {action: overview|astrologer|topup, ...}  — X-Admin-Key required."""
    from . import consult
    if not consult.is_admin(headers or {}):
        raise BadRequest("admin key required (X-Admin-Key)")
    action = str(payload.get("action") or "overview")
    if action == "dashboard":
        return consult.admin_dashboard()
    if action == "subscriber":
        return _consult_call("admin_set_subscriber", payload.get("phone"), payload.get("fields") or {})
    if action == "override":
        return _consult_call("admin_save_override", int(payload.get("year") or 0), payload.get("data") or {})
    if action == "send_test":
        from . import notify
        res = notify.send_whatsapp(notify.normalize_phone(payload.get("phone")), str(payload.get("text") or "कुंडली ऐप: परीक्षण संदेश ✅"))
        return res
    if action == "astrologer":
        return _consult_call("upsert_astrologer", payload.get("astrologer") or {})
    if action == "topup":
        return _consult_call("topup", payload.get("phone"), int(payload.get("amount") or 0), str(payload.get("ref") or ""), str(payload.get("note") or ""))
    return consult.admin_overview()


def eclipse_from_query(q: dict) -> dict:
    """GET /v1/panchang/eclipse?year=YYYY&lat&lon&tz[&date=YYYY-MM-DD] — the year's eclipses with local circumstances and sutak."""
    from . import panchang_extra as px
    try:
        year = int(q.get("year") or str(q.get("date") or "")[:4] or datetime.now(timezone.utc).year)
        lat = float(q.get("lat") or 28.61); lon = float(q.get("lon") or 77.2)
    except (TypeError, ValueError):
        raise BadRequest("year, lat, lon must be numbers")
    tz = str(q.get("tz") or "Asia/Kolkata")
    if not _tz_ok(tz) or not 1950 <= year <= 2099:
        raise BadRequest("tz must be a valid zone and year 1950-2099")
    ecs = px.eclipses(year, tz)
    if q.get("date"):
        ecs = [e for e in ecs if e["date"] == q["date"]]
    return {"year": year, "lat": lat, "lon": lon, "tz": tz, "eclipses": [px.eclipse_local(e, lat, lon, tz) for e in ecs],
            "note_hi": "स्थानीय स्पर्श-मध्य-मोक्ष, दृश्यता और सूतक इस स्थान के लिए (चंद्र ग्रहण ±2 मिनट, सूर्य ग्रहण ±15 मिनट); परंपरा: सूर्य ग्रहण का सूतक 12 घंटे, चंद्र का 9 घंटे पहले; उपच्छाया ग्रहण का सूतक नहीं।",
            "note_en": "Local contacts, visibility and sutak for this place (lunar ±2 min, solar ±15 min); tradition: sutak 12 h before a solar, 9 h before a lunar eclipse; none for penumbral eclipses."}


def ai_summary_from_payload(payload: dict) -> dict:
    """POST /v1/ai/summary {kind: chart|match|varshaphal, body: {...}, lang?}"""
    from . import ai, access
    if not isinstance(payload.get("body"), dict) and not isinstance(payload.get("chart"), dict):
        raise BadRequest("body (the request used for the chart/match/varshaphal) is required")
    try:
        return ai.summary(payload, store=access.default_store(), who=_ai_who(payload))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def ai_calendar_text_from_payload(payload: dict) -> dict:
    from . import ai, access
    try:
        return ai.calendar_text(payload, store=access.default_store(), who=_ai_who(payload))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def ai_quiz_from_payload(payload: dict) -> dict:
    from . import ai, access
    try:
        return ai.quiz(payload, store=access.default_store(), who=_ai_who(payload))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def consult_draft_from_payload(payload: dict, headers: dict | None = None) -> dict:
    """POST /v1/consult/draft {id, phone (astrologer's)} — AI first draft for the assigned astrologer or admin."""
    from . import ai, consult, access, notify
    rid = str(payload.get("id") or "")
    admin = consult.is_admin(headers or {})
    req = _consult_call("get_request", rid, None, admin=True)
    if not admin:
        a = next((x for x in consult.list_astrologers(include_inactive=True) if x["id"] == req["astrologer_id"]), None)
        row = consult._rows("SELECT phone FROM astrologers WHERE id=?", (req["astrologer_id"],))
        if not (payload.get("phone") and row and row[0]["phone"] and notify.normalize_phone(payload["phone"]) == row[0]["phone"]):
            raise BadRequest("only the assigned astrologer (or admin) can request a draft")
    try:
        return ai.consult_draft(req, store=access.default_store(), who="astro:" + rid)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


def ai_extract_rules_from_payload(payload: dict, headers: dict | None = None) -> dict:
    """POST /v1/ai/extract_rules {text, source, save?: true} — admin only; drafts land in data/rules/drafts/."""
    from . import ai, consult
    if not consult.is_admin(headers or {}):
        raise BadRequest("admin key required (X-Admin-Key)")
    try:
        out = ai.extract_rules(str(payload.get("text") or ""), str(payload.get("source") or "unknown"), payload.get("lang") or "hi")
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    if payload.get("save") and out["rules"]:
        import json as _json, re as _re
        from pathlib import Path
        d = (Path(os.environ["KUNDALI_DB"]).resolve().parent / "rules_drafts") if os.environ.get("KUNDALI_DB") else (Path(__file__).resolve().parents[2] / "data" / "rules" / "drafts")
        d.mkdir(parents=True, exist_ok=True)
        name = _re.sub(r"[^a-z0-9_-]", "_", str(payload.get("source") or "draft").lower())[:40] + "_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + ".json"
        (d / name).write_text(_json.dumps({"source": payload.get("source"), "review_status": "draft", "rules": out["rules"]}, ensure_ascii=False, indent=1), "utf-8")
        out["saved_as"] = str(d / name)
    return out


def i18n_languages() -> dict:
    """GET /v1/i18n/languages — UI language packs present as data/i18n_<code>.json."""
    import json as _json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "data"
    out = []
    for f in sorted(root.glob("i18n_*.json")):
        code = f.stem.split("_", 1)[1]
        name = {"en": "English", "te": "తెలుగు", "kn": "ಕನ್ನಡ", "mr": "मराठी", "gu": "ગુજરાતી", "bn": "বাংলা", "ta": "தமிழ்", "ml": "മലയാളം", "pa": "ਪੰਜਾਬੀ", "or": "ଓଡ଼ିଆ", "ne": "नेपाली"}.get(code)
        if not name:
            try:
                name = _json.loads(f.read_text("utf-8")).get("name", code)
            except ValueError:
                name = code
        out.append({"code": code, "name": name})
    return {"languages": out}


def year_ahead_from_payload(payload: dict) -> dict:
    """POST /v1/chart/year_ahead — 12-month transit table with Ashtakavarga bindus and change dates for this chart."""
    from . import alerts
    chart = chart_from_payload(payload)
    tz = chart["input"]["tz"]
    start = datetime.now(ZoneInfo(tz)).date()
    if payload.get("from"):
        try:
            start = datetime.fromisoformat(str(payload["from"])).date()
        except ValueError:
            raise BadRequest("from must be YYYY-MM-DD")
    months = max(1, min(24, int(payload.get("months", 12))))
    return alerts.year_ahead(chart, start, tz, months)


def panchang_card_from_query(q: dict) -> bytes:
    """GET /v1/panchang/card.png?date&lat&lon&tz&lang&place&theme&name&tagline → PNG."""
    from . import card, panchang_month
    try:
        d = datetime.fromisoformat(str(q.get("date") or datetime.now(timezone.utc).date().isoformat())).date()
        lat = float(q.get("lat") or 28.61); lon = float(q.get("lon") or 77.2)
    except (TypeError, ValueError):
        raise BadRequest("date must be YYYY-MM-DD and lat/lon numbers")
    tz = str(q.get("tz") or "Asia/Kolkata")
    if not _tz_ok(tz):
        raise BadRequest("unknown tz")
    m = panchang_month.month(d.year, d.month, lat, lon, tz, only_day=d.day)
    if not m["days"]:
        raise BadRequest("no sunrise on that date at this latitude")
    biz = {"name": str(q.get("name") or os.environ.get("KUNDALI_BRAND_NAME", ""))[:60], "tagline": str(q.get("tagline") or os.environ.get("KUNDALI_BRAND_TAGLINE", ""))[:80],
           "website": str(q.get("website") or os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com").replace("https://", ""))[:60]}
    return card.render_panchang_card(m["days"][0], d, str(q.get("place") or "")[:40], "en" if q.get("lang") == "en" else "hi", biz, str(q.get("theme") or "saffron"))
