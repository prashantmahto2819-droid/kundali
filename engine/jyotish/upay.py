"""उपाय (remedies) for a problem the seeker names, and राशि-रत्न (gemstone) guidance — DRAFT, traditional options only.

How a remedy plan is built
  1. Each problem names the houses and natural karakas that tradition looks at (career → 10th lord, Sun, Saturn; marriage →
     7th lord, Venus/Jupiter; ...).
  2. With a birth chart, each of those planets is checked: debilitated, in the 6th/8th/12th, combust, with Rahu/Ketu/Saturn,
     or the lord of the running Mahadasha/Antardasha. Those planets get remedies first.
  3. For every chosen planet: beej mantra with count, daan (charity) with day and items, vrat, deity/stotra, colour and simple
     conduct. A gemstone is suggested only for planets that are friendly lords for the lagna (lagna, 5th, 9th lords) and never
     for the 6th/8th/12th lords — otherwise rudraksha and mantra instead.
  4. Problem-specific traditional practices are added (e.g. Katyayani mantra for marriage delay).

Without a chart the plan uses the problem's karakas (and the Moon sign when given). Remedies are faith practices; health,
legal and money problems also need the right professional — the texts say so.
"""
from __future__ import annotations

from .constants import PLANETS_HI, SIGNS, SIGNS_HI

SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

PLANET = {
    "Sun": {"mantra": "ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः", "count": 7000, "day_hi": "रविवार", "day_en": "Sunday",
            "daan_hi": "गेहूँ, गुड़, ताँबा, लाल वस्त्र", "daan_en": "wheat, jaggery, copper, red cloth", "deity_hi": "सूर्य देव — आदित्य हृदय स्तोत्र", "deity_en": "Surya — Aditya Hridayam",
            "colour_hi": "लाल / केसरिया", "colour_en": "red / saffron", "act_hi": "सूर्योदय के समय ताँबे के लोटे से जल (अर्घ्य) दें; पिता का सम्मान करें।",
            "act_en": "Offer water to the rising Sun from a copper pot; respect your father.", "gem": ("माणिक्य", "Ruby"), "upa": ("लाल गार्नेट / सूर्यकांत", "Red garnet / sunstone"),
            "metal_hi": "सोना / ताँबा", "finger_hi": "अनामिका", "rudraksha": "एक या बारह मुखी"},
    "Moon": {"mantra": "ॐ श्रां श्रीं श्रौं सः चंद्रमसे नमः", "count": 11000, "day_hi": "सोमवार", "day_en": "Monday",
             "daan_hi": "चावल, दूध, चाँदी, सफ़ेद वस्त्र", "daan_en": "rice, milk, silver, white cloth", "deity_hi": "शिव — शिवलिंग पर जल/दूध, सोमवार व्रत", "deity_en": "Shiva — water/milk on the lingam, Monday vrat",
             "colour_hi": "सफ़ेद / चाँदी", "colour_en": "white / silver", "act_hi": "माँ के पैर छूकर आशीर्वाद लें; रात में सोने से पहले ध्यान/प्राणायाम।",
             "act_en": "Take your mother's blessings; meditate or do pranayama before sleep.", "gem": ("मोती", "Pearl"), "upa": ("मूनस्टोन", "Moonstone"),
             "metal_hi": "चाँदी", "finger_hi": "कनिष्ठा", "rudraksha": "दो मुखी"},
    "Mars": {"mantra": "ॐ क्रां क्रीं क्रौं सः भौमाय नमः", "count": 10000, "day_hi": "मंगलवार", "day_en": "Tuesday",
             "daan_hi": "मसूर दाल, लाल वस्त्र, गुड़, ताँबा", "daan_en": "red lentils, red cloth, jaggery, copper", "deity_hi": "हनुमान — हनुमान चालीसा, सुंदरकांड", "deity_en": "Hanuman — Hanuman Chalisa, Sundarkand",
             "colour_hi": "लाल", "colour_en": "red", "act_hi": "भाई-बहनों से संबंध मधुर रखें; क्रोध पर नियंत्रण, नियमित व्यायाम।",
             "act_en": "Keep good ties with siblings; control anger, exercise regularly.", "gem": ("मूँगा", "Red coral"), "upa": ("कार्नेलियन", "Carnelian"),
             "metal_hi": "सोना / ताँबा", "finger_hi": "अनामिका", "rudraksha": "तीन मुखी"},
    "Mercury": {"mantra": "ॐ ब्रां ब्रीं ब्रौं सः बुधाय नमः", "count": 9000, "day_hi": "बुधवार", "day_en": "Wednesday",
                "daan_hi": "हरी मूँग, हरा वस्त्र, हरी सब्ज़ी, कांसा", "daan_en": "green gram, green cloth, green vegetables, bronze", "deity_hi": "गणेश / विष्णु — विष्णु सहस्रनाम", "deity_en": "Ganesha / Vishnu — Vishnu Sahasranama",
                "colour_hi": "हरा", "colour_en": "green", "act_hi": "गाय को हरा चारा; बहन/बुआ/मौसी का सम्मान; वाणी में मिठास।",
                "act_en": "Feed green fodder to a cow; respect sisters and aunts; speak gently.", "gem": ("पन्ना", "Emerald"), "upa": ("पेरिडॉट / हरा ओनिक्स", "Peridot / green onyx"),
                "metal_hi": "सोना / कांसा", "finger_hi": "कनिष्ठा", "rudraksha": "चार मुखी"},
    "Jupiter": {"mantra": "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः", "count": 19000, "day_hi": "गुरुवार", "day_en": "Thursday",
                "daan_hi": "चने की दाल, हल्दी, पीला वस्त्र, केले", "daan_en": "chana dal, turmeric, yellow cloth, bananas", "deity_hi": "विष्णु / बृहस्पति — गुरुवार व्रत, केले के पेड़ की पूजा", "deity_en": "Vishnu / Brihaspati — Thursday vrat, worship of the banana tree",
                "colour_hi": "पीला", "colour_en": "yellow", "act_hi": "गुरु, शिक्षक और बड़ों का सम्मान; माथे पर हल्दी/केसर का तिलक।",
                "act_en": "Respect teachers, gurus and elders; a turmeric or saffron tilak.", "gem": ("पुखराज", "Yellow sapphire"), "upa": ("सुनहला (सिट्रीन)", "Citrine"),
                "metal_hi": "सोना", "finger_hi": "तर्जनी", "rudraksha": "पाँच मुखी"},
    "Venus": {"mantra": "ॐ द्रां द्रीं द्रौं सः शुक्राय नमः", "count": 16000, "day_hi": "शुक्रवार", "day_en": "Friday",
              "daan_hi": "चावल, दही, मिश्री, सफ़ेद वस्त्र, इत्र", "daan_en": "rice, curd, sugar candy, white cloth, perfume", "deity_hi": "लक्ष्मी — श्री सूक्त, शुक्रवार व्रत", "deity_en": "Lakshmi — Shri Suktam, Friday vrat",
              "colour_hi": "सफ़ेद / हल्का गुलाबी", "colour_en": "white / light pink", "act_hi": "जीवनसाथी व स्त्रियों का सम्मान; स्वच्छता और सुगंध।",
              "act_en": "Respect your spouse and women; cleanliness and fragrance.", "gem": ("हीरा", "Diamond"), "upa": ("ओपल / सफ़ेद पुखराज / ज़रकन", "Opal / white sapphire / zircon"),
              "metal_hi": "चाँदी / प्लैटिनम", "finger_hi": "मध्यमा / कनिष्ठा", "rudraksha": "छह मुखी"},
    "Saturn": {"mantra": "ॐ प्रां प्रीं प्रौं सः शनैश्चराय नमः", "count": 23000, "day_hi": "शनिवार", "day_en": "Saturday",
               "daan_hi": "काले तिल, सरसों का तेल, उड़द, लोहा, काला कंबल", "daan_en": "black sesame, mustard oil, urad, iron, a black blanket", "deity_hi": "शनि देव / हनुमान — शनिवार को पीपल पर दीपक", "deity_en": "Shani / Hanuman — a lamp under the peepal on Saturday",
               "colour_hi": "नीला / काला", "colour_en": "blue / black", "act_hi": "मज़दूरों, बुज़ुर्गों और ज़रूरतमंदों की सेवा; ईमानदारी और अनुशासन।",
               "act_en": "Serve workers, the elderly and the needy; honesty and discipline.", "gem": ("नीलम", "Blue sapphire"), "upa": ("नीली (एमेथिस्ट) / लाजवर्त", "Amethyst / lapis lazuli"),
               "metal_hi": "पंचधातु / लोहा", "finger_hi": "मध्यमा", "rudraksha": "सात मुखी"},
    "Rahu": {"mantra": "ॐ भ्रां भ्रीं भ्रौं सः राहवे नमः", "count": 18000, "day_hi": "शनिवार", "day_en": "Saturday",
             "daan_hi": "नारियल, काले-नीले वस्त्र, सरसों, कंबल", "daan_en": "coconut, black/blue cloth, mustard, blanket", "deity_hi": "दुर्गा — दुर्गा सप्तशती / दुर्गा चालीसा", "deity_en": "Durga — Durga Saptashati / Chalisa",
             "colour_hi": "गहरा नीला / धूसर", "colour_en": "dark blue / grey", "act_hi": "नशा, जुआ और शॉर्टकट से दूरी; पक्षियों को दाना।",
             "act_en": "Stay away from intoxicants, gambling and shortcuts; feed birds.", "gem": ("गोमेद", "Hessonite"), "upa": ("—", "—"),
             "metal_hi": "पंचधातु / चाँदी", "finger_hi": "मध्यमा", "rudraksha": "आठ मुखी"},
    "Ketu": {"mantra": "ॐ स्रां स्रीं स्रौं सः केतवे नमः", "count": 17000, "day_hi": "मंगलवार / शनिवार", "day_en": "Tuesday / Saturday",
             "daan_hi": "कंबल, तिल, सात अनाज, कुत्ते को रोटी", "daan_en": "blanket, sesame, seven grains, bread to a dog", "deity_hi": "गणेश — गणपति अथर्वशीर्ष", "deity_en": "Ganesha — Ganapati Atharvashirsha",
             "colour_hi": "धूसर / चितकबरा", "colour_en": "grey / multicolour", "act_hi": "कुत्ते की सेवा; ध्यान और आध्यात्मिक साधना।",
             "act_en": "Care for dogs; meditation and spiritual practice.", "gem": ("लहसुनिया", "Cat's eye"), "upa": ("—", "—"),
             "metal_hi": "पंचधातु / चाँदी", "finger_hi": "अनामिका / कनिष्ठा", "rudraksha": "नौ मुखी"},
}

# problem → houses (from lagna), natural karakas, and problem-specific traditional practices
PROBLEMS = {
    "career": {"hi": "नौकरी / करियर में रुकावट", "en": "Job / career obstacles", "houses": [10, 6], "karakas": ["Sun", "Saturn", "Mercury"],
               "extra_hi": ["रोज़ सूर्य को अर्घ्य और आदित्य हृदय स्तोत्र", "शनिवार को पीपल के नीचे सरसों के तेल का दीपक", "काम की जगह साफ़-सुथरी, समय की पाबंदी"],
               "extra_en": ["Daily arghya to the Sun and Aditya Hridayam", "A mustard-oil lamp under the peepal on Saturdays", "A tidy workplace and punctuality"]},
    "business": {"hi": "व्यापार / धन में कमी", "en": "Business / money shortfall", "houses": [2, 11, 7], "karakas": ["Jupiter", "Venus", "Mercury"],
                 "extra_hi": ["शुक्रवार को श्री सूक्त / लक्ष्मी पूजा", "बुधवार को गणेश जी को दूर्वा", "आय का एक छोटा हिस्सा नियमित दान"],
                 "extra_en": ["Shri Suktam / Lakshmi puja on Fridays", "Durva grass to Ganesha on Wednesdays", "Give a small fixed share of income regularly"]},
    "marriage_delay": {"hi": "विवाह में देरी", "en": "Delay in marriage", "houses": [7, 2], "karakas": ["Venus", "Jupiter"],
                       "extra_hi": ["कन्याओं के लिए कात्यायनी मंत्र: 'कात्यायनि महामाये महायोगिन्यधीश्वरि। नन्दगोपसुतं देवि पतिं मे कुरु ते नमः॥'", "गुरुवार व्रत और केले के पेड़ में जल", "शिव-पार्वती (गौरी-शंकर) की पूजा, सोमवार व्रत"],
                       "extra_en": ["For girls, the Katyayani mantra", "Thursday vrat and water to a banana tree", "Shiva-Parvati (Gauri-Shankar) worship, Monday vrat"]},
    "married_life": {"hi": "दांपत्य जीवन में तनाव", "en": "Strain in married life", "houses": [7, 8, 2], "karakas": ["Venus", "Jupiter", "Moon"],
                     "extra_hi": ["उमा-महेश्वर / गौरी-शंकर पूजा", "शुक्रवार को साथ में मीठा बाँटें; एक-दूसरे के परिवार का सम्मान", "ज़रूरत हो तो परिवार परामर्शदाता से बात"],
                     "extra_en": ["Uma-Maheshwara / Gauri-Shankar puja", "Share sweets together on Fridays; respect each other's families", "Talk to a family counsellor if needed"]},
    "health": {"hi": "स्वास्थ्य", "en": "Health", "houses": [1, 6, 8], "karakas": ["Sun", "Moon"],
               "extra_hi": ["महामृत्युंजय मंत्र का जप", "सूर्य नमस्कार / योग, समय पर भोजन-नींद", "सबसे पहले योग्य डॉक्टर से इलाज — उपाय केवल साथ में"],
               "extra_en": ["Chant the Mahamrityunjaya mantra", "Surya namaskar / yoga, regular meals and sleep", "First see a qualified doctor — remedies only alongside treatment"]},
    "education": {"hi": "पढ़ाई / परीक्षा", "en": "Studies / exams", "houses": [4, 5, 9], "karakas": ["Mercury", "Jupiter"],
                  "extra_hi": ["सरस्वती वंदना / 'ॐ ऐं सरस्वत्यै नमः'", "पढ़ाई पूर्व या उत्तर-पूर्व मुख करके", "बुधवार को गणेश पूजा"],
                  "extra_en": ["Saraswati vandana / 'Om Aim Saraswatyai Namah'", "Study facing east or north-east", "Ganesha puja on Wednesdays"]},
    "children": {"hi": "संतान", "en": "Children", "houses": [5, 9], "karakas": ["Jupiter"],
                 "extra_hi": ["संतान गोपाल मंत्र / हरिवंश पुराण का श्रवण", "गुरुवार व्रत", "डॉक्टर की सलाह के साथ"],
                 "extra_en": ["Santana Gopala mantra / listening to the Harivamsha", "Thursday vrat", "Together with medical advice"]},
    "legal": {"hi": "कोर्ट-कचहरी / विवाद", "en": "Court case / disputes", "houses": [6, 12], "karakas": ["Mars", "Saturn"],
              "extra_hi": ["हनुमान चालीसा / बजरंग बाण", "मंगलवार को हनुमान जी को सिंदूर-चोला", "अच्छे वकील की सलाह — उपाय केवल साथ में"],
              "extra_en": ["Hanuman Chalisa / Bajrang Baan", "Sindoor offering to Hanuman on Tuesdays", "A good lawyer first — remedies only alongside"]},
    "debt": {"hi": "क़र्ज़", "en": "Debt", "houses": [6, 11], "karakas": ["Mars", "Jupiter"],
             "extra_hi": ["ऋणमोचक मंगल स्तोत्र (मंगलवार)", "मंगलवार को क़र्ज़ की किस्त चुकाने की शुरुआत", "ख़र्च का हिसाब और बजट"],
             "extra_en": ["Rinamochaka Mangala Stotra (Tuesdays)", "Start repaying on a Tuesday", "Track spending and keep a budget"]},
    "peace": {"hi": "मानसिक तनाव / बेचैनी", "en": "Stress / restlessness", "houses": [4, 1], "karakas": ["Moon", "Mercury"],
              "extra_hi": ["रोज़ 10 मिनट ध्यान / अनुलोम-विलोम", "सोमवार को शिवलिंग पर जल", "ज़रूरत हो तो मनोचिकित्सक/काउंसलर से बात"],
              "extra_en": ["10 minutes of meditation / alternate-nostril breathing daily", "Water on the Shiva lingam on Mondays", "Talk to a counsellor or doctor if needed"]},
    "foreign": {"hi": "विदेश यात्रा / बसना", "en": "Foreign travel / settling abroad", "houses": [12, 9, 3], "karakas": ["Rahu", "Moon"],
                "extra_hi": ["दुर्गा चालीसा", "पक्षियों को दाना", "दस्तावेज़ समय पर पूरे रखें"], "extra_en": ["Durga Chalisa", "Feed birds", "Keep documents complete and on time"]},
    "property": {"hi": "मकान / ज़मीन", "en": "House / land", "houses": [4], "karakas": ["Mars", "Venus"],
                 "extra_hi": ["मंगलवार को हनुमान पूजा", "भूमि-पूजन शुभ मुहूर्त में", "घर की उत्तर-पूर्व दिशा साफ़ रखें"],
                 "extra_en": ["Hanuman puja on Tuesdays", "Bhoomi puja at a good muhurta", "Keep the north-east of the home clean"]},
    "enemies": {"hi": "शत्रु / नज़र-दोष का डर", "en": "Enemies / fear of the evil eye", "houses": [6, 8], "karakas": ["Mars", "Rahu"],
                "extra_hi": ["हनुमान चालीसा / बजरंग बाण", "दुर्गा कवच", "बातचीत से विवाद सुलझाने की कोशिश"],
                "extra_en": ["Hanuman Chalisa / Bajrang Baan", "Durga Kavacham", "Try to settle disputes by talking"]},
    "sade_sati": {"hi": "साढ़ेसाती / शनि ढैया", "en": "Sade Sati / Shani dhaiya", "houses": [], "karakas": ["Saturn"],
                  "extra_hi": ["शनिवार को शनि मंदिर में तेल अर्पण, हनुमान चालीसा", "दशरथकृत शनि स्तोत्र", "ज़रूरतमंदों को भोजन, अनुशासित दिनचर्या"],
                  "extra_en": ["Oil to Shani on Saturdays, Hanuman Chalisa", "Dasharatha's Shani Stotra", "Feed the needy, keep a disciplined routine"]},
    "mangal_dosha": {"hi": "मांगलिक दोष", "en": "Mangal dosha", "houses": [], "karakas": ["Mars"],
                     "extra_hi": ["मंगलवार व्रत, हनुमान पूजा", "मंगल चंडिका स्तोत्र", "मिलान में दोनों कुंडलियों का परिहार देखें"],
                     "extra_en": ["Tuesday vrat, Hanuman puja", "Mangala Chandika Stotra", "Check cancellations in both charts when matching"]},
    "kaal_sarp": {"hi": "कालसर्प दोष", "en": "Kaal Sarp dosha", "houses": [], "karakas": ["Rahu", "Ketu"],
                  "extra_hi": ["नाग पंचमी / महाशिवरात्रि पर शिव अभिषेक", "महामृत्युंजय जप", "त्र्यंबकेश्वर/उज्जैन में शांति पूजा (परंपरा अनुसार)"],
                  "extra_en": ["Shiva abhisheka on Nag Panchami / Mahashivaratri", "Mahamrityunjaya japa", "Shanti puja at Trimbakeshwar/Ujjain (by tradition)"]},
    "pitru": {"hi": "पितृ दोष", "en": "Pitru dosha", "houses": [9], "karakas": ["Sun", "Rahu"],
              "extra_hi": ["अमावस्या को पितरों के नाम दान और तर्पण", "पितृ पक्ष में श्राद्ध", "पीपल पर जल, कौए/गाय को भोजन"],
              "extra_en": ["Charity and tarpan for ancestors on Amavasya", "Shraddha in Pitru Paksha", "Water to the peepal, food to crows/cows"]},
}

NOTE_HI = ("ये परंपरागत उपाय हैं (DRAFT, विद्वान-समीक्षा जारी)। मंत्र-जप, दान और व्रत आस्था के साधन हैं; स्वास्थ्य, क़ानूनी या आर्थिक समस्या में पहले "
           "संबंधित विशेषज्ञ से सलाह लें। रत्न धारण से पहले योग्य ज्योतिषी से पूरी कुंडली दिखाएँ।")
NOTE_EN = ("Traditional remedies (DRAFT, under scholar review). Mantra, charity and vrat are practices of faith; for health, legal or money "
           "problems see the right professional first. Show your full chart to a qualified astrologer before wearing a gemstone.")


def ordinal_hi(h: int) -> str:
    return {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 6: "छठे"}.get(h, f"{h}वें")


def _planet_card(pl: str, why_hi: str, why_en: str, gem_ok: bool) -> dict:
    d = PLANET[pl]
    return {"planet": pl, "planet_hi": PLANETS_HI[pl], "why_hi": why_hi, "why_en": why_en,
            "mantra": d["mantra"], "count": d["count"], "day_hi": d["day_hi"], "day_en": d["day_en"],
            "daan_hi": d["daan_hi"], "daan_en": d["daan_en"], "deity_hi": d["deity_hi"], "deity_en": d["deity_en"],
            "colour_hi": d["colour_hi"], "colour_en": d["colour_en"], "act_hi": d["act_hi"], "act_en": d["act_en"],
            "rudraksha_hi": d["rudraksha"],
            "gem": ({"hi": d["gem"][0], "en": d["gem"][1], "upa_hi": d["upa"][0], "upa_en": d["upa"][1], "metal_hi": d["metal_hi"], "finger_hi": d["finger_hi"]} if gem_ok else None)}


def lucky_lords(lagna_sign: int) -> tuple[list[str], set[str]]:
    lord = SIGN_LORDS[lagna_sign]
    good = [lord] + [SIGN_LORDS[(lagna_sign + k) % 12] for k in (4, 8)]
    avoid = {SIGN_LORDS[(lagna_sign + h - 1) % 12] for h in (6, 8, 12)} - set(good)
    seen = []
    for g in good:
        if g not in seen and g not in avoid:
            seen.append(g)
    return seen, avoid


def plan(problem: str, chart: dict | None = None, moon_sign: int | None = None) -> dict:
    if problem not in PROBLEMS:
        raise ValueError("unknown problem; one of: " + ", ".join(PROBLEMS))
    pr = PROBLEMS[problem]
    picked: list[tuple[str, str, str]] = []
    gem_ok_set: set[str] = set()
    basis = "general"
    if chart:
        basis = "chart"
        p = {x["name"]: x for x in chart["planets"]}
        ls = chart["lagna"]["sign"]
        good, avoid = lucky_lords(ls)
        gem_ok_set = set(good) - avoid
        dasha = [x["lord"] for x in (chart.get("dasha_running") or [])[:2]]
        cands: list[tuple[str, str, str]] = []
        for h in pr["houses"]:
            lord = SIGN_LORDS[(ls + h - 1) % 12]
            cands.append((lord, f"{ordinal_hi(h)} भाव का स्वामी", f"lord of house {h}"))
        for k in pr["karakas"]:
            cands.append((k, "इस विषय का कारक ग्रह", "natural significator"))
        for pl, why_hi, why_en in cands:
            x = p.get(pl)
            if not x:
                continue
            issues_hi, issues_en = [], []
            if x.get("dignity") == "debilitated":
                issues_hi.append("नीच राशि में"); issues_en.append("debilitated")
            if x.get("house") in (6, 8, 12):
                issues_hi.append(f"{ordinal_hi(x['house'])} भाव में"); issues_en.append(f"in house {x['house']}")
            if x.get("combust"):
                issues_hi.append("अस्त"); issues_en.append("combust")
            with_malefic = [o for o in ("Rahu", "Ketu", "Saturn") if o != pl and p.get(o, {}).get("sign") == x["sign"]]
            if with_malefic:
                issues_hi.append("साथ में " + ", ".join(PLANETS_HI[o] for o in with_malefic)); issues_en.append("with " + ", ".join(with_malefic))
            if pl in dasha:
                issues_hi.append("इसकी दशा चल रही है"); issues_en.append("its dasha is running")
            if issues_hi or not picked:
                if all(pl != q[0] for q in picked):
                    picked.append((pl, f"{why_hi} — " + ("; ".join(issues_hi) if issues_hi else "विषय का मुख्य ग्रह"),
                                   f"{why_en} — " + ("; ".join(issues_en) if issues_en else "main planet for this topic")))
            if len(picked) >= 3:
                break
        # the running mahadasha lord is always worth calming when it is a dusthana lord
        if dasha and dasha[0] in avoid and all(dasha[0] != q[0] for q in picked) and len(picked) < 4:
            picked.append((dasha[0], "चल रही महादशा का स्वामी (6/8/12 भाव का स्वामी)", "running Mahadasha lord (6th/8th/12th lord)"))
    else:
        for k in pr["karakas"][:2]:
            picked.append((k, "इस विषय का कारक ग्रह", "natural significator for this topic"))
        if moon_sign is not None:
            ml = SIGN_LORDS[int(moon_sign) % 12]
            if all(ml != q[0] for q in picked):
                picked.append((ml, f"आपकी चंद्र राशि ({SIGNS_HI[int(moon_sign) % 12]}) का स्वामी", f"lord of your Moon sign ({SIGNS[int(moon_sign) % 12]})"))
            basis = "moon_sign"
        gem_ok_set = set()
    cards = [_planet_card(pl, wh, we, pl in gem_ok_set) for pl, wh, we in picked]
    return {"problem": problem, "problem_hi": pr["hi"], "problem_en": pr["en"], "basis": basis, "planets": cards,
            "practices_hi": pr["extra_hi"], "practices_en": pr["extra_en"], "note_hi": NOTE_HI, "note_en": NOTE_EN, "review_status": "draft"}


# ---------------------------------------------------------------- राशि रत्न
HOW_HI = ["शुक्ल पक्ष में, ग्रह के वार को, सूर्योदय के बाद (उस ग्रह की होरा में) धारण करें।",
          "पहनने से पहले अँगूठी को गंगाजल / कच्चे दूध से धोकर ग्रह के बीज मंत्र का 108 बार जप करें।",
          "रत्न त्वचा को छूता हो — ऐसी खुली अँगूठी/पेंडेंट बनवाएँ; प्राकृतिक, बिना ट्रीटमेंट और प्रमाणपत्र वाला रत्न लें।",
          "नीलम, हीरा, गोमेद, लहसुनिया पहले कुछ दिन परख कर ही पहनें; कोई परेशानी हो तो उतार दें।"]
HOW_EN = ["Wear in the bright fortnight, on the planet's weekday, after sunrise (in its hora).",
          "Wash the ring in Ganga water / raw milk and chant the planet's beej mantra 108 times.",
          "Use an open setting so the stone touches the skin; buy a natural, untreated, certified stone.",
          "Try blue sapphire, diamond, hessonite and cat's eye for a few days first; remove if anything feels wrong."]


def ratna(lagna_sign: int | None = None, moon_sign: int | None = None) -> dict:
    """Lucky gemstones: by lagna (lagna, 5th and 9th lords — the traditional method) and/or by Moon sign (popular)."""
    def gem(pl, role_hi, role_en):
        d = PLANET[pl]
        return {"planet": pl, "planet_hi": PLANETS_HI[pl], "role_hi": role_hi, "role_en": role_en, "gem_hi": d["gem"][0], "gem_en": d["gem"][1],
                "upa_hi": d["upa"][0], "upa_en": d["upa"][1], "metal_hi": d["metal_hi"], "finger_hi": d["finger_hi"], "day_hi": d["day_hi"], "day_en": d["day_en"],
                "mantra": d["mantra"]}
    out = {"how_hi": HOW_HI, "how_en": HOW_EN, "note_hi": NOTE_HI, "note_en": NOTE_EN}
    if lagna_sign is not None:
        ls = int(lagna_sign) % 12; good, avoid = lucky_lords(ls)
        roles = {SIGN_LORDS[ls]: ("लग्नेश — जीवन रत्न", "lagna lord — life stone"), SIGN_LORDS[(ls + 4) % 12]: ("पंचमेश — बुद्धि/संतान", "5th lord — intellect/children"),
                 SIGN_LORDS[(ls + 8) % 12]: ("नवमेश — भाग्य रत्न", "9th lord — fortune stone")}
        out["by_lagna"] = {"sign": ls, "sign_hi": SIGNS_HI[ls], "sign_en": SIGNS[ls], "stones": [gem(pl, *roles[pl]) for pl in good],
                           "avoid": [{"planet": pl, "planet_hi": PLANETS_HI[pl], "gem_hi": PLANET[pl]["gem"][0], "gem_en": PLANET[pl]["gem"][1]} for pl in sorted(avoid)]}
    if moon_sign is not None:
        ms = int(moon_sign) % 12; pl = SIGN_LORDS[ms]
        out["by_moon"] = {"sign": ms, "sign_hi": SIGNS_HI[ms], "sign_en": SIGNS[ms], "stone": gem(pl, "राशि स्वामी — राशि रत्न", "sign lord — rashi ratna")}
    return out


def table() -> list[dict]:
    """All 12 signs → rashi ratna (for the public /ratna page)."""
    return [{"sign": i, "sign_hi": SIGNS_HI[i], "sign_en": SIGNS[i], "lord": SIGN_LORDS[i], "lord_hi": PLANETS_HI[SIGN_LORDS[i]],
             "gem_hi": PLANET[SIGN_LORDS[i]]["gem"][0], "gem_en": PLANET[SIGN_LORDS[i]]["gem"][1], "upa_hi": PLANET[SIGN_LORDS[i]]["upa"][0],
             "lagna_stones": [PLANET[p]["gem"][0] for p in lucky_lords(i)[0]]} for i in range(12)]
