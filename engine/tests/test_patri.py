from jyotish import compute_chart, patri

KORBA = compute_chart("1991-11-10", "14:20", "Asia/Kolkata", 22.3667, 82.7667)
JBP = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)


def test_matches_the_printed_patri():
    d = patri.details(KORBA)
    b, a = d["birth"], d["avakahada"]
    assert (b["vara"]["name"], b["tithi"]["paksha"], b["tithi"]["name"], b["yoga"]["name"]) == ("Ravivara", "Shukla", "Chaturthi", "Sukarma")
    assert (b["nakshatra"]["name"], b["nakshatra"]["pada"], b["nakshatra"]["lord"]) == ("Mula", 3, "Ketu")
    assert (b["masa"]["name"], b["vikram_samvat"], b["shaka_samvat"]) == ("Kartika", 2048, 1913)
    assert b["sun_sign_tropical"]["name"] == "Scorpio" and b["ayana"]["name"] == "Dakshinayana"
    assert 20 <= b["ishta_kaal"]["ghati"] <= 21                    # printout 20:25 with its own sunrise
    assert (a["varna"]["name"], a["vashya"]["name"], a["yoni"]["name"], a["gana"]["name"], a["nadi"]["name"]) == \
        ("Kshatriya", "Manav", "Dog", "Rakshasa", "Adi")
    assert a["name_syllable"]["pada"] == "भा" and a["name_syllable"]["pada_en"] == "Bha"
    assert (a["lagna"]["name"], a["lagna"]["lord"], a["rashi"]["name"], a["rashi"]["lord"]) == ("Kumbha", "Saturn", "Dhanu", "Jupiter")


def test_other_dates_and_year_boundary():
    d = patri.details(JBP)["birth"]
    assert (d["masa"]["name"], d["vikram_samvat"], d["shaka_samvat"], d["ritu"]["name"]) == ("Vaishakha", 2047, 1912, "Vasanta")
    feb = patri.details(compute_chart("2000-02-10", "10:00", "Asia/Kolkata", 28.6, 77.2))["birth"]
    assert (feb["masa"]["name"], feb["vikram_samvat"], feb["shaka_samvat"]) == ("Magha", 2056, 1921)
    apr = patri.details(compute_chart("2024-04-15", "10:00", "Asia/Kolkata", 28.6, 77.2))["birth"]
    assert (apr["masa"]["name"], apr["vikram_samvat"]) == ("Chaitra", 2081)


def test_chart_and_report_carry_patri():
    from jyotish import report
    assert KORBA["patri"]["avakahada"]["yoni"]["name_hi"] == "श्वान"
    h = report.render(KORBA)
    assert "जन्म विवरण" in h and "अवकहड़ा" not in h.split("जन्म विवरण")[0] and "श्वान" in h


def test_syllable_tables_are_complete():
    assert len(patri.SYLLABLES) == len(patri.SYLLABLES_EN) == 27
    assert all(len(s.split()) == 4 for s in patri.SYLLABLES + patri.SYLLABLES_EN)
