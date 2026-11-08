"""Compare the engine with reference charts exported from trusted software.

    cd engine && python tools/check_reference.py [folder] [--tol-arcmin 1.0]

Each reference file (JSON, see tests/reference/README.md) holds the birth input and
the positions printed by the reference program (Lahiri, mean node, whole-sign).
Prints the difference per planet in arc-minutes and exits non-zero on any miss.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jyotish import compute_chart  # noqa: E402
from jyotish.constants import SIGNS  # noqa: E402

WESTERN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_NAMES = {n.lower(): i for i, n in enumerate(SIGNS)}
_NAMES.update({n.lower(): i for i, n in enumerate(WESTERN)})
_NAMES.update({"vrishchik": 7, "vrischika": 7, "vrishabh": 1, "mithun": 2, "kark": 3, "singh": 4,
               "simha": 4, "tula": 6, "dhanu": 8, "dhanus": 8, "makar": 9, "kumbh": 10, "meen": 11,
               "kanya": 5, "mesh": 0})
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def parse_position(text: str) -> float:
    """'Taurus 2°10′45″', 'Vrishabha 02:10:45', 'Tau 2 10 45' or a plain number (0-360)."""
    t = str(text).strip()
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t) % 360
    m = re.match(r"([A-Za-z]+)\D*(\d+(?:\.\d+)?)?\D*(\d+(?:\.\d+)?)?\D*(\d+(?:\.\d+)?)?", t)
    if not m:
        raise ValueError(f"cannot parse position '{text}'")
    word = m.group(1).lower()
    sign = _NAMES.get(word) if word in _NAMES else next(
        (i for n, i in _NAMES.items() if len(word) >= 3 and n.startswith(word)), None)
    if sign is None:
        raise ValueError(f"unknown sign '{m.group(1)}' in '{text}'")
    d, mi, s = (float(x) if x else 0.0 for x in m.groups()[1:])
    return sign * 30 + d + mi / 60 + s / 3600


def diff_arcmin(a: float, b: float) -> float:
    return ((a - b + 180) % 360 - 180) * 60


def check_file(path: Path, tol_arcmin: float) -> tuple[list[dict], bool]:
    ref = json.loads(path.read_text(encoding="utf-8"))
    inp = ref["input"]
    chart = compute_chart(inp["date"], inp["time"], inp["tz"], float(inp["lat"]), float(inp["lon"]))
    got = {p["name"]: p for p in chart["planets"]}
    rows, ok = [], True
    exp = ref["expected"]

    def row(label, expected_lon, got_lon):
        nonlocal ok
        d = diff_arcmin(got_lon, expected_lon)
        bad = abs(d) > tol_arcmin
        ok = ok and not bad
        rows.append({"what": label, "diff_arcmin": round(d, 2), "ok": not bad})

    if "lagna" in exp:
        row("Lagna", parse_position(exp["lagna"]), chart["lagna"]["longitude"])
    for name, pos in exp.get("planets", {}).items():
        row(name, parse_position(pos), got[name]["longitude"])
    if "moon_nakshatra" in exp:
        same = got["Moon"]["nakshatra"].lower() == exp["moon_nakshatra"].lower()
        ok = ok and same
        rows.append({"what": "Moon nakshatra", "diff_arcmin": None, "ok": same,
                     "note": f"got {got['Moon']['nakshatra']}, expected {exp['moon_nakshatra']}"})
    if "birth_dasha_lord" in exp:
        same = chart["dasha"]["birth_nakshatra_lord"].lower() == exp["birth_dasha_lord"].lower()
        ok = ok and same
        rows.append({"what": "Birth dasha lord", "diff_arcmin": None, "ok": same})
    if "balance_years" in exp:
        d = chart["dasha"]["balance_at_birth_years"] - float(exp["balance_years"])
        bad = abs(d) > 0.05
        ok = ok and not bad
        rows.append({"what": "Dasha balance (years)", "diff_arcmin": None, "ok": not bad,
                     "note": f"difference {d:+.3f} y (year length {chart['dasha']['year_days']})"})
    def same(label, got_v, exp_v, note=""):
        nonlocal ok
        eq = str(got_v).strip().lower() == str(exp_v).strip().lower()
        ok = ok and eq
        rows.append({"what": label, "diff_arcmin": None, "ok": eq, "note": note or f"got {got_v}, expected {exp_v}"})

    sign_of = lambda lon: SIGNS[int(lon // 30) % 12]
    if "lagna_sign" in exp:            # sign only (printouts that give no degree)
        same("Lagna sign", sign_of(chart["lagna"]["longitude"]), SIGNS[_sign_index(exp["lagna_sign"])])
    if "moon_sign" in exp:
        same("Moon sign", sign_of(got["Moon"]["longitude"]), SIGNS[_sign_index(exp["moon_sign"])])
    if "moon_pada" in exp:
        same("Moon pada", got["Moon"]["pada"], exp["moon_pada"])
    if "ayanamsa" in exp:              # '23:44:34' or '23°44′34″'
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(exp["ayanamsa"]))] + [0, 0, 0]
        want = nums[0] + nums[1] / 60 + nums[2] / 3600
        d = (chart["ayanamsa_value"] - want) * 60
        bad = abs(d) > tol_arcmin
        ok = ok and not bad
        rows.append({"what": "Ayanamsa", "diff_arcmin": round(d, 2), "ok": not bad})
    pc = chart["panchang"]
    if "tithi" in exp:
        same("Tithi", pc["tithi"]["name"], exp["tithi"])
    if "paksha" in exp:
        same("Paksha", pc["tithi"]["paksha"], exp["paksha"])
    if "yoga" in exp:
        same("Yoga", pc["yoga"]["name"], exp["yoga"])
    if "balance_dmy" in exp:           # '2y 9m 14d' as printed by Indian programs; tolerance 3 days
        y, m, d = (int(x) for x in re.findall(r"\d+", exp["balance_dmy"])[:3])
        want_days = y * 365.25 + m * 30.44 + d
        got_days = chart["dasha"]["balance_at_birth_years"] * 365.25
        diff = got_days - want_days
        bad = abs(diff) > 3
        ok = ok and not bad
        rows.append({"what": "Dasha balance (d/m/y)", "diff_arcmin": None, "ok": not bad,
                     "note": f"difference {diff:+.1f} days"})
    return rows, ok


def _sign_index(word: str) -> int:
    w = word.strip().lower()
    if w in _NAMES:
        return _NAMES[w]
    hit = next((i for n, i in _NAMES.items() if len(w) >= 3 and n.startswith(w)), None)
    if hit is None:
        raise ValueError(f"unknown sign '{word}'")
    return hit


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tol = 1.0
    if "--tol-arcmin" in sys.argv:
        tol = float(sys.argv[sys.argv.index("--tol-arcmin") + 1])
        args = [a for a in args if a != str(tol) and a != sys.argv[sys.argv.index("--tol-arcmin") + 1]]
    folder = Path(args[0]) if args else Path(__file__).resolve().parents[1] / "tests" / "reference"
    files = sorted(p for p in folder.glob("*.json") if not p.name.startswith("_"))
    if not files:
        print(f"No reference files in {folder} (see README.md there).")
        return 2
    all_ok = True
    for f in files:
        rows, ok = check_file(f, tol)
        all_ok = all_ok and ok
        print(f"\n{f.name}: {'PASS' if ok else 'FAIL'}  (tolerance {tol} arc-min)")
        for r in rows:
            d = "" if r["diff_arcmin"] is None else f"{r['diff_arcmin']:+8.2f}'"
            print(f"  {'ok ' if r['ok'] else 'BAD'} {r['what']:22} {d} {r.get('note', '')}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
