"""Palmistry v2: a palm photo traced by the person (photo never leaves the browser; only points arrive here).

Input: six landmarks in image pixels (wrist centre, bases of index / middle / ring / little fingers, thumb base
where the thumb meets the palm), the traced lines (life, head, heart, optional fate and sun) as point lists, marks
on lines (island, break, ...) and counted extras (union lines, bracelets, travel lines, girdle of Venus).
Output: measurements as ratios of the palm frame, the checklist choices they imply (fed into palm.read), mark and
extra readings. Thresholds are the common textbook proportions and are draft (a palmist should review them).
"""
from __future__ import annotations

import math

from . import palm

LANDMARKS = ("wrist", "index", "middle", "ring", "little", "thumb")
LANDMARK_HI = {"wrist": "कलाई का मध्य", "index": "तर्जनी का आधार", "middle": "मध्यमा का आधार", "ring": "अनामिका का आधार",
               "little": "कनिष्ठा का आधार", "thumb": "अंगूठे का जोड़ (हथेली से)"}
LANDMARK_EN = {"wrist": "wrist centre", "index": "base of the index finger", "middle": "base of the middle finger",
               "ring": "base of the ring finger", "little": "base of the little finger", "thumb": "thumb joint (where it meets the palm)"}
LINE_KEYS = ("life", "head", "heart", "fate", "sun")


def _pt(p):
    return float(p[0]), float(p[1])


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _length(pts):
    return sum(_dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def _project(p, a, b):
    """Scalar position of p along the a→b axis (0 at a, 1 at b) and signed perpendicular distance (in axis units)."""
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay or 1e-9
    t = ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2
    perp = ((p[0] - a[0]) * ay - (p[1] - a[1]) * ax) / math.sqrt(L2)
    return t, perp / math.sqrt(L2)


def _sagitta_ratio(pts):
    """Max distance of the line from its chord divided by the chord length (0 = straight)."""
    if len(pts) < 3:
        return 0.0
    a, b = pts[0], pts[-1]
    return max(abs(_project(p, a, b)[1]) for p in pts[1:-1])


def frame(landmarks: dict) -> dict:
    L = {k: _pt(landmarks[k]) for k in LANDMARKS}
    width = _dist(L["index"], L["little"])
    length = _dist(L["middle"], L["wrist"])
    if width < 5 or length < 5:
        raise ValueError("landmarks are too close together; mark the finger bases and the wrist on the photo")
    return {"L": L, "width": width, "length": length}


def measure(landmarks: dict, lines: dict) -> tuple[dict, dict, list]:
    """Returns (measurements, implied checklist choices, notes)."""
    F = frame(landmarks)
    L, W, H = F["L"], F["width"], F["length"]
    m, choices, notes = {}, {}, []
    wrist, middle, index, little, thumb = L["wrist"], L["middle"], L["index"], L["little"], L["thumb"]

    life = lines.get("life")
    if life and len(life) >= 2:
        # how far down the palm the life line reaches: position of its end along middle-base → wrist (1 = at the wrist)
        t_end, _ = _project(life[-1], middle, wrist)
        reach = max(0.0, min(1.2, t_end))
        # width of the curve: in the middle of the palm, how close the line comes to the palm's centre line (middle-base→wrist)
        # compared with the thumb base: 1 = hugging the thumb, 0 = at the centre line. Reported as sweep = 1 - that.
        axis = _dist(middle, wrist)
        thumb_off = abs(_project(thumb, middle, wrist)[1]) * axis or 1e-9
        mid = [abs(pp[1]) * axis for pp in (_project(p, middle, wrist) for p in life) if 0.3 <= pp[0] <= 0.8]
        sweep = 1.0 - (min(mid) / thumb_off if mid else 1.0)
        m["life_reach"] = round(reach, 2); m["life_sweep"] = round(sweep, 2); m["life_length_ratio"] = round(_length(life) / H, 2)
        choices["life_length"] = "long" if reach >= 0.85 else "medium" if reach >= 0.6 else "short"
        choices["life_curve"] = "wide" if sweep >= 0.33 else "narrow"
    head = lines.get("head")
    if head and len(head) >= 2:
        span = _length(head) / W
        # slope: how much the end drops towards the wrist compared with the start, as a fraction of palm length
        t0, _ = _project(head[0], middle, wrist); t1, _ = _project(head[-1], middle, wrist)
        drop = t1 - t0
        m["head_span"] = round(span, 2); m["head_drop"] = round(drop, 2)
        choices["head_length"] = "long" if span >= 0.75 else "short"
        choices["head_slope"] = "sloping" if drop >= 0.18 else "straight"
    heart = lines.get("heart")
    if heart and len(heart) >= 2:
        # the heart line runs from under the little finger towards the index; its end is the point nearest the index side
        end = min(heart, key=lambda p: _dist(p, index))
        t_i, _ = _project(end, little, index)              # 0 under the little finger, 1 under the index
        t_m, _ = _project(middle, little, index)
        m["heart_end_pos"] = round(t_i, 2); m["heart_curve"] = round(_sagitta_ratio(heart), 2)
        choices["heart_end"] = "index" if t_i >= (t_m + 1) / 2 + 0.08 else "middle" if t_i <= t_m + 0.05 else "between"
        choices["heart_shape"] = "curved" if m["heart_curve"] >= 0.1 else "straight"
    fate = lines.get("fate")
    if fate and len(fate) >= 2:
        r = _length(fate) / H
        m["fate_length_ratio"] = round(r, 2)
        choices["fate"] = "clear" if r >= 0.45 else "faint"
    elif "fate" in lines:
        choices["fate"] = "absent"
    sun = lines.get("sun")
    if sun and len(sun) >= 2:
        m["sun_length_ratio"] = round(_length(sun) / H, 2); choices["sun_line"] = "present"
    elif "sun" in lines:
        choices["sun_line"] = "absent"
    m["palm_width_px"] = round(W, 1); m["palm_length_px"] = round(H, 1); m["palm_ratio"] = round(H / W, 2)
    # hand shape from the palm proportion (fingers are not traced): a long palm leans "water/air", a square palm "earth/fire"
    notes.append({"hi": f"हथेली लंबाई/चौड़ाई = {m['palm_ratio']} ({'लंबी हथेली' if m['palm_ratio'] > 1.15 else 'चौकोर हथेली'}); हाथ का तत्व उँगलियों की लंबाई से भी तय होता है, इसलिए वह आप चुनिए।",
                  "en": f"Palm length/width = {m['palm_ratio']} ({'long palm' if m['palm_ratio'] > 1.15 else 'square palm'}); the hand's element also depends on finger length, so choose it yourself."})
    return m, choices, notes


def read_marks(marks: list, lines_hi: dict) -> list[dict]:
    K = palm.knowledge()
    out = []
    for mk in marks:
        line, kind = mk.get("line"), mk.get("type")
        if line not in K["lines"] or kind not in K["marks"]:
            raise ValueError(f"mark must have line in {', '.join(K['lines'])} and type in {', '.join(K['marks'])}")
        M = K["marks"][kind]; Ln = K["lines"][line]
        out.append({"line": line, "line_hi": Ln["hi"], "type": kind, "type_hi": M["hi"], "type_en": M["en"],
                    "text_hi": M["hi_t"].replace("{line}", Ln["hi"]), "text_en": M["en_t"].replace("{line}", Ln["en"]),
                    "x": mk.get("x"), "y": mk.get("y")})
    return out


def read_extras(extras: dict) -> list[dict]:
    K = palm.knowledge()
    out = []
    for key, n in (extras or {}).items():
        if key not in K["extras"]:
            raise ValueError(f"unknown extra '{key}' (choose {', '.join(K['extras'])})")
        try:
            n = int(n)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be a whole number")
        n = max(0, min(9, n))
        band = max((b for b in K["extras"][key]["bands"] if n >= b["min"]), key=lambda b: b["min"])
        out.append({"key": key, "hi": K["extras"][key]["hi"], "en": K["extras"][key]["en"], "count": n, "text_hi": band["hi"], "text_en": band["en"]})
    return out


def trace(payload: dict) -> dict:
    lm = payload.get("landmarks") or {}
    missing = [k for k in LANDMARKS if k not in lm]
    if missing:
        raise ValueError("landmarks missing: " + ", ".join(missing))
    lines_in = payload.get("lines") or {}
    lines = {}
    for k, pts in lines_in.items():
        if k not in LINE_KEYS:
            raise ValueError(f"unknown line '{k}' (choose {', '.join(LINE_KEYS)})")
        if pts in (None, []):
            lines[k] = []
            continue
        if not isinstance(pts, list) or len(pts) > 200:
            raise ValueError(f"line {k} must be a list of up to 200 points")
        lines[k] = [_pt(p) for p in pts]
    measurements, implied, notes = measure(lm, lines)
    choices = {**implied, **{k: v for k, v in (payload.get("choices") or {}).items() if v}}
    reading = palm.read(choices) if choices else {"traits": [], "groups": {}, "count": 0}
    K = palm.knowledge()
    return {"measurements": measurements, "implied_choices": implied, "choices": choices, "reading": reading,
            "marks": read_marks(payload.get("marks") or [], K["lines"]), "extras": read_extras(payload.get("extras") or {}),
            "notes": notes, "lines_traced": [k for k, v in lines.items() if len(v) >= 2], "review_status": "draft",
            "trace_note_hi": K["trace_note_hi"], "trace_note": K["trace_note"],
            "general_hi": K["general_hi"], "disclaimer_hi": K["disclaimer_hi"], "disclaimer": K.get("disclaimer", "")}
