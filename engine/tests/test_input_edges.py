from datetime import timezone

from jyotish import compute_chart, handlers
from jyotish.timeutil import local_time_issue, local_to_utc


def codes(c):
    return {w["code"] for w in c["input_warnings"]}


def test_history_and_dst_are_applied():
    assert local_to_utc("1990-07-01", "12:00", "Europe/London").hour == 11            # BST
    assert local_to_utc("1944-06-01", "12:00", "Asia/Kolkata").strftime("%H:%M") == "05:30"   # war-time +6:30
    assert local_to_utc("1990-01-15", "12:00", "Europe/London").hour == 12            # GMT


def test_gap_and_fold_detection():
    assert local_time_issue("1990-03-25", "01:30", "Europe/London") == "nonexistent"
    assert local_time_issue("1990-10-28", "01:30", "Europe/London") == "ambiguous"
    assert local_time_issue("1990-07-01", "12:00", "Europe/London") is None
    assert local_time_issue("1990-05-17", "06:45", "Asia/Kolkata") is None


def test_warnings_in_chart_and_report():
    c = compute_chart("1990-03-25", "01:30", "Europe/London", 51.5, -0.1)
    assert "time_nonexistent" in codes(c)
    assert "time_ambiguous" in codes(compute_chart("1990-10-28", "01:30", "Europe/London", 51.5, -0.1))
    assert "polar_latitude" in codes(compute_chart("2000-06-21", "12:00", "UTC", 78.2, 15.6))
    assert "date_outside_verified_range" in codes(compute_chart("2150-01-01", "12:00", "UTC", 28.6, 77.2))
    assert codes(compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)) <= {"birth_time_sensitive"}   # navamsa lagna 5 min
    html = handlers.report_from_payload({"date": "1990-03-25", "time": "01:30", "tz": "Europe/London", "lat": 51.5, "lon": -0.1})
    assert "⚠" in html


def test_extreme_places_do_not_crash():
    for lat, lon in [(89.9, 0), (-89.9, 100), (0, 0), (-77.8, 166.7), (35.7, 139.7), (-33.9, 18.4)]:
        c = compute_chart("2000-06-21", "12:00", "UTC", lat, lon)
        assert 0 <= c["lagna"]["longitude"] < 360 and len(c["timeline"]["periods"]) >= 5
    for d in ("1850-06-01", "1900-01-01", "2100-12-31", "2200-01-01"):
        compute_chart(d, "12:00", "UTC", 28.6, 77.2)
