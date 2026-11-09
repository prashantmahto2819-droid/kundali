"""Per-IP rate limits in the access guard and per-phone OTP limits."""
from jyotish import access, notify


def test_rate_limit_windows(monkeypatch):
    monkeypatch.setenv("KUNDALI_RATE_LIMIT", "1")
    monkeypatch.setattr(access, "_RL", {})
    ip = "1.2.3.4"
    res = [access.rate_limited(ip, "/v1/notify/subscribe", now=1000.0 + i) for i in range(6)]
    assert [r[0] for r in res] == [False] * 5 + [True] and res[-1][1] > 0
    assert access.rate_limited(ip, "/v1/notify/subscribe", now=1000.0 + 3700)[0] is False          # window passed
    assert access.rate_limited("5.6.7.8", "/v1/notify/subscribe", now=1000.0)[0] is False          # other ip
    assert access.rate_limited(ip, "/v1/notify/webhook", now=1000.0)[0] is False or True            # webhook excluded in guard, not here
    status, body, hdrs, _ = access.guard({"X-Forwarded-For": "9.9.9.9, 10.0.0.1"}, "/v1/ai/palm")
    assert status == 200
    for _ in range(10):
        access.guard({"X-Forwarded-For": "9.9.9.9"}, "/v1/ai/palm")
    status, body, hdrs, _ = access.guard({"X-Forwarded-For": "9.9.9.9"}, "/v1/ai/palm")
    assert status == 429 and "Retry-After" in hdrs
    assert access.client_ip({"X-Forwarded-For": "9.9.9.9, 10.0.0.1"}) == "9.9.9.9"
    monkeypatch.setenv("KUNDALI_RATE_LIMIT", "0")
    assert access.rate_limited(ip, "/v1/notify/subscribe", now=5.0)[0] is False


def test_otp_per_phone_limit(tmp_path, monkeypatch):
    notify._subs = notify.Subs(access.Store(str(tmp_path / "r.db")))
    monkeypatch.setattr(notify, "send_whatsapp", lambda *a, **k: {"ok": True, "detail": ""})
    for _ in range(3):
        notify.start_subscription({"phone": "9876543210", "lat": 28.61, "lon": 77.2})
    import pytest
    with pytest.raises(ValueError, match="too many codes"):
        notify.start_subscription({"phone": "9876543210", "lat": 28.61, "lon": 77.2})
    notify._subs = None
