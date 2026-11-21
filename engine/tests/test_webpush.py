import json
from datetime import date, datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from jyotish import access, handlers, webpush


@pytest.fixture
def pstore(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDALI_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(webpush, "_KEY", None)
    webpush._subs = webpush.Subs(access.Store(str(tmp_path / "p.db")))
    yield webpush._subs
    webpush._subs = None


def _browser():
    k = ec.generate_private_key(ec.SECP256R1())
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return k, webpush.b64u(pub), webpush.b64u(b"0123456789abcdef")


def test_rfc8291_roundtrip_and_vapid(pstore, tmp_path):
    k, p256dh, auth = _browser()
    msg = json.dumps({"title": "आज का पंचांग", "body": "तिथि"}, ensure_ascii=False).encode()
    body = webpush.encrypt(msg, p256dh, auth)
    assert body[16:20] == (4096).to_bytes(4, "big") and body[20] == 65
    assert webpush.decrypt(body, k, auth) == msg
    # VAPID: key persisted next to the DB, JWT verifies with the public key
    pk = handlers.push_key()["publicKey"]
    assert len(webpush.unb64u(pk)) == 65 and (tmp_path / "vapid.json").exists()
    h = webpush.vapid_header("https://fcm.googleapis.com/fcm/send/abc")
    tok = h.split("t=")[1].split(",")[0]
    head, payload, sig = tok.split(".")
    claims = json.loads(webpush.unb64u(payload))
    assert claims["aud"] == "https://fcm.googleapis.com" and claims["exp"] > datetime.now().timestamp()
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    raw = webpush.unb64u(sig)
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), webpush.unb64u(pk))
    pub.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")), f"{head}.{payload}".encode(), ec.ECDSA(hashes.SHA256()))


def test_subscribe_compose_and_worker(pstore):
    _, p256dh, auth = _browser()
    ep = "https://fcm.googleapis.com/fcm/send/xyz"
    r = handlers.push_subscribe_from_payload({"subscription": {"endpoint": ep, "keys": {"p256dh": p256dh, "auth": auth}},
                                              "lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata", "place": "दिल्ली", "daily_time": "06:30"})
    assert r["subscribed"] and r["count"] == 1
    with pytest.raises(handlers.BadRequest):
        handlers.push_subscribe_from_payload({"subscription": {"endpoint": "http://x", "keys": {}}})
    m = webpush.compose(pstore.get(ep), date(2025, 10, 19))
    assert m["title"].startswith("🌅 आज का पंचांग") and "तिथि:" in m["body"] and "राहु काल" in m["body"] and "कल:" in m["body"] and "दीपावली" in m["body"]
    sent = []
    early = datetime(2026, 11, 21, 0, 50, tzinfo=timezone.utc)        # 06:20 IST — not yet
    assert webpush.run_once(early, sender=lambda s, msg: sent.append(msg) or {"ok": True, "status": 201}) == []
    t = datetime(2026, 11, 21, 1, 1, tzinfo=timezone.utc)             # 06:31 IST
    out = webpush.run_once(t, sender=lambda s, msg: sent.append(msg) or {"ok": True, "status": 201})
    assert len(out) == 1 and sent and pstore.get(ep)["last_daily"] == "2026-11-21"
    assert webpush.run_once(t, sender=lambda s, msg: {"ok": True}) == []        # once a day
    # an expired endpoint (410) is removed
    t2 = datetime(2026, 11, 22, 1, 1, tzinfo=timezone.utc)
    webpush.run_once(t2, sender=lambda s, msg: {"ok": False, "status": 410, "gone": True})
    assert pstore.get(ep) is None


def test_rfc8291_appendix_a_vector():
    d = lambda s: int.from_bytes(webpush.unb64u(s), "big")
    ua = ec.derive_private_key(d("q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94"), ec.SECP256R1())
    eph = ec.derive_private_key(d("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"), ec.SECP256R1())
    body = webpush.encrypt(b"When I grow up, I want to be a watermelon", "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
                           "BTBZMqHH6r4Tts7J_aSIgg", _eph=eph, _salt=webpush.unb64u("DGv6ra1nlYgDCS1FRnbzlw"))
    assert webpush.b64u(body) == ("DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN")
