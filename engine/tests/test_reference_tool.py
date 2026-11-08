import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_reference as cr  # noqa: E402


def test_parse_position_formats():
    assert cr.parse_position("Taurus 2°10′45″") == pytest.approx(30 + 2 + 10 / 60 + 45 / 3600)
    assert cr.parse_position("Vrishabha 02:10:45") == pytest.approx(32.179166, abs=1e-5)
    assert cr.parse_position("Tau 2 10") == pytest.approx(32.1666, abs=1e-3)
    assert cr.parse_position("Makara 22°56′") == pytest.approx(9 * 30 + 22 + 56 / 60)
    assert cr.parse_position("45.5") == 45.5
    assert cr.parse_position("Pisces 29°59′59″") < 360
    with pytest.raises(ValueError):
        cr.parse_position("Nowhere 3°")


def test_diff_wraps_around_zero():
    assert cr.diff_arcmin(0.1, 359.9) == pytest.approx(12.0)
    assert cr.diff_arcmin(359.9, 0.1) == pytest.approx(-12.0)


def test_check_file_reports_failure_and_success(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDALI_BACKEND", "analytic")
    inp = {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.1815, "lon": 79.9864}
    from jyotish import compute_chart
    chart = compute_chart(**inp)
    sun = chart["planets"][0]["longitude"]

    good = tmp_path / "good.json"
    good.write_text(json.dumps({"input": inp, "expected": {"planets": {"Sun": str(sun)},
                                                             "moon_nakshatra": "Shravana"}}))
    rows, ok = cr.check_file(good, 1.0)
    assert ok and rows[0]["diff_arcmin"] == pytest.approx(0, abs=1e-6)

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"input": inp, "expected": {"planets": {"Sun": str((sun + 0.5) % 360)}}}))
    rows, ok = cr.check_file(bad, 1.0)
    assert not ok and rows[0]["diff_arcmin"] == pytest.approx(-30, abs=0.01)
