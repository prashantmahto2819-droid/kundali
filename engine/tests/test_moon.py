"""Moonrise / moonset against published almanac values (Delhi, IST)."""
from datetime import date

from jyotish.moon import moon_latitude, moon_times


def _hm(dt):
    return dt.strftime("%H:%M") if dt else None


def test_delhi_moonrise_matches_almanac_within_two_minutes():
    # Karva Chauth 2025 (10 Oct): published moonrise 20:13 IST; Sharad Purnima 2025 (6 Oct): 17:27 IST
    r = moon_times(date(2025, 10, 10), 28.6139, 77.2090, "Asia/Kolkata")
    assert _hm(r["moonrise"]) in ("20:11", "20:12", "20:13", "20:14", "20:15")
    r2 = moon_times(date(2025, 10, 6), 28.6139, 77.2090, "Asia/Kolkata")
    assert _hm(r2["moonrise"]) in ("17:25", "17:26", "17:27", "17:28", "17:29")


def test_rise_and_set_exist_most_days_and_latitude_bounded():
    missing = 0
    for d in range(1, 31):
        r = moon_times(date(2026, 3, d), 22.35, 82.68, "Asia/Kolkata")
        missing += (r["moonrise"] is None) + (r["moonset"] is None)
    assert missing <= 2                        # one day a month has no rise (or set)
    from jyotish.timeutil import julian_day
    from datetime import datetime, timezone
    for k in range(0, 300, 7):
        b = moon_latitude(julian_day(datetime(2026, 1, 1, tzinfo=timezone.utc)) + k)
        assert -5.4 <= b <= 5.4


def test_day_table_and_festivals_carry_moon_times():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from jyotish.muhurta import day_table
    t = day_table(datetime(2025, 10, 10, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata")), 28.6139, 77.2090, "Asia/Kolkata")
    assert t["moonrise"] and t["moonrise"].startswith("20:1")
    from jyotish import festivals as f
    c = f.calendar(2025, 28.6139, 77.2090, "Asia/Kolkata")
    d = {e["key"]: e["date"] for e in c["events"] if e["kind"] == "festival"}
    assert d["karva_chauth"] == "2025-10-10" and d["sharad_purnima"] == "2025-10-06"
