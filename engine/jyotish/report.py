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


def render(chart: dict) -> str:
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
    ss = go["sade_sati"]
    sade = ("साढ़ेसाती चल रही है (" + {"rising": "पहला", "peak": "मध्य", "setting": "अंतिम"}[ss["phase"]] + " चरण)."
            if ss["active"] else ("अष्टम शनि चल रहा है." if ss["ashtama"] else "अभी साढ़ेसाती नहीं है."))
    yoga_rows = [[e(y["name_hi"]), "बना है" if y["present"] else "नहीं", e(y["why"])] for y in chart["yogas"]]
    day = chart.get("day", {})
    day_html = ""
    if day.get("available"):
        day_html = (f'<p>सूर्योदय {e(day["sunrise"][11:16])} · सूर्यास्त {e(day["sunset"][11:16])} (स्थानीय समय)।</p>')
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    caution = ("यह विकास-संस्करण की गणना है; ग्रह-स्थिति में कुछ कला तक अंतर संभव है और सटीकता का सत्यापन बाकी है। "
               if dev else "") + "सभी व्याख्याएँ ‘ड्राफ़्ट’ हैं और विद्वान-समीक्षा के अधीन हैं।"

    return f"""<!doctype html><html lang="hi"><head><meta charset="utf-8">
<title>कुंडली रिपोर्ट — {e(name)}</title>
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ font-family: 'Noto Sans Devanagari','Noto Serif Devanagari','FreeSans','Mangal',sans-serif; color:#2b2118; font-size:12.5px; line-height:1.55; }}
h1 {{ font-size:22px; margin:0 0 2px; color:#7a4a12; }} h2 {{ font-size:15px; margin:18px 0 6px; color:#7a4a12; border-bottom:1px solid #d8c8a8; padding-bottom:2px; page-break-after:avoid; }}
.meta {{ color:#6b5a44; }} .banner {{ background:#fff4d6; border:1px solid #e3c878; padding:6px 10px; border-radius:6px; margin:10px 0; font-size:11.5px; }}
table {{ border-collapse:collapse; width:100%; margin:6px 0; page-break-inside:avoid; }} th,td {{ border:1px solid #d8c8a8; padding:3px 6px; text-align:center; }}
th {{ background:#f6ecd6; }} td:first-child {{ text-align:left; }}
.charts {{ display:flex; gap:14px; }} .charts > div {{ flex:1; text-align:center; }} svg.chart {{ width:100%; max-width:330px; }}
.small {{ font-size:11px; color:#6b5a44; }} .sum td {{ text-align:left; }}
</style></head><body>
<h1>कुंडली रिपोर्ट</h1>
<div class="meta"><b>{e(name)}</b> · जन्म: {e(inp["date"])} {e(inp["time"])} ({e(inp["tz"])}) · अक्षांश {inp["lat"]}, देशांतर {inp["lon"]} · अयनांश: लाहिड़ी {e(chart["ayanamsa_dms"])}</div>
<div class="banner">{e(caution)}</div>

<h2>सारांश</h2>
<table class="sum">
<tr><td>लग्न</td><td>{e(lg["sign_name_hi"])} {e(lg["dms"])} · {e(lg["nakshatra_hi"])} पाद {lg["pada"]} · स्वामी {e(PLANETS_HI[lg["lord"]])}</td></tr>
<tr><td>चंद्र राशि / नक्षत्र</td><td>{e(moon["sign_name_hi"])} · {e(moon["nakshatra_hi"])} पाद {moon["pada"]}</td></tr>
<tr><td>चल रही दशा</td><td>{dasha_run}</td></tr>
<tr><td>साढ़ेसाती</td><td>{e(sade)}</td></tr>
</table>

<h2>कुंडलियाँ</h2>
<div class="charts"><div><b>लग्न कुंडली (D1)</b>{north_chart_svg(_d1_cells(chart))}</div>
<div><b>नवांश (D9)</b>{north_chart_svg(_varga_cells(chart, "D9"))}</div></div>
<div class="small">खानों में अंक राशि-संख्या हैं (1 = मेष)। ‘v’ = वक्री।</div>

<h2>ग्रह स्थिति</h2>
{_table(["ग्रह", "राशि", "अंश", "भाव", "नक्षत्र (पाद)", "स्थिति"], planets_rows)}

<h2>पंचांग</h2>
<table class="sum">
<tr><td>वार</td><td>{e(pc["vara"]["name_hi"])}</td></tr>
<tr><td>तिथि</td><td>{e(pc["tithi"]["paksha"])} {e(pc["tithi"]["name"])} ({pc["tithi"]["number"]})</td></tr>
<tr><td>नक्षत्र</td><td>{e(pc["nakshatra"]["name_hi"])} पाद {pc["nakshatra"]["pada"]}</td></tr>
<tr><td>योग / करण</td><td>{e(pc["yoga"]["name"])} / {e(pc["karana"]["name"])}</td></tr>
</table>{day_html}

<h2>विंशोत्तरी दशा</h2>
<p>जन्म के समय {e(PLANETS_HI[chart["dasha"]["birth_nakshatra_lord"]])} की दशा शेष: {chart["dasha"]["balance_at_birth_years"]:.2f} वर्ष (वर्ष = {chart["dasha"]["year_days"]} दिन)।</p>
{_table(["महादशा", "आरंभ", "समाप्ति"], maha_rows)}

<h2>अष्टकवर्ग</h2>
<p class="small">{e(av["why_hi"])}</p>
{_table(sav_head, sav_rows)}
{_table(["ग्रह"] + [str(i + 1) for i in range(12)] + ["कुल"], bav_rows)}

<h2>गोचर ({e(go["as_of"][:10])})</h2>
<p class="small">{e(go["why_hi"])}</p>
{_table(["ग्रह", "राशि", "चंद्र से भाव", "लग्न से भाव", "बिंदु", "संकेत"], go_rows)}

<h2>योग और दोष</h2>
{_table(["योग", "स्थिति", "कारण"], yoga_rows)}

<p class="small" style="margin-top:18px">इंजन संस्करण {e(ENGINE_VERSION)} · बैकएंड: {e(chart["backend"])} · बनाया गया: {e(generated)}।
यह रिपोर्ट शिक्षा और मार्गदर्शन के लिए है; स्वास्थ्य, धन या क़ानून के फ़ैसले विशेषज्ञ की सलाह से लें।</p>
</body></html>"""
