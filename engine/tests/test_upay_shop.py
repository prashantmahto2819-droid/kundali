import json

import pytest

from jyotish import access, handlers, shop, upay

B = {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}


def test_problem_list_and_general_plan():
    probs = handlers.upay_problems()["problems"]
    assert len(probs) >= 15 and {"career", "marriage_delay", "health", "sade_sati"} <= {p["key"] for p in probs}
    r = handlers.upay_from_payload({"problem": "career", "moon_sign": 8})
    assert r["basis"] == "moon_sign" and r["planets"][0]["planet"] == "Sun" and all(p["gem"] is None for p in r["planets"])   # no stone without a chart
    assert "धनु" in r["planets"][-1]["why_hi"] and r["practices_hi"]
    with pytest.raises(handlers.BadRequest):
        handlers.upay_from_payload({"problem": "lottery"})


def test_chart_plan_picks_afflicted_planets_and_safe_gems():
    r = handlers.upay_from_payload({"problem": "marriage_delay", **B})          # Karka lagna: 7th lord Saturn (with Rahu)
    assert r["basis"] == "chart"
    first = r["planets"][0]
    assert first["planet"] == "Saturn" and "सातवें" not in first["why_hi"] and "7वें भाव का स्वामी" in first["why_hi"] and "राहु" in first["why_hi"]
    assert first["gem"] is None                                                  # Saturn is the 7th/8th lord for Karka: no blue sapphire
    assert any(p["gem"] and p["gem"]["hi"] == "पुखराज" for p in r["planets"])   # Jupiter, 9th lord, may get a stone
    for p in r["planets"]:
        assert p["mantra"].startswith("ॐ") and p["count"] > 0 and p["daan_hi"]


def test_ratna_by_lagna_and_moon():
    r = handlers.ratna_from_payload(B)
    assert [s["gem_hi"] for s in r["by_lagna"]["stones"]] == ["मोती", "मूँगा", "पुखराज"]
    assert {a["gem_hi"] for a in r["by_lagna"]["avoid"]} == {"पन्ना", "नीलम"}
    assert r["by_moon"]["stone"]["gem_hi"] == "पुखराज" and len(r["table"]) == 12 and len(r["how_hi"]) == 4
    assert handlers.ratna_from_payload({"moon_sign": 0})["by_moon"]["stone"]["gem_hi"] == "मूँगा"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDALI_DB", str(tmp_path / "s.db"))
    monkeypatch.setenv("KUNDALI_ADMIN_KEY", "secret")
    monkeypatch.setenv("KUNDALI_UPI_ID", "shop@upi")
    monkeypatch.setenv("KUNDALI_SHOP_WHATSAPP", "919800000000")
    monkeypatch.setenv("KUNDALI_SHOP_SHIPPING", "60")
    monkeypatch.setenv("KUNDALI_SHOP_FREE_ABOVE", "2000")
    shop._shop = shop.Shop(access.Store(str(tmp_path / "s.db")))
    yield shop._shop
    shop._shop = None


def test_shop_catalogue_order_and_admin(store):
    H = {"X-Admin-Key": "secret"}
    with pytest.raises(handlers.BadRequest):
        handlers.shop_admin_from_payload({"action": "list"}, {})
    pid = handlers.shop_admin_from_payload({"action": "save_product", "product": {"name_hi": "पुखराज (सीलोन)", "name_en": "Yellow sapphire", "category": "gemstone",
                                            "planet": "Jupiter", "price": 1500, "unit": "ratti", "min_qty": 3, "max_qty": 9, "stock": 2, "certificate": "IGI"}}, H)["saved"]
    handlers.shop_admin_from_payload({"action": "save_product", "product": {"name_hi": "पंचमुखी रुद्राक्ष", "category": "rudraksha", "price": 251, "unit": "piece"}}, H)
    png = "data:image/png;base64," + __import__("base64").b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 100).decode()
    imgs = handlers.shop_admin_from_payload({"action": "upload_image", "id": pid, "data": png}, H)["images"]
    assert imgs[0].startswith("/v1/shop/img/") and shop.image_path(imgs[0].rsplit("/", 1)[1])
    cat = handlers.shop_products_from_query({"planet": "Jupiter"})
    assert [p["id"] for p in cat["products"]] == [pid] and cat["settings"]["upi"] and cat["products"][0]["unit_hi"] == "रत्ती"
    sent = []
    with pytest.raises(handlers.BadRequest):
        handlers.shop_order_from_payload({"items": [{"id": pid, "qty": 1}], "name": "राम", "phone": "9876543210", "address": "12 गांधी मार्ग", "pincode": "482001"})  # below 3 ratti
    r = shop.place_order({"items": [{"id": pid, "qty": 5.25, "option": "चाँदी की अँगूठी"}], "name": "राम", "phone": "98765 43210", "address": "12 गांधी मार्ग, नेपियर टाउन",
                          "city": "जबलपुर", "pincode": "482001"}, notifier=lambda ph, t: sent.append((ph, t)) or {"ok": True})
    assert r["total"] == 7875.0 and r["shipping"] == 0 and r["upi_link"].startswith("upi://pay?pa=shop%40upi") and "am=7875.00" in r["upi_link"]
    assert r["owner_alerted"] and sent[0][0] == "919800000000" and r["order_id"] in sent[0][1] and "wa.me/919800000000" in r["whatsapp_link"]
    st = handlers.shop_status_from_payload({"order_id": r["order_id"], "phone": "9876543210"})
    assert st["status"] == "new" and st["items"][0]["qty"] == 5.25
    told = []
    res = shop.admin({"action": "order_status", "id": r["order_id"], "status": "paid", "pay_ref": "UPI123", "_sender": lambda ph, m: told.append((ph, m)) or {"ok": True}})
    assert res["customer_notified"] and told[0][0] == "919876543210" and "भुगतान मिल गया" in told[0][1]
    lst = handlers.shop_admin_from_payload({"action": "list"}, H)
    o = lst["orders"][0]
    assert o["status"] == "paid" and o["pay_ref"] == "UPI123" and len(o["history"]) == 2
    assert next(p for p in lst["products"] if p["id"] == pid)["stock"] == 1
    small = shop.place_order({"items": [{"id": [p for p in lst["products"] if p["category"] == "rudraksha"][0]["id"], "qty": 1}], "name": "सीता", "phone": "9876500000",
                              "address": "5 सदर बाज़ार रोड", "pincode": "482001"}, notifier=lambda *a: {"ok": True})
    assert small["shipping"] == 60 and small["total"] == 311
    with pytest.raises(handlers.BadRequest):
        handlers.shop_status_from_payload({"order_id": r["order_id"], "phone": "9000000000"})


def test_bot_upay_ratna_shop(monkeypatch):
    from jyotish import notify, wa_bot
    monkeypatch.setattr(notify, "subs", lambda: type("S", (), {"get": staticmethod(lambda p: None)})())
    a = wa_bot.answer("919811111111", "उपाय नौकरी 15-05-1990 10:30 जबलपुर")
    assert "नौकरी / करियर में रुकावट — उपाय" in a and "आपकी कुंडली से" in a and "मंत्र: ॐ" in a
    g = wa_bot.answer("919811111111", "उपाय विवाह धनु")
    assert "विवाह में देरी" in g and "सटीक उपाय" in g
    assert "किस समस्या" in wa_bot.answer("919811111111", "उपाय")
    r = wa_bot.answer("919811111111", "रत्न 15-05-1990 10:30 जबलपुर")
    assert "मोती" in r and "न पहनें" in r and "नीलम" in r
    assert "पुखराज" in wa_bot.answer("919811111111", "रत्न धनु")
    assert "Lucky gemstones" in wa_bot.answer("919811111111", "ratna mesh") and "Red coral" in wa_bot.answer("919811111111", "ratna mesh")
    assert "रत्न शॉप" in wa_bot.answer("919811111111", "शॉप")
