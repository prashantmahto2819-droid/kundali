"""Printable panchang calendar pages (the "calendar studio"), v2.

Templates: classic (grid + side festival list), modern (hero image, big display month, airy grid with festival pills),
poster (vertical day list with panchang columns), panchang (full almanac page in the style of the popular Hindi wall
panchangs: day list with tithi/nakshatra/yoga/karana end times, sunrise/sunset/moonrise, Rahu kaal, special yogas,
plus boxes for festivals, planetary ingresses and auspicious dates), compact (two months per page), and an optional
cover page for the yearly set. Every page has an advertisement band at the top and at the bottom (image as data URL
or text) and an optional vertical side band; logo, business footer, palettes or fully custom colours (accent, festival,
Sunday, paper, ink), three font pairings (Google Fonts when online, system fallbacks offline), background styles,
bilingual month names, Monday/Sunday week start, notes and holidays per date. Self-contained HTML + CSS with @page
sizes; the browser's print dialog makes the PDF. Untrusted strings are escaped, images must be data URLs, colours #rrggbb.
"""
from __future__ import annotations

import html
import re
from functools import lru_cache

from . import panchang_month

e = html.escape
MONTH_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WD_HI = ["रवि", "सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"]
WD_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
THEMES = {
    "saffron": {"accent": "#b4541a", "ink": "#2b1d12", "paper": "#fffaf3", "sunday": "#c62828", "fest": "#7b1fa2"},
    "indigo": {"accent": "#283593", "ink": "#1a1f36", "paper": "#ffffff", "sunday": "#c62828", "fest": "#00695c"},
    "forest": {"accent": "#2e7d32", "ink": "#1b2a1b", "paper": "#fbfff7", "sunday": "#c62828", "fest": "#8d4e00"},
    "maroon": {"accent": "#7b1f3a", "ink": "#2b1a20", "paper": "#fffafb", "sunday": "#b71c1c", "fest": "#283593"},
    "teal": {"accent": "#00796b", "ink": "#102a27", "paper": "#f7fffd", "sunday": "#d84315", "fest": "#4527a0"},
    "royal": {"accent": "#1a237e", "ink": "#121a3a", "paper": "#fbfbff", "sunday": "#c62828", "fest": "#b8860b"},
    "sunset": {"accent": "#e65100", "ink": "#3e2723", "paper": "#fffdf9", "sunday": "#ad1457", "fest": "#283593"},
    "mono": {"accent": "#222222", "ink": "#111111", "paper": "#ffffff", "sunday": "#555555", "fest": "#000000"},
}
FONTS = {
    "modern": {"link": "https://fonts.googleapis.com/css2?family=Poppins:wght@500;700;900&family=Noto+Sans+Devanagari:wght@400;600;800&display=swap",
               "display": "'Poppins','Noto Sans Devanagari','Segoe UI',sans-serif", "body": "'Noto Sans Devanagari','Poppins','Segoe UI',sans-serif"},
    "classic": {"link": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;800&family=Tiro+Devanagari+Hindi&display=swap",
                "display": "'Playfair Display','Tiro Devanagari Hindi',Georgia,serif", "body": "'Tiro Devanagari Hindi','Noto Serif Devanagari',Georgia,serif"},
    "clean": {"link": "https://fonts.googleapis.com/css2?family=Inter:wght@500;700;900&family=Mukta:wght@400;600;800&display=swap",
              "display": "'Inter','Mukta','Segoe UI',sans-serif", "body": "'Mukta','Inter','Segoe UI',sans-serif"},
    "system": {"link": "", "display": "'Noto Sans Devanagari','Mangal','Segoe UI',sans-serif", "body": "'Noto Sans Devanagari','Mangal','Segoe UI',sans-serif"},
}
SIZES = {"A4": ("210mm", "297mm"), "A4-landscape": ("297mm", "210mm"), "A3": ("297mm", "420mm"), "A3-landscape": ("420mm", "297mm"),
         "Letter": ("8.5in", "11in"), "Square": ("297mm", "297mm")}
TEMPLATES = ("classic", "modern", "poster", "panchang", "compact", "quarter")
_DATA_URL = re.compile(r"^data:image/(png|jpeg|jpg|webp|gif|svg\+xml);base64,[A-Za-z0-9+/=\s]+$")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _img_ok(src) -> bool:
    return isinstance(src, str) and 0 < len(src) < 6_000_000 and bool(_DATA_URL.match(src))


def _col(v, default):
    return v if isinstance(v, str) and _COLOR.match(v) else default


@lru_cache(maxsize=128)
def _month(year, mon, lat, lon, tz):
    return panchang_month.month(year, mon, lat, lon, tz)


# ---------------------------------------------------------------- shared pieces
def _band(ad: dict, cls: str, vertical: bool = False) -> str:
    if not ad or not ad.get("enabled", True):
        return ""
    size_mm = max(12, min(120, int(ad.get("height_mm") or (28 if vertical else 35))))
    bg = _col(ad.get("bg"), "var(--tint)")
    fg = _col(ad.get("fg"), "var(--ink)")
    style = f'{"width" if vertical else "height"}:{size_mm}mm;background:{bg};color:{fg};border-radius:{"3mm" if (ad.get("style") or "rounded") == "rounded" else "0"}'
    if _img_ok(ad.get("image")):
        inner = f'<img src="{ad["image"]}" alt="" style="width:100%;height:100%;object-fit:{"cover" if ad.get("fit") == "cover" else "contain"}">'
    else:
        inner = (f'<div class="adtext{" vert" if vertical else ""}"><div class="adtitle">{e(ad.get("title") or "")}</div><div class="adsub">{e(ad.get("text") or "")}</div>'
                 f'<div class="adcontact">{e(ad.get("contact") or "")}</div></div>')
    return f'<div class="band {cls}{" vertical" if vertical else ""}" style="{style}">{inner}</div>'


def _hero(design: dict, mon: int, cls: str = "hero") -> str:
    imgs = design.get("hero_images") or {}
    src = imgs.get(str(mon)) or imgs.get("all") or design.get("hero")
    if not _img_ok(src):
        return ""
    return f'<div class="{cls}"><img src="{src}" alt="" style="object-position:{e(str(design.get("hero_position") or "center"))}"></div>'


def _logo(design: dict) -> str:
    return f'<img class="logo" src="{design["logo"]}" alt="">' if _img_ok(design.get("logo")) else ""


def _events_for(d: dict, sv) -> list:
    return [x for x in d["events"] if x["kind"] == "festival" or (sv("ekadashi") and x["kind"] == "ekadashi") or (sv("purnima_amavasya", False) and x["kind"] in ("purnima", "amavasya"))
            or (sv("vrat_extra", False) and x["kind"] in ("pradosh", "chaturthi", "shivaratri"))]


def _bits(d: dict, hi: bool, sv) -> dict:
    tithi = f'{d["paksha_hi"][:2] if hi else d["paksha"][:1]}. {d["tithi_hi"] if hi else d["tithi"]}'
    t_end = f'{d["tithi_ends"]}{"+" if d["tithi_ends_next_day"] else ""}' if sv("end_times") and d["tithi_ends"] else ""
    nak = d["nakshatra_hi"] if hi else d["nakshatra"]
    n_end = f'{d["nakshatra_ends"]}{"+" if d["nakshatra_ends_next_day"] else ""}' if sv("end_times") and d["nakshatra_ends"] else ""
    extra = []
    if sv("moonrise", False) and d["moonrise"]:
        extra.append(("चंद्रोदय " if hi else "Moonrise ") + d["moonrise"])
    if sv("sun_times", False):
        extra.append(f'{"सूर्योदय" if hi else "Sunrise"} {d["sunrise"]} · {"अस्त" if hi else "set"} {d["sunset"]}')
    if sv("rahu_kaal", False) and d.get("rahu_kaal"):
        extra.append(("राहु " if hi else "Rahu ") + f'{d["rahu_kaal"]["start"]}–{d["rahu_kaal"]["end"]}')
    if sv("yoga_karana", False):
        extra.append(f'{d["yoga_hi"] if hi else d["yoga"]} · {d["karana_hi"] if hi else d["karana"]}')
    if sv("special", True) and d.get("special"):
        extra.append(" · ".join(x["hi"] if hi else x["en"] for x in d["special"]))
    return {"tithi": tithi, "t_end": t_end, "nak": nak, "n_end": n_end, "extra": extra}


def _sub(m: dict, hi: bool, regional: bool = False) -> str:
    masas = sorted({d["masa_purnimanta_hi"] if hi else d["masa_purnimanta"] for d in m["days"]})
    amanta = sorted({d["masa_amanta_hi"] if hi else d["masa_amanta"] for d in m["days"]})
    samvats = sorted({d["vikram_samvat"] for d in m["days"]})
    out = (f"विक्रम संवत {'–'.join(map(str, samvats))} · पूर्णिमांत {' / '.join(masas)} · अमांत {' / '.join(amanta)}" if hi else
           f"Vikram samvat {'–'.join(map(str, samvats))} · Purnimanta {' / '.join(masas)} · Amanta {' / '.join(amanta)}")
    if regional:
        shaka = sorted({d["shaka_samvat"] for d in m["days"]}); guj = sorted({d["gujarati_samvat"] for d in m["days"]})
        ta = " / ".join(dict.fromkeys(d["tamil_month"] for d in m["days"])); bn = " / ".join(dict.fromkeys(d["bengali_month"] for d in m["days"])); ml = " / ".join(dict.fromkeys(d["malayalam_month"] for d in m["days"]))
        out += (f"<br>शक {'–'.join(map(str, shaka))} · गुजराती संवत {'–'.join(map(str, guj))} · तमिल {ta} · बंगाली {bn} · मलयालम {ml}" if hi else
                f"<br>Shaka {'–'.join(map(str, shaka))} · Gujarati samvat {'–'.join(map(str, guj))} · Tamil {ta} · Bengali {bn} · Malayalam {ml}")
    return out


def _mname(mon: int, hi: bool, bilingual: bool) -> str:
    a, b = (MONTH_HI, MONTH_EN) if hi else (MONTH_EN, MONTH_HI)
    return f'{a[mon - 1]}' + (f' <span class="alt">{b[mon - 1]}</span>' if bilingual else "")


def _order(design):
    return [1, 2, 3, 4, 5, 6, 0] if design.get("week_start") == "monday" else [0, 1, 2, 3, 4, 5, 6]


def _grid(m: dict, design: dict, hi: bool, sv, compact: bool = False) -> tuple[str, list]:
    notes = {n.get("date"): n.get("text") for n in (design.get("notes") or []) if n.get("date") and n.get("text")}
    holidays = {h.get("date") for h in (design.get("holidays") or []) if h.get("date")}
    order = _order(design)
    first = order.index(m["first_weekday"])
    wd = WD_HI if hi else WD_EN
    cells = [f'<div class="wd{" sun" if i == 0 else ""}">{wd[i]}</div>' for i in order]
    cells += ['<div class="cell empty"></div>'] * first
    fest_list = []
    for d in m["days"]:
        ev = _events_for(d, sv)
        for x in ev:
            fest_list.append((d["day"], x["name_hi"] if hi else x["name_en"], x["kind"]))
        b = _bits(d, hi, sv)
        cls = "cell" + (" sun" if d["weekday"] == 0 else "") + (" holiday" if d["date"] in holidays else "") + (" hasfest" if any(x["kind"] == "festival" for x in ev) else "")
        pills = "".join(f'<span class="pill {x["kind"]}">{e(x["name_hi"] if hi else x["name_en"])}</span>' for x in ev[:2])
        mark = ("संक्रांति" if hi else "Sankranti") if d["sankranti"] else ""
        body = (f'<div class="d">{d["day"]}</div>{f"<div class=mark>{mark}</div>" if mark else ""}'
                f'<div class="t">{b["tithi"]}{f" <span class=x>{b["t_end"]}</span>" if b["t_end"] else ""}</div>'
                + (f'<div class="n">{b["nak"]}{f" <span class=x>{b["n_end"]}</span>" if b["n_end"] else ""}</div>' if sv("nakshatra") and not compact else "")
                + ("" if compact else "".join(f'<div class="x">{e(x)}</div>' for x in b["extra"]))
                + (f'<div class="note">{e(notes[d["date"]])}</div>' if d["date"] in notes else "")
                + (f'<div class="f">{pills}</div>' if pills else ""))
        cells.append(f'<div class="{cls}">{body}</div>')
    while (len(cells) - 7) % 7:
        cells.append('<div class="cell empty"></div>')
    rows = (len(cells) - 7) // 7
    return f'<div class="grid" style="grid-template-rows:auto repeat({rows},1fr)">{"".join(cells)}</div>', fest_list


def _side_list(fest_list: list, design: dict, hi: bool, sv) -> str:
    if not sv("festival_list"):
        return ""
    items = "".join(f'<li class="{k}"><b class="dt">{d}</b> {e(n)}</li>' for d, n, k in fest_list) or "<li>—</li>"
    place = e(design.get("place") or "")
    return (f'<div class="side"><h3>{"इस माह के पर्व और व्रत" if hi else "Festivals and vrats this month"}</h3><ul>{items}</ul>'
            f'<p class="legend">{("स्थान: " + place + "<br>") if place else ""}{"सूर्योदय-कालीन तिथि · समय स्थानीय · + = अगले दिन" if hi else "Tithi at sunrise · local times · + = next day"}</p></div>')


def _foot(design: dict, hi: bool) -> str:
    biz = design.get("business") or {}
    web = e(biz.get("website") or "")
    return (f'<div class="foot"><div class="biz">{_logo(design) if design.get("logo_in_footer") else ""}<span>{e(biz.get("name") or "")}</span></div>'
            f'<div class="bizline">{e(biz.get("line") or "")}{(" · " + web) if web else ""}</div>'
            f'<div class="legend">{e(biz.get("tagline") or ("पंचांग: लाहिड़ी अयनांश" if hi else "Panchang: Lahiri ayanamsa"))}</div></div>')


def _page(design: dict, content: str) -> str:
    top = _band(design.get("ad_top") or {}, "top")
    bottom = _band(design.get("ad_bottom") or {}, "bottom")
    side = _band(design.get("ad_side") or {"enabled": False}, "side", vertical=True)
    side_left = design.get("ad_side", {}).get("position") == "left" if isinstance(design.get("ad_side"), dict) else False
    inner = f'{side if side_left else ""}<div class="col">{content}</div>{"" if side_left else side}'
    return f'<div class="page {e(str(design.get("background") or "plain"))}">{top}<div class="pagebody">{inner}</div>{bottom}</div>'


def _boxes(m: dict, hi: bool, sv, design: dict, which=("festivals", "muhurta", "ingress")) -> str:
    out = []
    if "festivals" in which:
        items = [(d["day"], x["name_hi"] if hi else x["name_en"], x["kind"]) for d in m["days"] for x in _events_for(d, sv)]
        out.append(f'<div class="box"><h3>{"व्रत-पर्व" if hi else "Festivals and vrats"}</h3><ul>' + "".join(f'<li class="{k}"><b class="dt">{d}</b>{e(n)}</li>' for d, n, k in items) + '</ul></div>')
    if "muhurta" in which and m.get("muhurta"):
        rows = "".join(f'<li><b>{e(x["activity_hi"] if hi else x["activity_en"])}:</b> {", ".join(str(y["day"]) for y in x["dates"])}</li>' for x in m["muhurta"])
        out.append(f'<div class="box"><h3>{"शुभ मुहूर्त (पंचांग-स्तर)" if hi else "Auspicious dates (almanac level)"}</h3><ul>{rows}</ul>'
                   f'<p class="legend">{"रिक्ता तिथि, वर्जित योग, भद्रा और वर्जित नक्षत्र हटाकर; विवाह आदि संस्कारों के लिए पंडित से मुहूर्त निकलवाएँ।" if hi else "Excluding rikta tithis, inauspicious yogas, Bhadra and shunned nakshatras; for marriage and samskaras consult a pandit."}</p></div>')
    if "ingress" in which:
        ing = [x for x in m.get("ingress", []) if x["planet"] != "Moon"]
        rows = "".join(f'<li><b class="dt">{int(x["date"][8:])}</b>{e(x["planet_hi"] if hi else x["planet"])} → {e(x["sign_hi"] if hi else x["sign"])}</li>' for x in ing) or "<li>—</li>"
        out.append(f'<div class="box"><h3>{"ग्रह गोचर (राशि परिवर्तन)" if hi else "Planetary ingresses"}</h3><ul>{rows}</ul></div>')
    return f'<div class="boxes">{"".join(out)}</div>'


# ---------------------------------------------------------------- templates
def tpl_classic(m, design, hi, sv) -> str:
    grid, fl = _grid(m, design, hi, sv)
    title = (f'<div class="title classic">{_logo(design)}<div class="mt"><span class="m">{_mname(m["month"], hi, design.get("bilingual", False))}</span> <span class="y">{m["year"]}</span></div>'
             f'<div class="sub">{_sub(m, hi, sv("regional", False))}</div></div>')
    return _page(design, f'{title}<div class="body">{grid}{_side_list(fl, design, hi, sv)}</div>{_foot(design, hi)}')


def tpl_modern(m, design, hi, sv) -> str:
    grid, fl = _grid(m, design, hi, sv)
    title = (f'<div class="title modern">{_hero(design, m["month"])}<div class="overlay"><div class="num">{m["month"]:02d}</div><div><div class="m">{_mname(m["month"], hi, design.get("bilingual", False))}</div>'
             f'<div class="y">{m["year"]}</div><div class="sub">{_sub(m, hi, sv("regional", False))}</div></div>{_logo(design)}</div></div>')
    return _page(design, f'{title}<div class="body">{grid}{_side_list(fl, design, hi, sv)}</div>{_foot(design, hi)}')


def _list_rows(m, design, hi, sv, full: bool) -> str:
    notes = {n.get("date"): n.get("text") for n in (design.get("notes") or []) if n.get("date") and n.get("text")}
    holidays = {h.get("date") for h in (design.get("holidays") or []) if h.get("date")}
    rows = []
    for d in m["days"]:
        ev = _events_for(d, sv); b = _bits(d, hi, sv)
        cls = ("sun" if d["weekday"] == 0 else "") + (" holiday" if d["date"] in holidays else "")
        fest = " · ".join(e(x["name_hi"] if hi else x["name_en"]) for x in ev[:2])
        sp = " · ".join(e(x["hi"] if hi else x["en"]) for x in d.get("special", []))
        note = f' <i>{e(notes[d["date"]])}</i>' if d["date"] in notes else ""
        if full:
            te = (d["tithi_ends"] or "") + ("+" if d["tithi_ends_next_day"] else ""); ne = (d["nakshatra_ends"] or "") + ("+" if d["nakshatra_ends_next_day"] else "")
            ye = (d["yoga_ends"] or "") + ("+" if d.get("yoga_ends_next_day") else "")
            rows.append(f'<tr class="{cls}"><td class="dn">{d["day"]}</td><td class="wd">{(WD_HI if hi else WD_EN)[d["weekday"]]}</td>'
                        f'<td>{b["tithi"]} <span class="x">{te}</span></td><td>{b["nak"]} <span class="x">{ne}</span></td>'
                        f'<td>{e(d["yoga_hi"] if hi else d["yoga"])} <span class="x">{ye}</span></td><td>{e(d["karana_hi"] if hi else d["karana"])} <span class="x">{d["karana_ends"] or ""}</span></td>'
                        f'<td class="x">{d["sunrise"]} / {d["sunset"]}</td><td class="x">{d["moonrise"] or "—"} / {d["moonset"] or "—"}</td>'
                        f'<td class="x">{d["rahu_kaal"]["start"] + "–" + d["rahu_kaal"]["end"] if d.get("rahu_kaal") else ""}</td>'
                        f'<td class="x">{e(d["moon_sign_hi"] if hi else d["moon_sign"])}</td>'
                        f'<td class="fest">{fest}{note}{(" <span class=sp>" + sp + "</span>") if sp else ""}{" ✦" if d["sankranti"] else ""}</td></tr>')
        else:
            rows.append(f'<tr class="{cls}"><td class="dn">{d["day"]}</td><td class="wd">{(WD_HI if hi else WD_EN)[d["weekday"]]}</td>'
                        f'<td>{b["tithi"]} <span class="x">{b["t_end"]}</span></td><td>{b["nak"]} <span class="x">{b["n_end"]}</span></td>'
                        f'<td class="x">{e(" · ".join(b["extra"])) if b["extra"] else (d["sunrise"] + " / " + d["sunset"])}</td>'
                        f'<td class="fest">{fest}{note}{" ✦" if d["sankranti"] else ""}</td></tr>')
    return "".join(rows)


def tpl_poster(m, design, hi, sv) -> str:
    head = (f'<div class="title poster">{_hero(design, m["month"], "hero")}<div class="overlay"><div><div class="m">{_mname(m["month"], hi, design.get("bilingual", False))} <span class="y">{m["year"]}</span></div>'
            f'<div class="sub">{_sub(m, hi, sv("regional", False))}</div></div>{_logo(design)}</div></div>')
    th = ["दिन", "वार", "तिथि", "नक्षत्र", "सूर्योदय / अस्त", "पर्व / नोट"] if hi else ["Day", "Vara", "Tithi", "Nakshatra", "Sunrise / set", "Festival / note"]
    table = f'<table class="list"><thead><tr>{"".join(f"<th>{x}</th>" for x in th)}</tr></thead><tbody>{_list_rows(m, design, hi, sv, False)}</tbody></table>'
    return _page(design, f'{head}<div class="body col2">{table}</div>{_foot(design, hi)}')


def tpl_panchang(m, design, hi, sv) -> str:
    head = (f'<div class="title panchang"><div class="pl">{_logo(design)}</div><div class="pc"><div class="m">{_mname(m["month"], hi, design.get("bilingual", False))} <span class="y">{m["year"]}</span></div>'
            f'<div class="sub">{_sub(m, hi, sv("regional", False))}</div></div><div class="pr">{e((design.get("business") or {}).get("name") or "")}<br><span class="legend">{e(design.get("place") or "")}</span></div></div>')
    th = (["दिन", "वार", "तिथि", "नक्षत्र", "योग", "करण", "सूर्योदय / अस्त", "चंद्रोदय / अस्त", "राहु काल", "चंद्र राशि", "पर्व · विशेष"] if hi else
          ["Day", "Vara", "Tithi", "Nakshatra", "Yoga", "Karana", "Sunrise / set", "Moonrise / set", "Rahu kaal", "Moon sign", "Festival · special"])
    table = f'<table class="list full"><thead><tr>{"".join(f"<th>{x}</th>" for x in th)}</tr></thead><tbody>{_list_rows(m, design, hi, sv, True)}</tbody></table>'
    legend = ("समय स्थानीय · + = अगले दिन · ✦ संक्रांति · विशेष: सर्वार्थ/अमृत सिद्धि, गंड मूल, पंचक, भद्रा (सूर्योदय-कालीन)" if hi else
              "Local times · + = next day · ✦ sankranti · special: Sarvartha/Amrita Siddhi, Gand Mool, Panchak, Bhadra (at sunrise)")
    return _page(design, f'{head}<div class="body col2">{table}</div>{_boxes(m, hi, sv, design)}<p class="legend">{legend}</p>{_foot(design, hi)}')


def tpl_compact_pair(m1, m2, design, hi, sv) -> str:
    def half(m):
        if not m:
            return '<div class="half"></div>'
        grid, fl = _grid(m, design, hi, sv, compact=True)
        fest = "".join(f'<li><b class="dt">{d}</b> {e(n)}</li>' for d, n, k in fl[:14])
        return (f'<div class="half"><div class="title compact"><div class="m">{_mname(m["month"], hi, design.get("bilingual", False))} <span class="y">{m["year"]}</span></div>'
                f'<div class="sub">{_sub(m, hi, sv("regional", False))}</div></div>{grid}<ul class="minilist">{fest}</ul></div>')
    return _page(design, f'<div class="pair">{half(m1)}{half(m2)}</div>{_foot(design, hi)}')


def tpl_quarter(ms, design, hi, sv) -> str:
    def third(m):
        if not m:
            return '<div class="third"></div>'
        grid, fl = _grid(m, design, hi, sv, compact=True)
        return (f'<div class="third"><div class="title compact"><div class="m">{_mname(m["month"], hi, design.get("bilingual", False))} <span class="y">{m["year"]}</span></div>'
                f'<div class="sub">{_sub(m, hi, sv("regional", False))}</div></div>{grid}<ul class="minilist">{"".join(f"<li><b class=dt>{d}</b> {e(n)}</li>" for d, n, k in fl[:9])}</ul></div>')
    ms = list(ms) + [None] * (3 - len(ms))
    return _page(design, f'<div class="trio">{"".join(third(m) for m in ms)}</div>{_foot(design, hi)}')


def tpl_muhurta_year(year, months, design, hi) -> str:
    """Yearly page: auspicious dates per activity for every month (almanac level)."""
    acts: dict[str, dict] = {}
    for m in months:
        for x in m.get("muhurta", []):
            a = acts.setdefault(x["activity"], {"hi": x["activity_hi"], "en": x["activity_en"], "months": []})
            a["months"].append((m["month"], [y["day"] for y in x["dates"]]))
    rows = ""
    for key, a in acts.items():
        cells = "".join(f'<li><b>{(MONTH_HI if hi else MONTH_EN)[mo - 1][:3 if not hi else 4]}</b> {", ".join(map(str, days))}</li>' for mo, days in a["months"])
        rows += f'<div class="box"><h3>{e(a["hi"] if hi else a["en"])}</h3><ul class="mlist">{cells}</ul></div>'
    head = (f'<div class="title panchang"><div class="pl">{_logo(design)}</div><div class="pc"><div class="m">{"वार्षिक शुभ मुहूर्त" if hi else "Auspicious dates of the year"} <span class="y">{year}</span></div>'
            f'<div class="sub">{"पंचांग-स्तर: तिथि, नक्षत्र, वार, योग, भद्रा; संस्कारों में खरमास, चातुर्मास, होलाष्टक, अधिक मास, पितृ पक्ष, गुरु-शुक्र अस्त वर्जित" if hi else "Almanac level: tithi, nakshatra, weekday, yoga, Bhadra; samskaras exclude Kharmas, Chaturmas, Holashtak, adhika masa, Pitru paksha, Jupiter/Venus combust"}</div></div></div>')
    legend = ("विवाह, उपनयन आदि संस्कारों के लिए लग्न-शुद्धि सहित पंडित से मुहूर्त निकलवाएँ; यह सूची दिशा-संकेत है।" if hi else
              "For marriage, upanayana and other samskaras have a pandit fix the muhurta with the lagna; this list is a pointer.")
    return _page(design, f'{head}<div class="boxes year">{rows}</div><p class="legend">{legend}</p>{_foot(design, hi)}')


def tpl_cover(year, months, design, hi) -> str:
    minis = []
    order = _order(design)
    for m in months:
        first = order.index(m["first_weekday"])
        cells = "".join(f'<i class="{"s" if i == 0 else ""}">{(WD_HI if hi else WD_EN)[i][0]}</i>' for i in order) + "<b></b>" * first
        cells += "".join(f'<b class="{"s" if d["weekday"] == 0 else ""}{" f" if any(x["kind"] == "festival" for x in d["events"]) else ""}">{d["day"]}</b>' for d in m["days"])
        minis.append(f'<div class="mini"><div class="mm">{(MONTH_HI if hi else MONTH_EN)[m["month"] - 1]}</div><div class="mg">{cells}</div></div>')
    biz = design.get("business") or {}
    content = (f'<div class="cover">{_hero(design, 0, "hero cover")}<div class="coverhead">{_logo(design)}<div class="yr">{year}</div>'
               f'<div class="cm">{e(design.get("cover_title") or biz.get("name") or ("पंचांग कैलेंडर" if hi else "Panchang Calendar"))}</div>'
               f'<div class="cs">{e(design.get("cover_subtitle") or biz.get("tagline") or "")}</div></div><div class="minis">{"".join(minis)}</div></div>')
    return _page(design, content + _foot(design, hi))


# ---------------------------------------------------------------- CSS
def _css(colors: dict, size: tuple, scale: float, font: dict) -> str:
    w, h = size
    fs = lambda v: f"{v * scale:.1f}pt"
    return f"""
:root {{ --accent:{colors['accent']}; --ink:{colors['ink']}; --paper:{colors['paper']}; --sun:{colors['sunday']}; --fest:{colors['fest']}; --head:{colors['head']};
        --tint: color-mix(in srgb, var(--accent) 10%, white); --tint2: color-mix(in srgb, var(--accent) 22%, white); --line: color-mix(in srgb, var(--accent) 26%, white); }}
@page {{ size: {w} {h}; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#6b6b6b; font-family:{font['body']}; color:var(--ink); font-size:{fs(10)}; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
.page {{ width:{w}; height:{h}; margin:6mm auto; padding:9mm; background:var(--paper); display:flex; flex-direction:column; gap:3mm; page-break-after:always; overflow:hidden; box-shadow:0 2px 14px rgba(0,0,0,.35); position:relative; }}
.page.soft {{ background: linear-gradient(160deg, var(--paper) 0%, var(--tint) 100%); }}
.page.pattern {{ background-color:var(--paper); background-image: radial-gradient(color-mix(in srgb, var(--accent) 12%, transparent) 0.6mm, transparent 0.7mm); background-size: 6mm 6mm; }}
.page.stripe {{ background: var(--paper) repeating-linear-gradient(135deg, transparent 0 9mm, color-mix(in srgb, var(--accent) 5%, transparent) 9mm 10mm); }}
.page.dark {{ --paper:#161a22; --ink:#f3f4f8; --tint: color-mix(in srgb, var(--accent) 28%, #161a22); --tint2: color-mix(in srgb, var(--accent) 40%, #161a22); --line: color-mix(in srgb, var(--accent) 45%, #161a22); background:#161a22; color:#f3f4f8; }}
.page.dark .cell {{ background: color-mix(in srgb, #ffffff 4%, transparent); }} .page.dark table.list tbody tr:nth-child(even) {{ background: color-mix(in srgb, #ffffff 4%, transparent); }}
@media print {{ body {{ background:none; }} .page {{ margin:0; box-shadow:none; }} }}
.pagebody {{ flex:1 1 auto; min-height:0; display:flex; gap:3mm; }}
.pagebody > .band.vertical {{ flex:0 0 auto; }}
.col {{ flex:1 1 auto; min-width:0; display:flex; flex-direction:column; gap:3mm; min-height:0; }}
.band {{ flex:0 0 auto; overflow:hidden; display:flex; align-items:center; justify-content:center; text-align:center; }}
.adtext {{ padding:2mm 4mm; }} .adtext.vert {{ writing-mode:vertical-rl; transform:rotate(180deg); }}
.adtitle {{ font-family:{font['display']}; font-size:{fs(19)}; font-weight:800; letter-spacing:.2px; }} .adsub {{ font-size:{fs(10.5)}; margin-top:1mm; }} .adcontact {{ font-size:{fs(9.5)}; margin-top:1mm; opacity:.85; }}
.logo {{ height:13mm; max-width:38mm; object-fit:contain; }}
.alt {{ font-weight:500; opacity:.7; font-size:.55em; margin-left:1.5mm; }}
.title {{ flex:0 0 auto; }} .title .sub {{ font-size:{fs(9)}; opacity:.85; }}
.title.classic {{ display:flex; align-items:center; gap:4mm; border-bottom:0.9mm solid var(--accent); padding-bottom:1.5mm; }}
.title.classic .mt {{ flex:1 1 auto; }} .title.classic .m {{ font-family:{font['display']}; font-size:{fs(26)}; font-weight:800; color:var(--accent); }} .title.classic .y {{ font-size:{fs(16)}; font-weight:700; }}
.title.modern {{ position:relative; min-height:34mm; border-radius:4mm; overflow:hidden; background: linear-gradient(120deg, var(--accent), color-mix(in srgb, var(--accent) 55%, #000)); color:var(--head); }}
.hero {{ position:absolute; inset:0; }} .hero img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.title.modern .overlay {{ position:relative; display:flex; align-items:center; gap:4mm; padding:4mm 6mm; height:100%; background: linear-gradient(90deg, rgba(0,0,0,.55), rgba(0,0,0,.15) 60%, rgba(0,0,0,0)); }}
.title.modern .num {{ font-family:{font['display']}; font-size:{fs(44)}; font-weight:900; line-height:1; opacity:.95; }}
.title.modern .m {{ font-family:{font['display']}; font-size:{fs(24)}; font-weight:800; line-height:1.1; }} .title.modern .y {{ font-size:{fs(13)}; font-weight:600; opacity:.9; }} .title.modern .sub {{ color:var(--head); opacity:.85; }}
.title.modern .logo, .title.poster .logo {{ margin-left:auto; background:rgba(255,255,255,.92); padding:1.5mm; border-radius:2mm; }}
.title.poster {{ position:relative; min-height:26mm; border-radius:3mm; overflow:hidden; background:var(--accent); color:var(--head); }}
.title.poster .overlay {{ position:relative; display:flex; align-items:center; gap:4mm; padding:3mm 5mm; height:100%; background:linear-gradient(90deg, rgba(0,0,0,.5), rgba(0,0,0,0)); }}
.title.poster .m {{ font-family:{font['display']}; font-size:{fs(22)}; font-weight:800; }} .title.poster .y {{ font-size:{fs(14)}; }} .title.poster .sub {{ color:var(--head); opacity:.9; }}
.title.panchang {{ display:flex; align-items:center; gap:4mm; background:var(--accent); color:var(--head); border-radius:3mm; padding:2.5mm 5mm; }}
.title.panchang .pc {{ flex:1 1 auto; text-align:center; }} .title.panchang .m {{ font-family:{font['display']}; font-size:{fs(22)}; font-weight:800; }} .title.panchang .y {{ font-size:{fs(14)}; }} .title.panchang .sub {{ color:var(--head); opacity:.9; }}
.title.panchang .pr {{ text-align:right; font-weight:700; font-size:{fs(10)}; }} .title.panchang .pr .legend {{ color:var(--head); }} .title.panchang .logo {{ background:rgba(255,255,255,.92); padding:1.5mm; border-radius:2mm; }}
.title.compact {{ border-left:1.5mm solid var(--accent); padding-left:2.5mm; }} .title.compact .m {{ font-family:{font['display']}; font-size:{fs(16)}; font-weight:800; color:var(--accent); }} .title.compact .y {{ font-size:{fs(11)}; }}
.body {{ flex:1 1 auto; display:flex; gap:3mm; min-height:0; }} .body.col2 {{ display:block; overflow:hidden; }}
.grid {{ flex:1 1 auto; display:grid; grid-template-columns:repeat(7,1fr); gap:1.2mm; min-height:0; }}
.grid > .wd {{ background:var(--accent); color:var(--head); text-align:center; font-weight:700; padding:1.2mm 0; border-radius:1.5mm; font-size:{fs(9.5)}; letter-spacing:.3px; }}
.grid > .wd.sun {{ background:var(--sun); }}
table.list td.wd {{ font-weight:600; opacity:.85; }}
.cell {{ border:0.3mm solid var(--line); border-radius:1.8mm; padding:1.2mm 1.4mm; position:relative; overflow:hidden; display:flex; flex-direction:column; background:color-mix(in srgb, var(--paper) 70%, white); }}
.cell.hasfest {{ background:var(--tint); border-color:var(--tint2); }}
.cell.empty {{ border-color:transparent; background:transparent; }}
.cell .d {{ font-family:{font['display']}; font-size:{fs(17)}; font-weight:800; line-height:1; }}
.cell.sun .d, .cell.holiday .d {{ color:var(--sun); }}
.cell .t {{ font-size:{fs(8.3)}; font-weight:600; margin-top:.7mm; }} .cell .n {{ font-size:{fs(7.4)}; opacity:.85; }}
.cell .x, .x {{ font-size:{fs(7)}; opacity:.72; font-weight:500; }}
.cell .note {{ font-size:{fs(7.4)}; color:var(--accent); font-style:italic; }}
.cell .f {{ margin-top:auto; display:flex; flex-wrap:wrap; gap:.6mm; }}
.pill {{ display:inline-block; font-size:{fs(6.9)}; font-weight:700; padding:.3mm 1.3mm; border-radius:1.2mm; line-height:1.2; max-width:100%; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }}
.pill.festival {{ background:var(--fest); color:#fff; }} .pill.ekadashi {{ background:var(--tint2); color:var(--ink); }} .pill.purnima, .pill.amavasya {{ background:transparent; border:0.25mm solid var(--line); color:var(--ink); }}
.cell .mark {{ position:absolute; top:1mm; right:1.4mm; font-size:{fs(6.8)}; opacity:.7; }}
.side {{ flex:0 0 50mm; border-left:0.3mm solid var(--line); padding-left:3mm; font-size:{fs(8.4)}; overflow:hidden; }}
.side h3, .box h3 {{ margin:0 0 1.5mm; color:var(--accent); font-family:{font['display']}; font-size:{fs(10.5)}; }}
.side ul, .box ul {{ margin:0; padding:0; }} .side li, .box li {{ list-style:none; margin:0 0 .8mm; display:flex; gap:1.5mm; align-items:baseline; }} .side li.ekadashi {{ opacity:.75; }}
b.dt {{ display:inline-block; min-width:7mm; text-align:center; color:var(--head); background:var(--accent); border-radius:1.2mm; font-size:{fs(7.6)}; padding:.2mm 0; }}
li.festival b.dt {{ background:var(--fest); }}
.legend {{ font-size:{fs(7.4)}; opacity:.75; }}
.foot {{ flex:0 0 auto; display:flex; justify-content:space-between; align-items:center; gap:3mm; font-size:{fs(8.6)}; border-top:0.3mm solid var(--line); padding-top:1.2mm; }}
.foot .biz {{ font-weight:800; display:flex; align-items:center; gap:2mm; font-family:{font['display']}; }} .foot .logo {{ height:8mm; }}
table.list {{ width:100%; border-collapse:collapse; font-size:{fs(8.4)}; }}
table.list th {{ background:var(--accent); color:var(--head); text-align:left; padding:1.1mm 1.4mm; font-size:{fs(8.2)}; line-height:1.15; }}
table.list td {{ padding:.55mm 1.4mm; border-bottom:0.2mm solid var(--line); vertical-align:top; line-height:1.2; }}
table.list.full td {{ padding:.2mm 1mm; font-size:{fs(6.9)}; white-space:nowrap; line-height:1.15; }} table.list.full .x {{ font-size:{fs(6.1)}; }} table.list.full th {{ font-size:{fs(7)}; padding:.8mm 1mm; }} table.list.full td.dn {{ font-size:{fs(8.6)}; width:5mm; }} table.list.full td.fest {{ white-space:normal; }}
table.list td.dn {{ font-family:{font['display']}; font-weight:800; font-size:{fs(10.5)}; width:7mm; }} table.list tr.sun td.dn, table.list tr.sun td.wd, table.list tr.holiday td.dn {{ color:var(--sun); }}
table.list td.fest {{ color:var(--fest); font-weight:700; }} table.list td.fest i {{ color:var(--accent); font-weight:500; }} table.list td.fest .sp {{ color:var(--ink); font-weight:500; opacity:.8; }}
table.list tbody tr:nth-child(even) {{ background:color-mix(in srgb, var(--accent) 4%, transparent); }}
.boxes {{ flex:0 0 auto; display:grid; grid-template-columns:repeat(3,1fr); gap:3mm; }}
.boxes.year {{ flex:1 1 auto; grid-template-columns:repeat(2,1fr); align-content:start; }} .boxes.year .box {{ max-height:none; font-size:{fs(8.6)}; }} .mlist {{ columns:2; }} .mlist li {{ display:block; break-inside:avoid; }} .mlist b {{ color:var(--accent); display:inline-block; min-width:9mm; }}
.box {{ border:0.3mm solid var(--line); border-radius:2mm; padding:1.6mm 2.2mm; font-size:{fs(7.2)}; background:color-mix(in srgb, var(--accent) 3%, transparent); max-height:40mm; overflow:hidden; }} .box li {{ margin:0 0 .4mm; }} .box b.dt {{ min-width:5.5mm; font-size:{fs(6.6)}; }}
.box li b {{ color:var(--accent); }}
.pair {{ flex:1 1 auto; display:grid; grid-template-rows:1fr 1fr; gap:4mm; min-height:0; }}
.trio {{ flex:1 1 auto; display:grid; grid-template-rows:repeat(3,1fr); gap:3mm; min-height:0; }}
.third {{ display:flex; flex-direction:column; gap:1.5mm; min-height:0; }} .third .grid {{ gap:.6mm; }} .third .cell {{ padding:.6mm .8mm; }} .third .cell .d {{ font-size:{fs(10)}; }} .third .cell .t {{ font-size:{fs(6.4)}; }} .third .pill {{ font-size:{fs(6)}; }} .third .minilist {{ columns:3; font-size:{fs(6.8)}; }}
.pill.pradosh, .pill.chaturthi, .pill.shivaratri {{ background:transparent; border:0.25mm dashed var(--line); color:var(--ink); }}
.half {{ display:flex; flex-direction:column; gap:2mm; min-height:0; }} .half .grid {{ gap:.8mm; }} .half .cell {{ padding:.8mm 1mm; }} .half .cell .d {{ font-size:{fs(12)}; }} .half .cell .t {{ font-size:{fs(7)}; }}
.minilist {{ margin:0; padding:0; columns:3; font-size:{fs(7.6)}; }} .minilist li {{ list-style:none; }} .minilist b.dt {{ min-width:5mm; }}
.cover {{ flex:1 1 auto; display:flex; flex-direction:column; gap:4mm; min-height:0; }}
.hero.cover {{ position:relative; flex:1 1 45%; border-radius:4mm; overflow:hidden; background:linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 50%, #000)); min-height:40mm; }}
.coverhead {{ text-align:center; }} .coverhead .yr {{ font-family:{font['display']}; font-size:{fs(54)}; font-weight:900; color:var(--accent); line-height:1; }}
.coverhead .cm {{ font-family:{font['display']}; font-size:{fs(20)}; font-weight:700; }} .coverhead .cs {{ font-size:{fs(10.5)}; opacity:.8; }}
.minis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:3mm; }}
.mini .mm {{ font-weight:700; color:var(--accent); font-size:{fs(9)}; margin-bottom:.8mm; }}
.mini .mg {{ display:grid; grid-template-columns:repeat(7,1fr); gap:.3mm; font-size:{fs(6.6)}; text-align:center; }}
.mini .mg i {{ font-style:normal; font-weight:700; opacity:.6; }} .mini .mg i.s, .mini .mg b.s {{ color:var(--sun); }} .mini .mg b {{ font-weight:500; }} .mini .mg b.f {{ font-weight:800; color:var(--fest); }}
"""


def render_calendar(year: int, months: list[int], lat: float, lon: float, tz: str, design: dict, lang: str = "hi") -> str:
    hi = lang != "en"
    theme = dict(THEMES.get(str(design.get("theme") or "saffron"), THEMES["saffron"]))
    colors = {"accent": _col(design.get("accent"), theme["accent"]), "ink": _col(design.get("ink"), theme["ink"]), "paper": _col(design.get("paper"), theme["paper"]),
              "sunday": _col(design.get("sunday_color"), theme["sunday"]), "fest": _col(design.get("fest_color"), theme["fest"]), "head": _col(design.get("head_color"), "#ffffff")}
    size = SIZES.get(str(design.get("size") or "A4"), SIZES["A4"])
    font = FONTS.get(str(design.get("font") or "modern"), FONTS["modern"])
    try:
        scale = max(0.7, min(1.4, float(design.get("font_scale") or 1.0)))
    except (TypeError, ValueError):
        scale = 1.0
    tpl = str(design.get("template") or "classic")
    if tpl not in TEMPLATES:
        tpl = "classic"
    show = design.get("show") or {}
    sv = lambda k, d=True: show.get(k, d)
    data = [_month(year, mo, lat, lon, tz) for mo in months]
    pages = []
    if design.get("cover") and len(months) > 1:
        pages.append(tpl_cover(year, data, design, hi))
    if design.get("muhurta_page") and len(months) > 1:
        pages.append(tpl_muhurta_year(year, data, design, hi))
    if tpl == "compact":
        for i in range(0, len(data), 2):
            pages.append(tpl_compact_pair(data[i], data[i + 1] if i + 1 < len(data) else None, design, hi, sv))
    elif tpl == "quarter":
        for i in range(0, len(data), 3):
            pages.append(tpl_quarter(data[i:i + 3], design, hi, sv))
    else:
        fn = {"classic": tpl_classic, "modern": tpl_modern, "poster": tpl_poster, "panchang": tpl_panchang}[tpl]
        pages += [fn(m, design, hi, sv) for m in data]
    title = (design.get("business") or {}).get("name") or ("पंचांग कैलेंडर" if hi else "Panchang calendar")
    link = f'<link rel="stylesheet" href="{font["link"]}">' if font["link"] and design.get("web_fonts", True) else ""
    return (f'<!doctype html><html lang="{"hi" if hi else "en"}"><head><meta charset="utf-8"><title>{e(title)} {year}</title>{link}'
            f'<style>{_css(colors, size, scale, font)}</style></head><body>{"".join(pages)}'
            '<script>(function(){function fit(){if(matchMedia("print").matches)return;var p=document.querySelector(".page");if(!p)return;var z=Math.min(1,(window.innerWidth-16)/p.offsetWidth);document.body.style.zoom=z;}'
            'window.addEventListener("resize",fit);window.addEventListener("beforeprint",function(){document.body.style.zoom=1;});window.addEventListener("afterprint",fit);fit();})();</script></body></html>')
