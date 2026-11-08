import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from jyotish import handlers, i18n

ROOT = Path(__file__).resolve().parents[2]
PAYLOADS = [
    {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99},
    {"date": "1975-12-02", "time": "23:10", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2},
    {"date": "1985-08-09", "time": "03:30", "tz": "Asia/Kolkata", "lat": 13.08, "lon": 80.27},
    {"date": "1999-09-09", "time": "09:09", "tz": "America/New_York", "lat": 40.71, "lon": -74.0},
]


def test_translation_is_all_or_nothing_and_safe():
    assert i18n.translate_text("सूर्य") == "Sun"
    assert i18n.translate_text("सूर्योदय") == "सूर्योदय"                   # unknown word untouched (no partial 'Sunोदय')
    assert i18n.translate_text("बिलकुल अनजान वाक्य") == "बिलकुल अनजान वाक्य"
    assert i18n.translate_text("  Mars  ") == "  Mars  "                    # Latin text passes through
    assert i18n.translate_text("{1}") == "{1}"
    out = i18n.translate_text("गजकेसरी योग")
    assert out == "Gajakesari yoga"
    assert not re.search("[ऀ-ॿ]", i18n.translate_text("शनि महादशा"))


def test_ordinals_and_lists():
    assert i18n.translate_text("3वाँ भाव (साहस और पराक्रम)") == "house 3 (courage and effort)"
    assert re.sub(r"[ऀ-ॿ]", "", i18n._ORD.sub(i18n._ordinal, "1वाँ 2वें 3वीं 11वाँ 22वाँ")) == "1st 2nd 3rd 11th 22nd"


@pytest.mark.parametrize("payload", PAYLOADS)
def test_english_report_is_fully_translated(payload, monkeypatch):
    monkeypatch.setenv("KUNDALI_BACKEND", "analytic")
    hi = handlers.report_from_payload(payload)
    en = handlers.report_from_payload({**payload, "lang": "en"})
    assert '<html lang="hi">' in hi and '<html lang="en">' in en
    assert i18n.coverage(hi) >= 0.98
    left = [" ".join(t.split()) for t in re.split(r"<[^>]+>", re.sub(r"<style.*?</style>", "", en, flags=re.S))
            if re.search("[ऀ-ॿ]", t)]
    assert len(left) <= 2, left
    assert "Lal Kitab (draft)" in en and "Kundali report" in en


def test_default_language_is_unchanged_hindi():
    hi = handlers.report_from_payload(PAYLOADS[0])
    assert "सारांश" in hi and "Summary" not in hi


def test_dictionary_file_is_reproducible():
    path = ROOT / "data" / "i18n_en.json"
    before = path.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "engine" / "tools" / "build_i18n.py")], check=True, capture_output=True)
    assert path.read_text(encoding="utf-8") == before
    d = json.loads(before)
    assert len(d["exact"]) > 250 and len(d["phrases"]) > 400 and len(d["patterns"]) > 30
