"""Write a Hindi kundali PDF with headless Chromium (needs `playwright` + its Chromium).

    cd engine && python tools/make_pdf.py 1990-05-17 06:45 Asia/Kolkata 23.18 79.99 out.pdf [Name]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jyotish import handlers  # noqa: E402


def main() -> int:
    if len(sys.argv) < 7:
        print(__doc__)
        return 2
    date, time_, tz, lat, lon, out = sys.argv[1:7]
    name = sys.argv[7] if len(sys.argv) > 7 else None
    html = handlers.report_from_payload({"date": date, "time": time_, "tz": tz, "lat": float(lat),
                                         "lon": float(lon), "name": name})
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(path=out, format="A4", print_background=True)
        browser.close()
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
