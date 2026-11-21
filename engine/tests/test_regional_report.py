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
