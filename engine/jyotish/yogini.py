"""Yogini dasha: the 36-year cycle of eight yoginis (Mangala 1, Pingala 2, Dhanya 3, Bhramari 4, Bhadrika 5, Ulka 6, Siddha 7,
Sankata 8 years), started from the Moon's nakshatra: index = (nakshatra number + 3) mod 8, balance in proportion to the part
of the nakshatra still to run. Antardashas divide each period in the same 1..8 proportion from the running yogini onward.
Lords: Mangala–Moon, Pingala–Sun, Dhanya–Jupiter, Bhramari–Mars, Bhadrika–Mercury, Ulka–Saturn, Siddha–Venus, Sankata–Rahu.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import PLANETS_HI

YOGINIS = [("Mangala", "मंगला", 1, "Moon", "शुभ, सौम्य; मन और घर के विषय आगे आते हैं।", "Benign; matters of mind and home come forward."),
           ("Pingala", "पिंगला", 2, "Sun", "मिश्रित; अधिकार, पिता, स्वास्थ्य पर ध्यान।", "Mixed; authority, father and health in focus."),
           ("Dhanya", "धान्या", 3, "Jupiter", "शुभ; धन, विद्या, संतान का पोषण।", "Favourable; wealth, learning and children are nourished."),
           ("Bhramari", "भ्रामरी", 4, "Mars", "भ्रमण, परिवर्तन, संघर्ष की प्रवृत्ति।", "Movement, change and struggle."),
           ("Bhadrika", "भद्रिका", 5, "Mercury", "शुभ; व्यापार, वाणी, मित्रों से लाभ।", "Favourable; trade, speech, friends."),
           ("Ulka", "उल्का", 6, "Saturn", "कठिन; विलंब, श्रम, हानि से सावधानी।", "Difficult; delays, toil, caution against loss."),
           ("Siddha", "सिद्धा", 7, "Venus", "सिद्धि, सुख, कला, संबंध।", "Accomplishment, comfort, arts, relationships."),
           ("Sankata", "संकटा", 8, "Rahu", "संकट, अनिश्चितता; धैर्य का काल।", "Crisis and uncertainty; a time for patience.")]
TOTAL = 36
YEAR = 365.25


def yogini(moon_sidereal: float, birth_utc: datetime, as_of: datetime | None = None) -> dict:
    nak = int(moon_sidereal // (360 / 27))              # 0..26
    frac = (moon_sidereal % (360 / 27)) / (360 / 27)
    start_idx = (nak + 1 + 3) % 8                      # (nakshatra number + 3) mod 8 with 1-based nakshatra number
    first_years = YOGINIS[start_idx][2]
    balance = first_years * (1 - frac)
    periods = []
    t = birth_utc - timedelta(days=(first_years - balance) * YEAR)
    idx = start_idx
    while (t - birth_utc).days < 100 * YEAR:
        name, hi, years, lord, th, te = YOGINIS[idx]
        end = t + timedelta(days=years * YEAR)
        subs, st = [], t
        for k in range(8):
            j = (idx + k) % 8
            sn, sh, sy, sl, _, _ = YOGINIS[j]
            se = st + timedelta(days=years * sy / TOTAL * YEAR)
            subs.append({"name": sn, "name_hi": sh, "lord": sl, "lord_hi": PLANETS_HI[sl], "start": st.date().isoformat(), "end": se.date().isoformat()})
            st = se
        periods.append({"name": name, "name_hi": hi, "years": years, "lord": lord, "lord_hi": PLANETS_HI[lord], "start": t.date().isoformat(), "end": end.date().isoformat(),
                        "text_hi": th, "text_en": te, "antardashas": subs})
        t = end
        idx = (idx + 1) % 8
    periods[0]["start"] = birth_utc.date().isoformat()         # the first period starts at birth (balance only)
    periods[0]["balance_years"] = round(balance, 2)
    running = None
    if as_of is not None:
        d = as_of.date().isoformat()
        md = next((x for x in periods if x["start"] <= d < x["end"]), None)
        if md:
            ad = next((x for x in md["antardashas"] if x["start"] <= d < x["end"]), None)
            running = {"mahadasha": {k: md[k] for k in ("name", "name_hi", "lord", "lord_hi", "start", "end", "text_hi", "text_en")},
                       "antardasha": ad}
    return {"system": "yogini", "cycle_years": TOTAL, "start_nakshatra_index": nak, "periods": periods, "running": running, "review_status": "draft",
            "note_hi": "योगिनी दशा (36 वर्ष चक्र, 8 योगिनियाँ) विंशोत्तरी के साथ पढ़ी जाती है; यहाँ नक्षत्र-आधारित आरंभ और समानुपाती शेष लिया गया है।",
            "note_en": "Yogini dasha (36-year cycle, eight yoginis) is read alongside Vimshottari; nakshatra-based start with proportional balance."}
