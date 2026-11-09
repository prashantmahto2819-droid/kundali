"""Two-way WhatsApp bot: command parsing, replies, webhook signature and de-duplication."""
import hashlib
import hmac
import json
import time

import pytest

from jyotish import access, notify, wa_bot


@pytest.fixture
def store(tmp_path, monkeypatch):
    notify._subs = notify.Subs(access.Store(str(tmp_path / "t.db")))
    yield notify._subs
    notify._subs = None


def test_parse_commands():
    assert wa_bot.parse("पंचांग जबलपुर") == ("panchang", ["जबलपुर"])
    assert wa_bot.parse("Rashifal Mesh") == ("rashifal", ["mesh"])
    assert wa_bot.parse("मेष राशिफल")[0] == "rashifal"
    assert wa_bot.parse("15-05-1990 10:30 indore")[0] == "kundali"
    assert wa_bot.parse("STOP") == ("stop", []) and wa_bot.parse("शुरू") == ("start", [])
    assert wa_bot.parse("kya haal hai")[0] == "help"


def test_find_place_hindi_english_alias():
    assert wa_bot.find_place(["जबलपुर"])["name"] == "Jabalpur"
    assert wa_bot.find_place(["panchang", "indore"])["name"] == "Indore"
    assert wa_bot.find_place(["jubbulpore"])["name"] == "Jabalpur"
    assert wa_bot.find_place(["xyzcity"]) is None


def test_replies(store):
    assert "पंचांग" in wa_bot.answer("919876543210", "नमस्ते", "राम") and "राम" in wa_bot.answer("919876543210", "नमस्ते", "राम")
    p = wa_bot.answer("919876543210", "पंचांग जबलपुर")
    assert "(जबलपुर)" in p and "तिथि:" in p and "शुरू" in p
    r = wa_bot.answer("919876543210", "rashifal mesh")
    assert "Mesha" in r and "/100" in r
    r_all = wa_bot.answer("919876543210", "राशिफल")
    assert r_all.count("•") == 12
    k = wa_bot.answer("919876543210", "कुंडली 15-05-1990 10:30 जबलपुर")
    assert "लग्न: कर्क" in k and "चंद्र राशि: धनु" in k and "?d=1990-05-15&t=10:30" in k and "lat=23.18" in k
    k2 = wa_bot.answer("919876543210", "kundali 15/05/1990 10.30 pm indore")
    assert "22:30, Indore" in k2 and "until" in k2
    assert "कृपया ऐसे लिखिए" in wa_bot.answer("919876543210", "कुंडली कल")
    v = wa_bot.answer("919876543210", "व्रत")
    assert "इस सप्ताह" in v
    m = wa_bot.answer("919876543210", "मुहूर्त विवाह")
    assert "विवाह मुहूर्त" in m and ("•" in m or "कोई शुद्ध दिन" in m)
    assert "Buying a vehicle" in wa_bot.answer("919876543210", "muhurta gadi bhopal")


def test_start_stop_flow(store):
    assert "06:30" in wa_bot.answer("919876543210", "शुरू", "सीता")
    sub = store.get("919876543210")
    assert sub["verified"] == 1 and sub["status"] == "active" and sub["lang"] == "hi" and sub["name"] == "सीता"
    assert "बंद कर दिया" in wa_bot.answer("919876543210", "बंद")
    assert store.get("919876543210")["status"] == "stopped"
    assert "✅" in wa_bot.answer("919876543210", "start")
    assert store.get("919876543210")["status"] == "active"


def _signed(body: bytes, secret: str):
    ts = str(int(time.time()))
    sig = "sha256=" + hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    return {"X-Timestamp": ts, "X-Signature": sig}


def test_webhook_signature_dedupe_and_filters(store, monkeypatch):
    monkeypatch.setenv("RELAY_WEBHOOK_SECRET", "s3cret")
    sent = []
    sender = lambda phone, text: (sent.append((phone, text)) or {"ok": True, "detail": "{}"})
    evt = {"event": "message", "session": "main", "timestamp": 1, "data": {"id": "ABC1", "from_phone": "919876543210", "chat_type": "dm", "from_me": False, "type": "text", "text": "मदद", "push_name": "Ram"}}
    body = json.dumps(evt).encode()
    with pytest.raises(PermissionError):
        wa_bot.handle_webhook(body, {"X-Timestamp": "1", "X-Signature": "sha256=00"}, sender)
    with pytest.raises(PermissionError):
        wa_bot.handle_webhook(body, _signed(body, "wrong"), sender)
    r = wa_bot.handle_webhook(body, _signed(body, "s3cret"), sender)
    assert r["handled"] and r["sent"] and sent[-1][0] == "919876543210" and "पंचांग" in sent[-1][1]
    r2 = wa_bot.handle_webhook(body, _signed(body, "s3cret"), sender)        # Relay retry → no second reply
    assert r2["handled"] is False and r2["reason"] == "duplicate" and len(sent) == 1
    own = dict(evt); own["data"] = {**evt["data"], "id": "ABC2", "from_me": True}
    assert wa_bot.handle_webhook(json.dumps(own).encode(), _signed(json.dumps(own).encode(), "s3cret"), sender)["handled"] is False
    grp = dict(evt); grp["data"] = {**evt["data"], "id": "ABC3", "chat_type": "group"}
    assert wa_bot.handle_webhook(json.dumps(grp).encode(), _signed(json.dumps(grp).encode(), "s3cret"), sender)["handled"] is False
    rc = {"event": "message.receipt", "data": {}}
    assert wa_bot.handle_webhook(json.dumps(rc).encode(), _signed(json.dumps(rc).encode(), "s3cret"), sender)["reason"] == "event ignored"
    assert len(sent) == 1
    assert store.recent_log("919876543210", 1)[0]["kind"] == "inbound"


def test_webhook_without_secret_accepts(store, monkeypatch):
    monkeypatch.delenv("RELAY_WEBHOOK_SECRET", raising=False)
    evt = {"event": "message", "data": {"id": "Z1", "from_phone": "919876543210", "chat_type": "dm", "type": "text", "text": "panchang"}}
    r = wa_bot.handle_webhook(json.dumps(evt).encode(), {}, lambda p, t: {"ok": False, "detail": "HTTP 503"})
    assert r["handled"] and r["sent"] is False and "Today's panchang" in r["reply"]


def test_kundali_command_sends_image(store, monkeypatch):
    monkeypatch.delenv("RELAY_WEBHOOK_SECRET", raising=False)
    sent = []
    def sender(phone, text, image=None):
        sent.append((phone, text, image)); return {"ok": True, "detail": ""}
    evt = {"event": "message", "data": {"id": "K1", "from_phone": "919876543210", "chat_type": "dm", "type": "text", "text": "कुंडली 15-05-1990 10:30 जबलपुर"}}
    r = wa_bot.handle_webhook(json.dumps(evt).encode(), {}, sender)
    assert r["handled"] and sent[-1][2] is not None and sent[-1][2][:4] == b"\x89PNG" and "लग्न" in sent[-1][1]
    # a 2-arg sender still works (text only)
    sent2 = []
    evt["data"]["id"] = "K2"
    wa_bot.handle_webhook(json.dumps(evt).encode(), {}, lambda p, t: (sent2.append(t) or {"ok": True, "detail": ""}))
    assert sent2 and "लग्न" in sent2[0]


def test_interactive_menu_and_list_reply(store, monkeypatch):
    monkeypatch.delenv("RELAY_WEBHOOK_SECRET", raising=False)
    sent = []
    def sender(phone, text, image=None, extra=None):
        sent.append((phone, text, image, extra)); return {"ok": True, "detail": ""}
    evt = {"event": "message", "data": {"id": "M1", "from_phone": "919876543210", "chat_type": "dm", "type": "text", "text": "नमस्ते"}}
    wa_bot.handle_webhook(json.dumps(evt).encode(), {}, sender)
    assert sent[-1][3] and sent[-1][3]["list"]["sections"][0]["rows"][0]["id"] == "cmd:panchang"
    evt["data"] = {**evt["data"], "id": "M2", "type": "list_reply", "button_id": "cmd:rashifal", "text": "राशिफल"}
    wa_bot.handle_webhook(json.dumps(evt).encode(), {}, sender)
    assert sent[-1][1].count("•") == 12 and sent[-1][3]["list"]["sections"][0]["rows"][0]["id"] == "cmd:rashifal:mesha"
    evt["data"] = {**evt["data"], "id": "M3", "button_id": "cmd:rashifal:mesha", "text": "मेष"}
    wa_bot.handle_webhook(json.dumps(evt).encode(), {}, sender)
    assert "मेष — आज का राशिफल" in sent[-1][1] and sent[-1][3] is None
    # old 2-arg sender: interactive extra is dropped, text still goes
    sent2 = []
    evt["data"] = {**evt["data"], "id": "M4", "type": "text", "text": "help"}
    wa_bot.handle_webhook(json.dumps(evt).encode(), {}, lambda p, t: (sent2.append(t) or {"ok": True, "detail": ""}))
    assert sent2 and "panchang" in sent2[0].lower()


def test_settings_over_whatsapp(store, monkeypatch):
    monkeypatch.setattr(notify, "send_whatsapp", lambda *a, **k: {"ok": True, "detail": ""})
    assert "06:30" in wa_bot.answer("919876543210", "शुरू", "राम")
    assert "इंदौर" in wa_bot.answer("919876543210", "शहर इंदौर")
    s = store.get("919876543210"); assert abs(s["lat"] - 22.72) < 0.1 and s["place"] == "इंदौर"
    assert "07:15" in wa_bot.answer("919876543210", "समय 7:15 am")
    assert store.get("919876543210")["daily_time"] == "07:15"
    r = wa_bot.answer("919876543210", "जन्म 15-05-1990 10:30 जबलपुर")
    s = store.get("919876543210"); assert s["moon_sign_name"] and s["want_rashifal"] == 1 and json.loads(s["birth"])["date"] == "1990-05-15" and "धनु" in r
    assert "తెలుగు" in wa_bot.answer("919876543210", "भाषा telugu") and store.get("919876543210")["lang"] == "te"
    wa_bot.answer("919876543210", "language hindi")
    st = wa_bot.answer("919876543210", "सेटिंग")
    assert "इंदौर" in st and "07:15" in st and "1990-05-15" in st
    assert "पहचाना नहीं" in wa_bot.answer("919876543210", "शहर xyzville")
    # settings on a number that never subscribed → auto-subscribes first
    assert "✅" in wa_bot.answer("919111111111", "शहर भोपाल") and store.get("919111111111")["place"] == "भोपाल"


def test_weekly_rashifal_and_personal_muhurta(store, monkeypatch):
    monkeypatch.setattr(notify, "send_whatsapp", lambda *a, **k: {"ok": True, "detail": ""})
    w = wa_bot.answer("919876543210", "साप्ताहिक राशिफल मेष")
    assert "साप्ताहिक राशिफल" in w and "–" in w
    assert "monthly rashifal" in wa_bot.answer("919876543210", "monthly rashifal").lower()
    wa_bot.answer("919876543210", "शुरू"); wa_bot.answer("919876543210", "जन्म 15-05-1990 10:30 दिल्ली")
    m = wa_bot.answer("919876543210", "मुहूर्त विवाह")
    assert "आपके लिए" in m and "चंद्रबल" in m and "उत्तम लग्न" in m
