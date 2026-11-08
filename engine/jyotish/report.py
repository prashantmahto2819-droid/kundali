"""Printable Hindi kundali report: one self-contained HTML page (inline SVG, print CSS).

Open it in a browser and print to PDF, or run tools/make_pdf.py (Chromium) to write a PDF.
Chromium is used for PDF because it shapes Devanagari conjuncts correctly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape as _e

from . import ENGINE_VERSION
from .constants import PLANETS_HI, SIGNS_HI

DIGNITY_HI = {"exalted": "उच्च", "debilitated": "नीच", "own": "स्वराशि"}
BAND_HI = {"strong": "मज़बूत", "medium": "मध्यम", "weak": "कमज़ोर"}
VERDICT_HI = {"supportive": "सहायक", "mixed": "मिश्रित", "challenging": "कठिन"}
LEVEL_HI = {1: "महादशा", 2: "अंतर्दशा", 3: "प्रत्यंतर"}

# North-Indian chart geometry: house -> (polygon points, label centre)
_HOUSES = {
    1: ([(200, 200), (100, 100), (200, 0), (300, 100)], (200, 92)),
    2: ([(0, 0), (200, 0), (100, 100)], (100, 38)),
    3: ([(0, 0), (100, 100), (0, 200)], (38, 100)),
    4: ([(100, 100), (0, 200), (100, 300), (200, 200)], (98, 200)),
    5: ([(0, 200), (100, 300), (0, 400)], (38, 300)),
    6: ([(0, 400), (100, 300), (200, 400)], (100, 362)),
    7: ([(200, 200), (100, 300), (200, 400), (300, 300)], (200, 308)),
    8: ([(200, 400), (300, 300), (400, 400)], (300, 362)),
    9: ([(400, 400), (300, 300), (400, 200)], (362, 300)),
    10: ([(200, 200), (300, 300), (400, 200), (300, 100)], (302, 200)),
    11: ([(400, 200), (300, 100), (400, 0)], (362, 100)),
    12: ([(400, 0), (300, 100), (200, 0)], (300, 38)),
}


def e(x) -> str:
    return _e(str(x if x is not None else ""))


def north_chart_svg(cells: list[dict]) -> str:
    """cells: 12 dicts {sign:int, planets:[(short_hi, retro)]} in house order."""
    out = ['<svg viewBox="-4 -4 408 408" class="chart" xmlns="http://www.w3.org/2000/svg">']
    for h in range(1, 13):
        pts, (cx, cy) = _HOUSES[h]
        cell = cells[h - 1]
        out.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="#7a5c2e" stroke-width="1.6"/>')
        out.append(f'<text x="{cx}" y="{cy - 14}" text-anchor="middle" font-size="12" fill="#8a7a64">{cell["sign"] + 1}</text>')
        pl = cell["planets"]
        for i, (short, retro) in enumerate(pl):
            col, row = i % 3, i // 3
            n = min(3, len(pl) - row * 3)
            x = cx + (col - (n - 1) / 2) * 24
            y = cy + 6 + row * 18
            mark = '<tspan font-size="9" dy="-6">v</tspan>' if retro else ""
            out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="15" font-weight="600" fill="#2b2118">{e(short)}{mark}</text>')
    out.append("</svg>")
    return "".join(out)


def _d1_cells(chart: dict) -> list[dict]:
    pm = {p["name"]: p for p in chart["planets"]}
    return [{"sign": h["sign"], "planets": [(pm[n]["short_hi"], pm[n]["retrograde"]) for n in h["planets"]]}
            for h in chart["houses"]]


def _varga_cells(chart: dict, key: str) -> list[dict]:
    pm = {p["name"]: p for p in chart["planets"]}
    return [{"sign": h["sign"], "planets": [(pm[n]["short_hi"], False) for n in h["planets"]]}
            for h in chart["vargas"][key]["houses"]]


def _d(s: str) -> str:
    return s[:10]


def _table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def render(chart: dict, brand: dict | None = None) -> str:
    inp, lg = chart["input"], chart["lagna"]
    pm = {p["name"]: p for p in chart["planets"]}
    moon = pm["Moon"]
    name = inp.get("name") or "जातक"
    run = chart["dasha_running"]
    go, av = chart["gochara"], chart["ashtakavarga"]
    pc = chart["panchang"]
    dev = not chart["backend"].startswith("jpl")

    planets_rows = [[e(p["name_hi"]) + (" (व)" if p["retrograde"] else ""), e(p["sign_name_hi"]), e(p["dms"]),
                     str(p["house"]), f'{e(p["nakshatra_hi"])} ({p["pada"]})',
                     e(DIGNITY_HI.get(p["dignity"], ""))] for p in chart["planets"]]
    dasha_run = " · ".join(f'{LEVEL_HI.get(r["level"], "")} {e(PLANETS_HI[r["lord"]])} ({_d(r["start"])} → {_d(r["end"])})'
                           for r in run)
    maha_rows = [[e(PLANETS_HI[m["lord"]]), _d(m["start"]), _d(m["end"])] for m in chart["dasha"]["mahadashas"]]
    sav = av["sav"]
    sav_head = ["भाव"] + [str(i + 1) for i in range(12)] + ["कुल"]
    sav_rows = [["राशि"] + [e(SIGNS_HI[(lg["sign"] + h) % 12]) for h in range(12)] + [""],
                ["SAV"] + [f"<b>{v}</b>" for v in sav["by_house"]] + [f'<b>{sav["total"]}</b>'],
                ["स्तर"] + [e(BAND_HI[b]) for b in sav["bands"]] + [""]]
    bav_rows = [[e(PLANETS_HI[pl])] + [str(v) for v in r["by_house"]] + [f'<b>{r["total"]}</b>']
                for pl, r in av["bav"].items()]
    go_rows = [[e(r["name_hi"]) + (" (व)" if r["retrograde"] else ""),
                f'{e(r["sign_name_hi"])} {int(r["degree_in_sign"])}°', str(r["house_from_moon"]),
                str(r["house_from_lagna"]), str(r.get("bindus", "–")),
                e(VERDICT_HI.get(r.get("verdict"), "–"))] for r in go["planets"]]
    strength_rows = [[e(r["name_hi"]), str(r["sthana"]), str(r["dig"]), str(r["kala"]), str(r["cheshta"]), str(r["drik"]),
                      str(r["naisargika"]), f'<b>{r["total"]}</b>', str(r["rupas"]), str(r["rank"]), str(r["ishta"]), str(r["kashta"])] for r in chart["strength"]["planets"]]
    timeline_rows = [[e(m["lord_hi"]) + (" ◀ अभी" if m["phase"] == "running" else ""),
                      f'{m["age_start"]}–{m["age_end"]}', f'{m["start"][:4]}–{m["end"][:4]}', e(m["profile"]["tag_hi"]),
                      e("; ".join(f'{t["house"]}वाँ: {", ".join(t["themes_hi"][:2])}' for t in m["profile"]["themes"]))]
                     for m in chart["timeline"]["periods"]]
    ss = go["sade_sati"]
    sade = ("साढ़ेसाती चल रही है (" + {"rising": "पहला", "peak": "मध्य", "setting": "अंतिम"}[ss["phase"]] + " चरण)."
            if ss["active"] else ("अष्टम शनि चल रहा है." if ss["ashtama"] else "अभी साढ़ेसाती नहीं है."))
    yoga_rows = [[e(y["name_hi"]), "बना है" if y["present"] else "नहीं", e(y["why_hi"])] for y in chart["yogas"]]
    rl = chart["relations"]
    rel_items = [f'<li><b>{e(x["planet_hi"])}</b> ({e(x["sign_hi"])}): {e(x["text_hi"])}'
                 + ("".join(f'<br><span class="small">• {e(c["text_hi"])}</span>' for c in x["conditions"])) + "</li>"
                 for x in rl["neecha_bhanga"]]
    rel_items += [f'<li>{e(" + ".join(x["planets_hi"]))} युति ({e(x["sign_hi"])}, {x["house"]}वाँ भाव), अंतर {x["orb"]}°'
                  + (" — बहुत पास" if x["close"] else "") + "</li>" for x in rl["conjunctions"]]
    rel_items += [f'<li>{e(x["text_hi"])}</li>' for x in rl["combustion"]]
    rel_html = "<ul>" + "".join(rel_items) + "</ul>" if rel_items else "<p>कोई नीच ग्रह, निकट युति या अस्त ग्रह नहीं मिला।</p>"
    asp_rows = [[e(r["from_hi"]), f'{r["from_house"]}', f'{r["aspect"]}वीं', f'{r["to_house"]}',
                 e(", ".join(r["on_hi"]) or "–")] for r in rl["aspects"]["planets"]]
    lk_rows = [[e(r["name_hi"]), str(r["views"]["lagna"]["house"]), str(r["views"]["aries"]["house"]), str(r["pakka_ghar"]),
                e(r["views"]["lagna"]["text_hi"]), e(r["upay_hi"])] for r in chart["lalkitab"]["planets"]]
    P = chart.get("patri")
    patri_html = ""
    if P:
        b, a = P["birth"], P["avakahada"]
        birth_rows = [["वार", e(b["vara"]["name_hi"])], ["तिथि", f'{e(b["tithi"]["paksha_hi"])} {e(b["tithi"]["name_hi"])}'],
                      ["नक्षत्र-चरण", f'{e(b["nakshatra"]["name_hi"])}-{b["nakshatra"]["pada"]} (स्वामी {e(b["nakshatra"]["lord_hi"])})'],
                      ["योग", e(b["yoga"]["name_hi"])], ["करण", e(b["karana"]["name_hi"])],
                      ["सूर्योदय / सूर्यास्त", f'{e(b["sunrise"] or "—")} ({e(b.get("sunrise_centre") or "")}) / {e(b["sunset"] or "—")} ({e(b.get("sunset_centre") or "")})'],
                      ["इष्टकाल (घटी:पल)", e(b["ishta_kaal"]["text"]) if b["ishta_kaal"] else "—"],
                      ["मास (अमांत / पूर्णिमांत)", f'{e(b["masa"]["name_hi"])} / {e(b["masa"].get("purnimanta_hi", ""))}'], ["ऋतु", e(b["ritu"]["name_hi"])], ["अयन", e(b["ayana"]["name_hi"])],
                      ["विक्रम संवत्", str(b["vikram_samvat"])], ["शक संवत्", str(b["shaka_samvat"])],
                      ["सूर्य राशि (पाश्चात्य)", e(b["sun_sign_tropical"]["name_hi"])], ["अयनांश (लाहिरी)", e(b["ayanamsa"])]]
        ava_rows = [["लग्न-लग्नेश", f'{e(a["lagna"]["name_hi"])}-{e(a["lagna"]["lord_hi"])}'],
                    ["राशि-राशि स्वामी", f'{e(a["rashi"]["name_hi"])}-{e(a["rashi"]["lord_hi"])}'],
                    ["नक्षत्र स्वामी", e(a["nakshatra_lord"]["name_hi"])], ["वर्ण", e(a["varna"]["name_hi"])],
                    ["वश्य", e(a["vashya"]["name_hi"])], ["योनि", e(a["yoni"]["name_hi"])], ["गण", e(a["gana"]["name_hi"])],
                    ["नाड़ी", e(a["nadi"]["name_hi"])], ["तत्व", e(a["tattva"]["name_hi"])],
                    ["नाम अक्षर", f'<b>{e(a["name_syllable"]["pada"])}</b> ({e(a["name_syllable"]["all"])})']]
        g = P.get("ghata")
        if g:
            ava_rows += [["<b>घात चक्र</b> (ड्राफ़्ट)", ""], ["घात मास", e(g["masa_hi"])], ["घात तिथि", e(g["tithi"])], ["घात वार", e(g["vara_hi"])],
                         ["घात नक्षत्र", e(g["nakshatra_hi"])], ["घात योग", e(g["yoga_hi"])], ["घात करण", e(g["karana_hi"])],
                         ["घात प्रहर", str(g["prahar"])], ["घात चंद्र", e(g["chandra_hi"])], ["स्त्री घात चंद्र", e(g["stri_chandra_hi"])]]
        patri_html = (f'<h2>जन्म विवरण</h2><div class="two">{_table(["", ""], birth_rows)}{_table(["", ""], ava_rows)}</div>'
                      f'<p class="small">{e(P["note_hi"])}</p>')
    K = chart.get("kp")
    kp_html = ""
    if K:
        H = lambda n: PLANETS_HI.get(n, n)
        dm = lambda d: f"{int(d)}°{int(round((d % 1) * 60)):02d}′"
        kc = [[str(x["house"]), e(x["sign_name_hi"]), dm(x["degree_in_sign"]), e(H(x["sign_lord"])), e(H(x["star_lord"])), f'<b>{e(H(x["sub_lord"]))}</b>', e(H(x["sub_sub_lord"]))] for x in K["cusps"]]
        kpl = [[e(v["name_hi"]) + (" (व)" if v["retrograde"] else ""), e(v["sign_name_hi"]), dm(v["degree_in_sign"]), str(v["house"]), e(H(v["star_lord"])), f'<b>{e(H(v["sub_lord"]))}</b>', e(H(v["sub_sub_lord"]))] for v in K["planets"].values()]
        kp_html = (f'<h2>कृष्णमूर्ति पद्धति (KP)</h2>{_table(["भाव-स्पष्ट", "राशि", "अंश", "राशि-स्वामी", "नक्षत्र-स्वामी", "उप-स्वामी", "उप-उप"], kc)}'
                   f'{_table(["ग्रह", "राशि", "अंश", "भाव (KP)", "नक्षत्र-स्वामी", "उप-स्वामी", "उप-उप"], kpl)}<p class="small">{e(K["note_hi"])}</p>')
    J = chart.get("jaimini")
    jm_html = ""
    if J:
        kr = [[e(k["karaka_hi"]), f'<b>{e(k["planet_hi"])}</b>', f'{k["degree_in_sign"]}°', e(k["signifies_hi"])] for k in J["chara_karakas"]["scheme7"]]
        pd = [[e(p["name_hi"]), str(p["house"]), e(p["pada_sign_name_hi"]) + (" (अपवाद)" if p["exception_applied"] else ""), str(p["pada_house"])] for p in J["arudha_padas"]]
        cd = J.get("chara_dasha")
        cd_html = ""
        if cd:
            rows = [[e(p["sign_name_hi"]), str(p["years"]), e(p["start"]), e(p["end"])] for p in cd["periods"]]
            run = cd.get("running")
            cd_html = (f'<h3>चर दशा</h3>' + (f'<p>अभी: <b>{e(run["sign_name_hi"])}</b> ({e(run["start"])} → {e(run["end"])})</p>' if run else "")
                       + _table(["राशि", "वर्ष", "आरंभ", "समाप्ति"], rows) + f'<p class="small">{e(cd["note_hi"])}</p>')
        jm_html = (f'<h2>जैमिनी: चर कारक और आरूढ़ पद</h2>{_table(["कारक", "ग्रह", "अंश", "विषय"], kr)}'
                   f'<p>कारकांश: <b>{e(J["karakamsa"]["sign_name_hi"])}</b></p>{_table(["पद", "भाव", "पद की राशि", "लग्न से भाव"], pd)}<p class="small">{e(J["note_hi"])}</p>{cd_html}')
    LT = chart.get("life_transits")
    lt_html = ""
    if LT:
        ST = {"past": "बीत चुकी", "running": "चल रही", "future": "आगामी"}
        rows = [[f'{e(w["start"])} → {e(w["end"])}', ST[w["status"]], e(" · ".join(f'{p["phase_hi"]}: {p["start"]}–{p["end"]}' for p in w["phases"]))] for w in LT["sade_sati_windows"]]
        ash = ", ".join(f'{a["start"]}–{a["end"]}' for a in LT["ashtama_shani"]) or "—"
        lt_html = (f'<h2>जीवन भर के शनि गोचर</h2>{_table(["साढ़ेसाती", "स्थिति", "चरण"], rows)}<p>अष्टम शनि: {e(ash)}</p><p class="small">{e(LT["note_hi"])}</p>')
    S, T = chart.get("sensitivity"), chart.get("transit_calendar")
    sens_html = tc_html = ""
    if S:
        f = lambda v: "—" if v is None else f"{v} मिनट"
        sens_rows = [[e(v["label_hi"]), f(v["minutes_earlier"]), f(v["minutes_later"]),
                      "स्थिर" if v["stable_within_15_min"] else ("सावधान" if v["stable_within_5_min"] else "संवेदनशील")] for v in S["items"].values()]
        sens_html = f'<h2>जन्म-समय की संवेदनशीलता</h2>{_table(["", "पहले", "बाद", "स्थिति"], sens_rows)}<p class="small">{e(S["note_hi"])}</p>'
    if T:
        ing = "".join(f'<li><b>{e(g["date"])}</b>: {e(g["planet_hi"])} {e(g["from_sign_hi"])} → <b>{e(g["to_sign_hi"])}</b> (चंद्र से {g["house_from_moon"]}, लग्न से {g["house_from_lagna"]})</li>' for g in T["ingress"])
        tc_html = f'<h2>आगामी 12 महीनों का गोचर</h2><ul>{ing or "<li>धीमे ग्रहों का कोई राशि-प्रवेश नहीं।</li>"}</ul><p class="small">{e(T["note_hi"])}</p>'
    ch = chart.get("chalit")
    chalit_html = ""
    if ch:
        mv = "".join(f'<li>{e(m["planet_hi"])}: राशि-भाव {m["rasi_house"]} → चलित भाव {m["chalit_house"]}</li>' for m in ch["moved"]) or "<li>सभी ग्रह राशि-भाव वाले भाव में ही हैं।</li>"
        chalit_html = (f'<h2>भाव-चलित (श्रीपति)</h2><p>दशम भाव-मध्य (MC): <b>{e(ch["mc_sign_name_hi"])} {e(ch["mc_dms"])}</b></p><ul>{mv}</ul>'
                       f'<p class="small">{e(ch["note_hi"])}</p>')
    day = chart.get("day", {})
    day_html = ""
    if day.get("available"):
        day_html = (f'<p>सूर्योदय {e(day["sunrise"][11:16])} · सूर्यास्त {e(day["sunset"][11:16])} (स्थानीय समय)।</p>')
    warn_html = "".join(f'<div class="banner" style="background:#fdecea;border-color:#e0a09a">⚠ {e(w["text_hi"])}</div>' for w in chart.get("input_warnings", []))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    brand_html = ""
    if brand and brand.get("brand_name"):
        bits = [e(brand["brand_name"])] + [e(brand[k]) for k in ("phone", "website", "address") if brand.get(k)]
        brand_html = (f'<div class="brand"><b>{bits[0]}</b>' + "".join(f" · {b}" for b in bits[1:]) + "</div>"
                      + (f'<div class="small">{e(brand["line"])}</div>' if brand.get("line") else ""))
    caution = ("यह विकास-संस्करण की गणना है; ग्रह-स्थिति में कुछ कला तक अंतर संभव है और सटीकता का सत्यापन बाकी है। "
               if dev else "") + "सभी व्याख्याएँ ‘ड्राफ़्ट’ हैं और विद्वान-समीक्षा के अधीन हैं।"

    return f"""<!doctype html><html lang="hi"><head><meta charset="utf-8">
<title>कुंडली रिपोर्ट — {e(name)}</title>
<style>
@page {{ size: A4; margin: 14mm; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }} .two table th {{ width:45%; }}
body {{ font-family: 'Noto Sans Devanagari','Noto Serif Devanagari','FreeSans','Mangal',sans-serif; color:#2b2118; font-size:12.5px; line-height:1.55; }}
h1 {{ font-size:22px; margin:0 0 2px; color:#7a4a12; }} h2 {{ font-size:15px; margin:18px 0 6px; color:#7a4a12; border-bottom:1px solid #d8c8a8; padding-bottom:2px; page-break-after:avoid; }}
.meta {{ color:#6b5a44; }} .banner {{ background:#fff4d6; border:1px solid #e3c878; padding:6px 10px; border-radius:6px; margin:10px 0; font-size:11.5px; }}
table {{ border-collapse:collapse; width:100%; margin:6px 0; page-break-inside:avoid; }} th,td {{ border:1px solid #d8c8a8; padding:3px 6px; text-align:center; }}
th {{ background:#f6ecd6; }} td:first-child {{ text-align:left; }}
.charts {{ display:flex; gap:14px; }} .charts > div {{ flex:1; text-align:center; }} svg.chart {{ width:100%; max-width:330px; }}
.small {{ font-size:11px; color:#6b5a44; }} .brand {{ font-size:14px; color:#7a4a12; border-bottom:2px solid #d8c8a8; padding-bottom:4px; margin-bottom:6px; }} .sum td {{ text-align:left; }}
</style></head><body>
{brand_html}
<h1>कुंडली रिपोर्ट</h1>
<div class="meta"><b>{e(name)}</b> · जन्म: {e(inp["date"])} {e(inp["time"])} ({e(inp["tz"])}) · अक्षांश {inp["lat"]}, देशांतर {inp["lon"]} · अयनांश: लाहिड़ी {e(chart["ayanamsa_dms"])}</div>
<div class="banner">{e(caution)}</div>
{warn_html}

<h2>सारांश</h2>
<table class="sum">
<tr><td>लग्न</td><td>{e(lg["sign_name_hi"])} {e(lg["dms"])} · {e(lg["nakshatra_hi"])} पाद {lg["pada"]} · स्वामी {e(PLANETS_HI[lg["lord"]])}</td></tr>
<tr><td>चंद्र राशि / नक्षत्र</td><td>{e(moon["sign_name_hi"])} · {e(moon["nakshatra_hi"])} पाद {moon["pada"]}</td></tr>
<tr><td>चल रही दशा</td><td>{dasha_run}</td></tr>
<tr><td>साढ़ेसाती</td><td>{e(sade)}</td></tr>
</table>

{patri_html}
<h2>कुंडलियाँ</h2>
<div class="charts"><div><b>लग्न कुंडली (D1)</b>{north_chart_svg(_d1_cells(chart))}</div>
<div><b>नवांश (D9)</b>{north_chart_svg(_varga_cells(chart, "D9"))}</div></div>
<div class="small">खानों में अंक राशि-संख्या हैं (1 = मेष)। ‘v’ = वक्री।</div>

<h2>ग्रह स्थिति</h2>
{_table(["ग्रह", "राशि", "अंश", "भाव", "नक्षत्र (पाद)", "स्थिति"], planets_rows)}

{chalit_html}
{sens_html}
<h2>पंचांग</h2>
<table class="sum">
<tr><td>वार</td><td>{e(pc["vara"]["name_hi"])}</td></tr>
<tr><td>तिथि</td><td>{e(pc["tithi"]["paksha_hi"])} {e(pc["tithi"]["name_hi"])} ({pc["tithi"]["number"]})</td></tr>
<tr><td>नक्षत्र</td><td>{e(pc["nakshatra"]["name_hi"])} पाद {pc["nakshatra"]["pada"]}</td></tr>
<tr><td>योग / करण</td><td>{e(pc["yoga"]["name_hi"])} / {e(pc["karana"]["name_hi"])}</td></tr>
</table>{day_html}

{tc_html}
{lt_html}
{kp_html}
{jm_html}
<h2>विंशोत्तरी दशा</h2>
<p>जन्म के समय {e(PLANETS_HI[chart["dasha"]["birth_nakshatra_lord"]])} की दशा शेष: {chart["dasha"]["balance_at_birth_years"]:.2f} वर्ष (वर्ष = {chart["dasha"]["year_days"]} दिन)।</p>
{_table(["महादशा", "आरंभ", "समाप्ति"], maha_rows)}

<h2>जीवन समय-रेखा</h2>
<p class="small">{e(chart["timeline"]["note_hi"])}</p>
{_table(["महादशा", "आयु", "वर्ष", "बल-संकेत", "सक्रिय क्षेत्र"], timeline_rows)}

<h2>अष्टकवर्ग</h2>
<p class="small">{e(av["why_hi"])}</p>
{_table(sav_head, sav_rows)}
{_table(["ग्रह"] + [str(i + 1) for i in range(12)] + ["कुल"], bav_rows)}

<h2>ग्रह-बल (षड्बल)</h2>
<p class="small">{e(chart["strength"]["missing_hi"])}</p>
{_table(["ग्रह", "स्थान", "दिक्", "काल", "चेष्टा", "दृग्", "नैसर्गिक", "कुल", "रूप", "क्रम", "इष्ट", "कष्ट"], strength_rows)}

<h2>गोचर ({e(go["as_of"][:10])})</h2>
<p class="small">{e(go["why_hi"])}</p>
{_table(["ग्रह", "राशि", "चंद्र से भाव", "लग्न से भाव", "बिंदु", "संकेत"], go_rows)}
<p><b>गोचर-फल (ड्राफ़्ट)</b></p><ul>{"".join(f'<li>{e(r["text_hi"])}</li>' for r in go["planets"] if r.get("text_hi"))}</ul>

<h2>ग्रह-संबंध: नीच-भंग, युति, अस्त, दृष्टि</h2>
<p class="small">{e(rl["neecha_bhanga"][0]["why_hi"]) if rl["neecha_bhanga"] else ""}</p>
{rel_html}
<p class="small">{e(rl["aspects"]["why_hi"])}</p>
{_table(["ग्रह", "स्थित भाव", "दृष्टि", "देखा गया भाव", "उस भाव में ग्रह"], asp_rows)}

<h2>लाल किताब (ड्राफ़्ट)</h2>
<p class="small">{e(chart["lalkitab"]["views_note_hi"])}</p>
{_table(["ग्रह", "घर (लग्न)", "घर (मेष)", "पक्का घर", "संकेत", "परंपरागत उपाय"], lk_rows)}
<p class="small">{e(chart["lalkitab"]["disclaimer_hi"])}</p>

<h2>योग और दोष</h2>
{_table(["योग", "स्थिति", "कारण"], yoga_rows)}

<p class="small" style="margin-top:18px">इंजन संस्करण {e(ENGINE_VERSION)} · बैकएंड: {e(chart["backend"])} · बनाया गया: {e(generated)}।
यह रिपोर्ट शिक्षा और मार्गदर्शन के लिए है; स्वास्थ्य, धन या क़ानून के फ़ैसले विशेषज्ञ की सलाह से लें।</p>
</body></html>"""
