"""Shareable panchang image card (PNG, 1080×1350 — WhatsApp/Instagram portrait) drawn with Pillow.

Fonts: a Devanagari-capable TrueType is searched in data/fonts/, then the system (Noto Sans Devanagari, FreeSans). Pillow's
raqm layout (bundled in the wheels) shapes Devanagari correctly. The card shows the date, vara, tithi (with end time and the
next tithi), nakshatra, yoga, karana, month/samvat, sunrise/sunset/moonrise, Rahu kaal / Abhijit / good choghadiya, special
yogas and the day's festivals, with the business name/tagline in the footer (same `business` dict as the calendar studio).
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
_FONT_CANDIDATES = [ROOT / "data" / "fonts" / "NotoSansDevanagari-Regular.ttf", ROOT / "data" / "fonts" / "NotoSerifDevanagari-Regular.ttf",
                    Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"), Path("/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf"),
                    Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"), Path("/usr/share/fonts/truetype/freefont/FreeSerif.ttf"),
                    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
_FONT_BOLD = [ROOT / "data" / "fonts" / "NotoSansDevanagari-Bold.ttf", Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"),
              Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]
THEMES = {"saffron": ("#fff6e8", "#b4541a", "#2b1d12", "#f3dcc2"), "maroon": ("#fbf3f0", "#7a1f2b", "#2a1216", "#f0d3cf"),
          "green": ("#f1f8f2", "#1f6b3a", "#102416", "#cfe8d6"), "blue": ("#eef3fb", "#1f4b8f", "#0f1b33", "#d2def3"), "dark": ("#1b1510", "#f0a060", "#f5ead9", "#3a2d22")}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for p in (_FONT_BOLD if bold else []) + _FONT_CANDIDATES:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                continue
    return ImageFont.load_default()


def font_available() -> bool:
    return any(p.exists() for p in _FONT_CANDIDATES[:6])


def _txt(draw, xy, text, font, fill, anchor="la", maxw=None):
    if maxw:
        while font.size > 14 and draw.textlength(text, font=font) > maxw:
            font = _font(font.size - 2, bold="Bold" in (font.path or ""))
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)
    return font


def render_panchang_card(day: dict, d: date, place: str = "", lang: str = "hi", business: dict | None = None, theme: str = "saffron", size: tuple[int, int] = (1080, 1350)) -> bytes:
    hi = lang != "en"
    bg, accent, ink, soft = THEMES.get(theme, THEMES["saffron"])
    W, H = size
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    # header band
    dr.rounded_rectangle((40, 40, W - 40, 300), 36, fill=accent)
    f_big, f_h1, f_h2, f_b, f_s = _font(64, True), _font(44, True), _font(36, True), _font(32), _font(26)
    vara = day["vara_hi"] if hi else day["vara"]
    _txt(dr, (W // 2, 105), f"{d.strftime('%d')} {d.strftime('%B') if not hi else ['जनवरी', 'फ़रवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर'][d.month - 1]} {d.year}", f_big, "#fff", "mm")
    _txt(dr, (W // 2, 180), vara + (f"  ·  {place}" if place else ""), f_h1, "#fff", "mm", maxw=W - 140)
    masa = (day["masa_purnimanta_hi"] if hi else day["masa_purnimanta"]) + (" (पूर्णिमांत)" if hi else " (purnimanta)")
    _txt(dr, (W // 2, 245), f"{masa}  ·  {'विक्रम संवत' if hi else 'Vikram samvat'} {day['vikram_samvat']}  ·  {'शक' if hi else 'Shaka'} {day['shaka_samvat']}", f_s, "#fff", "mm", maxw=W - 140)
    # tithi block
    y = 340
    paksha = day["paksha_hi"] if hi else day["paksha"]; tithi = day["tithi_hi"] if hi else day["tithi"]
    nxt = ("अगले दिन" if hi else "next day") if day.get("tithi_ends_next_day") else ""
    dr.rounded_rectangle((40, y, W - 40, y + 150), 28, fill=soft)
    _txt(dr, (70, y + 30), ("तिथि" if hi else "Tithi"), f_s, accent)
    _txt(dr, (70, y + 70), f"{paksha} {tithi}", f_h1, ink, maxw=W - 420)
    _txt(dr, (W - 70, y + 70), (f"{day['tithi_ends'] or '—'} {nxt} तक" if hi else f"until {day['tithi_ends'] or '—'} {nxt}"), f_h2, ink, "ra")
    y += 180
    # 2x2 grid: nakshatra, yoga/karana, sun, moon
    cells = [((("नक्षत्र" if hi else "Nakshatra"), (day["nakshatra_hi"] if hi else day["nakshatra"]), (f"{day['nakshatra_ends'] or '—'}{'+' if day.get('nakshatra_ends_next_day') else ''} {'तक' if hi else 'until'}"))),
             ((("योग · करण" if hi else "Yoga · Karana"), (day["yoga_hi"] if hi else day["yoga"]), (day["karana_hi"] if hi else day["karana"]))),
             ((("सूर्योदय · सूर्यास्त" if hi else "Sunrise · Sunset"), f"{day['sunrise']} · {day['sunset']}", (f"{'दिनमान' if hi else 'day length'} {day.get('day_length', '')}" if day.get("day_length") else ""))),
             ((("चंद्रोदय · चंद्र राशि" if hi else "Moonrise · Moon sign"), f"{day['moonrise'] or '—'} · {day['moon_sign_hi'] if hi else day['moon_sign']}", (f"{'चंद्रास्त' if hi else 'moonset'} {day['moonset']}" if day.get("moonset") else "")))]
    cw, ch = (W - 100) // 2, 150
    for i, (lbl, val, sub) in enumerate(cells):
        x0 = 40 + (i % 2) * (cw + 20); y0 = y + (i // 2) * (ch + 20)
        dr.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), 24, fill="#ffffff" if theme != "dark" else "#241c15", outline=soft, width=2)
        _txt(dr, (x0 + 26, y0 + 22), lbl, f_s, accent)
        _txt(dr, (x0 + 26, y0 + 62), val, f_h2, ink, maxw=cw - 52)
        if sub:
            _txt(dr, (x0 + 26, y0 + 108), sub, f_s, "#6b5a48" if theme != "dark" else "#b9a58e", maxw=cw - 52)
    y += 2 * (ch + 20) + 10
    # kaal line
    rk, ab = day.get("rahu_kaal"), day.get("abhijit")
    chog = ", ".join(f"{c.get('name_hi') if hi else c.get('name')} {c['start']}–{c['end']}" for c in (day.get("good_choghadiya") or [])[:3])
    lines = [(("राहु काल" if hi else "Rahu kaal"), f"{rk['start']}–{rk['end']}" if rk else "—", ("अभिजित" if hi else "Abhijit"), f"{ab['start']}–{ab['end']}" if ab else "—")]
    dr.rounded_rectangle((40, y, W - 40, y + 110), 24, fill=soft)
    _txt(dr, (70, y + 22), f"✕ {lines[0][0]}  {lines[0][1]}", f_b, ink)
    _txt(dr, (W - 70, y + 22), f"✓ {lines[0][2]}  {lines[0][3]}", f_b, ink, "ra")
    if chog:
        _txt(dr, (70, y + 68), ("शुभ चौघड़िया: " if hi else "Good choghadiya: ") + chog, f_s, ink, maxw=W - 140)
    y += 140
    # special + festivals
    sp = " · ".join(x["hi"] if hi else x["en"] for x in (day.get("special") or [])[:4])
    ev = [x["name_hi"] if hi else x["name_en"] for x in day.get("events", []) if x["kind"] in ("grahan", "festival", "ekadashi", "purnima", "amavasya", "pradosh", "national", "regional")]
    if sp:
        _txt(dr, (70, y), "✦ " + sp, f_b, accent, maxw=W - 140); y += 50
    if ev:
        _txt(dr, (70, y), "❖ " + (", ".join(ev[:4])), f_h2, ink, maxw=W - 140); y += 60
    if day.get("varjyam") or day.get("amrit_kalam"):
        v = ", ".join(f"{w['start']}–{w['end']}" for w in (day.get("varjyam") or [])) or "—"
        a = f"{day['amrit_kalam']['start']}–{day['amrit_kalam']['end']}" if day.get("amrit_kalam") else "—"
        _txt(dr, (70, y), (f"वर्ज्य {v}  ·  अमृत काल {a}" if hi else f"Varjyam {v}  ·  Amrit kalam {a}"), f_s, "#6b5a48" if theme != "dark" else "#b9a58e", maxw=W - 140); y += 44
    # footer
    b = business or {}
    dr.rectangle((40, H - 150, W - 40, H - 40), fill=accent)
    name = b.get("name") or ("कुंडली ऐप" if hi else "Kundali app")
    _txt(dr, (70, H - 118), name, f_h2, "#fff", maxw=W - 300)
    tag = b.get("tagline") or b.get("line") or ("आज का पंचांग · लाहिड़ी अयनांश" if hi else "Today's panchang · Lahiri ayanamsa")
    _txt(dr, (70, H - 72), tag, f_s, "#fff", maxw=W - 300)
    if b.get("website") or b.get("contact"):
        _txt(dr, (W - 70, H - 95), b.get("website") or b.get("contact"), f_s, "#fff", "rm", maxw=360)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- kundali card (chart image + key facts)
def _draw_north(dr, cells, x0, y0, S, accent, ink, soft, f_sign, f_pl):
    from .report import _HOUSES
    k = S / 400.0
    for h in range(1, 13):
        pts, (cx, cy) = _HOUSES[h]
        dr.polygon([(x0 + x * k, y0 + y * k) for x, y in pts], outline=accent, width=3)
        cell = cells[h - 1]
        dr.text((x0 + cx * k, y0 + (cy - 18) * k), str(cell["sign"] + 1), font=f_sign, fill="#8a7a64", anchor="mm")
        pl = cell["planets"]
        for i, (short, retro) in enumerate(pl):
            col, row = i % 3, i // 3
            n = min(3, len(pl) - row * 3)
            px = x0 + (cx + (col - (n - 1) / 2) * 26) * k
            py = y0 + (cy + 10 + row * 22) * k
            dr.text((px, py), short + ("ᵛ" if retro else ""), font=f_pl, fill=ink, anchor="mm")


def _draw_south(dr, cells, x0, y0, S, accent, ink, soft, f_sign, f_pl):
    from .report import _SOUTH_POS
    c = S / 4.0
    for i, cell in enumerate(cells):
        col, row = _SOUTH_POS[cell["sign"]]
        x, y = x0 + col * c, y0 + row * c
        dr.rectangle((x, y, x + c, y + c), outline=accent, width=3)
        if i == 0:
            dr.line((x, y, x + c * 0.28, y + c * 0.28), fill=accent, width=3)
        dr.text((x + c - 10, y + 16), str(cell["sign"] + 1), font=f_sign, fill="#8a7a64", anchor="rm")
        pl = cell["planets"]
        for k, (short, retro) in enumerate(pl):
            cc, rr = k % 3, k // 3
            n = min(3, len(pl) - rr * 3)
            dr.text((x + c / 2 + (cc - (n - 1) / 2) * 26 * (S / 400.0), y + c * 0.45 + rr * 22 * (S / 400.0)), short + ("ᵛ" if retro else ""), font=f_pl, fill=ink, anchor="mm")


def render_kundali_card(chart: dict, lang: str = "hi", business: dict | None = None, theme: str = "saffron", style: str = "north", size: tuple[int, int] = (1080, 1350)) -> bytes:
    from .report import _d1_cells
    hi = lang != "en"
    bg, accent, ink, soft = THEMES.get(theme, THEMES["saffron"])
    W, H = size
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    f_big, f_h1, f_h2, f_b, f_s = _font(56, True), _font(40, True), _font(32, True), _font(28), _font(24)
    inp = chart["input"]
    name = inp.get("name") or ("जन्म कुंडली" if hi else "Birth chart")
    dr.rounded_rectangle((40, 40, W - 40, 230), 36, fill=accent)
    _txt(dr, (W // 2, 100), name, f_big, "#fff", "mm", maxw=W - 140)
    _txt(dr, (W // 2, 170), f"{inp['date']}  ·  {inp['time']}  ·  {inp.get('place') or (str(inp['lat']) + ', ' + str(inp['lon']))}", f_s, "#fff", "mm", maxw=W - 140)
    # chart
    S = 620
    x0 = (W - S) // 2; y0 = 270
    dr.rounded_rectangle((x0 - 20, y0 - 20, x0 + S + 20, y0 + S + 20), 28, fill="#ffffff" if theme != "dark" else "#241c15", outline=soft, width=2)
    cells = _d1_cells(chart)
    (_draw_south if style == "south" else _draw_north)(dr, cells, x0, y0, S, accent, ink, soft, _font(20), _font(26, True))
    # facts
    y = y0 + S + 50
    lg = chart["lagna"]; moon = next(p for p in chart["planets"] if p["name"] == "Moon"); sun = next(p for p in chart["planets"] if p["name"] == "Sun")
    run = chart.get("dasha_running") or []
    from .constants import PLANETS_HI
    dasha = " › ".join((PLANETS_HI[r["lord"]] if hi else r["lord"]) + f" ({r['end'][8:10]}-{r['end'][5:7]}-{r['end'][:4]})" for r in run[:2])
    rows = [((("लग्न" if hi else "Lagna"), f"{lg['sign_name_hi'] if hi else lg['sign_name']} · {lg['nakshatra_hi'] if hi else lg['nakshatra']}")),
            ((("चंद्र राशि · नक्षत्र" if hi else "Moon sign · nakshatra"), f"{moon['sign_name_hi'] if hi else moon['sign_name']} · {moon['nakshatra_hi'] if hi else moon['nakshatra']} ({moon['pada']})")),
            ((("सूर्य राशि" if hi else "Sun sign"), (sun["sign_name_hi"] if hi else sun["sign_name"]))),
            ((("चल रही दशा" if hi else "Running dasha"), dasha or "—"))]
    cw = (W - 100) // 2
    for i, (lbl, val) in enumerate(rows):
        xx = 40 + (i % 2) * (cw + 20); yy = y + (i // 2) * 120
        dr.rounded_rectangle((xx, yy, xx + cw, yy + 100), 22, fill=soft)
        _txt(dr, (xx + 24, yy + 18), lbl, f_s, accent)
        _txt(dr, (xx + 24, yy + 54), val, f_h2, ink, maxw=cw - 48)
    y += 2 * 120 + 10
    yp = [yg for yg in chart.get("yogas", []) if yg.get("present")][:4]
    if yp:
        _txt(dr, (60, y), ("योग: " if hi else "Yogas: ") + ", ".join((yg.get("name_hi") if hi else yg.get("name")) for yg in yp), f_b, ink, maxw=W - 120)
    b = business or {}
    dr.rectangle((40, H - 130, W - 40, H - 40), fill=accent)
    _txt(dr, (70, H - 105), b.get("name") or ("कुंडली ऐप" if hi else "Kundali app"), f_h2, "#fff", maxw=W - 320)
    _txt(dr, (70, H - 66), b.get("tagline") or ("लाहिड़ी अयनांश · संपूर्ण राशि भाव" if hi else "Lahiri ayanamsa · whole-sign houses"), f_s, "#fff", maxw=W - 320)
    if b.get("website"):
        _txt(dr, (W - 70, H - 85), b["website"], f_s, "#fff", "rm", maxw=320)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
