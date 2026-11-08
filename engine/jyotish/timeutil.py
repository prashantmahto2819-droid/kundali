"""Calendar / time helpers: local time -> UT -> Julian days, Delta T."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def julian_day(dt_utc: datetime) -> float:
    """Julian Day (UT) for an aware or naive-UTC datetime (Meeus ch. 7)."""
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc)
    y, m = dt_utc.year, dt_utc.month
    d = dt_utc.day + (dt_utc.hour + (dt_utc.minute + (dt_utc.second + dt_utc.microsecond / 1e6) / 60) / 60) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4  # Gregorian
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def jd_to_datetime(jd: float) -> datetime:
    """Inverse of julian_day, returns aware UTC datetime (Gregorian)."""
    jd += 0.5
    z = int(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    secs = round(f * 86400)
    base = datetime(year, month, day, tzinfo=timezone.utc)
    from datetime import timedelta
    return base + timedelta(seconds=secs)


def delta_t(year_frac: float) -> float:
    """Delta T = TT - UT in seconds (Espenak & Meeus polynomial fits)."""
    y = year_frac
    if y < 1900:
        u = (y - 1820) / 100
        return -20 + 32 * u * u
    if y < 1920:
        t = y - 1900
        return -2.79 + 1.494119 * t - 0.0598939 * t**2 + 0.0061966 * t**3 - 0.000197 * t**4
    if y < 1941:
        t = y - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    if y < 1961:
        t = y - 1950
        return 29.07 + 0.407 * t - t**2 / 233 + t**3 / 2547
    if y < 1986:
        t = y - 1975
        return 45.45 + 1.067 * t - t**2 / 260 - t**3 / 718
    if y < 2005:
        t = y - 2000
        return (63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3
                + 0.000651814 * t**4 + 0.00002373599 * t**5)
    if y < 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    if y < 2150:
        return -20 + 32 * ((y - 1820) / 100) ** 2 - 0.5628 * (2150 - y)
    u = (y - 1820) / 100
    return -20 + 32 * u * u


def year_fraction(dt_utc: datetime) -> float:
    return dt_utc.year + (dt_utc.timetuple().tm_yday - 0.5) / 365.25


def local_to_utc(date_str: str, time_str: str, tz_name: str) -> datetime:
    """'YYYY-MM-DD', 'HH:MM[:SS]', IANA tz name -> aware UTC datetime."""
    parts = [int(p) for p in time_str.split(":")]
    while len(parts) < 3:
        parts.append(0)
    y, mo, d = (int(p) for p in date_str.split("-"))
    local = datetime(y, mo, d, parts[0], parts[1], parts[2], tzinfo=ZoneInfo(tz_name))
    return local.astimezone(timezone.utc)
