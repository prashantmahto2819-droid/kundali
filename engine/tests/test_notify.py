"""WhatsApp daily updates (Vivid Relay): composers, subscription flow with a fake sender, worker due-logic."""
import os
import re
from datetime import date, datetime, timezone

import pytest

from jyotish import access, notify

DELHI = {"lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata", "lang": "hi", "place": "दिल्ली", "want_panchang": 1, "want_rashifal": 1, "vrat_alert": 1,
         "vrat_kinds": "festival,ekadashi,purnima,amavasya,pradosh", "moon_sign": 8}


@pytest.fixture
def fresh_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDALI_DB", str(tmp_path / "t.db"))
    monkeypatch.setattr(access, "_DEFAULT", None, raising=False)
    notify._subs = notify.Subs(access.Store(str(tmp_path / "t.db")))
    yield notify._subs
    notify._subs = None


def test_phone_normalization():
    assert notify.normalize_phone("98765 43210") == "919876543210"
    assert notify.normalize_phone("+91 98765-43210") == "919876543210"
    assert notify.normalize_phone("14155550123") == "14155550123"
    with pytest.raises(ValueError):
        notify.normalize_phone("12345")


def test_daily_has_tithi_window_and_tomorrow_alert():
    txt = notify.compose_daily(DELHI, date(2025, 10, 19))      # day before Diwali 2025
    assert "आज का पंचांग" in txt and "19-10-2025" in txt
    assert re.search(r"तिथि: कृष्ण त्रयोदशी: \d\d:\d\d \(18-10\) से \d\d:\d\d तक, फिर कृष्ण चतुर्दशी", txt)
    assert "☀️ 06:2" in txt and "राहु काल" in txt
    assert "प्रदोष व्रत" in txt                                   # today's vrat
    assert "*कल* (20-10-2025" in txt and "दीपावली" in txt          # day-before alert with its tithi window
    assert "आपका राशिफल (धनु)" in txt
    assert txt.rstrip().endswith("STOP लिखें।_")


def test_daily_english_and_ekadashi_parana():
    sub = {**DELHI, "lang": "en", "moon_sign": None, "place": "Delhi"}
    txt = notify.compose_daily(sub, date(2025, 11, 1))
    assert "Today's panchang" in txt and "Tithi: Shukla Dashami: from" in txt and "then Shukla Ekadashi" in txt
    assert "*Tomorrow* (02-11-2025" in txt and "Dev Uthani" in txt and "Parana: after sunrise" in txt
    assert "rashifal" not in txt.split("\n\n")[1].lower() or "Your rashifal" not in txt   # no Moon sign → no personal line
    assert not re.search(r"[\u0900-\u097F]", txt)


def test_weekly_lists_each_day_with_tithi_end():
    txt = notify.compose_weekly(DELHI, date(2025, 10, 19))
    assert "इस सप्ताह के व्रत-पर्व" in txt and "(19-10 – 25-10-2025)" in txt
    assert re.search(r"• 20-10 सोमवार: .*दीपावली.*\(कृष्ण चतुर्दशी \d\d:\d\d तक\)", txt)
    assert "भाई दूज" in txt


def test_alert_empty_when_no_event():
    assert notify.compose_alert({**DELHI, "vrat_kinds": "ekadashi"}, date(2025, 10, 20)) == ""


def test_subscribe_verify_run_flow(fresh_store, monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "send_whatsapp", lambda phone, text: (sent.append((phone, text)) or {"ok": True, "detail": "{}"}))
    r = notify.start_subscription({"phone": "9876543210", "lat": 28.61, "lon": 77.2, "daily_time": "06:30", "place": "दिल्ली",
                                   "birth": {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2}})
    assert r["phone"] == "919876543210" and r["sent"] and r["moon_sign_name"]
    code = re.search(r"\*(\d{6})\*", sent[-1][1]).group(1)
    with pytest.raises(ValueError):
        notify.verify({"phone": "9876543210", "code": "000000"})
    v = notify.verify({"phone": "9876543210", "code": code})
    assert v["verified"] and v["welcome_sent"] and "आज का पंचांग" in sent[-1][1]
    sub = fresh_store.get("919876543210")
    assert sub["verified"] == 1 and sub["moon_sign"] is not None and sub["last_daily"] == datetime.now(timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).date().isoformat()
    # worker: already sent today → nothing due; next day 06:31 IST → daily due (and weekly on Sunday)
    assert notify.run_once(sender=lambda p, t: {"ok": True, "detail": ""}) == []
    nxt = datetime(2026, 11, 15, 1, 1, tzinfo=timezone.utc)        # Sunday 06:31 IST
    assert notify.due_now(fresh_store.get("919876543210"), nxt) == ["daily", "weekly"]
    out = notify.run_once(nxt, sender=lambda p, t: {"ok": True, "detail": ""})
    assert [o["kind"] for o in out] == ["daily", "weekly"]
    sub = fresh_store.get("919876543210")
    assert sub["last_daily"] == "2026-11-15" and sub["last_weekly"] == "2026-11-15"
    assert notify.due_now(sub, nxt) == []                             # deduped
    # a failed send keeps it due and records the error
    bad = datetime(2026, 11, 16, 1, 1, tzinfo=timezone.utc)
    notify.run_once(bad, sender=lambda p, t: {"ok": False, "detail": "HTTP 503"})
    sub = fresh_store.get("919876543210")
    assert sub["last_daily"] == "2026-11-15" and sub["last_error"] == "HTTP 503"
    assert notify.unsubscribe({"phone": "9876543210"})["status"] == "stopped"
    assert notify.run_once(bad, sender=lambda p, t: {"ok": True, "detail": ""}) == []
    st = notify.status({"phone": "9876543210"})
    assert st["exists"] and st["status"] == "stopped" and st["log"]


def test_preview_without_relay(monkeypatch):
    for k in ("RELAY_URL", "RELAY_API_KEY", "RELAY_SESSION"):
        monkeypatch.delenv(k, raising=False)
    r = notify.preview({"date": "2025-10-19", "lang": "en"})
    assert r["relay_ready"] is False and "Today's panchang" in r["daily"] and "This week" in r["weekly"]
    assert notify.send_whatsapp("919876543210", "x")["ok"] is False


def test_daily_card_png_and_image_send(fresh_store, monkeypatch):
    from jyotish import card
    from jyotish.handlers import panchang_card_from_query
    png = panchang_card_from_query({"date": "2026-11-09", "lat": "28.61", "lon": "77.2", "tz": "Asia/Kolkata", "place": "दिल्ली", "name": "परीक्षण"})
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 20000
    sent = []
    def fake(phone, text, image_png=None):
        sent.append((phone, text, image_png)); return {"ok": True, "detail": "{}"}
    monkeypatch.setattr(notify, "send_whatsapp", fake)
    notify.start_subscription({"phone": "9876543211", "lat": 28.61, "lon": 77.2, "daily_time": "06:30"})
    code = re.search(r"\*(\d{6})\*", sent[-1][1]).group(1)
    notify.verify({"phone": "9876543211", "code": code})
    assert sent[-1][2] is not None and sent[-1][2][:4] == b"\x89PNG"            # welcome message carries the card
    notify.subs().set("919876543211", want_image=0)
    assert notify.daily_card(notify.subs().get("919876543211"), date(2026, 11, 9)) is None
    assert card.font_available()


def test_birthday_and_broadcast(fresh_store, monkeypatch):
    sub = {"lang": "hi", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2, "place": "दिल्ली", "want_panchang": 0, "want_rashifal": 0, "vrat_alert": 0, "moon_sign": 8,
           "birth": '{"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2}'}
    txt = notify.compose_daily(sub, date(2027, 5, 15))
    assert "जन्मदिन की शुभकामनाएँ" in txt and "37 वर्ष" in txt and "वर्ष-लग्न" in txt
    assert "जन्मदिन" not in notify.compose_daily(sub, date(2027, 5, 16))
    # broadcast target: a group JID gets the plain daily (no STOP footer) at its own time
    b = fresh_store.upsert_broadcast({"target": "120363001234567890@g.us", "label": "परिवार समूह", "daily_time": "06:00", "place": "इंदौर", "lat": 22.72, "lon": 75.86})
    assert b["target"].endswith("@g.us") and b["active"] == 1
    sent = []
    out = notify.run_once(datetime(2026, 11, 15, 0, 31, tzinfo=timezone.utc), sender=lambda p, t, img=None: (sent.append((p, t, img)) or {"ok": True, "detail": ""}))   # 06:01 IST Sunday
    kinds = sorted(o["kind"] for o in out)
    assert kinds == ["broadcast_daily", "broadcast_weekly"] and sent[0][0].endswith("@g.us") and "STOP" not in sent[0][1] and sent[0][2][:4] == b"\x89PNG"
    assert fresh_store.broadcasts()[0]["last_daily"] == "2026-11-15"
    with pytest.raises(ValueError):
        fresh_store.upsert_broadcast({"target": "bad target"})
    fresh_store.delete_broadcast(b["target"]); assert fresh_store.broadcasts() == []
