"""WhatsApp daily updates through Vivid Relay (the user's own WhatsApp gateway).

Subscriptions live in the access SQLite store (table wa_subs). A subscriber gives a phone number, place, a delivery
time and what they want: the day's panchang (tithi with its end time and the next tithi, nakshatra, sunrise/sunset,
moonrise, Rahu kaal, special yogas, festivals), their own rashifal (Moon sign from their birth details), a vrat /
festival alert the day before (with the tithi window: when it begins and ends, so two-tithi days are clear), and a
weekly summary. Numbers are verified with a one-time code sent over WhatsApp. A worker thread (KUNDALI_NOTIFY=1)
checks every minute which subscribers are due in their own time zone and sends through
POST {RELAY_URL}/api/sessions/{RELAY_SESSION}/send with the Relay API key. Nothing predictive is sent: the texts are
the app's own tendency-level panchang and rashifal.
"""
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import threading
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import access, panchang_month, rashifal as rashifal_mod

SCHEMA = """
CREATE TABLE IF NOT EXISTS wa_subs(
  phone TEXT PRIMARY KEY, name TEXT, lang TEXT NOT NULL DEFAULT 'hi', tz TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  lat REAL NOT NULL, lon REAL NOT NULL, place TEXT,
  birth TEXT, moon_sign INTEGER, moon_sign_name TEXT,
  daily_time TEXT NOT NULL DEFAULT '06:30', want_panchang INTEGER NOT NULL DEFAULT 1, want_rashifal INTEGER NOT NULL DEFAULT 1,
  vrat_alert INTEGER NOT NULL DEFAULT 1, vrat_kinds TEXT NOT NULL DEFAULT 'festival,ekadashi,purnima,amavasya,pradosh',
  weekly INTEGER NOT NULL DEFAULT 1, weekly_day INTEGER NOT NULL DEFAULT 0,
  verified INTEGER NOT NULL DEFAULT 0, code TEXT, code_expires TEXT, status TEXT NOT NULL DEFAULT 'active',
  user_id TEXT, created TEXT NOT NULL, last_daily TEXT, last_weekly TEXT, last_error TEXT
);
CREATE TABLE IF NOT EXISTS wa_log(id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, kind TEXT, at TEXT, ok INTEGER, detail TEXT);
"""
KINDS_HI = {"festival": "त्योहार", "ekadashi": "एकादशी", "purnima": "पूर्णिमा", "amavasya": "अमावस्या", "pradosh": "प्रदोष", "chaturthi": "चतुर्थी",
            "shivaratri": "मासिक शिवरात्रि", "grahan": "ग्रहण", "regional": "क्षेत्रीय पर्व", "national": "राष्ट्रीय दिवस", "christian": "ईसाई पर्व", "islamic": "इस्लामी पर्व"}
_PHONE = re.compile(r"^\d{10,15}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 10:
        digits = "91" + digits                      # Indian number without country code
    if not _PHONE.match(digits):
        raise ValueError("phone must be 10 digits (India) or an international number with country code")
    return digits


# ---------------------------------------------------------------- store
class Subs:
    def __init__(self, store: access.Store):
        self._db = store._db
        self._lock = store._lock
        with self._lock:
            self._db.executescript(SCHEMA)

    def upsert(self, sub: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            old = self._db.execute("SELECT * FROM wa_subs WHERE phone=?", (sub["phone"],)).fetchone()
            row = dict(old) if old else {"created": now, "verified": 0, "status": "active"}
            row.update({k: v for k, v in sub.items() if v is not None})
            if old and old["verified"] and not sub.get("force_reverify"):
                row["verified"] = 1
            row.pop("force_reverify", None)
            cols = ["phone", "name", "lang", "tz", "lat", "lon", "place", "birth", "moon_sign", "moon_sign_name", "daily_time", "want_panchang", "want_rashifal",
                    "vrat_alert", "vrat_kinds", "weekly", "weekly_day", "verified", "code", "code_expires", "status", "user_id", "created", "last_daily", "last_weekly", "last_error"]
            vals = {c: row.get(c) for c in cols}
            self._db.execute(f"INSERT OR REPLACE INTO wa_subs({','.join(cols)}) VALUES ({','.join(':' + c for c in cols)})", vals)
            self._db.commit()
        return self.get(sub["phone"])

    def get(self, phone: str) -> dict | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM wa_subs WHERE phone=?", (phone,)).fetchone()
        return dict(r) if r else None

    def set(self, phone: str, **fields):
        with self._lock:
            self._db.execute(f"UPDATE wa_subs SET {', '.join(f'{k}=:{k}' for k in fields)} WHERE phone=:phone", {**fields, "phone": phone})
            self._db.commit()

    def active(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM wa_subs WHERE verified=1 AND status='active'").fetchall()
        return [dict(r) for r in rows]

    def log(self, phone: str, kind: str, ok: bool, detail: str = ""):
        with self._lock:
            self._db.execute("INSERT INTO wa_log(phone, kind, at, ok, detail) VALUES (?,?,?,?,?)", (phone, kind, datetime.now(timezone.utc).isoformat(), int(ok), detail[:500]))
            self._db.commit()

    def recent_log(self, phone: str, n: int = 10) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT kind, at, ok, detail FROM wa_log WHERE phone=? ORDER BY id DESC LIMIT ?", (phone, n)).fetchall()
        return [dict(r) for r in rows]


_subs: Subs | None = None


def subs() -> Subs:
    global _subs
    if _subs is None:
        _subs = Subs(access.default_store())
    return _subs


# ---------------------------------------------------------------- relay
def relay_config() -> dict:
    return {"url": os.environ.get("RELAY_URL", "").rstrip("/"), "key": os.environ.get("RELAY_API_KEY", ""), "session": os.environ.get("RELAY_SESSION", "")}


def relay_ready() -> bool:
    c = relay_config()
    return bool(c["url"] and c["key"] and c["session"])


def send_whatsapp(phone: str, text: str) -> dict:
    """POST to Vivid Relay. Returns {ok, detail}. Never raises."""
    c = relay_config()
    if not relay_ready():
        return {"ok": False, "detail": "relay not configured (RELAY_URL, RELAY_API_KEY, RELAY_SESSION)"}
    body = json.dumps({"to": phone, "text": text, "preview": False}).encode("utf-8")
    req = urllib.request.Request(f"{c['url']}/api/sessions/{c['session']}/send", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {c['key']}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            return {"ok": bool(data.get("ok", True)), "detail": json.dumps(data)[:300]}
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = str(exc)
        return {"ok": False, "detail": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------- composing
def _day(sub: dict, d: date) -> dict | None:
    m = panchang_month.month(d.year, d.month, sub["lat"], sub["lon"], sub["tz"], only_day=d.day)
    return m["days"][0] if m["days"] else None


def _next_tithi_name(t_number: int, hi: bool) -> str:
    from .constants import TITHI_HI, TITHI_NAMES
    n = t_number % 30 + 1                         # 1..30, the tithi after t_number
    name = "Purnima" if n == 15 else "Amavasya" if n == 30 else TITHI_NAMES[(n - 1) % 15]
    paksha = ("शुक्ल" if hi else "Shukla") if n <= 15 else ("कृष्ण" if hi else "Krishna")
    return f"{paksha} {TITHI_HI[name] if hi else name}"


def _tithi_window(sub: dict, d: date, hi: bool) -> str:
    """'कृष्ण चतुर्दशी सूर्योदय से 12:32 तक, फिर अमावस्या (कल 10:15 तक)' — the tithi running at sunrise with its start and end."""
    today = _day(sub, d); yday = _day(sub, d - timedelta(days=1))
    if not today:
        return ""
    prev_lbl = (d - timedelta(days=1)).strftime("%d-%m"); next_lbl = (d + timedelta(days=1)).strftime("%d-%m")
    start = (yday["tithi_ends"] + ("" if yday["tithi_ends_next_day"] else f" ({prev_lbl})")) if yday and yday["tithi_ends"] else ("सूर्योदय से पहले" if hi else "before sunrise")
    end = (today["tithi_ends"] or "—") + (f" ({next_lbl})" if today["tithi_ends_next_day"] else "")
    cur = f'{today["paksha_hi"]} {today["tithi_hi"]}' if hi else f'{today["paksha"]} {today["tithi"]}'
    nxt = _next_tithi_name(today["tithi_number"], hi)
    return (f"{cur}: {start} से {end} तक, फिर {nxt}" if hi else f"{cur}: from {start} to {end}, then {nxt}")


def compose_daily(sub: dict, d: date) -> str:
    hi = sub.get("lang", "hi") != "en"
    day = _day(sub, d)
    if not day:
        return ""
    L = []
    L.append(("🌅 *आज का पंचांग* — " if hi else "🌅 *Today's panchang* — ") + f'{d.strftime("%d-%m-%Y")}, {day["vara_hi"] if hi else day["vara"]}' + (f' ({sub["place"]})' if sub.get("place") else ""))
    if sub.get("want_panchang", 1):
        L.append(f'{"मास" if hi else "Month"}: {day["masa_purnimanta_hi"] if hi else day["masa_purnimanta"]} ({"पूर्णिमांत" if hi else "purnimanta"}) · {"वि.सं." if hi else "V.S."} {day["vikram_samvat"]}')
        L.append(("तिथि: " if hi else "Tithi: ") + _tithi_window(sub, d, hi))
        L.append(f'{"नक्षत्र" if hi else "Nakshatra"}: {day["nakshatra_hi"] if hi else day["nakshatra"]} ({("" if hi else "until ") + (day["nakshatra_ends"] or "—") + ("+" if day["nakshatra_ends_next_day"] else "") + (" तक" if hi else "")}) · {"योग" if hi else "Yoga"}: {day["yoga_hi"] if hi else day["yoga"]} · {"करण" if hi else "Karana"}: {day["karana_hi"] if hi else day["karana"]}')
        L.append(f'☀️ {day["sunrise"]} – {day["sunset"]} · 🌙 {"चंद्रोदय" if hi else "moonrise"} {day["moonrise"] or "—"} · {"चंद्र राशि" if hi else "Moon sign"} {day["moon_sign_hi"] if hi else day["moon_sign"]}')
        rk = day.get("rahu_kaal"); ab = day.get("abhijit")
        L.append(f'⏳ {"राहु काल" if hi else "Rahu kaal"} {rk["start"] + "–" + rk["end"] if rk else "—"} · {"अभिजित" if hi else "Abhijit"} {ab["start"] + "–" + ab["end"] if ab else "—"} · {"दिशाशूल" if hi else "Disha shool"} {day["disha_shool_hi"] if hi else day["disha_shool"]}')
        if day.get("special"):
            L.append("✨ " + " · ".join(x["hi"] if hi else x["en"] for x in day["special"]))
        ev = [x for x in day["events"] if x["kind"] in ("grahan", "festival", "ekadashi", "purnima", "amavasya", "pradosh", "chaturthi", "shivaratri", "national", "regional")]
        if ev:
            L.append(("🪔 आज: " if hi else "🪔 Today: ") + ", ".join(x["name_hi"] if hi else x["name_en"] for x in ev))
    if sub.get("want_rashifal", 1) and sub.get("moon_sign") is not None:
        try:
            r = rashifal_mod.rashifal(d.isoformat(), sub["tz"], "daily")
            s = r["signs"][int(sub["moon_sign"])]
            top = [p for p in s["planets"] if p["planet"] in ("Moon", "Jupiter", "Saturn")]
            L.append("")
            L.append((f'🔮 *आपका राशिफल ({s["sign_name_hi"]})*: {s["grade_hi"]} {s["score"]}/100 — {s["summary_hi"]}' if hi else
                      f'🔮 *Your rashifal ({s["sign_name"]})*: {s["grade_en"]} {s["score"]}/100 — {s["summary_en"]}'))
            for p in top:
                txt = (p["text_hi"] if hi else p["text_en"]).split(": ", 1)[-1]
                L.append(f'• {p["planet_hi"] if hi else p["planet"]}: {txt}')
            L.append(("शुभ रंग " if hi else "Lucky colour ") + (r["lucky_colour_hi"] if hi else r["lucky_colour"]) + (" · शुभ अंक " if hi else " · lucky number ") + str(r["lucky_number"]))
        except Exception:
            pass
    if sub.get("birth"):
        try:
            personal = compose_personal_alerts(sub, d)
            if personal:
                L.append("")
                L.append(personal)
        except Exception:
            pass
    if sub.get("vrat_alert", 1):
        alert = compose_alert(sub, d + timedelta(days=1), prefix=True)
        if alert:
            L.append("")
            L.append(alert)
    L.append("")
    L.append("_" + ("पंचांग: लाहिड़ी अयनांश, सूर्योदय-कालीन तिथि; राशिफल प्रवृत्ति-संकेत है। बंद करने के लिए STOP लिखें।" if hi else
                    "Panchang: Lahiri ayanamsa, tithi at sunrise; the rashifal is a tendency pointer. Reply STOP to unsubscribe.") + "_")
    return "\n".join(L)


def compose_personal_alerts(sub: dict, d: date) -> str:
    """Dasha / transit changes for the subscriber's own chart: today's, and the coming week's."""
    from .handlers import chart_from_payload
    from . import alerts as alerts_mod
    hi = sub.get("lang", "hi") != "en"
    birth = json.loads(sub["birth"]) if isinstance(sub["birth"], str) else sub["birth"]
    ch = chart_from_payload(birth)
    a = alerts_mod.alerts(ch, d, sub["tz"])
    L = []
    for ev in a["today"]:
        L.append("🔔 " + (ev["hi"] if hi else ev["en"]))
    up = [ev for ev in a["upcoming"] if ev["kind"] in ("dasha", "sadesati", "ashtama") or ev.get("planet") in ("Jupiter", "Saturn", "Rahu")]
    for ev in up[:3]:
        L.append(("📌 " + f'{ev["date"][8:10]}-{ev["date"][5:7]} से: ' if hi else "📌 " + f'From {ev["date"][8:10]}-{ev["date"][5:7]}: ') + (ev["hi"] if hi else ev["en"]))
    if not L:
        return ""
    return ("*आपकी कुंडली में*\n" if hi else "*In your chart*\n") + "\n".join(L)


def compose_alert(sub: dict, d: date, prefix: bool = False) -> str:
    """Vrat / festival alert for date d (normally tomorrow) with the tithi window."""
    hi = sub.get("lang", "hi") != "en"
    kinds = set((sub.get("vrat_kinds") or "festival,ekadashi,purnima,amavasya,pradosh").split(","))
    day = _day(sub, d)
    if not day:
        return ""
    ev = [x for x in day["events"] if x["kind"] in kinds]
    if not ev:
        return ""
    names = ", ".join(x["name_hi"] if hi else x["name_en"] for x in ev)
    head = (("📿 *कल* " if hi else "📿 *Tomorrow* ") if prefix else "📿 ") + f'({d.strftime("%d-%m-%Y")}, {day["vara_hi"] if hi else day["vara"]}): ' + names
    window = _tithi_window(sub, d, hi)
    lines = [head, ("तिथि " if hi else "Tithi ") + window, f'☀️ {"सूर्योदय" if hi else "sunrise"} {day["sunrise"]} · {"सूर्यास्त" if hi else "sunset"} {day["sunset"]} · 🌙 {"चंद्रोदय" if hi else "moonrise"} {day["moonrise"] or "—"}']
    if any(x["kind"] == "ekadashi" for x in ev):
        nxt = _day(sub, d + timedelta(days=1))
        if nxt:
            lines.append((f'पारण: अगले दिन सूर्योदय {nxt["sunrise"]} के बाद, द्वादशी {nxt["tithi_ends"] or "—"} तक' if hi else f'Parana: after sunrise {nxt["sunrise"]} the next day, Dwadashi until {nxt["tithi_ends"] or "—"}')
                         if nxt["tithi_number"] in (12, 27) else (f'पारण: अगले दिन सूर्योदय {nxt["sunrise"]} के बाद' if hi else f'Parana: after sunrise {nxt["sunrise"]} the next day'))
    if any(x["kind"] == "pradosh" for x in ev):
        lines.append(("प्रदोष काल: सूर्यास्त " + day["sunset"] + " से लगभग 2 घंटे 24 मिनट") if hi else ("Pradosha: about 2 h 24 min from sunset " + day["sunset"]))
    return "\n".join(lines)


def compose_weekly(sub: dict, d: date) -> str:
    hi = sub.get("lang", "hi") != "en"
    kinds = set((sub.get("vrat_kinds") or "festival,ekadashi,purnima,amavasya,pradosh").split(",")) | {"festival", "national", "grahan"}
    L = [("📅 *इस सप्ताह के व्रत-पर्व* " if hi else "📅 *This week's vrats and festivals* ") + f'({d.strftime("%d-%m")} – {(d + timedelta(days=6)).strftime("%d-%m-%Y")})']
    any_ev = False
    for i in range(7):
        x = d + timedelta(days=i)
        day = _day(sub, x)
        if not day:
            continue
        ev = [e for e in day["events"] if e["kind"] in kinds]
        if ev:
            any_ev = True
            L.append(f'• {x.strftime("%d-%m")} {day["vara_hi"] if hi else day["vara"]}: ' + ", ".join(e["name_hi"] if hi else e["name_en"] for e in ev)
                     + f' ({day["paksha_hi"] if hi else day["paksha"]} {day["tithi_hi"] if hi else day["tithi"]} {("" if hi else "until ") + (day["tithi_ends"] or "") + ("+" if day["tithi_ends_next_day"] else "") + (" तक" if hi else "")})')
    if not any_ev:
        L.append("इस सप्ताह कोई चुना हुआ व्रत-पर्व नहीं।" if hi else "No selected vrat or festival this week.")
    L.append("")
    L.append("_" + ("हर दिन का विवरण सुबह के संदेश में। बंद करने के लिए STOP लिखें।" if hi else "Daily details come in the morning message. Reply STOP to unsubscribe.") + "_")
    return "\n".join(L)


# ---------------------------------------------------------------- subscription flow
def moon_sign_from_birth(birth: dict) -> tuple[int | None, str | None]:
    try:
        from .handlers import chart_from_payload
        ch = chart_from_payload(birth)
        moon = next(p for p in ch["planets"] if p["name"] == "Moon")
        return int(moon["sign"]), moon.get("sign_name_hi") or moon.get("sign_name")
    except Exception:
        return None, None


def start_subscription(payload: dict) -> dict:
    phone = normalize_phone(payload.get("phone"))
    tz = str(payload.get("tz") or "Asia/Kolkata"); ZoneInfo(tz)
    lat, lon = float(payload.get("lat", 28.61)), float(payload.get("lon", 77.2))
    daily_time = str(payload.get("daily_time") or "06:30")
    if not re.fullmatch(r"\d{2}:\d{2}", daily_time):
        raise ValueError("daily_time must be HH:MM")
    kinds = [k for k in str(payload.get("vrat_kinds") or "festival,ekadashi,purnima,amavasya,pradosh").split(",") if k in KINDS_HI]
    birth = payload.get("birth") if isinstance(payload.get("birth"), dict) else None
    moon_sign, moon_name = moon_sign_from_birth(birth) if birth else (None, None)
    code = f"{random.randint(0, 999999):06d}"
    sub = {"phone": phone, "name": str(payload.get("name") or "")[:60], "lang": "en" if payload.get("lang") == "en" else "hi", "tz": tz, "lat": lat, "lon": lon,
           "place": str(payload.get("place") or "")[:80], "birth": json.dumps(birth, ensure_ascii=False) if birth else None, "moon_sign": moon_sign, "moon_sign_name": moon_name,
           "daily_time": daily_time, "want_panchang": int(bool(payload.get("want_panchang", True))), "want_rashifal": int(bool(payload.get("want_rashifal", True)) and moon_sign is not None),
           "vrat_alert": int(bool(payload.get("vrat_alert", True))), "vrat_kinds": ",".join(kinds), "weekly": int(bool(payload.get("weekly", True))), "weekly_day": int(payload.get("weekly_day", 0)) % 7,
           "code": code, "code_expires": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(), "status": "active", "user_id": payload.get("user_id"), "force_reverify": True, "verified": 0}
    saved = subs().upsert(sub)
    hi = saved["lang"] != "en"
    text = (f"कुंडली ऐप: आपका सत्यापन कोड *{code}* है (15 मिनट तक मान्य)। रोज़ {daily_time} बजे पंचांग/राशिफल पाने के लिए ऐप में यह कोड डालिए।" if hi else
            f"Kundali app: your verification code is *{code}* (valid 15 minutes). Enter it in the app to receive the panchang/rashifal daily at {daily_time}.")
    sent = send_whatsapp(phone, text)
    subs().log(phone, "code", sent["ok"], sent["detail"])
    return {"phone": phone, "sent": sent["ok"], "detail": None if sent["ok"] else sent["detail"], "relay_ready": relay_ready(), "moon_sign_name": moon_name}


def verify(payload: dict) -> dict:
    phone = normalize_phone(payload.get("phone"))
    sub = subs().get(phone)
    if not sub or not sub.get("code"):
        raise ValueError("no pending verification for this number")
    if datetime.fromisoformat(sub["code_expires"]) < datetime.now(timezone.utc):
        raise ValueError("code expired; request a new one")
    if str(payload.get("code") or "").strip() != sub["code"]:
        raise ValueError("wrong code")
    subs().set(phone, verified=1, code=None, code_expires=None, status="active")
    sub = subs().get(phone)
    today = datetime.now(ZoneInfo(sub["tz"])).date()
    text = compose_daily(sub, today)
    sent = send_whatsapp(phone, text)
    subs().log(phone, "welcome", sent["ok"], sent["detail"])
    if sent["ok"]:
        subs().set(phone, last_daily=today.isoformat())
    return {"phone": phone, "verified": True, "welcome_sent": sent["ok"], "detail": None if sent["ok"] else sent["detail"]}


def unsubscribe(payload: dict) -> dict:
    phone = normalize_phone(payload.get("phone"))
    sub = subs().get(phone)
    if not sub:
        raise ValueError("number not found")
    subs().set(phone, status="stopped")
    return {"phone": phone, "status": "stopped"}


def status(payload: dict) -> dict:
    phone = normalize_phone(payload.get("phone"))
    sub = subs().get(phone)
    if not sub:
        return {"phone": phone, "exists": False}
    pub = {k: sub[k] for k in ("phone", "name", "lang", "tz", "place", "daily_time", "want_panchang", "want_rashifal", "vrat_alert", "vrat_kinds", "weekly", "weekly_day", "verified", "status", "moon_sign_name", "last_daily", "last_weekly")}
    return {**pub, "exists": True, "log": subs().recent_log(phone, 5)}


def preview(payload: dict) -> dict:
    """What the subscriber would receive today (no sending)."""
    tz = str(payload.get("tz") or "Asia/Kolkata"); ZoneInfo(tz)
    birth = payload.get("birth") if isinstance(payload.get("birth"), dict) else None
    moon_sign, moon_name = moon_sign_from_birth(birth) if birth else (None, None)
    kinds = [k for k in str(payload.get("vrat_kinds") or "festival,ekadashi,purnima,amavasya,pradosh").split(",") if k in KINDS_HI]
    sub = {"lang": "en" if payload.get("lang") == "en" else "hi", "tz": tz, "lat": float(payload.get("lat", 28.61)), "lon": float(payload.get("lon", 77.2)), "place": payload.get("place") or "",
           "moon_sign": moon_sign, "want_panchang": payload.get("want_panchang", True), "want_rashifal": payload.get("want_rashifal", True), "vrat_alert": payload.get("vrat_alert", True), "vrat_kinds": ",".join(kinds)}
    d = date.fromisoformat(payload["date"]) if payload.get("date") else datetime.now(ZoneInfo(tz)).date()
    return {"daily": compose_daily(sub, d), "weekly": compose_weekly(sub, d), "moon_sign_name": moon_name, "relay_ready": relay_ready()}


# ---------------------------------------------------------------- worker
def due_now(sub: dict, now_utc: datetime) -> list[str]:
    """Which messages are due for this subscriber at this instant: 'daily' and/or 'weekly'."""
    local = now_utc.astimezone(ZoneInfo(sub["tz"]))
    hh, mm = (int(x) for x in sub["daily_time"].split(":"))
    due = []
    if (local.hour, local.minute) >= (hh, mm) and sub.get("last_daily") != local.date().isoformat():
        due.append("daily")
    if sub.get("weekly") and local.weekday() == (int(sub.get("weekly_day", 0)) - 1) % 7 and (local.hour, local.minute) >= (hh, mm) and sub.get("last_weekly") != local.date().isoformat():
        due.append("weekly")
    return due


def run_once(now_utc: datetime | None = None, sender=send_whatsapp) -> list[dict]:
    now_utc = now_utc or datetime.now(timezone.utc)
    results = []
    for sub in subs().active():
        for kind in due_now(sub, now_utc):
            local_day = now_utc.astimezone(ZoneInfo(sub["tz"])).date()
            text = compose_daily(sub, local_day) if kind == "daily" else compose_weekly(sub, local_day)
            res = sender(sub["phone"], text) if text else {"ok": False, "detail": "empty message"}
            subs().log(sub["phone"], kind, res["ok"], res["detail"])
            if res["ok"]:
                subs().set(sub["phone"], **{("last_daily" if kind == "daily" else "last_weekly"): local_day.isoformat()}, last_error=None)
            else:
                subs().set(sub["phone"], last_error=res["detail"])
            results.append({"phone": sub["phone"], "kind": kind, **res})
    return results


def start_worker(interval: int = 60) -> threading.Thread:
    def loop():
        while True:
            try:
                run_once()
            except Exception as exc:          # keep the worker alive
                print("notify worker error:", exc, flush=True)
            time.sleep(interval)
    t = threading.Thread(target=loop, name="kundali-notify", daemon=True)
    t.start()
    return t
