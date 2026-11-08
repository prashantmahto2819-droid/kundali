"""Saved people (birth data) per organisation.

Only the birth input is stored; charts are recomputed on demand, so an engine fix
automatically improves every saved chart. Every query is scoped by org_id, so one
organisation can never read or delete another's records.

REST (shared by devserver.py and app.py):
    POST   /v1/people            {name, date, time, tz, lat, lon, [place, note]}
    GET    /v1/people
    GET    /v1/people/{id}
    GET    /v1/people/{id}/chart
    PUT    /v1/people/{id}       {name?, place?, note?}   (astrologer's private note, up to 2000 characters)
    DELETE /v1/people/{id}
    GET    /v1/me                 org, plan, profile (branding for reports)
    PUT    /v1/me                 {brand_name, phone, line, address, website}
Always requires a valid API key or a Supabase login token (even when KUNDALI_AUTH=off), because the data belongs to an org.
"""
from __future__ import annotations

import json
import re
import secrets

from . import access, handlers

MAX_PEOPLE = 500
_FIELDS = ("date", "time", "tz", "lat", "lon")
_ID = re.compile(r"^p_[A-Za-z0-9_-]{6,}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS people(id TEXT PRIMARY KEY, org_id TEXT NOT NULL, name TEXT NOT NULL,
  birth TEXT NOT NULL, place TEXT, note TEXT, created TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS people_org ON people(org_id);
"""


def _row(r) -> dict:
    return {"id": r["id"], "name": r["name"], "birth": json.loads(r["birth"]),
            "place": r["place"], "note": r["note"], "created": r["created"]}


def add(store, org_id: str, payload: dict) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 80:
        raise handlers.BadRequest("name is required (max 80 characters)")
    handlers.chart_from_payload(payload)                      # validates date/time/tz/lat/lon
    birth = {k: payload[k] for k in _FIELDS}
    pid = "p_" + secrets.token_urlsafe(9)
    with store._lock:
        n = store._db.execute("SELECT COUNT(*) FROM people WHERE org_id=?", (org_id,)).fetchone()[0]
        if n >= MAX_PEOPLE:
            raise handlers.BadRequest(f"limit of {MAX_PEOPLE} saved people reached")
        store._db.execute("INSERT INTO people VALUES(?,?,?,?,?,?,?)",
                          (pid, org_id, name, json.dumps(birth), str(payload.get("place", ""))[:120],
                           str(payload.get("note", ""))[:500], access._now().isoformat()))
        store._db.commit()
    return get(store, org_id, pid)


def get(store, org_id: str, pid: str) -> dict | None:
    with store._lock:
        r = store._db.execute("SELECT * FROM people WHERE id=? AND org_id=?", (pid, org_id)).fetchone()
    return _row(r) if r else None


def listing(store, org_id: str) -> list[dict]:
    with store._lock:
        rows = store._db.execute("SELECT * FROM people WHERE org_id=? ORDER BY created DESC", (org_id,)).fetchall()
    return [_row(r) for r in rows]


def update(store, org_id: str, pid: str, payload: dict) -> dict | None:
    sets, vals = [], []
    if "name" in payload:
        name = str(payload["name"]).strip()
        if not name or len(name) > 80:
            raise handlers.BadRequest("name is required (max 80 characters)")
        sets.append("name=?"); vals.append(name)
    if "place" in payload:
        sets.append("place=?"); vals.append(str(payload["place"] or "")[:120])
    if "note" in payload:
        sets.append("note=?"); vals.append(str(payload["note"] or "")[:2000])
    if not sets:
        raise handlers.BadRequest("nothing to update (name, place or note)")
    with store._lock:
        store._db.execute(f"UPDATE people SET {', '.join(sets)} WHERE id=? AND org_id=?", (*vals, pid, org_id))
        store._db.commit()
    return get(store, org_id, pid)


def remove(store, org_id: str, pid: str) -> bool:
    with store._lock:
        cur = store._db.execute("DELETE FROM people WHERE id=? AND org_id=?", (pid, org_id))
        store._db.commit()
    return cur.rowcount > 0


def api(method: str, path: str, headers, payload: dict | None = None, store=None) -> tuple[int, dict]:
    """Route /v1/people*. Returns (status, body)."""
    store = store or access.default_store()
    org, err = access.resolve(headers, store)
    if org is None:
        return 401, {"detail": err or "sign in or send an API key to use saved people"}
    clean = path.split("?")[0]
    if clean.rstrip("/") == "/v1/me":
        if method == "GET":
            return 200, {"org": {"id": org["id"], "name": org["name"], "plan": org["plan"]}, "profile": store.get_profile(org["id"])}
        if method == "PUT":
            return 200, {"profile": store.set_profile(org["id"], payload or {})}
        return 405, {"detail": "GET or PUT"}
    parts = [p for p in clean.split("/") if p][2:]       # after v1/people
    try:
        if not parts:
            if method == "POST":
                return 201, add(store, org["id"], payload or {})
            if method == "GET":
                return 200, {"people": listing(store, org["id"])}
        elif _ID.match(parts[0]):
            person = get(store, org["id"], parts[0])
            if person is None:
                return 404, {"detail": "not found"}
            if len(parts) == 1 and method == "GET":
                return 200, person
            if len(parts) == 1 and method == "PUT":
                return 200, update(store, org["id"], parts[0], payload or {})
            if len(parts) == 1 and method == "DELETE":
                remove(store, org["id"], parts[0])
                return 200, {"deleted": parts[0]}
            if parts[1:] == ["chart"] and method == "GET":
                return 200, {"person": person, "chart": handlers.chart_from_payload(person["birth"])}
    except handlers.BadRequest as exc:
        return 422, {"detail": str(exc)}
    return 404, {"detail": "not found"}
