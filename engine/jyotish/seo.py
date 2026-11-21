"""Server-rendered, search-engine friendly pages (no JavaScript needed to read them):

    /panchang                 today's panchang (Delhi), /panchang/<city> for 24 big cities
    /rashifal                 today's rashifal for all 12 signs, /rashifal/<sign> one sign (daily + weekly + monthly)
    /tyohar/<year>            every vrat and festival of the year, /tyohar/<year>/<key> one festival with its tithi window
    /sitemap.xml, /robots.txt

Each page has a title, description, canonical URL, Open Graph tags and JSON-LD, and links into the app.
Rendered pages are cached per day (they depend only on the date)."""
from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import handlers

IST = ZoneInfo("Asia/Kolkata")
SIGNS = [("mesh", "मेष", "Aries"), ("vrishabh", "वृषभ", "Taurus"), ("mithun", "मिथुन", "Gemini"), ("kark", "कर्क", "Cancer"), ("singh", "सिंह", "Leo"),
         ("kanya", "कन्या", "Virgo"), ("tula", "तुला", "Libra"), ("vrishchik", "वृश्चिक", "Scorpio"), ("dhanu", "धनु", "Sagittarius"), ("makar", "मकर", "Capricorn"),
         ("kumbh", "कुंभ", "Aquarius"), ("meen", "मीन", "Pisces")]
GLYPH = "♈♉♊♋♌♍♎♏♐♑♒♓"
CITIES = ["Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru", "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Patna", "Bhopal", "Indore",
          "Jabalpur", "Varanasi", "Nagpur", "Raipur", "Ranchi", "Chandigarh", "Dehradun", "Surat", "Kanpur", "Guwahati", "Bhubaneswar"]
MAJOR_KINDS = ("festival", "national", "grahan", "shivaratri")
_CACHE: dict = {}


def site() -> str:
    return os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com").rstrip("/")


def today() -> date:
    return datetime.now(IST).date()


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _dmy(d: str) -> str:
    y, m, dd = d.split("-"); return f"{dd}-{m}-{y}"


_HI_MONTH = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
_HI_DAY = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]


def hi_date(d: str) -> str:
    x = date.fromisoformat(d); return f"{x.day} {_HI_MONTH[x.month - 1]} {x.year}, {_HI_DAY[x.weekday()]}"


CSS = """
:root{--bg:#fbf6ef;--card:#fff;--ink:#2a1d14;--muted:#7a6a5c;--line:#ecdccb;--accent:#c2541b;--gold:#f3a23a}
@media (prefers-color-scheme:dark){:root{--bg:#15110d;--card:#1f1913;--ink:#f3e9dd;--muted:#b3a38f;--line:#3a2f24;--accent:#f39a5a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 "Noto Sans Devanagari","Noto Sans",system-ui,sans-serif}
a{color:var(--accent)}header{background:linear-gradient(160deg,#130d2e,#22154a 55%,#3a1c3c);color:#fff;padding:14px 16px}
header .in,main,footer .in{max-width:980px;margin:0 auto}header a{color:#ffd27a;text-decoration:none;font-weight:700}
header nav{display:flex;gap:14px;flex-wrap:wrap;font-size:.92rem;margin-top:6px}header nav a{color:#e4d8f3;font-weight:500}
.hero{padding:22px 0 8px}.hero h1{margin:0 0 6px;font-size:1.9rem;line-height:1.25}.hero p{margin:0;color:var(--muted)}
.crumb{font-size:.85rem;color:var(--muted);margin-top:14px}.crumb a{color:var(--muted)}
main{padding:0 16px 30px}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:6px 18px}.kv b{font-weight:600}.kv span{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:.95rem}td,th{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.sign{display:flex;gap:12px;align-items:flex-start;text-decoration:none;color:inherit}.sign .g{font-size:1.9rem;line-height:1;color:var(--gold)}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent);font-size:.8rem;font-weight:600}
.cta{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;padding:10px 18px;border-radius:12px;font-weight:700;margin:6px 8px 0 0}
.muted{color:var(--muted)}.en{color:var(--muted);font-size:.9rem}footer{border-top:1px solid var(--line);padding:18px 16px;font-size:.85rem;color:var(--muted)}
h2{font-size:1.25rem;margin:0 0 8px}ul{padding-left:20px}
"""


def page(path: str, title: str, desc: str, body: str, crumbs: list[tuple[str, str]], ld: list[dict] | None = None) -> str:
    url = site() + path
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": site() + u} for i, (n, u) in enumerate([("होम", "/")] + crumbs)]}
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in [bc] + (ld or []))
    crumb_html = " › ".join([f'<a href="/">होम</a>'] + [f'<a href="{e(u)}">{e(n)}</a>' for n, u in crumbs])
    return f"""<!doctype html><html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(site())}/icons/icon-512.png"><meta name="theme-color" content="#22154a"><link rel="icon" href="/icons/icon-192.png">
<link rel="manifest" href="/manifest.webmanifest"><style>{CSS}</style>{lds}</head><body>
<header><div class="in"><a href="/">🪔 कुंडली · पंचांग</a><nav><a href="/panchang">आज का पंचांग</a><a href="/rashifal">राशिफल</a><a href="/tyohar/{today().year}">व्रत-त्योहार {today().year}</a><a href="/ratna">राशि रत्न</a><a href="/">कुंडली बनाइए</a></nav></div></header>
<main><div class="crumb">{crumb_html}</div>{body}
<div class="card"><b>अपनी जन्म कुंडली, दशा और दैनिक फल निःशुल्क देखिए</b><br><a class="cta" href="/">कुंडली बनाइए →</a><a class="cta" style="background:#2e9d5b" href="/#wa">WhatsApp पर रोज़ पंचांग</a></div></main>
<footer><div class="in">गणना: NASA JPL DE440s, लाहिरी अयनांश। फलादेश परंपरागत मार्गदर्शन है, भविष्यवाणी या पेशेवर सलाह नहीं। · <a href="/panchang">पंचांग</a> · <a href="/rashifal">राशिफल</a> · <a href="/tyohar/{today().year}">त्योहार</a> · <a href="/privacy">गोपनीयता</a> · <a href="/terms">शर्तें</a> · <a href="/sitemap.xml">sitemap</a></div></footer>
</body></html>"""


def _cached(key, fn):
    k = (key, today().isoformat())
    if k not in _CACHE:
        if len(_CACHE) > 400:
            _CACHE.clear()
        _CACHE[k] = fn()
    return _CACHE[k]


def _city(slug: str | None):
    if not slug:
        return {"name": "Delhi", "hi": "दिल्ली", "lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata"}
    name = next((c for c in CITIES if c.lower() == slug.lower()), None)
    if not name:
        return None
    r = handlers.places_from_query(name, 1).get("results") or []
    return r[0] if r else None


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ------------------------------------------------------------------ pages
def panchang_page(city_slug: str | None = None) -> str | None:
    c = _city(city_slug)
    if c is None:
        return None

    def build():
        d = today().isoformat()
        p = handlers.panchang_today_from_query({"date": d, "lat": c["lat"], "lon": c["lon"], "tz": c["tz"]})
        nxt = lambda flag: " (अगले दिन)" if flag else ""
        rows = [("वार", p.get("vara_hi")), ("तिथि", f"{p.get('tithi_hi')} — {p.get('tithi_ends') or ''} तक{nxt(p.get('tithi_ends_next_day'))}"),
                ("नक्षत्र", f"{p.get('nakshatra_hi')} — {p.get('nakshatra_ends') or ''} तक{nxt(p.get('nakshatra_ends_next_day'))}"),
                ("योग", p.get("yoga_hi")), ("करण", p.get("karana_hi")), ("पक्ष", p.get("paksha_hi")),
                ("मास (अमांत / पूर्णिमांत)", f"{p.get('masa_amanta_hi')} / {p.get('masa_purnimanta_hi')}"), ("विक्रम संवत", p.get("vikram_samvat")),
                ("सूर्योदय · सूर्यास्त", f"{p.get('sunrise')} · {p.get('sunset')}"), ("चंद्रोदय · चंद्रास्त", f"{p.get('moonrise') or '—'} · {p.get('moonset') or '—'}"),
                ("सूर्य राशि · चंद्र राशि", f"{p.get('sun_sign_hi')} · {p.get('moon_sign_hi')}"),
                ("राहु काल", _span(p.get("rahu_kaal"))), ("यमगंड", _span(p.get("yamaganda"))), ("गुलिक काल", _span(p.get("gulika"))),
                ("अभिजित मुहूर्त", _span(p.get("abhijit"))), ("दिशा शूल", p.get("disha_shool_hi"))]
        kv = "".join(f"<b>{e(k)}</b><span>{e(v)}</span>" for k, v in rows if v)
        ev = p.get("events") or []
        evs = "".join(f"<li>{e(x.get('name_hi'))} <span class='en'>{e(x.get('name_en'))}</span></li>" for x in ev)
        others = " · ".join(f'<a href="/panchang/{k.lower()}">{e(_hi_of(k))}</a>' for k in CITIES if k.lower() != (city_slug or "delhi").lower())
        title = f"आज का पंचांग {c['hi']} — {hi_date(d)} | तिथि, नक्षत्र, राहु काल"
        desc = f"{hi_date(d)} का {c['hi']} पंचांग: {p.get('tithi_hi')} ({p.get('tithi_ends')} तक), {p.get('nakshatra_hi')} नक्षत्र, सूर्योदय {p.get('sunrise')}, राहु काल {_span(p.get('rahu_kaal'))}।"
        body = (f"<div class='hero'><h1>आज का पंचांग — {e(c['hi'])}</h1><p>{e(hi_date(d))} · <span class='en'>Today's panchang for {e(c['name'])}</span></p></div>"
                f"<div class='card'><div class='kv'>{kv}</div></div>"
                + (f"<div class='card'><h2>आज के व्रत-पर्व</h2><ul>{evs}</ul></div>" if evs else "")
                + f"<div class='card'><h2>दूसरे शहरों का पंचांग</h2><p>{others}</p><p class='muted'>किसी भी शहर, किसी भी तारीख का पंचांग और चौघड़िया ऐप में देखिए।</p></div>")
        path = "/panchang" + (f"/{city_slug.lower()}" if city_slug else "")
        return page(path, title, desc, body, [("पंचांग", "/panchang")] + ([(c["hi"], path)] if city_slug else []))
    return _cached(("panchang", (city_slug or "").lower()), build)


def _hi_of(city: str) -> str:
    r = handlers.places_from_query(city, 1).get("results") or []
    return r[0]["hi"] if r else city


def _span(o) -> str:
    return f"{o.get('start')}–{o.get('end')}" if isinstance(o, dict) and o.get("start") else ""


def rashifal_index() -> str:
    def build():
        d = today().isoformat(); r = handlers.rashifal_from_query({"date": d})
        cards = ""
        for s in r["signs"]:
            slug, hi, en = SIGNS[s["sign"]]
            cards += (f"<a class='card sign' href='/rashifal/{slug}'><span class='g'>{GLYPH[s['sign']]}</span><span><b>{e(hi)} राशिफल</b> <span class='pill'>{e(s['grade_hi'])}</span><br>"
                      f"<span class='muted'>{e(s['summary_hi'])}</span></span></a>")
        title = f"आज का राशिफल — {hi_date(d)} | मेष से मीन तक सभी 12 राशियाँ"
        desc = f"{hi_date(d)} का दैनिक राशिफल: मेष, वृषभ, मिथुन, कर्क, सिंह, कन्या, तुला, वृश्चिक, धनु, मकर, कुंभ, मीन — गोचर के आधार पर। शुभ रंग {r.get('lucky_colour_hi')}, शुभ अंक {r.get('lucky_number')}।"
        body = (f"<div class='hero'><h1>आज का राशिफल</h1><p>{e(hi_date(d))} · शुभ रंग: {e(r.get('lucky_colour_hi'))} · शुभ अंक: {e(r.get('lucky_number'))}</p></div>"
                f"<div class='grid'>{cards}</div><p class='muted'>{e(r.get('note_hi'))}</p>")
        return page("/rashifal", title, desc, body, [("राशिफल", "/rashifal")])
    return _cached(("rashifal", ""), build)


def rashifal_sign(slug: str) -> str | None:
    i = next((k for k, s in enumerate(SIGNS) if s[0] == slug.lower()), None)
    if i is None:
        return None

    def build():
        d = today().isoformat(); _, hi, en = SIGNS[i]
        parts = ""
        lead = None
        for period, label in (("daily", "आज"), ("weekly", "इस सप्ताह"), ("monthly", "इस माह")):
            r = handlers.rashifal_from_query({"date": d, "period": period}); s = r["signs"][i]
            lead = lead or s
            li = "".join(f"<li>{e(p['text_hi'])}</li>" for p in s.get("planets", []))
            parts += (f"<div class='card'><h2>{label} का {e(hi)} राशिफल <span class='pill'>{e(s['grade_hi'])} · {s['score']}/100</span></h2>"
                      f"<p>{e(s['summary_hi'])}</p><ul>{li}</ul><p class='en'>{e(s['summary_en'])}</p></div>")
        nav = " · ".join(f'<a href="/rashifal/{s[0]}">{e(s[1])}</a>' for s in SIGNS if s[0] != slug.lower())
        title = f"{hi} राशिफल आज — {hi_date(d)} | {en} horoscope today"
        desc = f"{hi} राशि ({en}) का आज, इस सप्ताह और इस माह का राशिफल ({hi_date(d)}): {lead['summary_hi']}"
        body = (f"<div class='hero'><h1>{GLYPH[i]} {e(hi)} राशिफल</h1><p>{e(hi_date(d))} · <span class='en'>{e(en)} horoscope — daily, weekly, monthly</span></p></div>"
                + parts + f"<div class='card'><h2>दूसरी राशियाँ</h2><p>{nav}</p><p class='muted'>यह चंद्र राशि से गोचर पर आधारित सामान्य फल है; आपकी अपनी कुंडली का दिन-स्कोर ऐप के डैशबोर्ड में देखिए।</p></div>")
        return page(f"/rashifal/{slug.lower()}", title, desc, body, [("राशिफल", "/rashifal"), (hi, f"/rashifal/{slug.lower()}")],
                    [{"@context": "https://schema.org", "@type": "Article", "headline": title, "datePublished": d, "inLanguage": "hi", "about": f"{hi} राशि ({en})"}])
    return _cached(("sign", slug.lower()), build)


def _events(year: int):
    return handlers.festivals_from_query({"year": year})["events"]


def _fkey(ev) -> str:
    return re.sub(r"_\d{4}-\d{2}-\d{2}$", "", ev["key"]).replace("_", "-")


def festivals_year(year: int) -> str | None:
    if not 1950 <= year <= 2099:
        return None

    def build():
        evs = _events(year); months: dict = {}
        for ev in evs:
            months.setdefault(int(ev["date"][5:7]), []).append(ev)
        host = site().split("//")[-1]
        gcal = "https://calendar.google.com/calendar/render?cid=" + urllib.parse.quote(f"webcal://{host}/tyohar/{year}.ics", safe="")
        body = (f"<div class='hero'><h1>व्रत-त्योहार {year}</h1><p>{year} के सभी प्रमुख त्योहार, एकादशी, पूर्णिमा, अमावस्या, प्रदोष और ग्रहण — तिथि सहित (दिल्ली सूर्योदय के अनुसार)</p></div>"
                f"<div class='card'><b>📅 अपने फ़ोन के कैलेंडर में जोड़िए</b> — सारे व्रत-त्योहार अपने-आप दिखेंगे।<br>"
                f"<a class='cta' href='{e(gcal)}' rel='nofollow'>Google Calendar में जोड़ें</a><a class='cta' style='background:#444' href='webcal://{e(host)}/tyohar/{year}.ics' rel='nofollow'>iPhone / Outlook</a>"
                f"<a class='cta' style='background:#777' href='/tyohar/{year}.ics' rel='nofollow'>.ics डाउनलोड</a></div>")
        for m in sorted(months):
            rows = ""
            for ev in months[m]:
                name = e(ev["name_hi"])
                if ev["kind"] in MAJOR_KINDS:
                    name = f"<a href='/tyohar/{year}/{_fkey(ev)}'>{name}</a>"
                rows += f"<tr><td style='white-space:nowrap'>{e(_dmy(ev['date']))}</td><td>{name} <span class='en'>{e(ev['name_en'])}</span></td><td class='muted'>{e(ev.get('tithi_hi') or '')}</td></tr>"
            body += f"<div class='card'><h2>{_HI_MONTH[m - 1]} {year}</h2><table>{rows}</table></div>"
        body += f"<p><a href='/tyohar/{year - 1}'>← {year - 1}</a> · <a href='/tyohar/{year + 1}'>{year + 1} →</a></p>"
        title = f"व्रत-त्योहार {year} कैलेंडर — एकादशी, पूर्णिमा, अमावस्या, ग्रहण की तारीखें"
        desc = f"{year} के सभी हिंदू व्रत और त्योहार: होली, रक्षाबंधन, जन्माष्टमी, नवरात्रि, दशहरा, दीपावली, छठ, एकादशी, पूर्णिमा व अमावस्या की तारीख और तिथि।"
        return page(f"/tyohar/{year}", title, desc, body, [(f"त्योहार {year}", f"/tyohar/{year}")])
    return _cached(("year", year), build)


def festival_page(year: int, key: str) -> str | None:
    if not 1950 <= year <= 2099:
        return None
    ev = next((x for x in _events(year) if _fkey(x) == key and x["kind"] in MAJOR_KINDS), None)
    if ev is None:
        return None

    def build():
        p = handlers.panchang_today_from_query({"date": ev["date"], "lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata"})
        prev = next((x for x in _events(year - 1) if _fkey(x) == key), None) if year > 1950 else None
        nxt = next((x for x in _events(year + 1) if _fkey(x) == key), None) if year < 2099 else None
        rows = [("तारीख", hi_date(ev["date"])), ("मास", ev.get("masa_hi")), ("तिथि", ev.get("tithi_hi")),
                ("उस दिन की तिथि", f"{p.get('tithi_hi')} — {p.get('tithi_ends')} तक" + (" (अगले दिन)" if p.get("tithi_ends_next_day") else "")),
                ("नक्षत्र", f"{p.get('nakshatra_hi')} — {p.get('nakshatra_ends')} तक"), ("सूर्योदय · सूर्यास्त", f"{p.get('sunrise')} · {p.get('sunset')}"),
                ("राहु काल", _span(p.get("rahu_kaal"))), ("अभिजित मुहूर्त", _span(p.get("abhijit")))]
        kv = "".join(f"<b>{e(k)}</b><span>{e(v)}</span>" for k, v in rows if v)
        other = " · ".join(f"<a href='/tyohar/{x['date'][:4]}/{key}'>{e(ev['name_hi'])} {x['date'][:4]}: {e(_dmy(x['date']))}</a>" for x in (prev, nxt) if x)
        note = ev.get("note_hi") or ""
        title = f"{ev['name_hi']} {year} कब है? तारीख, तिथि और शुभ मुहूर्त | {ev['name_en']} {year}"
        desc = f"{ev['name_hi']} {year}: {hi_date(ev['date'])}। {ev.get('tithi_hi') or ''}, उस दिन सूर्योदय {p.get('sunrise')}, राहु काल {_span(p.get('rahu_kaal'))} (दिल्ली)।"
        body = (f"<div class='hero'><h1>{e(ev['name_hi'])} {year}</h1><p>{e(hi_date(ev['date']))} · <span class='en'>{e(ev['name_en'])} {year}: {e(ev['date'])}</span></p></div>"
                f"<div class='card'><div class='kv'>{kv}</div>{('<p>' + e(note) + '</p>') if note else ''}<p class='muted'>समय दिल्ली के लिए हैं; अपने शहर के समय ऐप के पंचांग में देखिए। व्रत प्रायः सूर्योदय-कालीन तिथि से माना जाता है — स्थानीय परंपरा के अनुसार एक दिन का अंतर संभव है।</p></div>"
                + (f"<div class='card'><h2>दूसरे वर्ष</h2><p>{other}</p></div>" if other else "")
                + f"<p><a href='/tyohar/{year}'>← {year} के सभी व्रत-त्योहार</a></p>")
        ld = [{"@context": "https://schema.org", "@type": "Event", "name": f"{ev['name_en']} {year}", "alternateName": ev["name_hi"], "startDate": ev["date"],
               "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "eventStatus": "https://schema.org/EventScheduled",
               "location": {"@type": "Place", "name": "India", "address": "India"}, "description": desc}]
        return page(f"/tyohar/{year}/{key}", title, desc, body, [(f"त्योहार {year}", f"/tyohar/{year}"), (ev["name_hi"], f"/tyohar/{year}/{key}")], ld)
    return _cached(("fest", year, key), build)


def festivals_ics(year: int) -> str | None:
    """All-day calendar events for every vrat/festival of the year — subscribe once in Google/Apple/Outlook calendar."""
    if not 1950 <= year <= 2099:
        return None
    def esc_ics(t: str) -> str:
        return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    def fold(line: str) -> str:
        b = line.encode("utf-8"); out = []
        while len(b) > 74:
            cut = 74
            while cut and (b[cut] & 0xC0) == 0x80:       # never split a UTF-8 character
                cut -= 1
            out.append(b[:cut].decode()); b = b[cut:]
        out.append(b.decode())
        return "\r\n ".join(out)
    stamp = datetime.now(timezone_utc()).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//kundali//festivals//HI", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         f"X-WR-CALNAME:व्रत-त्योहार {year}", "X-WR-TIMEZONE:Asia/Kolkata", "REFRESH-INTERVAL;VALUE=DURATION:P7D", "X-PUBLISHED-TTL:P7D"]
    for ev in _events(year):
        d0 = date.fromisoformat(ev["date"]); d1 = d0 + timedelta(days=1)
        url = f"{site()}/tyohar/{year}/{_fkey(ev)}" if ev["kind"] in MAJOR_KINDS else f"{site()}/tyohar/{year}"
        desc = " · ".join(x for x in (ev.get("tithi_hi"), ev.get("masa_hi"), ev.get("name_en"), url) if x)
        L += ["BEGIN:VEVENT", f"UID:{ev['key']}@{site().split('//')[-1]}", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d0:%Y%m%d}", f"DTEND;VALUE=DATE:{d1:%Y%m%d}",
              f"SUMMARY:{esc_ics(ev['name_hi'])}", f"DESCRIPTION:{esc_ics(desc)}", f"URL:{url}", "TRANSP:TRANSPARENT",
              f"CATEGORIES:{esc_ics(ev['kind'])}", "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in L) + "\r\n"


def timezone_utc():
    from datetime import timezone
    return timezone.utc


def sitemap() -> str:
    y, d = today().year, today().isoformat()
    urls = ["/", "/panchang", "/rashifal", "/tyohar", "/ratna", "/privacy", "/terms"] + [f"/panchang/{c.lower()}" for c in CITIES[1:]] + [f"/rashifal/{s[0]}" for s in SIGNS]
    for yr in (y, y + 1):
        urls.append(f"/tyohar/{yr}")
        urls += sorted({f"/tyohar/{yr}/{_fkey(ev)}" for ev in _events(yr) if ev["kind"] in MAJOR_KINDS})
    items = "".join(f"<url><loc>{e(site() + u)}</loc><lastmod>{d}</lastmod><changefreq>{'daily' if u.startswith(('/panchang', '/rashifal')) or u == '/' else 'monthly'}</changefreq></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'


def robots() -> str:
    return f"User-agent: *\nAllow: /\nDisallow: /v1/\nDisallow: /admin.html\nSitemap: {site()}/sitemap.xml\n"


def route(path: str) -> tuple[int, str, str] | None:
    """-> (status, content_type, body) for an SEO path, or None if the path is not one of ours."""
    p = path.rstrip("/") or "/"
    H = "text/html; charset=utf-8"
    if p == "/sitemap.xml":
        return 200, "application/xml; charset=utf-8", _cached(("sitemap",), sitemap)
    if p == "/robots.txt":
        return 200, "text/plain; charset=utf-8", robots()
    m = re.fullmatch(r"/panchang(?:/([a-z]+))?", p)
    if m:
        b = panchang_page(m.group(1)); return (200, H, b) if b else (404, H, not_found())
    m = re.fullmatch(r"/rashifal(?:/([a-z]+))?", p)
    if m:
        b = rashifal_sign(m.group(1)) if m.group(1) else rashifal_index(); return (200, H, b) if b else (404, H, not_found())
    if p == "/.well-known/assetlinks.json":
        return 200, "application/json", assetlinks()
    if p == "/ratna":
        return 200, H, _cached(("ratna",), ratna_page)
    if p == "/privacy":
        return 200, H, privacy_page()
    if p == "/terms":
        return 200, H, terms_page()
    if p == "/tyohar":
        return 200, H, festivals_year(today().year)
    m = re.fullmatch(r"/tyohar/(\d{4})\.ics", p)
    if m:
        b = festivals_ics(int(m.group(1)))
        return (200, "text/calendar; charset=utf-8", b) if b else (404, H, not_found())
    m = re.fullmatch(r"/tyohar/(\d{4})(?:/([a-z0-9-]+))?", p)
    if m:
        y = int(m.group(1)); b = festival_page(y, m.group(2)) if m.group(2) else festivals_year(y)
        return (200, H, b) if b else (404, H, not_found())
    return None


def _contact() -> str:
    em = os.environ.get("KUNDALI_CONTACT_EMAIL", "").strip()
    return (f'<a href="mailto:{e(em)}">{e(em)}</a>' if em else "WhatsApp पर <b>मदद</b> लिखकर") + " (Contact: " + (e(em) if em else "WhatsApp, send <b>help</b>") + ")"


def ratna_page() -> str:
    from . import upay
    rows = "".join(f"<tr><td><b>{e(t['sign_hi'])}</b> <span class='en'>{e(t['sign_en'])}</span></td><td>{e(t['lord_hi'])}</td><td><b>{e(t['gem_hi'])}</b> <span class='en'>{e(t['gem_en'])}</span></td>"
                   f"<td>{e(t['upa_hi'])}</td><td>{e(', '.join(t['lagna_stones']))}</td></tr>" for t in upay.table())
    how = "".join(f"<li>{e(x)}</li>" for x in upay.HOW_HI)
    body = ("<div class='hero'><h1>राशि रत्न — किस राशि को कौन-सा रत्न पहनना चाहिए?</h1><p>मेष से मीन तक 12 राशियों के रत्न, उपरत्न और लग्न के अनुसार शुभ रत्न</p></div>"
            f"<div class='card'><table><tr><th>राशि</th><th>स्वामी</th><th>राशि रत्न</th><th>उपरत्न</th><th>उस लग्न के शुभ रत्न</th></tr>{rows}</table></div>"
            f"<div class='card'><h2>रत्न कैसे पहनें</h2><ul>{how}</ul><p class='muted'>{e(upay.NOTE_HI)}</p></div>"
            "<div class='card'><b>अपनी कुंडली से सही रत्न और समस्या के उपाय देखिए</b><br><a class='cta' href='/#t-upay'>उपाय व रत्न →</a><a class='cta' style='background:#444' href='/#t-shop'>रत्न शॉप</a></div>")
    return page("/ratna", "राशि रत्न — मेष से मीन तक कौन-सा रत्न पहनें | Rashi ratna", "12 राशियों के रत्न व उपरत्न, लग्न के अनुसार शुभ रत्न, न पहनने योग्य रत्न और धारण विधि।", body, [("राशि रत्न", "/ratna")])


def privacy_page() -> str:
    upd = "20 नवंबर 2026"
    sec = [
        ("हम कौन हैं", f"यह निःशुल्क ज्योतिष ऐप {e(site())} पर चलता है। इस नीति में बताया गया है कि ऐप कौन-सी जानकारी लेता है, क्यों, और आप उसे कैसे हटा सकते हैं।",
         "This free astrology app runs at " + e(site()) + ". This policy explains what it collects, why, and how you can delete it."),
        ("जन्म विवरण", "कुंडली, मिलान, मुहूर्त आदि के लिए नाम, जन्म तारीख, समय और स्थान हमारे सर्वर पर केवल गणना के लिए भेजे जाते हैं और सहेजे नहीं जाते — जब तक आप लॉगिन करके किसी व्यक्ति को \"सहेजें\" न करें। \"मेरे लोग\" की सूची आपके ब्राउज़र में रहती है; लॉगिन करने पर वह आपके खाते में sync होती है ताकि दूसरे फ़ोन पर भी दिखे।",
         "Birth details are sent to our server only to compute charts and are not stored unless you sign in and save a person. The \"My people\" list lives in your browser and, when you sign in, syncs to your account."),
        ("लॉगिन", "लॉगिन (Supabase के ज़रिए) पर आपका ईमेल और एक खाता-पहचान रखी जाती है ताकि आपकी सहेजी कुंडलियाँ आपके ही खाते में रहें।",
         "Sign-in (via Supabase) stores your email and an account id so saved charts stay in your account."),
        ("WhatsApp अपडेट", "रोज़ का पंचांग पाने के लिए आपका WhatsApp नंबर, चुना हुआ शहर, भाषा, समय और (वैकल्पिक) जन्म विवरण सहेजे जाते हैं, साथ में भेजे गए संदेशों का छोटा लॉग। \"STOP\" लिखते ही भेजना बंद हो जाता है; पूरा डेटा हटवाने के लिए नीचे संपर्क करें।",
         "For daily WhatsApp updates we store your number, city, language, time and optional birth details, plus a short delivery log. Send STOP to stop; contact us below to erase everything."),
        ("AI सुविधाएँ", "जब आप \"AI से पूछिए\", हस्तरेखा-फ़ोटो या वास्तु-नक्शा AI से जाँचते हैं, तो आपका प्रश्न/चित्र और कुंडली का सार उस समय चालू AI सेवा (जैसे OpenAI, Groq, Google Gemini) को उत्तर बनाने के लिए भेजा जाता है। हम फ़ोटो सहेजते नहीं; दैनिक सीमा के लिए केवल गिनती रखी जाती है। ये सेवाएँ अपनी नीतियों के अनुसार डेटा संभालती हैं।",
         "When you use AI features, your question or photo and a chart summary are sent to the active AI provider (e.g. OpenAI, Groq, Google Gemini) to produce the answer. We do not keep photos; only a usage count is kept for the daily limit."),
        ("ज्योतिषी परामर्श", "परामर्श में आपका सवाल, फ़ोन नंबर और ज्योतिषी का उत्तर सहेजा जाता है ताकि उत्तर आप तक पहुँचे।",
         "Consultations store your question, phone number and the astrologer's reply so it can reach you."),
        ("ब्राउज़र में", "भाषा, रंग-रूप, प्रोफ़ाइल और पसंद आपके ब्राउज़र के localStorage में रहते हैं। हम विज्ञापन-ट्रैकर या तीसरे पक्ष के analytics का उपयोग नहीं करते।",
         "Language, theme, profiles and preferences stay in your browser's localStorage. We use no advertising trackers or third-party analytics."),
        ("साझा करना", "हम आपकी जानकारी बेचते नहीं। केवल ऊपर लिखी सेवाओं (होस्टिंग, Supabase लॉगिन, WhatsApp भेजने का गेटवे, AI सेवा) के साथ, उतना ही, जितना काम के लिए ज़रूरी है।",
         "We never sell your data; it is shared only with the services above, and only as needed."),
        ("आपके अधिकार", "आप कभी भी अपनी सहेजी प्रोफ़ाइल ऐप में हटा सकते हैं, WhatsApp पर STOP लिख सकते हैं, या पूरा डेटा हटवाने/देखने के लिए संपर्क कर सकते हैं: " + _contact() + "। हम 30 दिनों में अनुरोध पूरा करते हैं।",
         "You can delete saved profiles in the app, send STOP on WhatsApp, or ask us to show or erase your data; we act within 30 days."),
        ("बच्चे", "यह सेवा 13 वर्ष से कम आयु के बच्चों के लिए नहीं है; माता-पिता बच्चों की कुंडली अपने खाते से बना सकते हैं।",
         "The service is not directed at children under 13; parents may make charts for their children from their own account."),
        ("सुरक्षा व बदलाव", "डेटा HTTPS से भेजा जाता है और सर्वर पर सुरक्षित रखा जाता है। नीति में बदलाव होने पर यह पेज और ऊपर की तारीख बदलेगी।",
         "Data travels over HTTPS and is kept on secured servers. Changes to this policy update this page and its date."),
    ]
    body = f"<div class='hero'><h1>गोपनीयता नीति</h1><p>Privacy policy · अंतिम अद्यतन: {upd}</p></div>" + "".join(
        f"<div class='card'><h2>{e(h)}</h2><p>{hi}</p><p class='en'>{en}</p></div>" for h, hi, en in sec)
    return page("/privacy", "गोपनीयता नीति | Privacy policy", "कुंडली ऐप कौन-सी जानकारी लेता है, क्यों, और आप उसे कैसे हटा सकते हैं।", body, [("गोपनीयता नीति", "/privacy")])


def terms_page() -> str:
    sec = [("सेवा", "यह ऐप परंपरागत ज्योतिष के नियमों के अनुसार गणना और सामान्य मार्गदर्शन देता है, निःशुल्क।", "The app provides traditional astrological computation and general guidance, free of charge."),
           ("सलाह नहीं", "फलादेश भविष्यवाणी, चिकित्सा, क़ानूनी या वित्तीय सलाह नहीं है। स्वास्थ्य, धन या क़ानूनी निर्णयों के लिए योग्य विशेषज्ञ से मिलें। व्याख्याएँ ड्राफ़्ट हैं और विद्वान-समीक्षा के अधीन।",
            "Readings are not predictions or medical, legal or financial advice. Consult a qualified professional for such decisions."),
           ("गणना", "ग्रह-स्थिति NASA JPL DE440s और लाहिरी अयनांश से। स्थानीय परंपराओं में व्रत-तिथि एक दिन अलग हो सकती है।", "Positions from NASA JPL DE440s with Lahiri ayanamsa; local traditions may differ by a day."),
           ("उचित उपयोग", "स्वचालित भारी उपयोग, दुरुपयोग या दूसरों को परेशान करने वाले संदेश मना हैं; ऐसे उपयोग पर सीमा लगाई जा सकती है।", "Abusive or automated heavy use may be rate-limited or blocked."),
           ("संपर्क", "प्रश्न या शिकायत: " + _contact(), "Questions or complaints: see contact above.")]
    body = "<div class='hero'><h1>उपयोग की शर्तें</h1><p>Terms of use</p></div>" + "".join(f"<div class='card'><h2>{e(h)}</h2><p>{hi}</p><p class='en'>{en}</p></div>" for h, hi, en in sec)
    return page("/terms", "उपयोग की शर्तें | Terms of use", "कुंडली ऐप के उपयोग की शर्तें।", body, [("उपयोग की शर्तें", "/terms")])


def assetlinks() -> str:
    """Digital Asset Links for the Play Store app (Trusted Web Activity). Set TWA_PACKAGE (e.g. com.vividbrandify.kundali) and
    TWA_SHA256 (the app-signing certificate fingerprint from Play Console → App integrity; several allowed, comma-separated)."""
    pkg = os.environ.get("TWA_PACKAGE", "").strip(); fps = [x.strip() for x in os.environ.get("TWA_SHA256", "").split(",") if x.strip()]
    if not pkg or not fps:
        return "[]"
    return json.dumps([{"relation": ["delegate_permission/common.handle_all_urls"],
                        "target": {"namespace": "android_app", "package_name": pkg, "sha256_cert_fingerprints": fps}}])


def not_found() -> str:
    return page("/", "पृष्ठ नहीं मिला", "यह पृष्ठ उपलब्ध नहीं है।", "<div class='hero'><h1>पृष्ठ नहीं मिला</h1><p>यह पता सही नहीं है।</p></div>", [])
