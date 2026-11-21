from jyotish import handlers, regional, regional_report

B = {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99, "name": "Ram", "place": "Jabalpur"}


def test_every_regional_language_gets_a_patrika_page():
    for lang in regional_report.LANGS:
        assert len(regional_report.T[lang]) == 21 and len(regional_report.PLANETS_L[lang]) == 9 and len(regional_report.SHORT_L[lang]) == 9
        h = handlers.report_from_payload({**B, "lang": lang})
        assert f'<section class="regional" lang="{lang}"' in h and regional_report.T[lang][0] in h
        assert regional.SIGNS_L[lang][3] in h                      # lagna Karka in that language
        assert h.count('class="regional"') == 1
    assert 'class="regional"' not in handlers.report_from_payload({**B, "lang": "hi"})


def test_tamil_page_details():
    h = handlers.report_from_payload({**B, "lang": "ta"})
    assert "ஜாதகம்" in h and "தனுசு" in h and "உத்திராடம் – 1" in h and "புதன்</b> <small>(வக்ரம்)" in h and "மகாதசை" in h


def test_regional_match_page():
    from jyotish import regional_report
    P = lambda n, d, t: {"name": n, "date": d, "time": t, "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}
    for lang in regional_report.LANGS:
        h = handlers.match_report_from_payload({"boy": P("A", "1990-05-15", "10:30"), "girl": P("B", "1993-08-20", "06:15"), "lang": lang})
        assert regional_report.MT[lang][0] in h and "28.5 / 36" in h and all(k in h for k in regional_report.KOOTA_L[lang])
        assert regional.SIGNS_L[lang][8] in h and regional.SIGNS_L[lang][5] in h          # Dhanu groom, Kanya bride
