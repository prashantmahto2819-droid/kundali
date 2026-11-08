"""Compare the JPL backend with the dev analytic backend on many dates.

Run on a machine where `pip install skyfield` works and de440s.bsp can be fetched:
    cd engine && python tools/compare_backends.py
Prints the maximum longitude difference (degrees) per planet 1900-2050, so we
know exactly how far the dev backend is from NASA data.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jyotish.ephemeris import AnalyticBackend, JPLBackend  # noqa: E402


def diff(a, b):
    return abs((a - b + 180) % 360 - 180)


def main():
    jpl, dev = JPLBackend(), AnalyticBackend()
    worst = {}
    jd = 2415020.5  # 1900-01-01
    while jd < 2469807.5:  # 2050-01-01
        a, b = jpl.positions(jd), dev.positions(jd)
        for name in a:
            worst[name] = max(worst.get(name, 0.0), diff(a[name], b[name]))
        jd += 37.3  # irregular step, covers all phases
    for name, w in worst.items():
        print(f"{name:8} max diff {w:.4f} deg")


if __name__ == "__main__":
    main()
