import re
import xml.etree.ElementTree as ET

from jyotish import seo


def _ok(path, must):
    code, ctype, body = seo.route(path)
    assert code == 200 and ctype.startswith("text/html"), path
    assert "<title>" in body and 'rel="canonical"' in body and "application/ld+json" in body
    for m in must:
        assert m in body, (path, m)
    return body


def test_panchang_pages():
    _ok("/panchang", ["आज का पंचांग — दिल्ली", "राहु काल", "सूर्योदय"])
    _ok("/panchang/jabalpur", ["जबलपुर", "तिथि"])
    assert seo.route("/panchang/atlantis")[0] == 404


def test_rashifal_pages():
    b = _ok("/rashifal", ["आज का राशिफल", "/rashifal/meen"])
    assert b.count("class='card sign'") == 12
    _ok("/rashifal/singh", ["सिंह राशिफल", "इस सप्ताह", "इस माह"])
    assert seo.route("/rashifal/pluto")[0] == 404


def test_festival_pages_and_sitemap():
    b = _ok("/tyohar/2026", ["व्रत-त्योहार 2026", "/tyohar/2026/diwali", "नवंबर 2026"])
    d = _ok("/tyohar/2026/diwali", ["दीपावली", "2026", '"@type": "Event"', "/tyohar/2025/diwali"])
    assert seo.route("/tyohar/2026/no-such")[0] == 404 and seo.route("/tyohar/1800")[0] == 404
    code, ctype, sm = seo.route("/sitemap.xml")
    root = ET.fromstring(sm)
    locs = [u[0].text for u in root]
    assert code == 200 and len(locs) > 80 and any(l.endswith("/rashifal/mesh") for l in locs) and any(re.search(r"/tyohar/\d{4}/holi$", l) for l in locs)
    assert "Sitemap:" in seo.route("/robots.txt")[2]
    assert seo.route("/assets/app.js") is None
