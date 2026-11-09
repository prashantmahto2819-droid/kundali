"""Festival calendar from the engine's own panchang."""
from jyotish import festivals as f, handlers


def _fest(year):
    c = f.calendar(year, 28.61, 77.2, "Asia/Kolkata")
    return c, {e["key"]: e["date"] for e in c["events"] if e["kind"] == "festival"}


def test_known_dates_2025_and_2026():
    c25, d25 = _fest(2025)
    assert d25["diwali"] == "2025-10-20" and d25["holi"] == "2025-03-14" and d25["makar_sankranti"] == "2025-01-14"
    assert d25["ram_navami"] == "2025-04-06" and d25["ganesh_chaturthi"] == "2025-08-27" and d25["vijayadashami"] == "2025-10-02"
    assert d25["raksha_bandhan"] == "2025-08-09" and d25["maha_shivaratri"] == "2025-02-26" and d25["chhath"] == "2025-10-27"
    assert c25["adhika_masa"] == []
    c26, d26 = _fest(2026)
    assert d26["diwali"] == "2026-11-08" and d26["makar_sankranti"] == "2026-01-14"
    assert [a["masa"] for a in c26["adhika_masa"]] == ["Jyeshtha"] and c26["adhika_masa"][0]["start"].startswith("2026-05")


def test_structure_and_vrat_days():
    c, _ = _fest(2026)
    kinds = {e["kind"] for e in c["events"]}
    assert kinds == {"festival", "ekadashi", "purnima", "amavasya", "pradosh", "chaturthi", "shivaratri", "regional", "national", "christian", "islamic"}
    by = {e["key"]: e["date"] for e in c["events"]}
    assert by["pongal"] == "2026-01-14" and by["lohri"] == "2026-01-13" and by["tamil_new_year"] == "2026-04-14" and by["easter"] == "2026-04-05"
    assert by["eid_ul_fitr_1447"] == "2026-03-20" and by["eid_ul_adha_1447"] == "2026-05-27" and by["kali_puja"] == by["diwali"] and by["republic_day"] == "2026-01-26"
    assert by["onam"].startswith("2026-08") and by["durga_puja_shashthi"] == "2026-10-16" and by["guru_nanak_jayanti"] == by["kartika_purnima"]
    assert 22 <= sum(1 for e in c["events"] if e["kind"] == "pradosh") <= 27 and 10 <= sum(1 for e in c["events"] if e["kind"] == "shivaratri") <= 13
    ek = [e for e in c["events"] if e["kind"] == "ekadashi"]
    assert 24 <= len(ek) <= 27 and any("अधिक" in e["name_hi"] for e in ek)           # adhika Jyeshtha adds two
    assert all(e["date"].startswith("2026") for e in c["events"])
    dates = [e["date"] for e in c["events"]]
    assert dates == sorted(dates)
    assert len([e for e in c["events"] if e["kind"] == "festival"]) == len(f.FESTIVALS) + 1   # + Makar Sankranti
    # Holi is the day after Holika Dahan
    d = {e["key"]: e["date"] for e in c["events"] if e["kind"] == "festival"}
    assert d["holi"] > d["holika_dahan"]


def test_handler_validation():
    out = handlers.festivals_from_query({"year": "2027", "lat": "22.35", "lon": "82.68", "tz": "Asia/Kolkata"})
    assert out["year"] == 2027 and out["events"]
    import pytest
    with pytest.raises(handlers.BadRequest):
        handlers.festivals_from_query({"year": "1800"})
    with pytest.raises(handlers.BadRequest):
        handlers.festivals_from_query({"year": "2026", "tz": "Mars/Olympus"})
