"""A few classical yogas/doshas, each with its 'why' so the UI can teach it.

All entries are DRAFT until reviewed by a scholar (see data/rules/README.md);
they are flagged ``review_status: draft``.
"""
from __future__ import annotations

from .constants import PLANETS_HI, SIGN_LORDS, SIGNS_HI

KENDRA = {1, 4, 7, 10}
DIG_HI = {"own": "स्वराशि", "exalted": "उच्च", "debilitated": "नीच", None: "सामान्य"}


def _p(chart: dict) -> dict:
    return {p["name"]: p for p in chart["planets"]}


def _house_from(a: int, b: int) -> int:
    """House number of b counted from a (1..12)."""
    return (b - a) % 12 + 1


def detect_yogas(chart: dict) -> list[dict]:
    p = _p(chart)
    out = []

    def add(yid, name, name_hi, present, why, why_hi=""):
        out.append({"id": yid, "name": name, "name_hi": name_hi, "present": bool(present),
                    "why": why, "why_hi": why_hi, "review_status": "draft"})

    # Gajakesari: Jupiter in a kendra (1,4,7,10) from the Moon
    gk = _house_from(p["Moon"]["house"], p["Jupiter"]["house"]) in KENDRA
    add("gajakesari", "Gajakesari Yoga", "गजकेसरी योग", gk,
        "Jupiter sits in a kendra (1/4/7/10th house) counted from the Moon. "
        f"Here Jupiter is in house {_house_from(p['Moon']['house'], p['Jupiter']['house'])} from the Moon.",
        f"गुरु चंद्र से केंद्र (1/4/7/10) में हो तो यह योग माना जाता है। यहाँ गुरु चंद्र से {_house_from(p['Moon']['house'], p['Jupiter']['house'])}वें भाव में है।")

    # Budhaditya: Sun and Mercury in the same sign
    ba = p["Sun"]["sign"] == p["Mercury"]["sign"]
    add("budhaditya", "Budhaditya Yoga", "बुधादित्य योग", ba,
        "Sun and Mercury occupy the same sign (Mercury is never far from the Sun, so this is common).",
        "सूर्य और बुध एक ही राशि में हों तो यह योग माना जाता है (बुध सूर्य से दूर नहीं जाता, इसलिए यह आम है)।")

    # Chandra-Mangala
    cm = p["Moon"]["sign"] == p["Mars"]["sign"]
    add("chandra_mangala", "Chandra-Mangala Yoga", "चंद्र-मंगल योग", cm,
        "Moon and Mars occupy the same sign.",
        "चंद्र और मंगल एक ही राशि में हों तो यह योग माना जाता है।")

    # Mangal dosha (Kuja dosha) from lagna: Mars in 1,4,7,8,12
    md = p["Mars"]["house"] in {1, 4, 7, 8, 12}
    add("mangal_dosha", "Mangal Dosha (from Lagna)", "मंगल दोष (लग्न से)", md,
        f"Mars is in house {p['Mars']['house']} from the Lagna. Schools differ: some include the 2nd house, "
        "and many also check from the Moon and Venus; cancellations (parihara) exist and must be weighed.",
        f"मंगल लग्न से {p['Mars']['house']}वें भाव में है। मंगल 1, 4, 7, 8, 12 में हो तो दोष गिना जाता है। परंपराओं में मतभेद हैं "
        "(कुछ दूसरा भाव भी गिनते हैं, कई चंद्र और शुक्र से भी देखते हैं), और परिहार (काट) भी होते हैं, इसलिए इसे अकेले फ़ैसला न मानें।")

    # Pancha Mahapurusha
    mahapurusha = {"Mars": ("ruchaka", "Ruchaka", "रुचक"), "Mercury": ("bhadra", "Bhadra", "भद्र"),
                   "Jupiter": ("hamsa", "Hamsa", "हंस"), "Venus": ("malavya", "Malavya", "मालव्य"),
                   "Saturn": ("shasha", "Shasha", "शश")}
    for planet, (yid, en, hi) in mahapurusha.items():
        pl = p[planet]
        present = pl["dignity"] in ("own", "exalted") and pl["house"] in KENDRA
        add(yid, f"{en} Yoga (Pancha Mahapurusha)", f"{hi} योग (पंच महापुरुष)", present,
            f"{planet} must be in its own or exalted sign and in a kendra from the Lagna. "
            f"Here: dignity={pl['dignity']}, house={pl['house']}.",
            f"{PLANETS_HI[planet]} अपनी या उच्च राशि में और लग्न से केंद्र भाव में हो तो यह योग बनता है। यहाँ स्थिति: "
            f"{ {'own': 'स्वराशि', 'exalted': 'उच्च', 'debilitated': 'नीच', None: 'सामान्य'}[pl['dignity']] }, भाव {pl['house']}।")

    # Kala Sarpa: all seven planets on one side of the Rahu-Ketu axis
    rahu = p["Rahu"]["longitude"]
    seven = [p[n]["longitude"] for n in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")]
    arcs = [((x - rahu) % 360) for x in seven]
    ks = all(a < 180 for a in arcs) or all(a > 180 for a in arcs)
    add("kala_sarpa", "Kala Sarpa Dosha", "कालसर्प दोष", ks,
        "All seven planets (Sun to Saturn) lie between Rahu and Ketu on one side of the axis. "
        "Opinions on its effect vary widely between traditions.",
        "सूर्य से शनि तक सातों ग्रह राहु-केतु अक्ष के एक ही ओर हों तो यह दोष कहा जाता है। इसके प्रभाव पर परंपराओं में बहुत मतभेद है।")

    # ---- second batch -------------------------------------------------------------------------------
    lagna = chart["lagna"]["sign"]
    H = PLANETS_HI
    TRUE = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    moon_h = p["Moon"]["house"]
    def in_house_from_moon(h):                                      # planets (Mars..Saturn) in house h from the Moon
        return [n for n in TRUE if _house_from(moon_h, p[n]["house"]) == h]
    def names(lst):
        return ", ".join(lst) or "none"
    def names_hi(lst):
        return ", ".join(H[n] for n in lst) or "कोई नहीं"

    # Moon yogas: Sunapha (2nd from Moon), Anapha (12th), Durudhara (both), Kemadruma (neither; Sun excluded)
    s2, s12 = in_house_from_moon(2), in_house_from_moon(12)
    add("sunapha", "Sunapha Yoga", "सुनफा योग", bool(s2) and not s12, f"A planet other than the Sun in the 2nd from the Moon: {names(s2)}.", f"चंद्र से दूसरे भाव में सूर्य के अलावा कोई ग्रह: {names_hi(s2)}।")
    add("anapha", "Anapha Yoga", "अनफा योग", bool(s12) and not s2, f"A planet other than the Sun in the 12th from the Moon: {names(s12)}.", f"चंद्र से बारहवें भाव में सूर्य के अलावा कोई ग्रह: {names_hi(s12)}।")
    add("durudhara", "Durudhara Yoga", "दुरुधरा योग", bool(s2) and bool(s12), f"Planets on both sides of the Moon: 2nd {names(s2)}, 12th {names(s12)}.", f"चंद्र के दोनों ओर ग्रह: दूसरे में {names_hi(s2)}, बारहवें में {names_hi(s12)}।")
    kendra_from_moon = [n for n in TRUE if _house_from(moon_h, p[n]["house"]) in KENDRA]
    add("kemadruma", "Kemadruma Yoga", "केमद्रुम योग", not s2 and not s12 and not kendra_from_moon,
        "No planet (other than the Sun) in the 2nd or 12th from the Moon, and none in a kendra from the Moon (a common cancellation).",
        "चंद्र से दूसरे और बारहवें में (सूर्य के अलावा) कोई ग्रह नहीं, और चंद्र से केंद्र में भी कोई ग्रह नहीं (जो प्रचलित परिहार है)।")
    # Sun yogas: Vesi (2nd from Sun), Vasi (12th), Ubhayachari (both); Moon excluded
    sun_h = p["Sun"]["house"]
    v2 = [n for n in TRUE if _house_from(sun_h, p[n]["house"]) == 2]
    v12 = [n for n in TRUE if _house_from(sun_h, p[n]["house"]) == 12]
    add("vesi", "Vesi Yoga", "वेशि योग", bool(v2) and not v12, f"A planet other than the Moon in the 2nd from the Sun: {names(v2)}.", f"सूर्य से दूसरे भाव में चंद्र के अलावा ग्रह: {names_hi(v2)}।")
    add("vasi", "Vasi Yoga", "वासि योग", bool(v12) and not v2, f"A planet other than the Moon in the 12th from the Sun: {names(v12)}.", f"सूर्य से बारहवें भाव में चंद्र के अलावा ग्रह: {names_hi(v12)}।")
    add("ubhayachari", "Ubhayachari Yoga", "उभयचरी योग", bool(v2) and bool(v12), f"Planets on both sides of the Sun: {names(v2)} / {names(v12)}.", f"सूर्य के दोनों ओर ग्रह: {names_hi(v2)} / {names_hi(v12)}।")
    # Adhi yoga: benefics (Mercury, Jupiter, Venus) in 6th, 7th, 8th from the Moon
    ben = [n for n in ("Mercury", "Jupiter", "Venus") if _house_from(moon_h, p[n]["house"]) in (6, 7, 8)]
    add("adhi", "Adhi Yoga", "अधि योग", len(ben) >= 2, f"Benefics in the 6th/7th/8th from the Moon: {names(ben)} (two or more counted here).", f"चंद्र से 6/7/8 में शुभ ग्रह: {names_hi(ben)} (यहाँ दो या अधिक गिने गए)।")
    # Amala yoga: a natural benefic alone in the 10th from Lagna or Moon
    am_l = [n for n in ("Mercury", "Jupiter", "Venus") if p[n]["house"] == 10]
    am_m = [n for n in ("Mercury", "Jupiter", "Venus") if _house_from(moon_h, p[n]["house"]) == 10]
    add("amala", "Amala Yoga", "अमला योग", bool(am_l or am_m), f"A natural benefic in the 10th from the Lagna ({names(am_l)}) or from the Moon ({names(am_m)}).", f"लग्न से दसवें में शुभ ग्रह ({names_hi(am_l)}) या चंद्र से दसवें में ({names_hi(am_m)})।")
    # Viparita Raja yogas: lord of 6/8/12 placed in 6/8/12 (other than its own)
    dus = {6, 8, 12}
    lord_of = lambda h: SIGN_LORDS[(lagna + h - 1) % 12]
    vip = []
    for h, (yid, en, hi) in {6: ("harsha", "Harsha", "हर्ष"), 8: ("sarala", "Sarala", "सरल"), 12: ("vimala", "Vimala", "विमल")}.items():
        L = lord_of(h); ph = p[L]["house"]
        ok = ph in dus
        add(yid, f"{en} Yoga (Viparita Raja)", f"{hi} योग (विपरीत राजयोग)", ok,
            f"Lord of the {h}th ({L}) is in house {ph}; counted when it falls in 6, 8 or 12.",
            f"{h}वें भाव का स्वामी ({H[L]}) {ph}वें भाव में है; 6, 8 या 12 में हो तो यह योग गिना जाता है।")
    # Parivartana (exchange of signs) between any two of the seven
    seven = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    pairs = []
    for i, a in enumerate(seven):
        for b in seven[i + 1:]:
            if SIGN_LORDS[p[a]["sign"]] == b and SIGN_LORDS[p[b]["sign"]] == a:
                pairs.append((a, b))
    add("parivartana", "Parivartana Yoga (exchange)", "परिवर्तन योग", bool(pairs),
        "Two planets occupy each other's signs: " + (", ".join(f"{a}–{b}" for a, b in pairs) or "none") + ".",
        "दो ग्रह एक-दूसरे की राशि में: " + (", ".join(f"{H[a]}–{H[b]}" for a, b in pairs) or "कोई नहीं") + "।")
    # Dhana yoga (simple): lords of 2 and 11 together, or 2/11 lord with lord of 5/9 (conjunct or exchange)
    L2, L11, L5, L9, L1, L4, L7, L10 = (lord_of(h) for h in (2, 11, 5, 9, 1, 4, 7, 10))
    conj = lambda a, b: a != b and p[a]["sign"] == p[b]["sign"]
    dh_pairs = [(a, b) for a, b in ((L2, L11), (L2, L5), (L2, L9), (L11, L5), (L11, L9)) if conj(a, b) or (a, b) in pairs or (b, a) in pairs]
    add("dhana", "Dhana Yoga (lords of 2/11 with 5/9)", "धन योग (2/11 व 5/9 के स्वामी)", bool(dh_pairs),
        "Lords of the wealth houses (2, 11) joined with each other or with trikona lords (5, 9): " + (", ".join(f"{a}–{b}" for a, b in dh_pairs) or "none") + ".",
        "धन भावों (2, 11) के स्वामी आपस में या त्रिकोण (5, 9) के स्वामी के साथ: " + (", ".join(f"{H[a]}–{H[b]}" for a, b in dh_pairs) or "कोई नहीं") + "।")
    # Raja yoga (simple): a kendra lord conjunct or exchanging with a trikona lord
    kendra_lords, trikona_lords = {L1, L4, L7, L10}, {L5, L9, L1}
    rj = sorted({tuple(sorted((a, b))) for a in kendra_lords for b in trikona_lords if a != b and (conj(a, b) or (a, b) in pairs or (b, a) in pairs)})
    add("raja_kendra_trikona", "Raja Yoga (kendra–trikona lords)", "राजयोग (केंद्र-त्रिकोण स्वामी)", bool(rj),
        "A kendra lord (1/4/7/10) joined with a trikona lord (5/9) by conjunction or exchange: " + (", ".join(f"{a}–{b}" for a, b in rj) or "none") + ".",
        "केंद्र (1/4/7/10) का स्वामी त्रिकोण (5/9) के स्वामी से युति या परिवर्तन में: " + (", ".join(f"{H[a]}–{H[b]}" for a, b in rj) or "कोई नहीं") + "।")
    # Lakshmi yoga: lord of the 9th in own/exalted sign in a kendra or trikona, Venus strong (own/exalted)
    lk = p[L9]["dignity"] in ("own", "exalted") and p[L9]["house"] in KENDRA | {5, 9} and p["Venus"]["dignity"] in ("own", "exalted")
    add("lakshmi", "Lakshmi Yoga", "लक्ष्मी योग", lk,
        f"Lord of the 9th ({L9}) in own/exalted sign in a kendra or trikona, and Venus in own/exalted sign. Here: {L9} {p[L9]['dignity']} in house {p[L9]['house']}; Venus {p['Venus']['dignity']}.",
        f"नवमेश ({H[L9]}) स्वराशि/उच्च में केंद्र या त्रिकोण में, और शुक्र स्वराशि/उच्च में। यहाँ: {H[L9]} भाव {p[L9]['house']} में, शुक्र {DIG_HI.get(p['Venus']['dignity'], 'सामान्य')}।")
    # Saraswati yoga: Jupiter, Venus and Mercury each in a kendra, trikona or 2nd, Jupiter in own/exalted/friendly (own/exalted checked)
    sw_h = {1, 2, 4, 5, 7, 9, 10}
    sw = all(p[n]["house"] in sw_h for n in ("Jupiter", "Venus", "Mercury")) and p["Jupiter"]["dignity"] in ("own", "exalted")
    add("saraswati", "Saraswati Yoga", "सरस्वती योग", sw,
        "Jupiter, Venus and Mercury each in a kendra, trikona or the 2nd, with Jupiter in own/exalted sign (friendly sign not checked here).",
        "गुरु, शुक्र और बुध तीनों केंद्र, त्रिकोण या दूसरे भाव में, और गुरु स्वराशि/उच्च में (मित्र राशि यहाँ नहीं जाँची गई)।")
    return out
