"""Janma patrika summary page in a regional language (te, kn, mr, gu, bn, ta, ml): birth details, birth panchang,
lagna / rashi / nakshatra, the nine grahas with sign, degree, nakshatra-pada and house, a north-style chart grid, and the
running Vimshottari dasha. Terms come from regional.py; the long interpretive report that follows stays in Hindi."""
from __future__ import annotations

import html

from . import regional

PLANETS_L = {
    "te": ["సూర్యుడు", "చంద్రుడు", "కుజుడు", "బుధుడు", "గురువు", "శుక్రుడు", "శని", "రాహువు", "కేతువు"],
    "kn": ["ಸೂರ್ಯ", "ಚಂದ್ರ", "ಕುಜ", "ಬುಧ", "ಗುರು", "ಶುಕ್ರ", "ಶನಿ", "ರಾಹು", "ಕೇತು"],
    "mr": ["रवि", "चंद्र", "मंगळ", "बुध", "गुरु", "शुक्र", "शनि", "राहू", "केतू"],
    "gu": ["સૂર્ય", "ચંદ્ર", "મંગળ", "બુધ", "ગુરુ", "શુક્ર", "શનિ", "રાહુ", "કેતુ"],
    "bn": ["রবি", "চন্দ্র", "মঙ্গল", "বুধ", "বৃহস্পতি", "শুক্র", "শনি", "রাহু", "কেতু"],
    "ta": ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"],
    "ml": ["സൂര്യൻ", "ചന്ദ്രൻ", "ചൊവ്വ", "ബുധൻ", "വ്യാഴം", "ശുക്രൻ", "ശനി", "രാഹു", "കേതു"],
}
SHORT_L = {
    "te": ["సూ", "చం", "కు", "బు", "గు", "శు", "శ", "రా", "కే"], "kn": ["ಸೂ", "ಚಂ", "ಕು", "ಬು", "ಗು", "ಶು", "ಶ", "ರಾ", "ಕೇ"],
    "mr": ["र", "चं", "मं", "बु", "गु", "शु", "श", "रा", "के"], "gu": ["સૂ", "ચં", "મં", "બુ", "ગુ", "શુ", "શ", "રા", "કે"],
    "bn": ["র", "চ", "ম", "বু", "বৃ", "শু", "শ", "রা", "কে"], "ta": ["சூ", "சந்", "செவ்", "பு", "குரு", "சுக்", "சனி", "ரா", "கே"],
    "ml": ["സൂ", "ച", "കു", "ബു", "ഗു", "ശു", "ശ", "രാ", "കേ"],
}
ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# heading words: title, name, date, time, place, lagna, rashi, nakshatra, planets, planet, sign, degree, house,
# birth panchang, dasha, mahadasha, antardasha, pratyantar, till, retrograde, note
T = {
    "te": ["జన్మ పత్రిక", "పేరు", "తేదీ", "సమయం", "స్థలం", "లగ్నం", "రాశి", "నక్షత్రం", "గ్రహ స్థితి", "గ్రహం", "రాశి", "అంశ", "భావం",
           "జన్మ పంచాంగం", "నడుస్తున్న దశ", "మహాదశ", "అంతర్దశ", "ప్రత్యంతర", "వరకు", "వక్రి", "వివరణాత్మక నివేదిక హిందీలో తర్వాతి పేజీల్లో ఉంది."],
    "kn": ["ಜನ್ಮ ಪತ್ರಿಕೆ", "ಹೆಸರು", "ದಿನಾಂಕ", "ಸಮಯ", "ಸ್ಥಳ", "ಲಗ್ನ", "ರಾಶಿ", "ನಕ್ಷತ್ರ", "ಗ್ರಹ ಸ್ಥಿತಿ", "ಗ್ರಹ", "ರಾಶಿ", "ಅಂಶ", "ಭಾವ",
           "ಜನ್ಮ ಪಂಚಾಂಗ", "ನಡೆಯುತ್ತಿರುವ ದಶೆ", "ಮಹಾದಶೆ", "ಅಂತರ್ದಶೆ", "ಪ್ರತ್ಯಂತರ", "ವರೆಗೆ", "ವಕ್ರ", "ವಿವರವಾದ ವರದಿ ಮುಂದಿನ ಪುಟಗಳಲ್ಲಿ ಹಿಂದಿಯಲ್ಲಿದೆ."],
    "mr": ["जन्म पत्रिका", "नाव", "दिनांक", "वेळ", "ठिकाण", "लग्न", "रास", "नक्षत्र", "ग्रहस्थिती", "ग्रह", "रास", "अंश", "स्थान",
           "जन्म पंचांग", "चालू दशा", "महादशा", "अंतर्दशा", "प्रत्यंतर", "पर्यंत", "वक्री", "सविस्तर अहवाल पुढील पानांवर हिंदीत आहे."],
    "gu": ["જન્મ પત્રિકા", "નામ", "તારીખ", "સમય", "સ્થળ", "લગ્ન", "રાશિ", "નક્ષત્ર", "ગ્રહ સ્થિતિ", "ગ્રહ", "રાશિ", "અંશ", "ભાવ",
           "જન્મ પંચાંગ", "ચાલુ દશા", "મહાદશા", "અંતર્દશા", "પ્રત્યંતર", "સુધી", "વક્રી", "વિગતવાર અહેવાલ આગળનાં પાનાં પર હિન્દીમાં છે."],
    "bn": ["জন্ম পত্রিকা", "নাম", "তারিখ", "সময়", "স্থান", "লগ্ন", "রাশি", "নক্ষত্র", "গ্রহ অবস্থান", "গ্রহ", "রাশি", "অংশ", "ভাব",
           "জন্ম পঞ্জিকা", "চলমান দশা", "মহাদশা", "অন্তর্দশা", "প্রত্যন্তর", "পর্যন্ত", "বক্রী", "বিস্তারিত প্রতিবেদন পরের পাতাগুলিতে হিন্দিতে আছে।"],
    "ta": ["ஜாதகம்", "பெயர்", "தேதி", "நேரம்", "இடம்", "லக்னம்", "ராசி", "நட்சத்திரம்", "கிரக நிலை", "கிரகம்", "ராசி", "பாகை", "பாவம்",
           "பிறப்பு பஞ்சாங்கம்", "நடப்பு தசை", "மகாதசை", "புக்தி", "அந்தரம்", "வரை", "வக்ரம்", "விரிவான அறிக்கை அடுத்த பக்கங்களில் இந்தியில் உள்ளது."],
    "ml": ["ജാതകം", "പേര്", "തീയതി", "സമയം", "സ്ഥലം", "ലഗ്നം", "രാശി (കൂറ്)", "നക്ഷത്രം", "ഗ്രഹനില", "ഗ്രഹം", "രാശി", "ഡിഗ്രി", "ഭാവം",
           "ജനന പഞ്ചാംഗം", "നടപ്പുദശ", "മഹാദശ", "അപഹാരം", "ഛിദ്രം", "വരെ", "വക്രം", "വിശദമായ റിപ്പോർട്ട് അടുത്ത പേജുകളിൽ ഹിന്ദിയിൽ."],
}
LANGS = tuple(T)


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def page(chart: dict, lang: str, place: str = "") -> str:
    """One printable A4 page (a <section>) to put in front of the Hindi report."""
    L = T[lang]; P = dict(zip(ORDER, PLANETS_L[lang]))
    sg = regional.SIGNS_L[lang]; nk = regional.NAK_L[lang]; lab = regional.LABELS[lang]
    inp = chart["input"]; lg = chart["lagna"]; moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    nak_idx = lambda lon: int(lon // (360 / 27)) % 27
    pc = chart["panchang"]
    tithi_i = (pc["tithi"]["number"] - 1) % 15 if pc["tithi"]["number"] not in (15, 30) else (14 if pc["tithi"]["number"] == 15 else 15)
    paksha = regional.PAKSHA_L[lang][0 if pc["tithi"]["number"] <= 15 else 1]
    vara = regional.VARA_L[lang][pc["vara"]["index"]]
    yoga = regional.YOGA_L[lang][(pc["yoga"]["number"] - 1) % 27]
    kar = regional.KARANA_L[lang].get(pc["karana"]["name"], pc["karana"]["name"])
    info = [(L[1], inp.get("name") or "—"), (L[2], inp["date"]), (L[3], inp["time"]), (L[4], place or f'{inp["lat"]:.2f}, {inp["lon"]:.2f}'),
            (L[5], f'{sg[lg["sign"]]} {lg["dms"]}'), (L[6], sg[moon["sign"]]), (L[7], f'{nk[nak_idx(moon["longitude"])]} – {moon["pada"]}')]
    pan = [(lab["vara"], vara), (lab["tithi"], f"{paksha} {regional.TITHI_L[lang][tithi_i]}"), (lab["nakshatra"], nk[nak_idx(moon["longitude"])]),
           (lab["yoga"], yoga), (lab["karana"], kar)]
    rows = ""
    for p in sorted(chart["planets"], key=lambda x: ORDER.index(x["name"])):
        retro = f' <small>({L[19]})</small>' if p.get("retrograde") and p["name"] not in ("Rahu", "Ketu") else ""
        rows += (f'<tr><td><b>{e(P[p["name"]])}</b>{retro}</td><td>{e(sg[p["sign"]])}</td><td>{e(p["dms"])}</td>'
                 f'<td>{e(nk[nak_idx(p["longitude"])])} – {p["pada"]}</td><td>{p["house"]}</td></tr>')
    # north-style grid: lagna sign in the top diamond, houses counter-clockwise
    houses = {h: [] for h in range(1, 13)}
    for p in chart["planets"]:
        houses[p["house"]].append(SHORT_L[lang][ORDER.index(p["name"])])
    POS = {1: (150, 70), 2: (75, 30), 3: (30, 75), 4: (75, 150), 5: (30, 225), 6: (75, 270), 7: (150, 230), 8: (225, 270), 9: (270, 225), 10: (225, 150), 11: (270, 75), 12: (225, 30)}
    svg = ('<svg viewBox="0 0 300 300" width="280" height="280" style="font-family:inherit"><rect x="2" y="2" width="296" height="296" fill="none" stroke="#8a5a2b" stroke-width="2"/>'
           '<path d="M2 2L298 298M298 2L2 298M150 2L298 150L150 298L2 150Z" fill="none" stroke="#8a5a2b" stroke-width="1.5"/>')
    for h, (x, y) in POS.items():
        sign_no = (lg["sign"] + h - 1) % 12 + 1
        svg += f'<text x="{x}" y="{y - 14 if h in (1, 4, 7, 10) else y - 10}" text-anchor="middle" font-size="10" fill="#b05a1a">{sign_no}</text>'
        for k, nm in enumerate(houses[h][:4]):
            svg += f'<text x="{x}" y="{y + 4 + k * 13}" text-anchor="middle" font-size="11" font-weight="700" fill="#2a1d14">{e(nm)}</text>'
    svg += "</svg>"
    ds = chart.get("dasha_running") or []
    dasha = " › ".join(f'{e(L[15 + i])}: <b>{e(P.get(x["lord"], x["lord"]))}</b> ({e(x["end"][:10])} {e(L[18])})' for i, x in enumerate(ds[:3]))
    kv = lambda items: "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in items)
    return f"""<section class="regional" lang="{lang}" style="page-break-after:always;padding:6mm 2mm;font-family:'Noto Sans','Noto Sans Telugu','Noto Sans Kannada','Noto Sans Tamil','Noto Sans Malayalam','Noto Sans Bengali','Noto Sans Gujarati','Noto Sans Devanagari',sans-serif">
<h1 style="text-align:center;color:#8a3b12;margin:0 0 6px">🪔 {e(L[0])}</h1>
<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;justify-content:center">
<table class="kv" style="border-collapse:collapse;min-width:260px">{kv(info)}</table>{svg}</div>
<h3 style="color:#8a3b12;margin:14px 0 4px">{e(L[13])}</h3><table class="kv" style="border-collapse:collapse">{kv(pan)}</table>
<h3 style="color:#8a3b12;margin:14px 0 4px">{e(L[8])}</h3>
<table style="border-collapse:collapse;width:100%"><tr><th>{e(L[9])}</th><th>{e(L[10])}</th><th>{e(L[11])}</th><th>{e(L[7])}</th><th>{e(L[12])}</th></tr>{rows}</table>
<h3 style="color:#8a3b12;margin:14px 0 4px">{e(L[14])}</h3><p>{dasha}</p>
<p style="color:#7a6a5c;font-size:.85em">{e(L[20])}</p>
<style>.regional th,.regional td{{border:1px solid #ecdccb;padding:4px 8px;text-align:left}}.regional .kv th{{color:#7a6a5c;font-weight:600}}</style></section>"""


KOOTA_L = {
    "te": ["వర్ణ", "వశ్య", "తార", "యోని", "గ్రహ మైత్రి", "గణ", "భకూట", "నాడి"],
    "kn": ["ವರ್ಣ", "ವಶ್ಯ", "ತಾರಾ", "ಯೋನಿ", "ಗ್ರಹ ಮೈತ್ರಿ", "ಗಣ", "ಭಕೂಟ", "ನಾಡಿ"],
    "mr": ["वर्ण", "वश्य", "तारा", "योनी", "ग्रहमैत्री", "गण", "भकूट", "नाडी"],
    "gu": ["વર્ણ", "વશ્ય", "તારા", "યોનિ", "ગ્રહ મૈત્રી", "ગણ", "ભકૂટ", "નાડી"],
    "bn": ["বর্ণ", "বশ্য", "তারা", "যোনি", "গ্রহমৈত্রী", "গণ", "ভকূট", "নাড়ী"],
    "ta": ["வர்ணம்", "வசியம்", "தாரா", "யோனி", "கிரக மைத்ரி", "கணம்", "பகூட் (ராசி)", "நாடி"],
    "ml": ["വർണം", "വശ്യം", "താര", "യോനി", "ഗ്രഹമൈത്രി", "ഗണം", "ഭകൂടം", "നാഡി"],
}
KOOTA_ORDER = ["Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana", "Bhakoot", "Nadi"]
# title, groom, bride, koota, got, max, total, manglik dosha, yes, no, after parihara
MT = {
    "te": ["వివాహ పొంతన (గుణ మేళనం)", "వరుడు", "వధువు", "కూటం", "పొందినవి", "గరిష్ఠం", "మొత్తం గుణాలు", "కుజ దోషం", "ఉంది", "లేదు", "పరిహారం తర్వాత"],
    "kn": ["ವಿವಾಹ ಹೊಂದಾಣಿಕೆ (ಗುಣ ಮಿಲನ)", "ವರ", "ವಧು", "ಕೂಟ", "ಪಡೆದದ್ದು", "ಗರಿಷ್ಠ", "ಒಟ್ಟು ಗುಣಗಳು", "ಕುಜ ದೋಷ", "ಇದೆ", "ಇಲ್ಲ", "ಪರಿಹಾರದ ನಂತರ"],
    "mr": ["कुंडली जुळवणी (गुण मिलन)", "वर", "वधू", "कूट", "मिळालेले", "कमाल", "एकूण गुण", "मंगळ दोष", "आहे", "नाही", "परिहारानंतर"],
    "gu": ["કુંડળી મિલાન (ગુણ મિલન)", "વર", "કન્યા", "કૂટ", "મળેલા", "મહત્તમ", "કુલ ગુણ", "મંગળ દોષ", "છે", "નથી", "પરિહાર પછી"],
    "bn": ["কোষ্ঠী মিলন (গুণ মিলন)", "বর", "কনে", "কূট", "প্রাপ্ত", "সর্বোচ্চ", "মোট গুণ", "মঙ্গল দোষ", "আছে", "নেই", "পরিহারের পরে"],
    "ta": ["திருமணப் பொருத்தம் (குண மிலன்)", "மணமகன்", "மணமகள்", "பொருத்தம்", "பெற்றது", "அதிகபட்சம்", "மொத்த குணங்கள்", "செவ்வாய் தோஷம்", "உண்டு", "இல்லை", "பரிகாரத்திற்குப் பின்"],
    "ml": ["വിവാഹ പൊരുത്തം (ഗുണ മേളനം)", "വരൻ", "വധു", "കൂടം", "ലഭിച്ചത്", "പരമാവധി", "ആകെ ഗുണങ്ങൾ", "ചൊവ്വാദോഷം", "ഉണ്ട്", "ഇല്ല", "പരിഹാരത്തിനു ശേഷം"],
}


def match_page(m: dict, lang: str) -> str:
    """One regional page (Ashtakoota table, both people, Mangal dosha) in front of the Hindi matching report."""
    from .constants import NAKSHATRAS, SIGNS
    M = MT[lang]; K = dict(zip(KOOTA_ORDER, KOOTA_L[lang])); sg = regional.SIGNS_L[lang]; nk = regional.NAK_L[lang]
    def person(key, chart_key, name, label, mg):
        p = m[key]
        si = SIGNS.index(p["moon_sign"]) if p["moon_sign"] in SIGNS else 0
        ni = NAKSHATRAS.index(p["nakshatra"]) if p["nakshatra"] in NAKSHATRAS else 0
        lagna = (m.get(chart_key) or {}).get("lagna") or {}
        has = bool(mg and (mg.get("from_lagna") or mg.get("from_moon")))
        rows = [(T[lang][1], name or "—"), (T[lang][5], sg[lagna["sign"]] if "sign" in lagna else "—"), (T[lang][6], sg[si]),
                (T[lang][7], f"{nk[ni]} – {p['pada']}"), (M[7], M[8] if has else M[9])]
        return (f'<div style="flex:1;min-width:230px"><h3 style="color:#8a3b12;margin:0 0 4px">{e(label)}</h3><table class="kv" style="border-collapse:collapse;width:100%">'
                + "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in rows) + "</table></div>")
    mg = m.get("manglik") or {}
    rows = "".join(f'<tr><td><b>{e(K.get(k["name"], k["name"]))}</b></td><td>{k["score"]:g}</td><td>{k["max"]:g}</td>'
                   f'<td><div style="background:#f3e7d8;border-radius:6px;height:10px;width:120px"><div style="background:{"#2e9d5b" if k["score"] >= k["max"] / 2 else "#e0533d"};height:10px;border-radius:6px;width:{120 * k["score"] / k["max"]:.0f}px"></div></div></td></tr>'
                   for k in m["kootas"])
    total = f'{m["total"]:g} / {m["max"]:g}'
    par = f' · {e(M[10])}: <b>{m["total_with_parihara"]:g}</b>' if m.get("total_with_parihara") not in (None, m["total"]) else ""
    return f"""<section class="regional" lang="{lang}" style="page-break-after:always;padding:6mm 2mm;font-family:'Noto Sans','Noto Sans Telugu','Noto Sans Kannada','Noto Sans Tamil','Noto Sans Malayalam','Noto Sans Bengali','Noto Sans Gujarati','Noto Sans Devanagari',sans-serif">
<h1 style="text-align:center;color:#8a3b12;margin:0 0 10px">💍 {e(M[0])}</h1>
<div style="display:flex;gap:16px;flex-wrap:wrap">{person("groom", "boy_chart", m.get("boy_name"), M[1], mg.get("boy"))}{person("bride", "girl_chart", m.get("girl_name"), M[2], mg.get("girl"))}</div>
<h3 style="color:#8a3b12;margin:16px 0 4px">{e(M[3])}</h3>
<table style="border-collapse:collapse;width:100%"><tr><th>{e(M[3])}</th><th>{e(M[4])}</th><th>{e(M[5])}</th><th></th></tr>{rows}</table>
<p style="font-size:1.3em;margin:14px 0 4px">{e(M[6])}: <b style="color:#8a3b12">{total}</b>{par}</p>
<p style="color:#7a6a5c;font-size:.85em">{e(T[lang][20])}</p>
<style>.regional th,.regional td{{border:1px solid #ecdccb;padding:4px 8px;text-align:left}}.regional .kv th{{color:#7a6a5c;font-weight:600}}</style></section>"""
