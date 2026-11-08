"""Planet position backends.

Two interchangeable backends return *tropical ecliptic longitude of date*
(degrees) for Sun..Saturn, in a dict. Rahu/Ketu (mean node) are added by
``mean_node`` and are backend independent.

* ``JPLBackend``      production. Skyfield + NASA JPL DE440s (public domain
                      data, no AGPL). Needs `pip install skyfield` and the
                      de440s.bsp file (Skyfield downloads it on first use).
* ``AnalyticBackend`` zero-dependency development fallback. Sun/planets from
                      JPL's approximate Keplerian elements (E.M. Standish,
                      valid ~1800-2050), Moon from the Meeus ch.47 series.
                      Accuracy is roughly 0.01 deg for Sun/Moon and up to
                      ~0.1-0.3 deg for outer planets. NOT for production use.
"""
from __future__ import annotations

import math
import os

DEG = math.pi / 180.0


def norm360(x: float) -> float:
    return x % 360.0


def mean_node(jd_tt: float) -> float:
    """Mean lunar ascending node (Rahu), tropical longitude of date."""
    t = (jd_tt - 2451545.0) / 36525.0
    return norm360(125.04452 - 1934.136261 * t + 0.0020708 * t * t + t ** 3 / 450000.0)


# --------------------------------------------------------------------------
# Analytic backend
# --------------------------------------------------------------------------

# name: (a, e, I, L, long_peri, long_node) at J2000 then rates per century
_ELEMENTS = {
    "Mercury": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
                (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
    "Venus": ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
              (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
    "Earth": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
              (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "Mars": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
    "Jupiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
                (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
    "Saturn": ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
               (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
}


def _helio_xyz(name: str, t: float):
    el0, rate = _ELEMENTS[name]
    a, e, i, L, peri, node = (el0[k] + rate[k] * t for k in range(6))
    m = (L - peri) % 360.0
    if m > 180:
        m -= 360
    mr = m * DEG
    ecc = e
    big_e = mr + ecc * math.sin(mr)
    for _ in range(30):
        d = (big_e - ecc * math.sin(big_e) - mr) / (1 - ecc * math.cos(big_e))
        big_e -= d
        if abs(d) < 1e-12:
            break
    xp = a * (math.cos(big_e) - ecc)
    yp = a * math.sqrt(1 - ecc * ecc) * math.sin(big_e)
    w = (peri - node) * DEG
    om = node * DEG
    ii = i * DEG
    cw, sw, co, so, ci, si = math.cos(w), math.sin(w), math.cos(om), math.sin(om), math.cos(ii), math.sin(ii)
    x = (cw * co - sw * so * ci) * xp + (-sw * co - cw * so * ci) * yp
    y = (cw * so + sw * co * ci) * xp + (-sw * so + cw * co * ci) * yp
    z = (sw * si) * xp + (cw * si) * yp
    return x, y, z


def _precession_deg(t: float) -> float:
    """General precession in longitude since J2000 (degrees)."""
    return (5028.796195 * t + 1.1054348 * t * t) / 3600.0


# Meeus ch.47, table 47.A (D, M, M', F, coefficient in 1e-6 deg) - longitude
_MOON_LON = [
    (0, 0, 1, 0, 6288774), (2, 0, -1, 0, 1274027), (2, 0, 0, 0, 658314), (0, 0, 2, 0, 213618),
    (0, 1, 0, 0, -185116), (0, 0, 0, 2, -114332), (2, 0, -2, 0, 58793), (2, -1, -1, 0, 57066),
    (2, 0, 1, 0, 53322), (2, -1, 0, 0, 45758), (0, 1, -1, 0, -40923), (1, 0, 0, 0, -34720),
    (0, 1, 1, 0, -30383), (2, 0, 0, -2, 15327), (0, 0, 1, 2, -12528), (0, 0, 1, -2, 10980),
    (4, 0, -1, 0, 10675), (0, 0, 3, 0, 10034), (4, 0, -2, 0, 8548), (2, 1, -1, 0, -7888),
    (2, 1, 0, 0, -6766), (1, 0, -1, 0, -5163), (1, 1, 0, 0, 4987), (2, -1, 1, 0, 4036),
    (2, 0, 2, 0, 3994), (4, 0, 0, 0, 3861), (2, 0, -3, 0, 3665), (0, 1, -2, 0, -2689),
    (2, 0, -1, 2, -2602), (2, -1, -2, 0, 2390), (1, 0, 1, 0, -2348), (2, -2, 0, 0, 2236),
    (0, 1, 2, 0, -2120), (0, 2, 0, 0, -2069), (2, -2, -1, 0, 2048), (2, 0, 1, -2, -1773),
    (2, 0, 0, 2, -1595), (4, -1, -1, 0, 1215), (0, 0, 2, 2, -1110), (3, 0, -1, 0, -892),
    (2, 1, 1, 0, -810), (4, -1, -2, 0, 759), (0, 2, -1, 0, -713), (2, 2, -1, 0, -700),
    (2, 1, -2, 0, 691), (2, -1, 0, -2, 596), (4, 0, 1, 0, 549), (0, 0, 4, 0, 537),
    (4, -1, 0, 0, 520), (1, 0, -2, 0, -487), (2, 1, 0, -2, -399), (0, 0, 2, -2, -381),
    (1, 1, 1, 0, 351), (3, 0, -2, 0, -340), (4, 0, -3, 0, 330), (2, -1, 2, 0, 327),
    (0, 2, 1, 0, -323), (1, 1, -1, 0, 299), (2, 0, 3, 0, 294),
]


def moon_longitude(jd_tt: float) -> float:
    """Geometric geocentric Moon longitude, mean equinox of date (Meeus ch.47)."""
    t = (jd_tt - 2451545.0) / 36525.0
    lp = 218.3164477 + 481267.88123421 * t - 0.0015786 * t**2 + t**3 / 538841 - t**4 / 65194000
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t**2 + t**3 / 545868 - t**4 / 113065000
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t**2 + t**3 / 24490000
    mp = 134.9633964 + 477198.8675055 * t + 0.0087414 * t**2 + t**3 / 69699 - t**4 / 14712000
    f = 93.2720950 + 483202.0175233 * t - 0.0036539 * t**2 - t**3 / 3526000 + t**4 / 863310000
    a1 = 119.75 + 131.849 * t
    a2 = 53.09 + 479264.290 * t
    e = 1 - 0.002516 * t - 0.0000074 * t * t
    total = 0.0
    for cd, cm, cmp_, cf, coef in _MOON_LON:
        arg = (cd * d + cm * m + cmp_ * mp + cf * f) * DEG
        factor = e ** abs(cm)
        total += coef * factor * math.sin(arg)
    total += 3958 * math.sin(a1 * DEG) + 1962 * math.sin((lp - f) * DEG) + 318 * math.sin(a2 * DEG)
    return norm360(lp + total / 1e6)


class AnalyticBackend:
    name = "analytic-dev"
    accuracy_note = ("Development backend (approx. elements + Meeus Moon): about 0.01 deg for "
                     "Sun/Moon, up to ~0.3 deg for outer planets. Use the JPL backend in production.")

    def positions(self, jd_tt: float) -> dict[str, float]:
        t = (jd_tt - 2451545.0) / 36525.0
        precess = _precession_deg(t)
        ex, ey, ez = _helio_xyz("Earth", t)
        out = {"Sun": norm360(math.degrees(math.atan2(-ey, -ex)) + precess)}
        for planet in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            x, y, z = _helio_xyz(planet, t)
            out[planet] = norm360(math.degrees(math.atan2(y - ey, x - ex)) + precess)
        out["Moon"] = moon_longitude(jd_tt)
        return out


# --------------------------------------------------------------------------
# JPL backend (Skyfield)
# --------------------------------------------------------------------------

class JPLBackend:
    name = "jpl-de440s"
    accuracy_note = "NASA JPL DE440s via Skyfield (apparent positions, ecliptic of date)."
    _KEYS = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury barycenter",
             "Venus": "venus barycenter", "Mars": "mars barycenter",
             "Jupiter": "jupiter barycenter", "Saturn": "saturn barycenter"}

    def __init__(self, directory: str | None = None, filename: str = "de440s.bsp"):
        from skyfield.api import Loader  # imported lazily: optional dependency
        directory = directory or os.environ.get("KUNDALI_EPHEMERIS_DIR", "data/ephemeris")
        os.makedirs(directory, exist_ok=True)
        load = Loader(directory)
        self._ts = load.timescale()
        self._eph = load(filename)  # downloads on first run if network is allowed

    def positions(self, jd_tt: float) -> dict[str, float]:
        t = self._ts.tt_jd(jd_tt)
        earth = self._eph["earth"]
        out = {}
        for name, key in self._KEYS.items():
            app = earth.at(t).observe(self._eph[key]).apparent()
            _, lon, _ = app.ecliptic_latlon(epoch="date")
            out[name] = float(norm360(float(lon.degrees)))
        return out


def get_backend(prefer: str | None = None):
    """Choose a backend. KUNDALI_BACKEND=jpl|analytic forces one."""
    prefer = (prefer or os.environ.get("KUNDALI_BACKEND") or "auto").lower()
    if prefer in ("jpl", "auto"):
        try:
            return JPLBackend()
        except Exception as exc:  # skyfield missing, file missing, offline ...
            if prefer == "jpl":
                raise RuntimeError(f"JPL backend unavailable: {exc}") from exc
    return AnalyticBackend()
