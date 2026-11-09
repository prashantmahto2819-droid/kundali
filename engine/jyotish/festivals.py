"""Festival and vrat calendar v1 for a Gregorian year, from the engine's own panchang.

Method: new moons of the year are found once (amanta months; the month is named from the Sun's sidereal sign at its
start, adhika when no sankranti falls inside). For every day the tithi prevailing at local sunrise (udaya tithi) is
taken; a festival falls on the first day of its month and paksha whose sunrise tithi matches. Three festivals use the
tithi at another moment instead, as the tradition does: Janmashtami at midnight, Diwali at sunset (pradosha),
Sharad Purnima at the computed moonrise. Makar Sankranti is the Sun's sidereal ingress
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
    ("sharad_purnima", "शरद पूर्णिमा", "Sharad Purnima", 5, 15, "moonrise", "चंद्रोदय की पूर्णिमा।", "Purnima at moonrise."),
    ("karva_chauth", "करवा चौथ", "Karva Chauth", 5, 19, "sunrise", "अमांत आश्विन कृष्ण चतुर्थी (पूर्णिमांत कार्तिक), उदया तिथि; व्रत चंद्रोदय पर खुलता है (चंद्रोदय समय पंचांग कार्ड में)।", "Amanta Ashwina Krishna 4 (Purnimanta Kartika), tithi at sunrise; the fast ends at moonrise (see the panchang card for the time)."),
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


def _sid(jd_tt: float) -> tuple[float, float]:
    pos = _B.positions(jd_tt)
    a = ayanamsa(jd_tt)
    return norm360(pos["Sun"] - a), norm360(pos["Moon"] - a)


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


def _sankranti_date(year: int, tz: str, sign: int, month_guess: int) -> str:
    """Local date of the Sun's sidereal ingress into `sign` (0 = Mesha) near the given Gregorian month."""
    zone = ZoneInfo(tz)
    lo = datetime(year, month_guess, 1, tzinfo=timezone.utc) - timedelta(days=5); hi = lo + timedelta(days=40)
    f = lambda d: norm360(_B.positions(_jd(d))["Sun"] - ayanamsa(_jd(d)))
    target = sign * 30.0
    for _ in range(45):
        mid = lo + (hi - lo) / 2
        if (f(mid) - target) % 360.0 > 180.0:
            lo = mid
        else:
            hi = mid
    return lo.astimezone(zone).strftime("%Y-%m-%d")


def _easter(year: int) -> date:
    a = year % 19; b, c = divmod(year, 100); d, e = divmod(b, 4); f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i, k = divmod(c, 4); l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; month = (h + l - 7 * m + 114) // 31; day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _hijri_to_gregorian(hy: int, hm: int, hd: int) -> date:
    """Tabular (arithmetic) Islamic calendar, civil epoch 16 July 622; actual dates depend on moon sighting (±1 day)."""
    jd = (hd + (29.5 * (hm - 1)).__ceil__() + (hy - 1) * 354 + (3 + 11 * hy) // 30 + 1948439.5) - 1
    jd = int(jd + 0.5)
    # JD → Gregorian (Fliegel–Van Flandern)
    l = jd + 68569; n = 4 * l // 146097; l = l - (146097 * n + 3) // 4; i = 4000 * (l + 1) // 1461001; l = l - 1461 * i // 4 + 31
    j = 80 * l // 2447; dd = l - 2447 * j // 80; l = j // 11; mm = j + 2 - 12 * l; yy = 100 * (n - 49) + i + l
    return date(yy, mm, dd)


def _month_start_by_sighting(tabular_first: date, tz: str, lat: float = 23.0, lon: float = 78.0) -> date:
    """Islamic month start for India: the day after the first evening (searched around the tabular date) on which the Moon
    sets more than 45 minutes after sunset following the conjunction. Falls back to the tabular date."""
    from .moon import moon_times
    from .sun import sun_times
    # conjunction just before the tabular first day
    conj = _amavasya_before(_B, _jd(datetime(tabular_first.year, tabular_first.month, tabular_first.day, 12, tzinfo=timezone.utc)) + 1.5)
    conj_dt = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=conj - 2451544.5)
    for k in range(0, 4):
        ev = (conj_dt.astimezone(ZoneInfo(tz)) + timedelta(days=k)).date()
        st = sun_times(ev, lat, lon, tz)
        mt = moon_times(ev, lat, lon, tz)
        if not st or not mt.get("moonset"):
            continue
        age_h = ((datetime(ev.year, ev.month, ev.day, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc) - conj_dt).total_seconds() / 3600) + 18
        lag = (mt["moonset"] - st["sunset"]).total_seconds() / 60
        if lag >= 45 and age_h >= 17:
            return ev + timedelta(days=1)
    return tabular_first


def other_calendars(year: int, tz: str) -> list[dict]:
    """National days, Christian feasts (computus) and the main Islamic observances (tabular calendar, approximate)."""
    out = []
    def add(key, hi, en, d, kind, note_hi="", note_en=""):
        out.append({"key": key, "name_hi": hi, "name_en": en, "date": d.isoformat() if isinstance(d, date) else d, "kind": kind, "masa": None, "masa_hi": None,
                    "tithi": None, "tithi_hi": None, "rule": "civil", "note_hi": note_hi, "note_en": note_en})
    add("republic_day", "गणतंत्र दिवस", "Republic Day", date(year, 1, 26), "national")
    add("independence_day", "स्वतंत्रता दिवस", "Independence Day", date(year, 8, 15), "national")
    add("gandhi_jayanti", "गांधी जयंती", "Gandhi Jayanti", date(year, 10, 2), "national")
    add("ambedkar_jayanti", "अम्बेडकर जयंती", "Ambedkar Jayanti", date(year, 4, 14), "national")
    e = _easter(year)
    add("good_friday", "गुड फ़्राइडे", "Good Friday", e - timedelta(days=2), "christian")
    add("easter", "ईस्टर", "Easter Sunday", e, "christian")
    add("christmas", "क्रिसमस", "Christmas", date(year, 12, 25), "christian")
    hn, hen = ("भारत में चाँद दिखने के अनुमान (संयुति के बाद पहली शाम जब चाँद सूर्यास्त के बाद ~45 मिनट से अधिक रहे); वास्तविक घोषणा से एक दिन का अंतर संभव।",
               "Estimated for moon sighting in India (first evening after conjunction with the Moon up more than ~45 min after sunset); the actual announcement may differ by a day.")
    for hy in range(year - 580, year - 577):
        for key, hi, en, hm, hd in (("eid_ul_fitr", "ईद-उल-फ़ित्र", "Eid ul-Fitr", 10, 1), ("eid_ul_adha", "ईद-उल-अज़हा (बक़रीद)", "Eid ul-Adha (Bakrid)", 12, 10),
                                   ("muharram", "मुहर्रम (आशूरा)", "Muharram (Ashura)", 1, 10), ("milad", "ईद-ए-मिलाद", "Eid-e-Milad", 3, 12), ("ramadan_start", "रमज़ान आरंभ", "Ramadan begins", 9, 1)):
            tab = _hijri_to_gregorian(hy, hm, 1)
            start = _month_start_by_sighting(tab, tz)
            d = start + timedelta(days=hd - 1)
            if d.year == year:
                add(f"{key}_{hy}", hi, en, d, "islamic", hn, hen)
    return out


def regional_festivals(year: int, lat: float, lon: float, tz: str, days: list, luns: tuple) -> list[dict]:
    """Regional festivals fixed by solar ingress or by month + tithi in a region's own convention."""
    out = []
    def add(key, hi, en, d, note_hi="", note_en="", region=""):
        out.append({"key": key, "name_hi": hi, "name_en": en, "date": d, "kind": "regional", "masa": None, "masa_hi": None, "tithi": None, "tithi_hi": None,
                    "rule": "regional", "note_hi": note_hi, "note_en": note_en, "region": region})
    mk = _sankranti_date(year, tz, 9, 1); mesha = _sankranti_date(year, tz, 0, 4)
    add("pongal", "पोंगल (थाई 1)", "Pongal (Thai 1)", mk, region="Tamil Nadu")
    add("lohri", "लोहड़ी", "Lohri", (date.fromisoformat(mk) - timedelta(days=1)).isoformat(), region="Punjab")
    add("tamil_new_year", "तमिल नववर्ष (चित्तिरै 1) / विशु / बिहू / पोइला बोइशाख", "Tamil New Year (Chithirai 1) / Vishu / Bihu / Poila Boishakh", mesha,
        "मेष संक्रांति; बंगाली नववर्ष प्रायः अगले दिन।", "Mesha sankranti; the Bengali new year usually falls the next day.", "Tamil Nadu, Kerala, Assam, Bengal")
    # tithi-based regional days (amanta masa index, tithi number)
    T = [("gangaur", "गणगौर", "Gangaur", 11, 3, "Rajasthan"), ("mahavir_jayanti", "महावीर जयंती", "Mahavir Jayanti", 11, 13, "Jain"),
         ("rath_yatra", "रथ यात्रा", "Rath Yatra", 2, 2, "Odisha"), ("ganga_dussehra", "गंगा दशहरा", "Ganga Dussehra", 1, 10, "North India"),
         ("vat_savitri", "वट सावित्री व्रत", "Vat Savitri vrat", 1, 30, "North India (amanta Jyeshtha Amavasya)"), ("hariyali_teej", "हरियाली तीज", "Hariyali Teej", 3, 3, "North India"),
         ("kajari_teej", "कजरी तीज", "Kajari Teej", 3, 18, "Bihar, UP, MP"), ("durga_puja_shashthi", "दुर्गा पूजा आरंभ (षष्ठी)", "Durga Puja begins (Shashthi)", 5, 6, "Bengal"),
         ("maha_navami", "महानवमी", "Maha Navami", 5, 9, ""),
         ("lakshmi_puja_kojagari", "कोजागरी लक्ष्मी पूजा", "Kojagari Lakshmi Puja", 5, 15, "Bengal"), ("bhishma_ashtami", "भीष्म अष्टमी", "Bhishma Ashtami", 9, 8, ""),
         ("saraswati_puja", "सरस्वती पूजा", "Saraswati Puja", 9, 5, "Bengal (Vasant Panchami)"), ("guru_nanak_jayanti", "गुरु नानक जयंती", "Guru Nanak Jayanti", 6, 15, "Sikh"),
         ("nuakhai", "नुआखाई", "Nuakhai", 4, 5, "Odisha"), ("kumar_purnima", "कुमार पूर्णिमा", "Kumar Purnima", 5, 15, "Odisha"), ("prathamastami", "प्रथमाष्टमी", "Prathamastami", 7, 23, "Odisha"),
         ("pola", "पोला / पिठोरी अमावस्या", "Pola / Pithori Amavasya", 3, 30, "Maharashtra, Chhattisgarh"), ("hola_mohalla", "होला मोहल्ला", "Hola Mohalla", 10, 16, "Punjab (day after Holi)"),
         ("jitiya", "जितिया (जीवित्पुत्रिका)", "Jitiya (Jivitputrika)", 4, 23, "Bihar, Jharkhand, UP"), ("bathukamma", "बतुकम्मा आरंभ", "Bathukamma begins", 4, 30, "Telangana"),
         ("hartalika_gauri", "ज्येष्ठा गौरी आवाहन", "Jyeshtha Gauri Avahan", 4, 7, "Maharashtra"), ("ugadi_telugu", "उगादि / युगादि", "Ugadi / Yugadi", 11, 1, "Andhra, Telangana, Karnataka"),
         ("vishwakarma_puja_bengal", "विश्वकर्मा पूजा (कन्या संक्रांति)", "Vishwakarma Puja (Kanya sankranti)", None, None, "Bengal, Bihar, Odisha"),
         ("herath", "हेरथ (कश्मीरी शिवरात्रि, त्रयोदशी)", "Herath (Kashmiri Shivaratri, Trayodashi)", 9, 28, "Kashmir")]
    for key, hi, en, masa, tnum, region in list(T):
        if masa is None:
            T.remove((key, hi, en, masa, tnum, region))
    add("vishwakarma_puja_bengal", "विश्वकर्मा पूजा (कन्या संक्रांति)", "Vishwakarma Puja (Kanya sankranti)", _sankranti_date(year, tz, 5, 9), region="Bengal, Bihar, Odisha, Jharkhand")
    add("baisakhi", "बैसाखी", "Baisakhi", mesha, region="Punjab")
    add("raja_parba", "रज पर्व (पहिली रज)", "Raja Parba (Pahili Raja)", (date.fromisoformat(_sankranti_date(year, tz, 2, 6)) - timedelta(days=1)).isoformat(), region="Odisha")
    add("karnataka_rajyotsava", "कर्नाटक राज्योत्सव", "Karnataka Rajyotsava", date(year, 11, 1).isoformat(), region="Karnataka")
    add("uttarayan", "उत्तरायण (पतंग)", "Uttarayan (kites)", mk, region="Gujarat")
    # Varalakshmi vratam: the Friday before Shravana Purnima (amanta Shravana Shukla paksha)
    sp = next((x for x in days if x["masa"] == 3 and not x["adhika"] and x["tithi"]["number"] == 15), None)
    if sp:
        fri = sp["date"]
        while fri.weekday() != 4:
            fri -= timedelta(days=1)
        add("varalakshmi", "वरलक्ष्मी व्रत", "Varalakshmi vratam", fri.isoformat(), region="Andhra, Telangana, Karnataka, Tamil Nadu")
    for key, hi, en, masa, tnum, region in T:
        cands = [x for x in days if x["masa"] == masa and not x["adhika"]]
        hit = next((x for x in cands if x["tithi"]["number"] == tnum), None) or next((x for x in cands if x["tithi"]["number"] == (tnum % 30) + 1), None)
        if hit:
            add(key, hi, en, hit["date"].isoformat(), region=region)
    # Onam: Thiruvonam (Shravana) nakshatra day in Chingam (Sun in Simha); Karthigai Deepam: Krittika day in Karthigai (Sun in Vrischika) near the full moon
    for key, hi, en, sun_sign, nak_idx, region in (("onam", "ओणम (तिरुवोणम)", "Onam (Thiruvonam)", 4, 21, "Kerala"), ("karthigai_deepam", "कार्तिगै दीपम", "Karthigai Deepam", 7, 2, "Tamil Nadu")):
        best = None
        for x in days:
            sun, moon = _sid(x["jd_rise"]) if "jd_rise" in x else (None, None)
            if sun is None:
                continue
            if int(sun // 30) == sun_sign and nakshatra_of(moon)["index"] == nak_idx:
                t = x["tithi"]["number"]
                if key == "karthigai_deepam" and not (12 <= t <= 17):
                    continue
                best = x; break
        if best:
            add(key, hi, en, best["date"].isoformat(), region=region)
    return out


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


def apply_overrides(year: int, events: list[dict]) -> list[dict]:
    """Yearly hand corrections from data/overrides/festivals_<year>.json — government holidays, a regional date that the
    local panchang fixes differently, or an event to drop:
      {"add": [{"key","name_hi","name_en","date":"YYYY-MM-DD","kind":"national|festival|regional","region"?}],
       "move": [{"key": "...", "date": "YYYY-MM-DD", "note_hi"?, "note_en"?}],
       "remove": ["key", ...]}
    The computed calendar stays the default; the file only patches it, so each year's list is reviewed once by a person."""
    import json
    from pathlib import Path
    f = Path(__file__).resolve().parents[2] / "data" / "overrides" / f"festivals_{year}.json"
    if not f.exists():
        return events
    try:
        ov = json.loads(f.read_text("utf-8"))
    except ValueError:
        return events
    remove = set(ov.get("remove", []))
    moves = {m["key"]: m for m in ov.get("move", []) if m.get("key") and m.get("date")}
    out = []
    for ev in events:
        if ev["key"] in remove:
            continue
        if ev["key"] in moves:
            m = moves[ev["key"]]
            ev = {**ev, "date": m["date"], "rule": "override", "note_hi": m.get("note_hi", "स्थानीय पंचांग के अनुसार तिथि समायोजित।"), "note_en": m.get("note_en", "Date adjusted to the local panchang.")}
        out.append(ev)
    for a in ov.get("add", []):
        if a.get("key") and a.get("date") and a.get("name_hi"):
            out.append({"key": a["key"], "name_hi": a["name_hi"], "name_en": a.get("name_en", a["name_hi"]), "date": a["date"], "kind": a.get("kind", "national"),
                        "rule": "override", "note_hi": a.get("note_hi", ""), "note_en": a.get("note_en", ""), **({"region": a["region"]} if a.get("region") else {})})
    return out


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
            from .moon import moon_times
            mr = moon_times(day["date"], lat, lon, tz).get("moonrise")
            # the evening moonrise: if the day's moonrise is before sunset (waxing gibbous days) it is the right one; otherwise fall back to sunset + 50 min
            return _tithi_at(_jd(mr if mr and mr > day["set"] - timedelta(hours=6) else day["set"] + timedelta(minutes=50)))
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
    VRAT = {13: ("प्रदोष व्रत", "Pradosh vrat", "pradosh"), 28: ("प्रदोष व्रत", "Pradosh vrat", "pradosh"), 4: ("विनायक चतुर्थी", "Vinayaka Chaturthi", "chaturthi"),
            19: ("संकष्टी चतुर्थी", "Sankashti Chaturthi", "chaturthi"), 29: ("मासिक शिवरात्रि", "Masik Shivaratri", "shivaratri")}
    seen_v = set()
    for x in days:
        n = x["tithi"]["number"]
        if n in VRAT and x["masa"] is not None:
            k = (x["lunation"], n)
            if k in seen_v:
                continue
            seen_v.add(k)
            hi, en, kind = VRAT[n]
            events.append({"key": f"{kind}_{x['date'].isoformat()}", "name_hi": hi, "name_en": en, "date": x["date"].isoformat(), "kind": kind,
                           "masa": MASA[x["masa"]], "masa_hi": MASA_HI[x["masa"]], "tithi": x["tithi"]["name"], "tithi_hi": f'{x["tithi"]["paksha_hi"]} {x["tithi"]["name_hi"]}',
                           "rule": "sunrise", "note_hi": "", "note_en": ""})
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
    events += regional_festivals(year, lat, lon, tz, days, luns)
    diwali = next((e for e in events if e["key"] == "diwali"), None)
    if diwali:
        events.append({**diwali, "key": "kali_puja", "name_hi": "काली पूजा", "name_en": "Kali Puja", "kind": "regional", "rule": "regional", "note_hi": "", "note_en": "", "region": "Bengal"})
    events += other_calendars(year, tz)
    try:
        from .panchang_extra import eclipses
        for ec in eclipses(year, tz):
            events.append({"key": f"{ec['kind']}_eclipse_{ec['date']}", "name_hi": ec["kind_hi"] + (" (संभावित)" if ec["certainty"] != "sure" else ""),
                           "name_en": ("Solar" if ec["kind"] == "solar" else "Lunar") + " eclipse" + (" (possible)" if ec["certainty"] != "sure" else ""),
                           "date": ec["date"], "kind": "grahan", "rule": "syzygy", "maximum_local": ec["maximum_local"], "note_hi": ec["note_hi"], "note_en": ec["note_en"]})
    except Exception:
        pass
    events = apply_overrides(year, events)
    order = {"grahan": 0, "festival": 0, "regional": 1, "national": 2, "ekadashi": 3, "purnima": 4, "amavasya": 4, "pradosh": 5, "chaturthi": 5, "shivaratri": 5, "christian": 6, "islamic": 6}
    events.sort(key=lambda e: (e["date"], order.get(e["kind"], 9)))
    adh = []
    for m in luns:
        if m["adhika"]:
            s = next((x["date"].isoformat() for x in days if x["jd_rise"] >= m["start"]), None)
            e = next((x["date"].isoformat() for x in days if x["jd_rise"] >= m["end"]), None)
            if s:
                adh.append({"masa": MASA[m["masa"]], "masa_hi": MASA_HI[m["masa"]], "start": s, "end": e})
    return {"year": year, "tz": tz, "lat": lat, "lon": lon, "events": events, "adhika_masa": adh, "review_status": "draft",
            "note_hi": "तिथियाँ इस ऐप के अपने पंचांग से (लाहिड़ी, अमांत मास, सूर्योदय की तिथि; जन्माष्टमी मध्यरात्रि, दीपावली/धनतेरस सूर्यास्त, शरद पूर्णिमा चंद्रोदय)। "
                       "क्षेत्रीय परंपराओं में एक दिन का अंतर संभव है; अंतिम निर्णय स्थानीय पंचांग से कीजिए।",
            "note_en": "Dates from this app's own panchang (Lahiri, amanta months, tithi at sunrise; Janmashtami at midnight, Diwali/Dhanteras at sunset, Sharad Purnima at moonrise). "
                       "Regional conventions can differ by a day; confirm with a local almanac."}
