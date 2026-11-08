"""Pattern yogas: the 32 Nabhasa yogas (BPHS ch. 35) and the five Mahapurusha yogas, plus a few common
conjunction yogas (Guru-Chandala, Grahana, Angaraka, Vish, Shakata). Seven planets Sun..Saturn, whole-sign
houses from the Lagna. Own wording, tendency language, draft: a jyotishi should check the definitions.

Nabhasa groups: Ashraya (3, by sign quality), Dala (2, benefics/malefics in kendras), Akriti (20, by the houses
occupied) and Sankhya (7, by the number of signs occupied; only when no Akriti yoga is formed, as BPHS says).
"""
from __future__ import annotations

from .constants import PLANETS_HI, SIGN_LORDS
from .core import dignity

SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
BENEFIC = {"Jupiter", "Venus", "Mercury"}
MALEFIC = {"Sun", "Mars", "Saturn"}
KENDRA = {1, 4, 7, 10}
PANAPHARA = {2, 5, 8, 11}
APOKLIMA = {3, 6, 9, 12}

MAHAPURUSHA = {"Mars": ("ruchaka", "Ruchaka", "रुचक", "साहस, नेतृत्व और शारीरिक बल की प्रवृत्ति; सेना, खेल, तकनीक में सफलता की परंपरा।",
                        "a tendency to courage, leadership and physical vigour; traditionally success in defence, sport, engineering."),
               "Mercury": ("bhadra", "Bhadra", "भद्र", "बुद्धि, वाणी, लेखन और व्यापार-कौशल की प्रवृत्ति; संतुलित विवेक।",
                           "a tendency to intellect, speech, writing and commercial skill; balanced judgement."),
               "Jupiter": ("hamsa", "Hamsa", "हंस", "ज्ञान, धर्म, शिक्षण और सम्मान की प्रवृत्ति; उदार स्वभाव।",
                           "a tendency to wisdom, dharma, teaching and respect; a generous nature."),
               "Venus": ("malavya", "Malavya", "मालव्य", "सौंदर्य, कला, सुख-सुविधा और आकर्षण की प्रवृत्ति; वाहन-गृह सुख।",
                         "a tendency to beauty, the arts, comfort and charm; traditionally conveyances and a good home."),
               "Saturn": ("shasha", "Shasha", "शश", "अनुशासन, संगठन, जन-नेतृत्व और धैर्य की प्रवृत्ति; देर से पर पक्की उन्नति।",
                          "a tendency to discipline, organisation, leadership of people and patience; slow but solid rise.")}

NABHASA_TEXT = {
    "rajju": ("Rajju", "रज्जु", "ashraya", "सभी ग्रह चर राशियों में: गतिशील, यात्रा-प्रिय, बदलाव पसंद स्वभाव।", "All planets in movable signs: a mobile, travel-loving nature that likes change."),
    "musala": ("Musala", "मुसल", "ashraya", "सभी ग्रह स्थिर राशियों में: दृढ़, टिकाऊ, स्थिर आय और प्रतिष्ठा की प्रवृत्ति।", "All planets in fixed signs: firm and steady, with lasting income and standing."),
    "nala": ("Nala", "नल", "ashraya", "सभी ग्रह द्विस्वभाव राशियों में: लचीला, बहु-कुशल, संग्रह करने वाला स्वभाव।", "All planets in dual signs: adaptable, many-skilled, inclined to collect and keep."),
    "mala": ("Mala", "माला", "dala", "शुभ ग्रह केंद्रों में, पाप ग्रह नहीं: सुख, मित्र और साधनों की माला।", "Benefics in kendras without malefics: a garland of comforts, friends and means."),
    "sarpa": ("Sarpa", "सर्प", "dala", "पाप ग्रह केंद्रों में, शुभ नहीं: संघर्षशील जीवन, धैर्य और परिश्रम की माँग।", "Malefics in kendras without benefics: a striving life that asks for patience and effort."),
    "gada": ("Gada", "गदा", "akriti", "सभी ग्रह दो सटे केंद्रों में: धन-अर्जन और धार्मिक कार्यों की प्रवृत्ति।", "All planets in two adjacent kendras: a tendency to earn well and to religious works."),
    "shakata": ("Shakata", "शकट", "akriti", "सभी ग्रह 1 और 7 में: उतार-चढ़ाव, श्रम से जीविका, गाड़ी-पहिए की तरह घूमता भाग्य।", "All planets in houses 1 and 7: ups and downs, livelihood through labour, fortune that turns like a cart-wheel."),
    "vihaga": ("Vihaga", "विहग", "akriti", "सभी ग्रह 4 और 10 में: घूमने-फिरने, दूत-कार्य, वाणी से जीविका की प्रवृत्ति।", "All planets in houses 4 and 10: wandering, messenger work, livelihood through speech."),
    "shringataka": ("Shringataka", "शृंगाटक", "akriti", "सभी ग्रह त्रिकोणों (1,5,9) में: सुखी, वीर, राज-कृपा; जीवन के उत्तरार्ध में अधिक सुख।", "All planets in trikonas (1,5,9): happy, brave, favoured by authority; more comfort later in life."),
    "hala": ("Hala", "हल", "akriti", "सभी ग्रह 2-6-10, 3-7-11 या 4-8-12 में: कृषि, भूमि और परिश्रम से जुड़ा जीवन।", "All planets in 2-6-10, 3-7-11 or 4-8-12: a life tied to land, farming and hard work."),
    "vajra": ("Vajra", "वज्र", "akriti", "शुभ 1 और 7 में, पाप 4 और 10 में: आरंभ और अंत में सुख, मध्य में संघर्ष; साहसी।", "Benefics in 1 and 7, malefics in 4 and 10: comfort early and late, struggle in between; brave."),
    "yava": ("Yava", "यव", "akriti", "पाप 1 और 7 में, शुभ 4 और 10 में: जीवन के मध्य में सुख और दान-धर्म; दृढ़।", "Malefics in 1 and 7, benefics in 4 and 10: comfort and charity in mid-life; steadfast."),
    "kamala": ("Kamala", "कमल", "akriti", "सभी ग्रह चारों केंद्रों में: कीर्ति, गुण, दीर्घ प्रभाव; बड़ा राजयोग माना गया।", "All planets in the four kendras: fame, virtues, lasting influence; counted as a great raja yoga."),
    "vapi": ("Vapi", "वापी", "akriti", "सभी ग्रह पणफरों में या सभी आपोक्लिमों में: संचय, धन इकट्ठा करने और बचाने की प्रवृत्ति।", "All planets in panapharas or all in apoklimas: accumulation, a tendency to gather and save wealth."),
    "yupa": ("Yupa", "यूप", "akriti", "सभी ग्रह 1 से 4 तक: यज्ञ-दान, आत्म-अनुशासन और गृहस्थ-धर्म की प्रवृत्ति।", "All planets in houses 1-4: sacrifice, charity, self-discipline and the householder's dharma."),
    "ishu": ("Ishu (Shara)", "इषु (शर)", "akriti", "सभी ग्रह 4 से 7 तक: शिकार/रक्षा, शस्त्र, कठोर कार्यों की प्रवृत्ति।", "All planets in houses 4-7: hunting/defence, weapons, hard occupations."),
    "shakti": ("Shakti", "शक्ति", "akriti", "सभी ग्रह 7 से 10 तक: आलस्य से संघर्ष, पर दृढ़ और दीर्घायु-सूचक परंपरा; युद्ध-कुशल।", "All planets in houses 7-10: a struggle with inertia but firm; traditionally skilled in contest."),
    "danda": ("Danda", "दंड", "akriti", "सभी ग्रह 10 से 1 तक: अकेलापन, सेवा-कार्य, कठोर अनुशासन की प्रवृत्ति।", "All planets in houses 10-1: solitude, service work, strict discipline."),
    "nauka": ("Nauka", "नौका", "akriti", "सभी ग्रह 1 से 7 तक लगातार: जल/यात्रा/व्यापार से लाभ, महत्वाकांक्षी, कंजूस प्रवृत्ति की परंपरा।", "All planets in the seven houses 1-7: gains from water, travel or trade; ambitious; traditionally thrifty."),
    "kuta": ("Kuta", "कूट", "akriti", "सभी ग्रह 4 से 10 तक लगातार: किले/जेल/सुरक्षा से जुड़े कार्य, छल से सावधानी की परंपरा।", "All planets in the seven houses 4-10: work tied to forts, prisons or security; tradition warns of deceit."),
    "chhatra": ("Chhatra", "छत्र", "akriti", "सभी ग्रह 7 से 1 तक लगातार: छत्र की तरह रक्षा; बुद्धिमान, दयालु, आरंभ-अंत में सुखी।", "All planets in the seven houses 7-1: shelter like an umbrella; wise, kind, happy early and late."),
    "chapa": ("Chapa (Dhanush)", "चाप (धनुष)", "akriti", "सभी ग्रह 10 से 4 तक लगातार: रक्षक, साहसी, मध्य-जीवन में सुख।", "All planets in the seven houses 10-4: a protector, brave, comfortable in mid-life."),
    "ardha_chandra": ("Ardha-chandra", "अर्धचंद्र", "akriti", "सभी ग्रह केंद्र से न शुरू होकर सात लगातार भावों में: सुंदर, सेना-नायक या अधिकारी की प्रवृत्ति।", "All planets in seven consecutive houses not starting from a kendra: graceful, a commander or officer type."),
    "chakra": ("Chakra", "चक्र", "akriti", "सभी ग्रह विषम भावों (1,3,5,7,9,11) में: सम्राट-सूचक, व्यापक प्रभाव।", "All planets in the odd houses (1,3,5,7,9,11): emperor-like, wide influence."),
    "samudra": ("Samudra", "समुद्र", "akriti", "सभी ग्रह सम भावों (2,4,6,8,10,12) में: समुद्र-सा धन और सुख, स्थिर मन।", "All planets in the even houses (2,4,6,8,10,12): wealth and comfort like the sea, a steady mind."),
    "veena": ("Veena (Vallaki)", "वीणा", "sankhya", "सात ग्रह सात राशियों में: संगीत, कला और अनेक रुचियों की प्रवृत्ति।", "Seven planets in seven signs: music, the arts and many interests."),
    "dama": ("Dama", "दाम", "sankhya", "सात ग्रह छह राशियों में: उदार, सहायक, धन देने वाला स्वभाव।", "Seven planets in six signs: generous, helpful, giving."),
    "pasha": ("Pasha", "पाश", "sankhya", "सात ग्रह पाँच राशियों में: बंधनों में उलझाव, बड़े परिवार और दायित्व की प्रवृत्ति।", "Seven planets in five signs: entanglements, a large family and many obligations."),
    "kedara": ("Kedara", "केदार", "sankhya", "सात ग्रह चार राशियों में: कृषि/उत्पादन, सत्यनिष्ठ, उपयोगी व्यक्ति।", "Seven planets in four signs: farming/production, truthful, useful to many."),
    "shoola": ("Shoola", "शूल", "sankhya", "सात ग्रह तीन राशियों में: तीखा, साहसी, संघर्ष में तपा हुआ।", "Seven planets in three signs: sharp, bold, tempered by struggle."),
    "yuga": ("Yuga", "युग", "sankhya", "सात ग्रह दो राशियों में: पाखंड से सावधानी की परंपरा; एकाग्र पर संकीर्ण रुचि।", "Seven planets in two signs: tradition warns against hypocrisy; focused but narrow interests."),
    "gola": ("Gola", "गोल", "sankhya", "सात ग्रह एक राशि में: अत्यंत दुर्लभ; एक ही विषय में डूबा जीवन।", "Seven planets in one sign: extremely rare; a life absorbed in a single theme."),
}

CONJ_TEXT = {
    "guru_chandala": ("Guru-Chandala", "गुरु-चांडाल", "गुरु राहु के साथ: परंपरागत नियमों से हटकर सोचने की प्रवृत्ति; शिक्षा और गुरु-संबंधों में विवेक ज़रूरी।",
                      "Jupiter with Rahu: a tendency to think outside convention; discernment needed in learning and with mentors."),
    "grahana_surya": ("Grahana (Sun)", "ग्रहण (सूर्य)", "सूर्य राहु/केतु के साथ: आत्मविश्वास और पिता/अधिकार से जुड़े विषयों में उतार-चढ़ाव की प्रवृत्ति।",
                      "Sun with Rahu/Ketu: fluctuation in confidence and in matters of father/authority."),
    "grahana_chandra": ("Grahana (Moon)", "ग्रहण (चंद्र)", "चंद्र राहु/केतु के साथ: मन की बेचैनी, कल्पना-प्रधानता; नियमित दिनचर्या सहायक।",
                        "Moon with Rahu/Ketu: restlessness of mind, strong imagination; routine helps."),
    "angaraka": ("Angaraka", "अंगारक", "मंगल राहु के साथ: तीव्र ऊर्जा और आवेग; क्रोध और जल्दबाज़ी में संयम की परंपरा।",
                 "Mars with Rahu: intense energy and impulse; tradition counsels restraint in anger and haste."),
    "vish": ("Vish (Punarphoo)", "विष (पुनर्फू)", "शनि चंद्र के साथ: गंभीर, जिम्मेदार मन; उदासी की प्रवृत्ति पर धैर्य और अनुशासन से परिपक्वता।",
             "Saturn with the Moon: a serious, responsible mind; a melancholic streak that matures through patience and discipline."),
    "shakata_moon": ("Shakata (Moon-Jupiter)", "शकट (चंद्र-गुरु)", "चंद्र गुरु से 6/8/12 में: भाग्य में उतार-चढ़ाव; परंपरा में चंद्र के केंद्र में होने से भंग।",
                     "Moon in 6/8/12 from Jupiter: fluctuating fortune; cancelled in tradition when the Moon is in a kendra."),
}


def _houses(chart):
    p = {x["name"]: x for x in chart["planets"]}
    return p, {k: p[k]["house"] for k in SEVEN}, {k: p[k]["sign"] for k in SEVEN}


def _consecutive(start: int, n: int) -> set:
    return {(start - 1 + i) % 12 + 1 for i in range(n)}


def detect(chart: dict) -> list[dict]:
    p, H, S = _houses(chart)
    occ = set(H.values())
    out = []

    def add(yid, name, hi, present, why, why_hi, group):
        out.append({"id": yid, "name": name, "name_hi": hi, "present": bool(present), "why": why, "why_hi": why_hi, "group": group, "review_status": "draft"})
        add.last = out[-1]

    # ---- Pancha Mahapurusha
    for planet, (yid, name, hi, t_hi, t_en) in MAHAPURUSHA.items():
        d = dignity(planet, S[planet]); own = SIGN_LORDS[S[planet]] == planet
        present = (d == "exalted" or own) and H[planet] in KENDRA
        add(yid, f"{name} Mahapurusha Yoga", f"{hi} महापुरुष योग", present,
            f"{planet} in its own or exaltation sign in a kendra from the Lagna (here house {H[planet]}, {'own' if own else d or 'ordinary'} sign). {t_en if present else ''}".strip(),
            f"{PLANETS_HI[planet]} स्वराशि या उच्च में, लग्न से केंद्र में (यहाँ भाव {H[planet]}, {'स्वराशि' if own else 'उच्च' if d == 'exalted' else 'सामान्य राशि'})। {t_hi if present else ''}".strip(), "mahapurusha")

    # ---- Nabhasa: Ashraya
    qual = {S[k] % 3 for k in SEVEN}            # 0 movable, 1 fixed, 2 dual
    for q, yid in ((0, "rajju"), (1, "musala"), (2, "nala")):
        _nab(add, yid, qual == {q}, f"sign qualities occupied: {sorted(qual)} (0 movable, 1 fixed, 2 dual)", f"राशि-स्वभाव: {sorted(qual)} (0 चर, 1 स्थिर, 2 द्विस्वभाव)")
    # ---- Dala
    ben_k = all(H[b] in KENDRA for b in BENEFIC); mal_k_none = not any(H[m] in KENDRA for m in MALEFIC)
    mal_k = all(H[m] in KENDRA for m in MALEFIC); ben_k_none = not any(H[b] in KENDRA for b in BENEFIC)
    _nab(add, "mala", ben_k and mal_k_none, "", "")
    _nab(add, "sarpa", mal_k and ben_k_none, "", "")
    # ---- Akriti
    ak = {}
    ak["gada"] = any(occ == {a, b} for a, b in ((1, 4), (4, 7), (7, 10), (10, 1)))
    ak["shakata"] = occ == {1, 7}
    ak["vihaga"] = occ == {4, 10}
    ak["shringataka"] = occ == {1, 5, 9}
    ak["hala"] = occ in ({2, 6, 10}, {3, 7, 11}, {4, 8, 12})
    ak["vajra"] = all(H[b] in (1, 7) for b in BENEFIC) and all(H[m] in (4, 10) for m in MALEFIC) and occ <= KENDRA
    ak["yava"] = all(H[m] in (1, 7) for m in MALEFIC) and all(H[b] in (4, 10) for b in BENEFIC) and occ <= KENDRA
    ak["kamala"] = occ == KENDRA
    ak["vapi"] = occ == PANAPHARA or occ == APOKLIMA
    ak["yupa"] = occ <= _consecutive(1, 4) and len(occ) >= 2 and occ != {1, 4}
    ak["ishu"] = occ <= _consecutive(4, 4) and len(occ) >= 2 and occ != {4, 7}
    ak["shakti"] = occ <= _consecutive(7, 4) and len(occ) >= 2 and occ != {7, 10}
    ak["danda"] = occ <= _consecutive(10, 4) and len(occ) >= 2 and occ != {10, 1}
    ak["nauka"] = occ == _consecutive(1, 7)
    ak["kuta"] = occ == _consecutive(4, 7)
    ak["chhatra"] = occ == _consecutive(7, 7)
    ak["chapa"] = occ == _consecutive(10, 7)
    ak["ardha_chandra"] = any(occ == _consecutive(s, 7) for s in (PANAPHARA | APOKLIMA))
    ak["chakra"] = occ == {1, 3, 5, 7, 9, 11}
    ak["samudra"] = occ == {2, 4, 6, 8, 10, 12}
    for yid, present in ak.items():
        _nab(add, yid, present, f"houses occupied by the seven planets: {sorted(occ)}", f"सातों ग्रहों के भाव: {sorted(occ)}")
    # ---- Sankhya (only when no Akriti yoga)
    nsigns = len(set(S.values()))
    any_akriti = any(ak.values())
    for n, yid in ((7, "veena"), (6, "dama"), (5, "pasha"), (4, "kedara"), (3, "shoola"), (2, "yuga"), (1, "gola")):
        _nab(add, yid, nsigns == n and not any_akriti, f"seven planets occupy {nsigns} sign(s){'; an Akriti yoga takes precedence' if any_akriti else ''}",
             f"सात ग्रह {nsigns} राशि(यों) में{'; आकृति योग को प्राथमिकता' if any_akriti else ''}")

    # ---- common conjunction yogas (same sign)
    rahu, ketu = p.get("Rahu"), p.get("Ketu")
    same = lambda a, b: a is not None and b is not None and a["sign"] == b["sign"]
    conj = {"guru_chandala": same(p["Jupiter"], rahu), "grahana_surya": same(p["Sun"], rahu) or same(p["Sun"], ketu),
            "grahana_chandra": same(p["Moon"], rahu) or same(p["Moon"], ketu), "angaraka": same(p["Mars"], rahu), "vish": same(p["Saturn"], p["Moon"])}
    for yid, present in conj.items():
        name, hi, t_hi, t_en = CONJ_TEXT[yid]
        add(yid, f"{name} Yoga", f"{hi} योग", present, t_en if present else "Not formed (the planets are not in one sign).", t_hi if present else "नहीं बना (ग्रह एक राशि में नहीं)।", "conjunction")
    hm = (H["Moon"] - H["Jupiter"]) % 12 + 1
    sk = hm in (6, 8, 12) and H["Moon"] not in KENDRA
    name, hi, t_hi, t_en = CONJ_TEXT["shakata_moon"]
    add("shakata_moon", f"{name} Yoga", f"{hi} योग", sk, f"Moon is in house {hm} from Jupiter. " + (t_en if sk else ""), f"चंद्र गुरु से {hm}वें भाव में। " + (t_hi if sk else ""), "conjunction")
    return out


def _nab(add, yid, present, why, why_hi):
    name, hi, group, t_hi, t_en = NABHASA_TEXT[yid]
    add(yid, f"{name} (Nabhasa) Yoga", f"{hi} (नाभस) योग", present, t_en, t_hi, f"nabhasa_{group}")
    if why:
        add.last["context"] = why; add.last["context_hi"] = why_hi
