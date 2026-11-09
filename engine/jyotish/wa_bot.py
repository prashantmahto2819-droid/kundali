"""Two-way WhatsApp through Vivid Relay: people message the business number and get panchang, rashifal, a short kundali,
vrat lists and muhurta dates back, or manage their daily subscription — Hindi or English, Devanagari or Roman commands.

Relay POSTs every inbound message to our webhook (`/v1/notify/webhook`) as
  {"event": "message", "session": "...", "timestamp": 1700000000, "data": {"id", "from_phone", "chat_type", "from_me", "type", "text", "push_name", ...}}
signed with `X-Signature: sha256=HMAC(secret, X-Timestamp + "." + body)`. We verify the signature when RELAY_WEBHOOK_SECRET is set,
answer only direct text messages that are not our own, remember handled message ids (table wa_inbox) so Relay's retries never
double-reply, and send the reply through the same Relay session.

Commands (case-insensitive; the first word decides):
  पंचांग / panchang [शहर]            today's panchang for the sender's saved place (or a city name, or Delhi)
  राशिफल / rashifal [राशि]           today's rashifal for the named sign, or the sender's own sign if subscribed with birth details
  कुंडली / kundali DD-MM-YYYY HH:MM [शहर]   lagna, Moon sign and nakshatra, running dasha, and a link to the full chart
  व्रत / vrat                         this week's vrats and festivals
  मुहूर्त / muhurta [कार्य]           best dates in the next 30 days (विवाह, गृह प्रवेश, वाहन, यात्रा, व्यापार, ...)
  शुरू / start                        subscribe this number to the daily message (default 06:30, Delhi, Hindi)
  बंद / stop                          stop the daily message
  मदद / help / anything else          the menu
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import notify
from .constants import PLANETS_HI, SIGNS, SIGNS_HI

ROOT = Path(__file__).resolve().parents[2]
SITE = os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com")
SIGN_WORDS = {s.lower(): i for i, s in enumerate(SIGNS)} | {h: i for i, h in enumerate(SIGNS_HI)} | {
    "aries": 0, "taurus": 1, "gemini": 2, "cancer": 3, "leo": 4, "virgo": 5, "libra": 6, "scorpio": 7, "sagittarius": 8, "capricorn": 9, "aquarius": 10, "pisces": 11,
    "mesh": 0, "vrishabh": 1, "vrushabh": 1, "mithun": 2, "kark": 3, "karka": 3, "singh": 4, "simha": 4, "kanya": 5, "tula": 6, "vrishchik": 7, "vrischik": 7, "dhanu": 8, "makar": 9, "kumbh": 10, "meen": 11, "मीन": 11}
CMD = {"panchang": ("पंचांग", "panchang", "panchaang", "panchag"), "rashifal": ("राशिफल", "rashifal", "rashi", "राशि", "horoscope"),
       "kundali": ("कुंडली", "kundali", "kundli", "chart", "janam"), "vrat": ("व्रत", "vrat", "festival", "त्योहार", "tyohar", "parv", "पर्व"),
       "muhurta": ("मुहूर्त", "muhurta", "muhurat", "muhurt"), "start": ("शुरू", "start", "subscribe", "चालू", "सब्सक्राइब"),
       "stop": ("बंद", "stop", "unsubscribe", "रोको"), "help": ("मदद", "help", "menu", "मेनू", "hi", "hello", "नमस्ते", "namaste")}
ACTIVITY_WORDS = {"विवाह": "marriage", "शादी": "marriage", "marriage": "marriage", "shadi": "marriage", "vivah": "marriage",
                  "गृह": "griha_pravesh", "grih": "griha_pravesh", "griha": "griha_pravesh", "housewarming": "griha_pravesh",
                  "वाहन": "vehicle", "vehicle": "vehicle", "gadi": "vehicle", "गाड़ी": "vehicle", "car": "vehicle",
                  "यात्रा": "travel", "travel": "travel", "yatra": "travel", "व्यापार": "business", "business": "business", "vyapar": "business", "दुकान": "business",
                  "शिक्षा": "education", "education": "education", "vidya": "education", "मुंडन": "mundan", "mundan": "mundan",
                  "नामकरण": "namakaran", "namkaran": "namakaran", "अन्नप्राशन": "annaprashan", "भूमि": "bhoomi_pujan", "bhoomi": "bhoomi_pujan",
                  "संपत्ति": "property", "property": "property", "जमीन": "property", "zameen": "property"}
_DATE = re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})")
_TIME = re.compile(r"(\d{1,2})[:.](\d{2})\s*(am|pm|AM|PM)?")
_places: list[dict] | None = None


# ---------------------------------------------------------------- helpers
def places() -> list[dict]:
    global _places
    if _places is None:
        _places = json.loads((ROOT / "data" / "places.json").read_text("utf-8"))["places"]
    return _places


def find_place(words: list[str]) -> dict | None:
    """Match a city by Hindi or English name (or alias) among the given words; longest match first."""
    text = " ".join(words).lower()
    best = None
    for p in places():
        names = [p["name"].lower(), p.get("hi", "").lower()] + [a.lower() for a in p.get("aka", [])]
        for n in names:
            if n and re.search(r"(^|\s)" + re.escape(n) + r"($|\s)", text) and (best is None or len(n) > best[0]):
                best = (len(n), p)
    return best[1] if best else None


def verify_signature(body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    if not secret:
        return True                                   # not configured: accept (the URL itself is unguessable only if the owner keeps it so)
    if not timestamp or not signature:
        return False
    try:
        if abs(time.time() - int(timestamp)) > 600:
            return False
    except ValueError:
        return False
    mac = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature.removeprefix("sha256="))


def _is_hindi(text: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text)) or not re.search(r"[a-zA-Z]", text)


def _norm(word: str) -> str:
    return word.strip().lower().strip("।.,!?:;")


def parse(text: str) -> tuple[str, list[str]]:
    words = [_norm(w) for w in re.split(r"\s+", text.strip()) if w.strip()]
    if not words:
        return "help", []
    first = words[0]
    for cmd, keys in CMD.items():
        if first in keys:
            return cmd, words[1:]
    # "मेष राशिफल" or "15-05-1990 10:30 jabalpur" without a keyword
    if any(w in CMD["rashifal"] for w in words):
        return "rashifal", [w for w in words if w not in CMD["rashifal"]]
    if _DATE.search(text) and _TIME.search(text):
        return "kundali", words
    return "help", words


def _place_for(sub: dict | None, words: list[str]) -> dict:
    p = find_place(words)
    if p:
        return {"lat": p["lat"], "lon": p["lon"], "tz": p["tz"], "place": p["hi"] or p["name"], "place_en": p["name"]}
    if sub:
        return {"lat": sub["lat"], "lon": sub["lon"], "tz": sub["tz"], "place": sub.get("place") or "", "place_en": sub.get("place") or ""}
    return {"lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata", "place": "दिल्ली", "place_en": "Delhi"}


# ---------------------------------------------------------------- replies
def reply_help(hi: bool, name: str = "") -> str:
    greet = (f"🙏 नमस्ते{(' ' + name) if name else ''}! " if hi else f"🙏 Namaste{(' ' + name) if name else ''}! ")
    if hi:
        return greet + ("कुंडली ऐप में आपका स्वागत है। कोई एक शब्द भेजिए:\n\n"
                        "• *पंचांग* [शहर] — आज का पंचांग\n• *राशिफल* [राशि] — आज का राशिफल (जैसे: राशिफल मेष)\n"
                        "• *कुंडली* 15-05-1990 10:30 जबलपुर — संक्षिप्त कुंडली और पूरी रिपोर्ट का लिंक\n"
                        "• *व्रत* — इस सप्ताह के व्रत-पर्व\n• *मुहूर्त* विवाह — अगले 30 दिन के शुभ दिन (विवाह, गृह प्रवेश, वाहन, यात्रा, व्यापार…)\n"
                        "• *शुरू* — रोज़ सुबह पंचांग-राशिफल पाइए · *बंद* — रोकिए\n\n"
                        f"पूरा ऐप: {SITE}\n_फलादेश परंपरागत मार्गदर्शन है, भविष्यवाणी नहीं।_")
    return greet + ("Welcome to the Kundali app. Send one word:\n\n"
                    "• *panchang* [city] — today's panchang\n• *rashifal* [sign] — today's rashifal (e.g. rashifal mesh)\n"
                    "• *kundali* 15-05-1990 10:30 Jabalpur — a short chart and a link to the full report\n"
                    "• *vrat* — this week's vrats and festivals\n• *muhurta* marriage — good dates in the next 30 days\n"
                    "• *start* — daily panchang/rashifal each morning · *stop* — stop it\n\n"
                    f"Full app: {SITE}\n_Readings are traditional guidance, not predictions._")


def reply_panchang(sub: dict | None, words: list[str], hi: bool) -> str:
    pl = _place_for(sub, words)
    s = {"lang": "hi" if hi else "en", "tz": pl["tz"], "lat": pl["lat"], "lon": pl["lon"], "place": pl["place"] if hi else pl["place_en"],
         "want_panchang": 1, "want_rashifal": 0, "vrat_alert": 1, "vrat_kinds": "festival,ekadashi,purnima,amavasya,pradosh", "moon_sign": None}
    today = datetime.now(ZoneInfo(pl["tz"])).date()
    txt = notify.compose_daily(s, today)
    return txt.replace("बंद करने के लिए STOP लिखें।", "रोज़ पाने के लिए *शुरू* लिखें।").replace("Reply STOP to unsubscribe.", "Send *start* to get this daily.")


def reply_rashifal(sub: dict | None, words: list[str], hi: bool) -> str:
    from . import rashifal as rf
    sign = next((SIGN_WORDS[w] for w in words if w in SIGN_WORDS), None)
    if sign is None and sub and sub.get("moon_sign") is not None:
        sign = int(sub["moon_sign"])
    tz = (sub or {}).get("tz") or "Asia/Kolkata"
    today = datetime.now(ZoneInfo(tz)).date()
    r = rf.rashifal(today.isoformat(), tz, "daily")
    if sign is None:
        lines = [("🔮 *आज का राशिफल* " if hi else "🔮 *Today's rashifal* ") + today.strftime("%d-%m-%Y")]
        for s in r["signs"]:
            lines.append(f'• {s["sign_name_hi"] if hi else s["sign_name"]}: {s["grade_hi"] if hi else s["grade_en"]} ({s["score"]})')
        lines.append(("\nअपनी राशि का विस्तार: *राशिफल मेष* जैसे लिखिए।" if hi else "\nFor one sign in detail send e.g. *rashifal mesh*."))
        return "\n".join(lines)
    s = r["signs"][sign]
    lines = [(f'🔮 *{s["sign_name_hi"]} — आज का राशिफल* ({today.strftime("%d-%m-%Y")})' if hi else f'🔮 *{s["sign_name"]} — today\'s rashifal* ({today.strftime("%d-%m-%Y")})'),
             f'{s["grade_hi"] if hi else s["grade_en"]} {s["score"]}/100 — {s["summary_hi"] if hi else s["summary_en"]}', ""]
    for p in s["planets"]:
        if p["planet"] in ("Moon", "Sun", "Mars", "Jupiter", "Saturn"):
            t = (p["text_hi"] if hi else p["text_en"]).split(": ", 1)[-1]
            lines.append(f'• {p["planet_hi"] if hi else p["planet"]}: {t}')
    lines.append("")
    lines.append((f'शुभ रंग {r["lucky_colour_hi"]} · शुभ अंक {r["lucky_number"]}' if hi else f'Lucky colour {r["lucky_colour"]} · lucky number {r["lucky_number"]}'))
    lines.append("_" + ("चंद्र-राशि से गोचर आधारित प्रवृत्ति-संकेत।" if hi else "Transit-based tendency pointer from the Moon sign.") + "_")
    return "\n".join(lines)


def reply_kundali(text: str, words: list[str], hi: bool) -> str:
    from .handlers import chart_from_payload, BadRequest
    md, mt = _DATE.search(text), _TIME.search(text)
    if not md or not mt:
        return ("कृपया ऐसे लिखिए: *कुंडली 15-05-1990 10:30 जबलपुर* (तारीख दिन-महीना-साल, समय 24-घंटे में)" if hi else
                "Please send like: *kundali 15-05-1990 10:30 Jabalpur* (date day-month-year, 24-hour time)")
    d, m, y = (int(x) for x in md.groups())
    hh, mm, ap = int(mt.group(1)), int(mt.group(2)), (mt.group(3) or "").lower()
    if ap == "pm" and hh < 12:
        hh += 12
    if ap == "am" and hh == 12:
        hh = 0
    pl = _place_for(None, words)
    try:
        ch = chart_from_payload({"date": f"{y:04d}-{m:02d}-{d:02d}", "time": f"{hh:02d}:{mm:02d}", "tz": pl["tz"], "lat": pl["lat"], "lon": pl["lon"]})
    except (BadRequest, ValueError) as exc:
        return ("जन्म-विवरण समझ नहीं आया: " if hi else "Could not read the birth details: ") + str(exc)
    moon = next(p for p in ch["planets"] if p["name"] == "Moon")
    sun = next(p for p in ch["planets"] if p["name"] == "Sun")
    run = ch.get("dasha_running") or []
    def lord(p): return PLANETS_HI[p] if hi else p
    dasha = " › ".join((f'{lord(r["lord"])} ({r["end"][8:10]}-{r["end"][5:7]}-{r["end"][:4]} तक)' if hi else f'{lord(r["lord"])} (until {r["end"][8:10]}-{r["end"][5:7]}-{r["end"][:4]})') for r in run[:2])
    link = f'{SITE}/?d={y:04d}-{m:02d}-{d:02d}&t={hh:02d}:{mm:02d}&tz={pl["tz"]}&lat={pl["lat"]}&lon={pl["lon"]}'
    place = pl["place"] if hi else pl["place_en"]
    if hi:
        return (f"🪔 *संक्षिप्त कुंडली* — {d:02d}-{m:02d}-{y}, {hh:02d}:{mm:02d}, {place}\n"
                f"लग्न: {ch['lagna']['sign_name_hi']} ({ch['lagna']['nakshatra_hi']})\n"
                f"चंद्र राशि: {moon['sign_name_hi']} · जन्म नक्षत्र: {moon['nakshatra_hi']} (पद {moon['pada']})\n"
                f"सूर्य राशि: {sun['sign_name_hi']}\n"
                f"चल रही दशा: {dasha or '—'}\n\n"
                f"पूरी कुंडली (ग्रह, भाव, दशा, योग, रिपोर्ट): {link}\n\n"
                f"रोज़ अपना राशिफल पाने के लिए *शुरू* लिखिए।\n_अयनांश लाहिड़ी; फलादेश परंपरागत मार्गदर्शन है।_")
    return (f"🪔 *Short kundali* — {d:02d}-{m:02d}-{y}, {hh:02d}:{mm:02d}, {place}\n"
            f"Lagna: {ch['lagna']['sign_name']} ({ch['lagna']['nakshatra']})\n"
            f"Moon sign: {moon['sign_name']} · birth nakshatra: {moon['nakshatra']} (pada {moon['pada']})\n"
            f"Sun sign: {sun['sign_name']}\nRunning dasha: {dasha or '—'}\n\n"
            f"Full chart (planets, houses, dasha, yogas, report): {link}\n\nSend *start* for your daily rashifal.\n_Lahiri ayanamsa; readings are traditional guidance._")


def reply_vrat(sub: dict | None, words: list[str], hi: bool) -> str:
    pl = _place_for(sub, words)
    s = {"lang": "hi" if hi else "en", "tz": pl["tz"], "lat": pl["lat"], "lon": pl["lon"], "vrat_kinds": "festival,ekadashi,purnima,amavasya,pradosh,chaturthi,shivaratri"}
    today = datetime.now(ZoneInfo(pl["tz"])).date()
    return notify.compose_weekly(s, today).replace("बंद करने के लिए STOP लिखें।", "रोज़ पाने के लिए *शुरू* लिखें।").replace("Reply STOP to unsubscribe.", "Send *start* to get this daily.")


def reply_muhurta(sub: dict | None, words: list[str], hi: bool) -> str:
    from . import muhurta_find
    act = next((ACTIVITY_WORDS[w] for w in words if w in ACTIVITY_WORDS), None)
    if act is None:
        for w in words:
            for k, v in ACTIVITY_WORDS.items():
                if w.startswith(k[:4]) and len(k) >= 4:
                    act = v
                    break
            if act:
                break
    act = act or "general"
    pl = _place_for(sub, [w for w in words if w not in ACTIVITY_WORDS])
    today = datetime.now(ZoneInfo(pl["tz"])).date()
    r = muhurta_find.find(act, pl["lat"], pl["lon"], pl["tz"], today.isoformat(), days=30)
    best = r["best"][:6]
    head = (f'📅 *{r["activity_hi"]} मुहूर्त* — अगले 30 दिन ({pl["place"]})' if hi else f'📅 *{r["activity_en"]} muhurta* — next 30 days ({pl["place_en"]})')
    VARA_EN = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    if not best:
        reasons = [x for d in r["all"] for x in d.get("reasons_hi" if hi else "reasons", [])]
        common = max(set(reasons), key=reasons.count) if reasons else ""
        return head + "\n" + ("इस अवधि में कोई शुद्ध दिन नहीं मिला" if hi else "No clear day found in this period") + (f" ({common})" if common else "") + "."
    lines = [head]
    for b in best:
        dd = date.fromisoformat(b["date"]).strftime("%d-%m")
        wins = ", ".join(f'{w["start"]}–{w["end"]}' for w in (b.get("good_windows") or [])[:2])
        lines.append(f'• {dd} {b["vara_hi"] if hi else VARA_EN[b["vara"]]}: {b["tithi_hi"] if hi else b["tithi"]}, {b["nakshatra_hi"] if hi else b["nakshatra"]} · {"स्कोर" if hi else "score"} {b["score"]}' + (f' · {"शुभ समय" if hi else "good hours"} {wins}' if wins else ""))
    lines.append("")
    lines.append(("सटीक लग्न-समय और व्यक्तिगत (चंद्रबल/ताराबल) जाँच ऐप के मुहूर्त टैब में: " if hi else "Exact lagna timing and personal (chandrabala/tarabala) checks in the app's muhurta tab: ") + SITE)
    return "\n".join(lines)


def reply_start(phone: str, name: str, hi: bool) -> str:
    sub = notify.subs().get(phone)
    if sub and sub["verified"]:
        notify.subs().set(phone, status="active")
    else:
        notify.subs().upsert({"phone": phone, "name": name[:60], "lang": "hi" if hi else "en", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2, "place": "दिल्ली" if hi else "Delhi",
                              "daily_time": "06:30", "want_panchang": 1, "want_rashifal": 0, "vrat_alert": 1, "weekly": 1, "weekly_day": 0, "verified": 1, "status": "active", "code": None})
    return (f"✅ रोज़ सुबह 06:30 पर पंचांग और व्रत-सूचना इसी नंबर पर आएगी (स्थान: दिल्ली)। अपना शहर, समय और जन्म-विवरण (अपने राशिफल के लिए) ऐप में सेट कीजिए: {SITE} → कुंडली → \"WhatsApp पर रोज़ का अपडेट\"।\nरोकने के लिए *बंद* लिखिए।" if hi else
            f"✅ The panchang and vrat alert will arrive here daily at 06:30 (place: Delhi). Set your city, time and birth details (for your own rashifal) in the app: {SITE} → Kundali → \"Daily update on WhatsApp\".\nSend *stop* to end it.")


def reply_stop(phone: str, hi: bool) -> str:
    if notify.subs().get(phone):
        notify.subs().set(phone, status="stopped")
    return "रोज़ का संदेश बंद कर दिया गया। फिर चाहिए तो *शुरू* लिखिए। 🙏" if hi else "Daily messages stopped. Send *start* to resume. 🙏"


def answer(phone: str, text: str, name: str = "") -> str:
    sub = notify.subs().get(phone)
    hi = _is_hindi(text) if not sub else (sub.get("lang", "hi") != "en" if not re.search(r"[a-zA-Z]{3,}", text) else _is_hindi(text))
    cmd, words = parse(text)
    try:
        if cmd == "panchang":
            return reply_panchang(sub, words, hi)
        if cmd == "rashifal":
            return reply_rashifal(sub, words, hi)
        if cmd == "kundali":
            return reply_kundali(text, words, hi)
        if cmd == "vrat":
            return reply_vrat(sub, words, hi)
        if cmd == "muhurta":
            return reply_muhurta(sub, words, hi)
        if cmd == "start":
            return reply_start(phone, name, hi)
        if cmd == "stop":
            return reply_stop(phone, hi)
    except Exception as exc:                        # never leave a sender without an answer
        return ("क्षमा करें, यह अभी नहीं बन सका (" + type(exc).__name__ + ")। *मदद* लिखकर विकल्प देखिए।" if hi else
                "Sorry, that could not be prepared (" + type(exc).__name__ + "). Send *help* for the options.")
    # free text: a question → AI chat grounded in the sender's chart (when subscribed with birth details), else the menu
    if len(words) >= 3 or "?" in text or "क्या" in text or "कैसा" in text or "कब" in text:
        ans = reply_ai(phone, text, sub, hi)
        if ans:
            return ans
    return reply_help(hi, name)


def reply_ai(phone: str, text: str, sub: dict | None, hi: bool) -> str | None:
    from . import ai, llm
    if not llm.available():
        return None
    try:
        payload = {"messages": [{"role": "user", "content": text}], "lang": "hi" if hi else "en", "phone": phone}
        if sub and sub.get("birth"):
            payload["birth"] = json.loads(sub["birth"]) if isinstance(sub["birth"], str) else sub["birth"]
            payload["lat"], payload["lon"], payload["tz"] = sub["lat"], sub["lon"], sub["tz"]
        r = ai.chat(payload, store=notify.subs()._store if hasattr(notify.subs(), "_store") else None, who=phone)
    except Exception:
        return None
    tail = ("\n\n_" + r["disclaimer"] + ("" if (sub and sub.get("birth")) else (" अपनी कुंडली के अनुसार उत्तर के लिए ऐप में जन्म-विवरण के साथ सब्सक्राइब करें।" if hi else " Subscribe in the app with birth details for answers from your own chart.")) + "_")
    return ("🤖 " if r["mode"] == "ai" else "📚 ") + r["answer"] + tail


# ---------------------------------------------------------------- webhook entry
_INBOX = "CREATE TABLE IF NOT EXISTS wa_inbox(id TEXT PRIMARY KEY, phone TEXT, at TEXT, text TEXT, reply_ok INTEGER)"


def _seen(msg_id: str, phone: str, text: str) -> bool:
    s = notify.subs()
    with s._lock:
        s._db.execute(_INBOX)
        try:
            s._db.execute("INSERT INTO wa_inbox(id, phone, at, text, reply_ok) VALUES (?,?,?,?,NULL)", (msg_id, phone, datetime.now(timezone.utc).isoformat(), text[:200]))
            s._db.commit()
            return False
        except Exception:
            return True


def _mark(msg_id: str, ok: bool):
    s = notify.subs()
    with s._lock:
        s._db.execute("UPDATE wa_inbox SET reply_ok=? WHERE id=?", (int(ok), msg_id))
        s._db.commit()


def handle_webhook(body: bytes, headers: dict, sender=None) -> dict:
    """Process one Relay webhook delivery. Returns {ok, handled, reason|reply}. Raises PermissionError on a bad signature."""
    secret = os.environ.get("RELAY_WEBHOOK_SECRET", "")
    h = {k.lower(): v for k, v in headers.items()}
    if not verify_signature(body, h.get("x-timestamp", ""), h.get("x-signature", ""), secret):
        raise PermissionError("bad signature")
    try:
        evt = json.loads(body.decode("utf-8") or "{}")
    except ValueError:
        return {"ok": True, "handled": False, "reason": "not json"}
    if evt.get("event") != "message":
        return {"ok": True, "handled": False, "reason": "event ignored"}
    d = evt.get("data") or {}
    if d.get("from_me") or d.get("chat_type") not in (None, "dm", "user", "private") or d.get("type") != "text":
        return {"ok": True, "handled": False, "reason": "not a direct text message"}
    text = str(d.get("text") or "").strip()
    phone = re.sub(r"\D", "", str(d.get("from_phone") or d.get("chat_phone") or ""))
    msg_id = str(d.get("id") or "")
    if not text or not phone:
        return {"ok": True, "handled": False, "reason": "empty"}
    if msg_id and _seen(msg_id, phone, text):
        return {"ok": True, "handled": False, "reason": "duplicate"}
    reply = answer(phone, text, str(d.get("push_name") or ""))
    res = (sender or notify.send_whatsapp)(phone, reply)
    if msg_id:
        _mark(msg_id, res["ok"])
    notify.subs().log(phone, "inbound", res["ok"], (text[:60] + " → " + res["detail"])[:500])
    return {"ok": True, "handled": True, "sent": res["ok"], "reply": reply if not res["ok"] else None, "detail": None if res["ok"] else res["detail"]}
