"""Personal dasha/transit alerts, South Indian chart rendering, festival override files."""
import json
from datetime import date

from jyotish import alerts, festivals, report
from jyotish.handlers import chart_from_payload, report_from_payload

BIRTH = {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2}


def test_alerts_detect_ingress_station_and_dasha_shape():
    ch = chart_from_payload(BIRTH)
    a = alerts.alerts(ch, date(2026, 11, 13), "Asia/Kolkata")
    kinds = [e["kind"] for e in a["today"]]
    assert "ingress" in kinds                                  # Mars enters Simha that day (analytic backend)
    ev = next(e for e in a["today"] if e["kind"] == "ingress")
    assert ev["planet"] == "Mars" and "चंद्र से" in ev["hi"] and "house from your Moon" in ev["en"]
    st = alerts.alerts(ch, date(2026, 11, 14), "Asia/Kolkata")["today"]
    assert any(e["kind"] == "station" and e["retrograde"] is False for e in st)
    # a day with no change
    assert alerts.alerts(ch, date(2026, 11, 10), "Asia/Kolkata")["today"] == []
    # dasha change detection on the antardasha boundary (Sun AD ends 2027-05-22 for this chart)
    d = alerts.alerts(ch, date(2027, 5, 23), "Asia/Kolkata")
    assert any(e["kind"] == "dasha" and e["level"] == 2 for e in d["today"] + [{**u, "kind": u["kind"], "level": u.get("level")} for u in d["upcoming"]]) or \
        any(e["kind"] == "dasha" for e in alerts.alerts(ch, date(2027, 5, 22), "Asia/Kolkata")["today"])
    assert "alerts" in ch and set(ch["alerts"]) >= {"today", "upcoming"}


def test_sadesati_messages():
    # Moon in Meena; Saturn moves Makara→Kumbha (12th from the Moon) → Sade Sati starts, rising phase
    fake = {"planets": [{"name": "Moon", "sign": 11}], "dasha": {"mahadashas": []}}
    from jyotish import transit
    orig = transit.positions_at
    def fake_pos(dt, b, system="lahiri"):
        sat = 9 if dt.day == 1 else 10
        return {p: {"sign": sat if p == "Saturn" else 0, "retrograde": False} for p in ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"]}
    alerts.positions_at = fake_pos
    try:
        out = alerts._day_changes(fake, date(2026, 1, 1), date(2026, 1, 2), "Asia/Kolkata")
    finally:
        alerts.positions_at = orig
    ss = [e for e in out if e["kind"] == "sadesati"]
    assert ss and ss[0]["state"] == "start" and ss[0]["phase"] == "rising" and "साढ़ेसाती शुरू" in ss[0]["hi"]


def test_south_chart_svg_and_report_style():
    cells = [{"sign": (3 + i) % 12, "planets": [("सू", False)] if i == 0 else []} for i in range(12)]   # Karka lagna
    svg = report.south_chart_svg(cells)
    assert svg.count("<rect") == 12 and "<line" in svg                      # lagna diagonal
    assert 'x="300" y="100"' in svg                                          # Karka sits at column 3, row 1
    html_s = report_from_payload({**BIRTH, "chart_style": "south"})
    html_n = report_from_payload(BIRTH)
    assert html_s.count("<rect") >= 24 and html_n.count("<rect") < html_s.count("<rect")


def test_festival_overrides(tmp_path, monkeypatch):
    import pathlib
    root = pathlib.Path(festivals.__file__).resolve().parents[2] / "data" / "overrides"
    f = root / "festivals_2031.json"
    f.write_text(json.dumps({"add": [{"key": "x_day", "name_hi": "एक्स दिवस", "date": "2031-02-02", "kind": "national"}],
                             "move": [{"key": "republic_day", "date": "2031-01-27"}], "remove": ["gandhi_jayanti"]}, ensure_ascii=False), "utf-8")
    try:
        ev = festivals.apply_overrides(2031, [{"key": "republic_day", "date": "2031-01-26", "kind": "national", "name_hi": "गणतंत्र दिवस", "name_en": "Republic Day"},
                                              {"key": "gandhi_jayanti", "date": "2031-10-02", "kind": "national", "name_hi": "गांधी जयंती", "name_en": "Gandhi Jayanti"}])
    finally:
        f.unlink()
    keys = {e["key"]: e for e in ev}
    assert "gandhi_jayanti" not in keys and keys["republic_day"]["date"] == "2031-01-27" and keys["republic_day"]["rule"] == "override"
    assert keys["x_day"]["name_en"] == "एक्स दिवस" and keys["x_day"]["kind"] == "national"
    assert festivals.apply_overrides(2032, [{"key": "a"}]) == [{"key": "a"}]
