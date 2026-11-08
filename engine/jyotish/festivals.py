"""Festival and vrat calendar v1 for a Gregorian year, from the engine's own panchang.

Method: new moons of the year are found once (amanta months; the month is named from the Sun's sidereal sign at its
start, adhika when no sankranti falls inside). For every day the tithi prevailing at local sunrise (udaya tithi) is
taken; a festival falls on the first day of its month and paksha whose sunrise tithi matches. Three festivals use the
tithi at another moment instead, as the tradition does: Janmashtami at midnight, Diwali at sunset (pradosha),
Karva Chauth at moonrise (approximated by sunset + 1 hour, flagged). Makar Sankranti is the Sun's sidereal ingress
into Makara. Regional conventions differ by a day in some years; the notes say which rule was applied. Draft.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from .core import ayanamsa, nakshatra_of
from .ephemeris import AnalyticBackend, norm360
from .panchang import tithi_info
from .patri import MASA, MASA_HI, _amavasya_before
from .sun import sun_times
from .timeutil import delta_t, julian_day, year_fraction

_B = AnalyticBackend()
# (key, hi, en, masa index (amanta; 0 = Vaishakha ... 11 = Chaitra), tithi number 1-30, moment, note_hi, note_en)
FESTIVALS = [
    ("vasant_panchami", "वसंत पंचमी", "Vasant Panchami", 9, 5, "midday", "पूर्वाह्न/मध्याह्न-व्यापिनी पंचमी।", "Panchami prevailing in the forenoon/midday."),
    ("maha_shivaratri", "महाशिवरात्रि", "Maha Shivaratri", 9, 29, "midnight", "अमांत माघ कृष्ण चतुर्दशी (पूर्णिमांत फाल्गुन); परंपरा में निशीथ-काल की चतुर्दशी देखी जाती है।", "Amanta Magha Krishna 14 (Purnimanta Phalguna); tradition checks the tithi at midnight."),
    ("holika_dahan", "होलिका दहन", "Holika Dahan", 10, 15, "sunset", "फाल्गुन पूर्णिमा; दहन प्रदोष में भद्रा-रहित समय पर।", "Phalguna Purnima; the fire is lit in pradosha outside Bhadra."),
    ("holi", "होली (धुलंडी)", "Holi (Dhulandi)", 10, 15, "after:holika_dahan", "होलिका दहन के अगले दिन।", "The day after Holika Dahan."),
    ("chaitra_navratri", "चैत्र नवरात्रि आरंभ / गुड़ी पड़वा / उगादि", "Chaitra Navratri begins / Gudi Padwa / Ugadi", 11, 1, "sunrise", "विक्रम संवत का नववर्ष।", "New year of the Vikram samvat."),
    ("ram_navami", "राम नवमी", "Ram Navami", 11, 9, "sunrise", "", ""),
    ("hanuman_jayanti", "हनुमान जयंती", "Hanuman Jayanti", 11, 15, "sunrise", "चैत्र पूर्णिमा (उत्तर भारत)।", "Chaitra Purnima (north Indian convention)."),
    ("akshaya_tritiya", "अक्षय तृतीया", "Akshaya Tritiya", 0, 3, "sunrise", "", ""),
    ("buddha_purnima", "बुद्ध पूर्णिमा", "Buddha Purnima", 0, 15, "sunrise", "", ""),
    ("guru_purnima", "गुरु पूर्णिमा", "Guru Purnima", 2, 15, "sunrise", "", ""),
    ("nag_panchami", "नाग पंचमी", "Nag Panchami", 3, 5, "sunrise", "", ""),
    ("raksha_bandhan", "रक्षाबंधन", "Raksha Bandhan", 3, 15, "sunrise", "श्रावण पूर्णिमा; भद्रा-रहित समय में।", "Shravana Purnima; outside Bhadra."),
    ("janmashtami", "कृष्ण जन्माष्टमी", "Krishna Janmashtami", 3, 23, "midnight", "अमांत श्रावण कृष्ण अष्टमी (पूर्णिमांत भाद्रपद), मध्यरात्रि की तिथि; रोहिणी नक्षत्र हो तो वैष्णव परंपरा अगला दिन भी लेती है।", "Amanta Shravana Krishna 8 (Purnimanta Bhadrapada), tithi at midnight; the Vaishnava convention may take the next day when Rohini falls there."),
    ("hartalika_teej", "हरतालिका तीज", "Hartalika Teej", 4, 3, "sunrise", "", ""),
    ("ganesh_chaturthi", "गणेश चतुर्थी", "Ganesh Chaturthi", 4, 4, "midday", "मध्याह्न में चतुर्थी होनी चाहिए।", "Chaturthi should prevail at midday."),
    ("anant_chaturdashi", "अनंत चतुर्दशी (गणेश विसर्जन)", "Anant Chaturdashi (Ganesh visarjan)", 4, 14, "sunrise", "", ""),
    ("pitru_paksha", "पितृ पक्ष आरंभ", "Pitru Paksha begins", 4, 16, "sunrise", "अमांत भाद्रपद कृष्ण प्रतिपदा (पूर्णिमांत आश्विन)।", "Amanta Bhadrapada Krishna 1 (Purnimanta Ashwina)."),
    ("sarva_pitru_amavasya", "सर्वपितृ अमावस्या", "Sarva Pitru Amavasya", 4, 30, "sunrise", "", ""),
    ("sharad_navratri", "शारदीय नवरात्रि आरंभ", "Sharad Navratri begins", 5, 1, "sunrise", "", ""),
    ("durga_ashtami", "दुर्गा अष्टमी", "Durga Ashtami", 5, 8, "sunrise", "", ""),
    ("vijayadashami", "विजयादशमी (दशहरा)", "Vijayadashami (Dussehra)", 5, 10, "sunrise", "", ""),
    ("sharad_purnima", "शरद पूर्णिमा", "Sharad Purnima", 5, 15, "moonrise", "चंद्रोदय की पूर्णिमा (अनुमानित)।", "Purnima at moonrise (approximate)."),
    ("karva_chauth", "करवा चौथ", "Karva Chauth", 5, 19, "moonrise", "अमांत आश्विन कृष्ण चतुर्थी (पूर्णिमांत कार्तिक); चंद्रोदय की तिथि (यहाँ सूर्यास्त + 1 घंटा से अनुमानित)।", "Amanta Ashwina Krishna 4 (Purnimanta Kartika); tithi at moonrise (approximated here by sunset + 1 h)."),
    ("dhanteras", "धनतेरस", "Dhanteras", 5, 28, "sunset", "प्रदोष काल में त्रयोदशी।", "Trayodashi at pradosha."),
    ("narak_chaturdashi", "नरक चतुर्दशी (छोटी दिवाली)", "Narak Chaturdashi (Chhoti Diwali)", 5, 29, "sunrise", "", ""),
    ("diwali", "दीपावली (लक्ष्मी पूजन)", "Diwali (Lakshmi Puja)", 5, 30, "sunset", "अमांत आश्विन अमावस्या (पूर्णिमांत कार्तिक), प्रदोष/सूर्यास्त की तिथि।", "Amanta Ashwina Amavasya (Purnimanta Kartika), tithi at sunset (pradosha)."),
    ("govardhan", "गोवर्धन पूजा (अन्नकूट)", "Govardhan Puja (Annakut)", 6, 1, "sunrise", "", ""),
    ("bhai_dooj", "भाई दूज", "Bhai Dooj", 6, 2, "sunrise", "", ""),
    ("chhath", "छठ पूजा (संध्या अर्घ्य)", "Chhath Puja (evening arghya)", 6, 6, "sunrise", "", ""),
    ("dev_uthani", "देवउठनी एकादशी", "Dev Uthani Ekadashi", 6, 11, "sunrise", "", ""),
    ("kartika_purnima", "कार्तिक पूर्णिमा (देव दीपावली)", "Kartika Purnima (Dev Deepawali)", 6, 15, "sunrise", "", ""),
]
EKADASHI_NAMES = {  # (amanta masa index, paksha) -> name
    (11, "Shukla"): ("कामदा", "Kamada"), (11, "Krishna"): ("वरूथिनी", "Varuthini"), (0, "Shukla"): ("मोहिनी", "Mohini"), (0, "Krishna"): ("अपरा", "Apara"), (1, "Shukla"): ("निर्जला", "Nirjala"), (1, "Krishna"): ("योगिनी", "Yogini"),
    (2, "Shukla"): ("देवशयनी", "Devshayani"), (2, "Krishna"): ("कामिका", "Kamika"), (3, "Shukla"): ("पुत्रदा (श्रावण)", "Putrada (Shravana)"), (3, "Krishna"): ("अजा", "Aja"), (4, "Shukla"): ("परिवर्तिनी", "Parivartini"), (4, "Krishna"): ("इंदिरा", "Indira"),
    (5, "Shukla"): ("पापांकुशा", "Papankusha"), (5, "Krishna"): ("रमा", "Rama"), (6, "Shukla"): ("देवउठनी (प्रबोधिनी)", "Dev Uthani (Prabodhini)"), (6, "Krishna"): ("उत्पन्ना", "Utpanna"), (7, "Shukla"): ("मोक्षदा", "Mokshada"), (7, "Krishna"): ("सफला", "Saphala"),
    (8, "Shukla"): ("पुत्रदा (पौष)", "Putrada (Pausha)"), (8, "Krishna"): ("षट्तिला", "Shattila"), (9, "Shukla"): ("जया", "Jaya"), (9, "Krishna"): ("विजया", "Vijaya"), (10, "Shukla"): ("आमलकी", "Amalaki"), (10, "Krishna"): ("पापमोचनी", "Papmochani"),
}


def _jd(dt: datetime) -> float:
    u = dt.astimezone(timezone.utc)
    jd_ut = julian_day(u)
    return jd_ut + delta_t(year_fraction(u)) / 86400.0


def _tithi_at(jd_tt: float) -> dict:
    pos = _B.positions(jd_tt)
    ayan = ayanamsa(jd_tt)
    return tithi_info(norm360(pos["Sun"] - ayan), norm360(pos["Moon"] - ayan))


@lru_cache(maxsize=64)
def lunations(year: int) -> tuple:
    """New moons (JD TT) from mid-November of the previous year to end of January of the next, with amanta month data."""
    start = _jd(datetime(year - 1, 11, 15, tzinfo=timezone.utc))
    end = _jd(datetime(year + 1, 2, 5, tzinfo=timezone.utc))
    t = _amavasya_before(_B, start)
    out = []
    while t < end:
        nxt = _amavasya_before(_B, t + 31.0)
        s0 = int(norm360(_B.positions(t)["Sun"] - ayanamsa(t)) // 30)
        s1 = int(norm360(_B.positions(nxt)["Sun"] - ayanamsa(nxt)) // 30)
        out.append({"start": t, "end": nxt, "masa": s0, "adhika": s0 == s1})
        t = nxt
    return tuple(out)


def _month_of(jd_tt: float, luns: tuple) -> dict | None:
    return next((m for m in luns if m["start"] <= jd_tt < m["end"]), None)


def _makara_sankranti(year: int, tz: str) -> str:
    """Local date of the Sun's sidereal ingress into Makara (Lahiri) in January of `year`."""
    zone = ZoneInfo(tz)
    lo = datetime(year, 1, 10, tzinfo=timezone.utc); hi = datetime(year, 1, 18, tzinfo=timezone.utc)
    f = lambda d: norm360(_B.positions(_jd(d))["Sun"] - ayanamsa(_jd(d)))
    for _ in range(40):
        mid = lo + (hi - lo) / 2
        if f(mid) < 270.0 and f(mid) > 180.0:
            lo = mid
        else:
            hi = mid
    return lo.astimezone(zone).strftime("%Y-%m-%d")


def calendar(year: int, lat: float, lon: float, tz: str) -> dict:
    year = max(1950, min(2099, int(year)))
    zone = ZoneInfo(tz)
    luns = lunations(year)
    days = []
    d = date(year, 1, 1)
    while d.year == year:
        st = sun_times(d, lat, lon, tz)
        if st:
            rise, sset = st["sunrise"], st["sunset"]
            jr = _jd(rise)
            m = _month_of(jr, luns)
            t = _tithi_at(jr)
            days.append({"date": d, "rise": rise, "set": sset, "jd_rise": jr, "tithi": t, "masa": m["masa"] if m else None, "adhika": m["adhika"] if m else False,
                         "lunation": round(m["start"], 3) if m else None})
        d += timedelta(days=1)

    def tithi_at_moment(day, moment):
        if moment == "sunrise":
            return day["tithi"]
        if moment == "sunset":
            return _tithi_at(_jd(day["set"]))
        if moment == "moonrise":
            return _tithi_at(_jd(day["set"] + timedelta(hours=1)))
        if moment == "midday":
            return _tithi_at(_jd(day["rise"] + (day["set"] - day["rise"]) / 2))
        if moment == "midnight":
            local_midnight = datetime(day["date"].year, day["date"].month, day["date"].day, tzinfo=zone) + timedelta(days=1)
            return _tithi_at(_jd(local_midnight))
        return day["tithi"]

    events = []
    for key, hi, en, masa, tnum, moment, nhi, nen in FESTIVALS:
        if moment.startswith("after:"):
            base = next((e for e in events if e["key"] == moment[6:]), None)
            if base:
                events.append({**base, "key": key, "name_hi": hi, "name_en": en, "date": (date.fromisoformat(base["date"]) + timedelta(days=1)).isoformat(), "rule": "next_day", "note_hi": nhi, "note_en": nen})
            continue
        cands = [x for x in days if x["masa"] == masa and not x["adhika"]]
        hit = next((x for x in cands if tithi_at_moment(x, moment)["number"] == tnum), None)
        if hit is None:
            # kshaya tithi (never prevailing at the moment): take the day whose sunrise tithi is the next one, i.e. the day the tithi ended
            hit = next((x for x in cands if x["tithi"]["number"] == (tnum % 30) + 1), None)
            if hit is None:
                continue
            nhi, nen = (nhi + " " if nhi else "") + "क्षय तिथि: उस दिन लिया गया जिसमें तिथि समाप्त हुई।", (nen + " " if nen else "") + "Kshaya tithi: the day on which the tithi ended was taken."
        events.append({"key": key, "name_hi": hi, "name_en": en, "date": hit["date"].isoformat(), "kind": "festival",
                       "masa": MASA[masa], "masa_hi": MASA_HI[masa], "tithi": hit["tithi"]["name"], "tithi_hi": f'{hit["tithi"]["paksha_hi"]} {hit["tithi"]["name_hi"]}',
                       "rule": moment, "note_hi": nhi, "note_en": nen})
    sank = _makara_sankranti(year, tz)
    events.append({"key": "makar_sankranti", "name_hi": "मकर संक्रांति", "name_en": "Makar Sankranti", "date": sank, "kind": "festival", "masa": None, "masa_hi": None,
                   "tithi": None, "tithi_hi": None, "rule": "solar", "note_hi": "सूर्य का निरयन मकर प्रवेश (लाहिड़ी)।", "note_en": "The Sun's sidereal ingress into Makara (Lahiri)."})
    # vrat days: ekadashi (first sunrise day of the tithi in each paksha), purnima, amavasya; also pradosha (13) could be added later
    seen = set()
    for i, x in enumerate(days):
        n = x["tithi"]["number"]
        prev = days[i - 1]["tithi"]["number"] if i else None
        kshaya = None
        if prev is not None and x["masa"] is not None:
            for target in (11, 26, 15, 30):
                if prev < target <= n - 1 if target != 30 else (prev in (28, 29) and n <= 2):   # the tithi fell wholly between two sunrises
                    kshaya = target
        if kshaya and n not in (11, 26, 15, 30):
            n = kshaya
        if n in (11, 26, 15, 30) and x["masa"] is not None:
            k = (x["lunation"], n)
            if k in seen:
                continue
            seen.add(k)
            paksha = "Shukla" if n <= 15 else "Krishna"
            if n in (11, 26):
                name = EKADASHI_NAMES.get((x["masa"], paksha))
                hi = ("अधिक मास की " if x["adhika"] else "") + (f"{name[0]} एकादशी" if name and not x["adhika"] else "एकादशी व्रत")
                en = ("Adhika " if x["adhika"] else "") + (f"{name[1]} Ekadashi" if name and not x["adhika"] else "Ekadashi vrat")
                kind = "ekadashi"
            elif n == 15:
                hi, en, kind = f"{MASA_HI[x['masa']]} पूर्णिमा", f"{MASA[x['masa']]} Purnima", "purnima"
            else:
                hi, en, kind = f"{MASA_HI[x['masa']]} अमावस्या", f"{MASA[x['masa']]} Amavasya", "amavasya"
            events.append({"key": f"{kind}_{x['date'].isoformat()}", "name_hi": hi, "name_en": en, "date": x["date"].isoformat(), "kind": kind,
                           "masa": MASA[x["masa"]], "masa_hi": MASA_HI[x["masa"]], "tithi": x["tithi"]["name"], "tithi_hi": f'{x["tithi"]["paksha_hi"]} {x["tithi"]["name_hi"]}',
                           "rule": "sunrise" if not kshaya else "kshaya", "note_hi": "क्षय तिथि: अगले सूर्योदय वाले दिन।" if kshaya else "", "note_en": "Kshaya tithi: taken on the following sunrise day." if kshaya else ""})
    events.sort(key=lambda e: (e["date"], 0 if e["kind"] == "festival" else 1))
    adh = []
    for m in luns:
        if m["adhika"]:
            s = next((x["date"].isoformat() for x in days if x["jd_rise"] >= m["start"]), None)
            e = next((x["date"].isoformat() for x in days if x["jd_rise"] >= m["end"]), None)
            if s:
                adh.append({"masa": MASA[m["masa"]], "masa_hi": MASA_HI[m["masa"]], "start": s, "end": e})
    return {"year": year, "tz": tz, "lat": lat, "lon": lon, "events": events, "adhika_masa": adh, "review_status": "draft",
            "note_hi": "तिथियाँ इस ऐप के अपने पंचांग से (लाहिड़ी, अमांत मास, सूर्योदय की तिथि; जन्माष्टमी मध्यरात्रि, दीपावली/धनतेरस सूर्यास्त, करवा चौथ चंद्रोदय-अनुमान)। "
                       "क्षेत्रीय परंपराओं में एक दिन का अंतर संभव है; अंतिम निर्णय स्थानीय पंचांग से कीजिए।",
            "note_en": "Dates from this app's own panchang (Lahiri, amanta months, tithi at sunrise; Janmashtami at midnight, Diwali/Dhanteras at sunset, Karva Chauth by an approximate moonrise). "
                       "Regional conventions can differ by a day; confirm with a local almanac."}
