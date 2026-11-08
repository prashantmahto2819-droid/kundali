import re

from jyotish import compute_chart
from jyotish.constants import KARANA_HI, KARANA_REPEATING, PAKSHA_HI, TITHI_HI, TITHI_NAMES, YOGA_HI, YOGA_NAMES
from jyotish.panchang import karana_info, tithi_info, yoga_info


def test_every_name_has_hindi():
    assert set(TITHI_NAMES) | {"Purnima", "Amavasya"} == set(TITHI_HI)
    assert set(YOGA_NAMES) == set(YOGA_HI) and len(YOGA_HI) == 27
    assert set(KARANA_REPEATING) | {"Shakuni", "Chatushpada", "Naga", "Kimstughna"} == set(KARANA_HI)
    assert set(PAKSHA_HI) == {"Shukla", "Krishna"}


def test_all_positions_resolve():
    for i in range(360):
        t = tithi_info(0.0, float(i))
        assert t["name_hi"] and t["paksha_hi"]
        assert karana_info(0.0, float(i))["name_hi"] and yoga_info(float(i), 0.0)["name_hi"]
    assert tithi_info(0.0, 179.0)["name_hi"] == "पूर्णिमा" and tithi_info(0.0, 359.0)["name_hi"] == "अमावस्या"


def test_yogas_have_devanagari_explanations():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    for y in c["yogas"]:
        assert re.search(r"[ऀ-ॿ]", y["why_hi"]) and not re.search(r"[A-Za-z]{4,}", y["why_hi"]), y["id"]
