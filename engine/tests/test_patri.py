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


def test_adhika_masa_from_real_lunations():
    def masa(date):
        return patri.details(compute_chart(date, "10:00", "Asia/Kolkata", 28.6, 77.2))["birth"]["masa"]
    assert masa("2023-07-25")["name"] == "Adhika Shravana" and masa("2023-07-25")["adhika"]
    assert masa("2023-08-20")["name"] == "Shravana" and not masa("2023-08-20")["adhika"]
    assert masa("2020-10-01")["name"] == "Adhika Ashwina"
    assert masa("2018-06-01")["name"] == "Adhika Jyeshtha"
    assert masa("2018-06-20")["name"] == "Jyeshtha"


def test_ghata_chakra_dhanu_row_matches_printout():
    g = KORBA["patri"]["ghata"]
    assert (g["masa"], g["tithi"], g["vara"], g["nakshatra"], g["karana"], g["prahar"]) == ("Shravana", "3 8 13", "Shukravara", "Bharani", "Taitila", 1)
    assert (g["chandra"], g["stri_chandra"]) == ("Karka", "Makara")       # printout gives sign numbers 4 and 10
    assert all(r in patri.GHATA for r in patri.SIGNS) and g["review_status"] == "draft"


def test_sunrise_conventions():
    b = KORBA["patri"]["birth"]
    assert b["sunrise"] == "06:07" and b["sunrise_centre"] == "06:11"     # centre/no-refraction is ~4 min later
    assert b["ishta_kaal"]["text"] == "20:22"                              # printout 20:25 (its sunrise 06:10:43)
