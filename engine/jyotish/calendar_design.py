"""Printable panchang calendar pages (the "calendar studio").

Renders one month (or all twelve) as print-ready HTML: an advertisement band at the top and at the bottom
(image as data URL, or text), a title band (Gregorian month, Vikram samvat, amanta/purnimanta masa), the 7-column
grid with tithi, nakshatra, festivals and optional details per day, a festival list, and a business footer.
The design is a plain dict chosen in the web studio; everything is self-contained HTML + CSS with @page sizes so
the browser's print dialog produces the PDF. No external resources are loaded.
"""
from __future__ import annotations

import html
import re

from . import panchang_month

e = html.escape
MONTH_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WD_HI = ["रवि", "सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"]
WD_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
THEMES = {
    "saffron": {"accent": "#b4541a", "accent2": "#f2d9b8", "ink": "#2b1d12", "paper": "#fffaf3", "sunday": "#c62828", "fest": "#7b1fa2"},
    "indigo": {"accent": "#283593", "accent2": "#dfe3f7", "ink": "#1a1f36", "paper": "#ffffff", "sunday": "#c62828", "fest": "#00695c"},
    "forest": {"accent": "#2e7d32", "accent2": "#dcedc8", "ink": "#1b2a1b", "paper": "#fbfff7", "sunday": "#c62828", "fest": "#8d4e00"},
    "maroon": {"accent": "#7b1f3a", "accent2": "#f3dfe6", "ink": "#2b1a20", "paper": "#fffafb", "sunday": "#b71c1c", "fest": "#283593"},
    "mono": {"accent": "#222222", "accent2": "#e6e6e6", "ink": "#111111", "paper": "#ffffff", "sunday": "#555555", "fest": "#000000"},
}
SIZES = {"A4": ("210mm", "297mm"), "A4-landscape": ("297mm", "210mm"), "A3": ("297mm", "420mm"), "A3-landscape": ("420mm", "297mm"), "Letter": ("8.5in", "11in")}
_DATA_URL = re.compile(r"^data:image/(png|jpeg|jpg|webp|gif|svg\+xml);base64,[A-Za-z0-9+/=\s]+$")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _img_ok(src: str | None) -> bool:
    return bool(src) and len(src) < 6_000_000 and bool(_DATA_URL.match(src))


def _band(ad: dict, theme: dict, cls: str) -> str:
    if not ad or not ad.get("enabled", True):
        return ""
    h = max(20, min(120, int(ad.get("height_mm") or 35)))
    bg = ad.get("bg") if _COLOR.match(str(ad.get("bg") or "")) else theme["accent2"]
    fg = ad.get("fg") if _COLOR.match(str(ad.get("fg") or "")) else theme["ink"]
    if _img_ok(ad.get("image")):
        inner = f'<img src="{ad["image"]}" alt="" style="width:100%;height:100%;object-fit:{"cover" if ad.get("fit") == "cover" else "contain"}">'
    else:
        inner = (f'<div class="adtext"><div class="adtitle">{e(ad.get("title") or "")}</div><div class="adsub">{e(ad.get("text") or "")}</div>'
                 f'<div class="adcontact">{e(ad.get("contact") or "")}</div></div>')
    return f'<div class="band {cls}" style="height:{h}mm;background:{bg};color:{fg}">{inner}</div>'


def _css(theme: dict, size: tuple, font_scale: float) -> str:
    w, h = size
    return f"""
@page {{ size: {w} {h}; margin: 8mm; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#888; font-family: 'Noto Sans Devanagari','Mangal','Noto Sans','Segoe UI',sans-serif; color:{theme['ink']}; font-size:{10 * font_scale:.1f}pt; }}
.page {{ width:{w}; height:{h}; margin:6mm auto; padding:8mm; background:{theme['paper']}; display:flex; flex-direction:column; gap:3mm; page-break-after:always; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,.35); }}
@media print {{ body {{ background:none; }} .page {{ margin:0; box-shadow:none; width:auto; height:calc({h} - 16mm); }} }}
.band {{ flex:0 0 auto; border-radius:2mm; overflow:hidden; display:flex; align-items:center; justify-content:center; text-align:center; }}
.adtext {{ padding:2mm 4mm; }} .adtitle {{ font-size:{20 * font_scale:.0f}pt; font-weight:800; letter-spacing:.3px; }} .adsub {{ font-size:{11 * font_scale:.0f}pt; margin-top:1mm; }} .adcontact {{ font-size:{10 * font_scale:.0f}pt; margin-top:1mm; opacity:.85; }}
.title {{ flex:0 0 auto; display:flex; align-items:center; justify-content:space-between; gap:4mm; border-bottom:1mm solid {theme['accent']}; padding-bottom:1.5mm; }}
.title .m {{ font-size:{26 * font_scale:.0f}pt; font-weight:900; color:{theme['accent']}; }} .title .y {{ font-size:{16 * font_scale:.0f}pt; font-weight:700; }}
.title .sub {{ font-size:{9.5 * font_scale:.1f}pt; text-align:right; line-height:1.35; }}
.logo {{ height:14mm; max-width:40mm; object-fit:contain; }}
.body {{ flex:1 1 auto; display:flex; gap:3mm; min-height:0; }}
.grid {{ flex:1 1 auto; display:grid; grid-template-columns:repeat(7,1fr); gap:1mm; min-height:0; }}
.wd {{ background:{theme['accent']}; color:#fff; text-align:center; font-weight:700; padding:1mm 0; border-radius:1mm; font-size:{10 * font_scale:.0f}pt; }}
.wd.sun {{ background:{theme['sunday']}; }}
.cell {{ border:0.3mm solid {theme['accent2']}; border-radius:1mm; padding:1mm 1.2mm; position:relative; overflow:hidden; display:flex; flex-direction:column; }}
.cell.empty {{ border-color:transparent; }}
.cell .d {{ font-size:{18 * font_scale:.0f}pt; font-weight:800; line-height:1; }}
.cell.sun .d, .cell.holiday .d {{ color:{theme['sunday']}; }}
.cell .t {{ font-size:{8.5 * font_scale:.1f}pt; font-weight:600; margin-top:.6mm; }}
.cell .n {{ font-size:{7.5 * font_scale:.1f}pt; opacity:.85; }}
.cell .f {{ font-size:{7.8 * font_scale:.1f}pt; color:{theme['fest']}; font-weight:700; margin-top:auto; line-height:1.15; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
.cell .x {{ font-size:{7 * font_scale:.1f}pt; opacity:.7; }}
.cell .note {{ font-size:{7.5 * font_scale:.1f}pt; color:{theme['accent']}; font-style:italic; }}
.cell .mark {{ position:absolute; top:1mm; right:1.2mm; font-size:{7 * font_scale:.1f}pt; opacity:.7; }}
.side {{ flex:0 0 52mm; border-left:0.3mm solid {theme['accent2']}; padding-left:3mm; font-size:{8.5 * font_scale:.1f}pt; overflow:hidden; }}
.side h3 {{ margin:0 0 1.5mm; color:{theme['accent']}; font-size:{11 * font_scale:.0f}pt; }}
.side li {{ margin:0 0 .8mm; list-style:none; }} .side ul {{ margin:0; padding:0; }} .side b.dt {{ display:inline-block; min-width:8mm; color:{theme['accent']}; }}
.foot {{ flex:0 0 auto; display:flex; justify-content:space-between; align-items:center; font-size:{8.5 * font_scale:.1f}pt; border-top:0.3mm solid {theme['accent2']}; padding-top:1mm; }}
.foot .biz {{ font-weight:700; }}
.legend {{ font-size:{7.5 * font_scale:.1f}pt; opacity:.75; }}
"""


def render_month_page(m: dict, design: dict, lang: str, theme: dict) -> str:
    hi = lang != "en"
    show = design.get("show") or {}
    sv = lambda k, d=True: show.get(k, d)
    notes = {n.get("date"): n.get("text") for n in (design.get("notes") or []) if n.get("date") and n.get("text")}
    holidays = {h.get("date") for h in (design.get("holidays") or []) if h.get("date")}
    first = m["first_weekday"]
    cells = [f'<div class="wd{" sun" if i == 0 else ""}">{(WD_HI if hi else WD_EN)[i]}</div>' for i in range(7)]
    cells += ['<div class="cell empty"></div>'] * first
    fest_list = []
    for d in m["days"]:
        ev = [x for x in d["events"] if x["kind"] == "festival" or (sv("ekadashi") and x["kind"] == "ekadashi") or (sv("purnima_amavasya", False) and x["kind"] in ("purnima", "amavasya"))]
        fest_txt = "<br>".join(e(x["name_hi"] if hi else x["name_en"]) for x in ev[:2])
        for x in ev:
            fest_list.append((d["day"], x["name_hi"] if hi else x["name_en"], x["kind"]))
        cls = "cell" + (" sun" if d["weekday"] == 0 else "") + (" holiday" if d["date"] in holidays else "")
        tithi = f'{d["paksha_hi"][:2] if hi else d["paksha"][:1]}. {d["tithi_hi"] if hi else d["tithi"]}' + (f' <span class="x">{d["tithi_ends"]}{"+" if d["tithi_ends_next_day"] else ""}</span>' if sv("end_times") and d["tithi_ends"] else "")
        nak = (d["nakshatra_hi"] if hi else d["nakshatra"]) + (f' <span class="x">{d["nakshatra_ends"]}{"+" if d["nakshatra_ends_next_day"] else ""}</span>' if sv("end_times") and d["nakshatra_ends"] else "")
        extra = []
        if sv("moonrise", False) and d["moonrise"]:
            extra.append(("चंद्रोदय " if hi else "Moonrise ") + d["moonrise"])
        if sv("rahu_kaal", False) and d.get("rahu_kaal"):
            extra.append(("राहु " if hi else "Rahu ") + f'{d["rahu_kaal"]["start"]}–{d["rahu_kaal"]["end"]}')
        if sv("yoga_karana", False):
            extra.append(f'{d["yoga_hi"] if hi else d["yoga"]} · {d["karana_hi"] if hi else d["karana"]}')
        mark = ("संक्रांति" if hi else "Sankranti") if d["sankranti"] else ""
        cells.append(f'<div class="{cls}"><div class="d">{d["day"]}</div>{f"<div class=mark>{mark}</div>" if mark else ""}'
                     f'<div class="t">{tithi}</div>{f"<div class=n>{nak}</div>" if sv("nakshatra") else ""}'
                     + "".join(f'<div class="x">{e(x)}</div>' for x in extra)
                     + (f'<div class="note">{e(notes[d["date"]])}</div>' if d["date"] in notes else "")
                     + (f'<div class="f">{fest_txt}</div>' if fest_txt else "") + "</div>")
    while (len(cells) - 7) % 7:
        cells.append('<div class="cell empty"></div>')
    rows = (len(cells) - 7) // 7
    d0, d1 = m["days"][0], m["days"][-1]
    masas = {d["masa_purnimanta_hi"] if hi else d["masa_purnimanta"] for d in m["days"]}
    amanta = {d["masa_amanta_hi"] if hi else d["masa_amanta"] for d in m["days"]}
    samvats = sorted({d["vikram_samvat"] for d in m["days"]})
    sub = ((f"विक्रम संवत {'–'.join(map(str, samvats))}<br>पूर्णिमांत: {' / '.join(sorted(masas))}<br>अमांत: {' / '.join(sorted(amanta))}") if hi else
           (f"Vikram samvat {'–'.join(map(str, samvats))}<br>Purnimanta: {' / '.join(sorted(masas))}<br>Amanta: {' / '.join(sorted(amanta))}"))
    logo = f'<img class="logo" src="{design["logo"]}" alt="">' if _img_ok(design.get("logo")) else ""
    title = (f'<div class="title">{logo}<div><span class="m">{MONTH_HI[m["month"] - 1] if hi else MONTH_EN[m["month"] - 1]}</span> <span class="y">{m["year"]}</span></div>'
             f'<div class="sub">{sub}</div></div>')
    side = ""
    if sv("festival_list"):
        items = "".join(f'<li><b class="dt">{d}</b> {e(n)}</li>' for d, n, k in fest_list) or ("<li>—</li>")
        place = e(design.get("place") or "")
        side = (f'<div class="side"><h3>{"इस माह के पर्व और व्रत" if hi else "Festivals and vrats this month"}</h3><ul>{items}</ul>'
                f'<p class="legend">{("स्थान: " + place + "<br>") if place else ""}{"सूर्योदय-कालीन तिथि; समय स्थानीय, + = अगले दिन" if hi else "Tithi at sunrise; local times, + = next day"}</p></div>')
    biz = design.get("business") or {}
    foot = (f'<div class="foot"><div class="biz">{e(biz.get("name") or "")}</div><div>{e(biz.get("line") or "")}</div>'
            f'<div class="legend">{e(biz.get("tagline") or ("पंचांग: लाहिड़ी अयनांश" if hi else "Panchang: Lahiri ayanamsa"))}</div></div>')
    return (f'<div class="page">{_band(design.get("ad_top") or {}, theme, "top")}{title}<div class="body"><div class="grid" style="grid-template-rows:auto repeat({rows},1fr)">{"".join(cells)}</div>{side}</div>'
            f'{foot}{_band(design.get("ad_bottom") or {}, theme, "bottom")}</div>')


def render_calendar(year: int, months: list[int], lat: float, lon: float, tz: str, design: dict, lang: str = "hi") -> str:
    theme = THEMES.get(str(design.get("theme") or "saffron"), THEMES["saffron"])
    size = SIZES.get(str(design.get("size") or "A4"), SIZES["A4"])
    try:
        scale = max(0.7, min(1.4, float(design.get("font_scale") or 1.0)))
    except (TypeError, ValueError):
        scale = 1.0
    pages = "".join(render_month_page(panchang_month.month(year, mo, lat, lon, tz), design, lang, theme) for mo in months)
    title = (design.get("business") or {}).get("name") or ("पंचांग कैलेंडर" if lang != "en" else "Panchang calendar")
    return (f'<!doctype html><html lang="{"en" if lang == "en" else "hi"}"><head><meta charset="utf-8"><title>{e(title)} {year}</title>'
            f'<style>{_css(theme, size, scale)}</style></head><body>{pages}'
            '<script>(function(){function fit(){if(matchMedia("print").matches)return;var p=document.querySelector(".page");if(!p)return;var z=Math.min(1,(window.innerWidth-16)/p.offsetWidth);document.body.style.zoom=z;}'
            'window.addEventListener("resize",fit);window.addEventListener("beforeprint",function(){document.body.style.zoom=1;});window.addEventListener("afterprint",fit);fit();})();</script></body></html>')
