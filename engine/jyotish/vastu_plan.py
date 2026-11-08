"""Vastu from a floor plan v1.

Two steps:
1. ``convert_upload(filename, data)``: turn an uploaded plan (PDF page 1, DXF drawing, or PNG/JPG image) into a
   PNG the browser can draw on. PDF via pypdfium2, DXF via a small built-in reader (LINE, LWPOLYLINE,
   POLYLINE/VERTEX, CIRCLE, ARC on all layers) rendered with Pillow, images re-encoded.
2. ``evaluate_plan(payload)``: given the plot polygon (image pixels), the angle of true north on the image and the
   marked rooms, compute for every room its bearing from the plot centre, its 16-zone (22.5 deg) and 8-direction
   placement, the 81-pada (9x9) Vastu Purusha Mandala cell and devata, and a rating from the room x zone lists.
   Also returns the degree wheel (16 zones with from/to degrees in image space) so the client can draw the chakra.

Bearing convention: compass degrees, 0 = north, clockwise. ``north_angle`` is where true north points on the
image, measured clockwise from "up" (0 = north is up, 90 = north points right).
All interpretation is tendency-level and draft (a vastu practitioner should review the zone data).
"""
from __future__ import annotations

import base64
import io
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from . import vastu

_ZONES = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "vastu_zones.json"
MAX_UPLOAD = 12 * 1024 * 1024
MAX_SIDE = 1600
DIRS8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


@lru_cache(maxsize=1)
def zones_data() -> dict:
    return json.loads(_ZONES.read_text(encoding="utf-8"))


def room_catalog() -> dict:
    """All room keys usable on a plan: the 8-direction table's rooms plus the zone-only extras."""
    k = vastu.knowledge()["rooms"]
    out = {key: {"hi": r["hi"], "en": r["en"]} for key, r in k.items()}
    for key, r in zones_data()["extra_rooms"].items():
        out.setdefault(key, r)
    return out


# ---------------------------------------------------------------- uploads
def _png_b64(img) -> tuple[str, int, int]:
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        f = MAX_SIDE / max(w, h)
        img = img.resize((max(1, int(w * f)), max(1, int(h * f))))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii"), img.size[0], img.size[1]


def _pdf_to_image(data: bytes):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(data)
    if len(doc) == 0:
        raise ValueError("PDF has no pages")
    page = doc[0]
    w, h = page.get_size()
    scale = min(3.0, MAX_SIDE / max(w, h))
    return page.render(scale=max(0.5, scale)).to_pil(), len(doc)


def _dxf_pairs(text: str):
    lines = text.splitlines()
    for i in range(0, len(lines) - 1, 2):
        code = lines[i].strip()
        if code.lstrip("-").isdigit():
            yield int(code), lines[i + 1].strip()


def parse_dxf(text: str) -> list[dict]:
    """Minimal DXF reader → list of primitives in drawing units: {type: line|polyline|circle|arc, ...}."""
    prims, cur, section, in_entities = [], None, None, False
    poly = None
    for code, val in _dxf_pairs(text):
        if code == 0:
            if cur:
                prims.append(cur)
            if poly and val != "VERTEX" and val != "SEQEND":
                prims.append(poly); poly = None
            cur = None
            if val == "SECTION":
                section = "pending"
            elif val == "ENDSEC":
                section, in_entities = None, False
            elif in_entities:
                if val == "LINE":
                    cur = {"type": "line"}
                elif val == "LWPOLYLINE":
                    cur = {"type": "polyline", "pts": [], "closed": False}
                elif val == "POLYLINE":
                    poly = {"type": "polyline", "pts": [], "closed": False}
                elif val == "VERTEX" and poly is not None:
                    cur = {"type": "_vertex"}
                elif val == "SEQEND" and poly is not None:
                    prims.append(poly); poly = None
                elif val in ("CIRCLE", "ARC"):
                    cur = {"type": val.lower()}
            continue
        if section == "pending" and code == 2:
            section = val
            in_entities = val == "ENTITIES"
            continue
        if cur is None:
            continue
        t = cur["type"]
        try:
            f = float(val)
        except ValueError:
            f = None
        if t == "line":
            if code == 10: cur["x1"] = f
            elif code == 20: cur["y1"] = f
            elif code == 11: cur["x2"] = f
            elif code == 21: cur["y2"] = f
        elif t == "polyline":
            if code == 10: cur["pts"].append([f, None])
            elif code == 20 and cur["pts"]: cur["pts"][-1][1] = f
            elif code == 70 and f is not None: cur["closed"] = bool(int(f) & 1)
        elif t == "_vertex":
            if code == 10: cur["x"] = f
            elif code == 20:
                cur["y"] = f
                poly["pts"].append([cur.get("x", 0.0), f])
        elif t in ("circle", "arc"):
            if code == 10: cur["cx"] = f
            elif code == 20: cur["cy"] = f
            elif code == 40: cur["r"] = f
            elif code == 50: cur["a1"] = f
            elif code == 51: cur["a2"] = f
    if cur:
        prims.append(cur)
    if poly:
        prims.append(poly)
    out = []
    for p in prims:
        if p["type"] == "line" and all(k in p for k in ("x1", "y1", "x2", "y2")):
            out.append(p)
        elif p["type"] == "polyline":
            pts = [q for q in p["pts"] if q[1] is not None]
            if len(pts) >= 2:
                out.append({"type": "polyline", "pts": pts, "closed": p["closed"]})
        elif p["type"] in ("circle", "arc") and all(k in p for k in ("cx", "cy", "r")):
            out.append(p)
    return out


def _dxf_bounds(prims):
    xs, ys = [], []
    for p in prims:
        if p["type"] == "line":
            xs += [p["x1"], p["x2"]]; ys += [p["y1"], p["y2"]]
        elif p["type"] == "polyline":
            xs += [q[0] for q in p["pts"]]; ys += [q[1] for q in p["pts"]]
        else:
            xs += [p["cx"] - p["r"], p["cx"] + p["r"]]; ys += [p["cy"] - p["r"], p["cy"] + p["r"]]
    return min(xs), min(ys), max(xs), max(ys)


def render_dxf(prims: list[dict]):
    from PIL import Image, ImageDraw
    if not prims:
        raise ValueError("no drawable entities (LINE / LWPOLYLINE / POLYLINE / CIRCLE / ARC) found in the DXF")
    x0, y0, x1, y1 = _dxf_bounds(prims)
    w, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    pad = 40
    scale = (MAX_SIDE - 2 * pad) / max(w, h)
    W, H = int(w * scale) + 2 * pad, int(h * scale) + 2 * pad
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    T = lambda x, y: (pad + (x - x0) * scale, pad + (y1 - y) * scale)    # DXF y up → image y down
    for p in prims:
        if p["type"] == "line":
            d.line([T(p["x1"], p["y1"]), T(p["x2"], p["y2"])], fill="black", width=2)
        elif p["type"] == "polyline":
            pts = [T(*q) for q in p["pts"]]
            if p["closed"]:
                pts.append(pts[0])
            d.line(pts, fill="black", width=2)
        elif p["type"] == "circle":
            cx, cy = T(p["cx"], p["cy"]); r = p["r"] * scale
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=2)
        elif p["type"] == "arc":
            cx, cy = T(p["cx"], p["cy"]); r = p["r"] * scale
            a1, a2 = -p.get("a2", 360.0), -p.get("a1", 0.0)        # PIL angles clockwise from 3 o'clock, image y down
            d.arc([cx - r, cy - r, cx + r, cy + r], a1, a2, fill="black", width=2)
    return img, {"units_width": round(w, 3), "units_height": round(h, 3), "entities": len(prims)}


def convert_upload(filename: str, data: bytes) -> dict:
    if len(data) > MAX_UPLOAD:
        raise ValueError("file is larger than 12 MB")
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    from PIL import Image
    if ext == "pdf" or data[:4] == b"%PDF":
        img, pages = _pdf_to_image(data)
        b64, w, h = _png_b64(img)
        return {"kind": "pdf", "pages": pages, "image_png_b64": b64, "width": w, "height": h,
                "note_hi": "PDF का पहला पृष्ठ चित्र में बदला गया।", "note_en": "Page 1 of the PDF was rendered to an image."}
    if ext == "dxf" or b"ENTITIES" in data[:200000] and b"SECTION" in data[:5000]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        prims = parse_dxf(text)
        img, meta = render_dxf(prims)
        b64, w, h = _png_b64(img)
        return {"kind": "dxf", "image_png_b64": b64, "width": w, "height": h, **meta,
                "note_hi": f"DXF की {meta['entities']} रेखा-आकृतियाँ (LINE/POLYLINE/CIRCLE/ARC) चित्र में बदली गईं; टेक्स्ट, हैच और ब्लॉक नहीं दिखते। DWG हो तो AutoCAD/LibreCAD से DXF में सेव कीजिए।",
                "note_en": f"{meta['entities']} DXF entities (LINE/POLYLINE/CIRCLE/ARC) rendered; text, hatches and blocks are not shown. For a DWG, save it as DXF from AutoCAD/LibreCAD."}
    if ext == "dwg" or data[:4] in (b"AC10", b"AC10"):
        raise ValueError("DWG is a closed binary format; please save the drawing as DXF (File → Save As → DXF) or PDF and upload that")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ValueError("unsupported file: upload a PDF, DXF, PNG or JPG plan") from exc
    b64, w, h = _png_b64(img)
    return {"kind": "image", "image_png_b64": b64, "width": w, "height": h}


# ---------------------------------------------------------------- geometry
def _centroid(poly):
    a = cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross; cx += (x0 + x1) * cross; cy += (y0 + y1) * cross
    if abs(a) < 1e-9:
        return sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def _inside(pt, poly) -> bool:
    x, y = pt; ins = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi:
                ins = not ins
    return ins


def image_bearing(cx, cy, x, y) -> float:
    """Clockwise degrees from image-up of the point as seen from the centre (image y grows downward)."""
    return math.degrees(math.atan2(x - cx, -(y - cy))) % 360.0


def true_bearing(cx, cy, x, y, north_angle: float) -> float:
    return (image_bearing(cx, cy, x, y) - north_angle) % 360.0


def zone16(bearing: float) -> dict:
    i = int(((bearing % 360) + 11.25) // 22.5) % 16
    return zones_data()["zones"][i]


def _rot(p, cx, cy, deg):
    """Rotate an image point about (cx, cy) by `deg` clockwise on screen (image y grows downward)."""
    a = math.radians(deg)
    dx, dy = p[0] - cx, p[1] - cy
    return (dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a))


def _north_up(poly, north_angle, pt=None):
    """Plot and point rotated so that true north points up (rotate by -north_angle), relative to the centroid."""
    cx, cy = _centroid(poly)
    rp = [_rot(p, cx, cy, -north_angle) for p in poly]
    return (cx, cy), rp, (_rot(pt, cx, cy, -north_angle) if pt is not None else None)


def mandala_cell(poly, north_angle: float, pt) -> dict:
    """9x9 pada of the plot's north-aligned bounding box that contains the point, with its devata."""
    _, rp, (px, py) = _north_up(poly, north_angle, pt)
    xs = [p[0] for p in rp]; ys = [p[1] for p in rp]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    col = min(8, max(0, int((px - x0) / max(x1 - x0, 1e-9) * 9)))
    row = min(8, max(0, int((py - y0) / max(y1 - y0, 1e-9) * 9)))      # row 0 = north edge
    M = zones_data()["mandala"]
    ring = max(abs(col - 4), abs(row - 4))
    if ring == 0 or ring == 1:
        dev = M["centre"]; ring_name = "brahma"
    elif ring == 4:
        # clockwise from the NE corner: east side top→bottom (rows 0..8 at col 8), south side right→left, west side bottom→top, north side left→right
        if col == 8:
            k = row
        elif row == 8:
            k = 8 + (8 - col)
        elif col == 0:
            k = 16 + (8 - row)
        else:
            k = 24 + col
        dev = M["outer_32_clockwise_from_ne"][k % 32]; ring_name = "outer"
    else:
        dc, dr = col - 4, row - 4
        if abs(dc) == abs(dr):
            key = ("NE" if dc > 0 else "NW") if dr < 0 else ("SE" if dc > 0 else "SW")
        elif abs(dc) > abs(dr):
            key = "E" if dc > 0 else "W"
        else:
            key = "N" if dr < 0 else "S"
        dev = M["inner_8"][key]; ring_name = "inner"
    return {"row": row, "col": col, "ring": ring_name, "devata": dev["en"], "devata_hi": dev["hi"]}


def wheel(north_angle: float) -> list[dict]:
    """16 zones with their from/to angles in IMAGE space (clockwise from up), for drawing."""
    out = []
    for z in zones_data()["zones"]:
        out.append({"key": z["key"], "hi": z["hi"], "en": z["en"], "centre_deg": z["centre_deg"],
                    "image_from_deg": (z["from_deg"] + north_angle) % 360, "image_to_deg": (z["to_deg"] + north_angle) % 360,
                    "element_hi": z["element_hi"], "element": z["element"], "theme_hi": z["theme_hi"], "theme": z["theme"]})
    return out


def rate_zone(room: str, z: dict) -> str:
    if room in z["good_rooms"]:
        return "ideal"
    if room in z["avoid_rooms"]:
        return "avoid"
    return "neutral"


def evaluate_plan(payload: dict) -> dict:
    poly = payload.get("polygon") or []
    if not isinstance(poly, list) or len(poly) < 3 or len(poly) > 60:
        raise ValueError("polygon must be 3-60 [x, y] points of the plot boundary")
    try:
        poly = [(float(p[0]), float(p[1])) for p in poly]
        north = float(payload.get("north_angle", 0.0)) % 360.0
    except (TypeError, ValueError, IndexError):
        raise ValueError("polygon points must be [x, y] numbers and north_angle a number")
    rooms = payload.get("rooms") or []
    if not isinstance(rooms, list) or len(rooms) > 60:
        raise ValueError("rooms must be a list of up to 60 {room, x, y}")
    cat = room_catalog()
    k8 = vastu.knowledge()
    cx, cy = _centroid(poly)
    out, score, mx = [], 0, 0
    for r in rooms:
        room = r.get("room")
        if room not in cat:
            raise ValueError(f"unknown room '{room}'")
        try:
            x, y = float(r["x"]), float(r["y"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("each room needs x and y")
        b = true_bearing(cx, cy, x, y, north)
        z = zone16(b)
        d8 = vastu.direction_from_degrees(b)
        lvl = rate_zone(room, z)
        # fall back to the 8-direction table when the zone lists say nothing
        if lvl == "neutral" and room in k8["rooms"]:
            lvl = vastu.rate(room, d8)
        score += vastu.SCORE[lvl]; mx += 2
        row = {"room": room, "room_hi": cat[room]["hi"], "room_en": cat[room]["en"], "x": x, "y": y, "bearing": round(b, 1),
               "zone": z["key"], "zone_hi": z["hi"], "zone_en": z["en"], "zone_theme_hi": z["theme_hi"], "zone_theme": z["theme"],
               "direction": d8, "direction_hi": k8["directions"][d8]["hi"], "inside_plot": _inside((x, y), poly),
               "pada": mandala_cell(poly, north, (x, y)), "rating": lvl, "rating_hi": vastu.LABEL_HI[lvl]}
        good = [zz for zz in zones_data()["zones"] if room in zz["good_rooms"]]
        if good:
            row["good_zones_hi"] = [zz["hi"] for zz in good]; row["good_zones"] = [zz["en"] for zz in good]
        if room in k8["rooms"]:
            row["why_hi"] = k8["rooms"][room]["why_hi"]; row["why"] = k8["rooms"][room]["why"]
            if lvl == "avoid":
                row["fix_hi"] = k8["rooms"][room]["fix_hi"]; row["fix"] = k8["rooms"][room]["fix"]
        out.append(row)
    # plot shape: cut corners relative to the north-aligned bounding box (classical "cut" check)
    (cx, cy), rp, _ = _north_up(poly, north, None)
    xs = [p[0] for p in rp]; ys = [p[1] for p in rp]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    corners = {"NE": (x1, y0), "NW": (x0, y0), "SE": (x1, y1), "SW": (x0, y1)}
    cut = []
    for key, c in corners.items():
        # sample a point 8% inside the box from that corner; the corner is "cut" when it lies outside the plot
        sx = c[0] + (x0 - c[0]) * 0.08 if c[0] == x1 else c[0] + (x1 - c[0]) * 0.08
        sy = c[1] + (y1 - c[1]) * 0.08 if c[1] == y0 else c[1] + (y0 - c[1]) * 0.08
        bx, by = _rot((sx + cx, sy + cy), cx, cy, north)             # back to image coordinates (relative to the centre)
        if not _inside((bx + cx, by + cy), poly):
            cut.append(key)
    skew_note = None
    if len(cut) == 4:        # plot not aligned with the cardinal directions: the bounding-box test says nothing useful
        cut = []
        skew_note = {"hi": "प्लॉट दिशाओं से तिरछा है, इसलिए कटे कोनों की जाँच छोड़ी गई।", "en": "The plot is skewed to the cardinal directions, so the cut-corner check was skipped."}
    CUT_HI = {"NE": "ईशान कटा हुआ: परंपरा में इसे सबसे अधिक टाला जाता है (ज्ञान, स्पष्टता की दिशा)।",
              "SW": "नैऋत्य कटा हुआ: स्थिरता की दिशा; परंपरा इसे भारी और पूरा रखने को कहती है।",
              "SE": "आग्नेय कटा हुआ: अग्नि/ऊर्जा की दिशा; हल्का दोष माना जाता है।",
              "NW": "वायव्य कटा हुआ: गति/सहयोग की दिशा; हल्का दोष माना जाता है।"}
    CUT_EN = {"NE": "North-east cut: tradition avoids this most (direction of knowledge and clarity).",
              "SW": "South-west cut: the direction of stability; tradition keeps it heavy and complete.",
              "SE": "South-east cut: the fire/energy direction; a minor defect.", "NW": "North-west cut: the direction of movement/support; a minor defect."}
    return {"centre": {"x": round(cx, 1), "y": round(cy, 1)}, "north_angle": north, "polygon": [[round(p[0], 1), round(p[1], 1)] for p in poly],
            "wheel": wheel(north), "rooms": out, "score": score, "max": mx,
            "cut_corners": [{"corner": c, "corner_hi": k8["directions"][c]["hi"], "text_hi": CUT_HI[c], "text_en": CUT_EN[c]} for c in cut],
            "skew_note": skew_note,
            "mandala": {"grid": 9, "centre_hi": zones_data()["mandala"]["centre"]["hi"]},
            "review_status": "draft",
            "note_hi": "16-ज़ोन चक्र (22.5° प्रत्येक) प्लॉट के केंद्र से, आपके बताए उत्तर-कोण पर। कमरे का ज़ोन उसकी चिह्नित बिंदु की दिशा से तय हुआ; "
                       "81-पद वास्तु पुरुष मंडल उत्तर-सीधे बाउंडिंग-बॉक्स पर रखा गया। यह परंपरागत प्रवृत्ति-मार्गदर्शन है, निर्णय नहीं; ज़ोन-सूची की समीक्षा बाकी है।",
            "note_en": "16-zone wheel (22.5° each) from the plot centre at the north angle you set. A room's zone comes from the direction of its marked point; "
                       "the 81-pada Vastu Purusha Mandala is laid on the north-aligned bounding box. Traditional tendency-level guidance, not a verdict; the zone lists await review.",
            "disclaimer_hi": vastu.knowledge().get("disclaimer_hi", ""), }
