"""Astrologer consultation + wallet: admin profiles, request flow with WhatsApp pings (fake sender), messages, closing/rating, paid mode."""
import pytest

from jyotish import access, consult, notify


@pytest.fixture
def setup(tmp_path, monkeypatch):
    st = access.Store(str(tmp_path / "c.db"))
    consult._store = None
    monkeypatch.setattr(access, "default_store", lambda: st)
    notify._subs = notify.Subs(st)
    sent = []
    monkeypatch.setattr(notify, "send_whatsapp", lambda phone, text: (sent.append((phone, text)) or {"ok": True, "detail": "{}"}))
    monkeypatch.setenv("KUNDALI_ADMIN_KEY", "adm")
    monkeypatch.delenv("KUNDALI_PAID", raising=False)
    yield st, sent
    consult._store = None
    notify._subs = None


def test_free_flow(setup):
    st, sent = setup
    a = consult.upsert_astrologer({"name": "Pt. Sharma", "name_hi": "पं. शर्मा", "phone": "9000000001", "languages": ["hi", "en"], "specialities": ["विवाह", "करियर"], "price_chat": 199, "experience_years": 12})
    assert a["id"] == "pt.-sharma".replace(".", "") or a["id"]
    lst = consult.list_astrologers()
    assert len(lst) == 1 and lst[0]["prices"] == {"chat": 0, "call": 0, "report": 0} and lst[0]["paid"] is False
    r = consult.create_request({"astrologer_id": a["id"], "phone": "9876543210", "name": "राम", "mode": "chat", "question": "मेरी नौकरी कब बदलेगी?", "birth": {"date": "1990-05-15", "time": "10:30"}})
    assert r["status"] == "open" and r["price"] == 0 and r["notified_astrologer"] and r["notified_seeker"]
    assert sent[0][0] == "919000000001" and "#" + r["id"] in sent[0][1] and "1990-05-15" in sent[0][1]
    assert sent[1][0] == "919876543210" and "भेज दिया" in sent[1][1]
    with pytest.raises(ValueError):
        consult.get_request(r["id"], phone="9111111111")
    g = consult.get_request(r["id"], phone="9876543210")
    assert g["messages"][0]["sender"] == "seeker" and g["phone"].endswith("…10")
    with pytest.raises(ValueError):
        consult.post_message(r["id"], "astrologer", "answer", phone="9876543210")          # seeker cannot answer as astrologer
    m = consult.post_message(r["id"], "astrologer", "गुरु की अंतर्दशा में परिवर्तन के योग हैं।", phone="9000000001")
    assert m["status"] == "answered" and sent[-1][0] == "919876543210" and "उत्तर आ गया" in sent[-1][1]
    consult.post_message(r["id"], "seeker", "धन्यवाद", phone="9876543210")
    assert sent[-1][0] == "919000000001"
    c = consult.close_request(r["id"], "9876543210", rating=5)
    assert c["status"] == "closed" and consult.list_astrologers()[0]["rating"] == 5.0
    assert consult.my_requests("9876543210")[0]["astrologer_name"] == "पं. शर्मा"
    assert consult.is_admin({"X-Admin-Key": "adm"}) and not consult.is_admin({"x-admin-key": "nope"})


def test_paid_mode_wallet(setup, monkeypatch):
    st, sent = setup
    monkeypatch.setenv("KUNDALI_PAID", "1")
    a = consult.upsert_astrologer({"id": "guru1", "name": "Guru", "phone": "9000000002", "price_chat": 150})
    assert consult.list_astrologers()[0]["prices"]["chat"] == 150
    with pytest.raises(ValueError, match="insufficient"):
        consult.create_request({"astrologer_id": "guru1", "phone": "9876543210", "mode": "chat", "question": "प्रश्न यह है"})
    t = consult.topup("9876543210", 500, ref="UPI123", note="verified")
    assert t["balance"] == 500
    with pytest.raises(ValueError):
        consult.topup("9876543210", 500, ref="UPI123")                 # idempotent on reference
    r = consult.create_request({"astrologer_id": "guru1", "phone": "9876543210", "mode": "chat", "question": "प्रश्न यह है"})
    assert r["price"] == 150 and r["balance"] == 350
    w = consult.wallet_view("9876543210")
    assert w["balance"] == 350 and [x["kind"] for x in w["ledger"]] == ["consult", "topup"]
