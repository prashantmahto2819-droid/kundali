"""Vastu from a floor plan: uploads, geometry, zones, mandala."""
import base64
import io

import pytest
from PIL import Image

from jyotish import handlers, vastu_plan as vp

SQ = [[0, 0], [400, 0], [400, 300], [0, 300]]
DXF = ("0\nSECTION\n2\nENTITIES\n0\nLINE\n8\n0\n10\n0\n20\n0\n11\n100\n21\n0\n0\nLWPOLYLINE\n8\nwalls\n90\n4\n70\n1\n"
       "10\n0\n20\n0\n10\n100\n20\n0\n10\n100\n20\n80\n10\n0\n20\n80\n0\nCIRCLE\n8\n0\n10\n50\n20\n40\n40\n5\n0\nENDSEC\n0\nEOF\n")


def test_bearings_and_zones_north_up():
    cx, cy = 200, 150
    assert vp.true_bearing(cx, cy, 200, 0, 0) == 0.0            # straight up = north
    assert vp.true_bearing(cx, cy, 400, 150, 0) == 90.0         # right = east
    assert vp.true_bearing(cx, cy, 400, 150, 90) == 0.0         # north points right → right is north
    assert vp.zone16(0)["key"] == "N" and vp.zone16(11.2)["key"] == "N" and vp.zone16(11.3)["key"] == "NNE"
    assert vp.zone16(45)["key"] == "NE" and vp.zone16(348.75)["key"] == "N" and vp.zone16(348.7)["key"] == "NNW"


def test_evaluate_rooms_rating_and_pada():
    res = vp.evaluate_plan({"polygon": SQ, "north_angle": 0, "rooms": [
        {"room": "kitchen", "x": 380, "y": 280}, {"room": "pooja", "x": 380, "y": 20}, {"room": "toilet", "x": 380, "y": 20}, {"room": "master_bedroom", "x": 20, "y": 280}]})
    by = {(r["room"]): r for r in res["rooms"]}
    assert by["kitchen"]["zone"] == "SE" and by["kitchen"]["rating"] == "ideal" and by["kitchen"]["pada"]["devata"] == "Agni"
    assert by["pooja"]["zone"] == "NE" and by["pooja"]["rating"] == "ideal" and by["pooja"]["pada"]["devata"] == "Isha"
    assert by["toilet"]["rating"] == "avoid" and by["toilet"]["fix_hi"]
    assert by["master_bedroom"]["zone"] == "SW" and by["master_bedroom"]["pada"]["devata"] == "Pitru"
    centre = vp.evaluate_plan({"polygon": SQ, "north_angle": 0, "rooms": [{"room": "living", "x": 200, "y": 150}]})["rooms"][0]
    assert centre["pada"]["ring"] == "brahma" and centre["inside_plot"]
    assert res["score"] == 2 + 2 - 2 + 2 and res["max"] == 8 and len(res["wheel"]) == 16


def test_north_angle_rotates_everything():
    r0 = vp.evaluate_plan({"polygon": SQ, "north_angle": 0, "rooms": [{"room": "kitchen", "x": 380, "y": 20}]})["rooms"][0]
    r90 = vp.evaluate_plan({"polygon": SQ, "north_angle": 90, "rooms": [{"room": "kitchen", "x": 380, "y": 20}]})["rooms"][0]
    assert r0["zone"] == "NE" and r90["zone"] == "NW"                   # top-right becomes north-west when north points right
    assert r90["pada"]["devata"] == "Roga"
    w = vp.wheel(30)
    assert w[0]["image_from_deg"] == pytest.approx((348.75 + 30) % 360) and w[0]["image_to_deg"] == pytest.approx(41.25)


def test_cut_corners_and_skew():
    L = [[0, 0], [400, 0], [400, 300], [200, 300], [200, 150], [0, 150]]
    assert [c["corner"] for c in vp.evaluate_plan({"polygon": L, "north_angle": 0, "rooms": []})["cut_corners"]] == ["SW"]
    assert [c["corner"] for c in vp.evaluate_plan({"polygon": L, "north_angle": 180, "rooms": []})["cut_corners"]] == ["NE"]
    sk = vp.evaluate_plan({"polygon": L, "north_angle": 45, "rooms": []})
    assert sk["cut_corners"] == [] and sk["skew_note"]
    assert vp.evaluate_plan({"polygon": SQ, "north_angle": 0, "rooms": []})["cut_corners"] == []


def test_uploads_dxf_pdf_image_and_errors():
    d = vp.convert_upload("plan.dxf", DXF.encode())
    assert d["kind"] == "dxf" and d["entities"] == 3 and d["width"] > 0 and base64.b64decode(d["image_png_b64"])[:4] == b"\x89PNG"
    prims = vp.parse_dxf(DXF)
    assert {p["type"] for p in prims} == {"line", "polyline", "circle"} and prims[1]["closed"] and len(prims[1]["pts"]) == 4
    img = Image.new("RGB", (300, 200), "white"); buf = io.BytesIO(); img.save(buf, format="JPEG")
    j = vp.convert_upload("x.jpg", buf.getvalue()); assert j["kind"] == "image" and j["width"] == 300
    pdf = io.BytesIO(); img.save(pdf, format="PDF")
    p = vp.convert_upload("x.pdf", pdf.getvalue()); assert p["kind"] == "pdf" and p["pages"] == 1
    with pytest.raises(ValueError):
        vp.convert_upload("x.dwg", b"AC1027" + b"\x00" * 100)
    with pytest.raises(ValueError):
        vp.convert_upload("x.bin", b"\x00\x01\x02")


def test_handlers_validate():
    out = handlers.vastu_plan_upload_from_payload({"filename": "a.dxf", "content_b64": base64.b64encode(DXF.encode()).decode()})
    assert out["kind"] == "dxf"
    with pytest.raises(handlers.BadRequest):
        handlers.vastu_plan_upload_from_payload({"filename": "a.dxf", "content_b64": ""})
    with pytest.raises(handlers.BadRequest):
        handlers.vastu_plan_from_payload({"polygon": [[0, 0], [1, 1]], "rooms": []})
    with pytest.raises(handlers.BadRequest):
        handlers.vastu_plan_from_payload({"polygon": SQ, "rooms": [{"room": "spaceship", "x": 1, "y": 1}]})
    html = handlers.vastu_plan_report_from_payload({"polygon": SQ, "north_angle": 0, "rooms": [{"room": "kitchen", "x": 380, "y": 280}], "lang": "en"})
    assert "Kitchen" in html and "Agni" in html
    cat = handlers.vastu_plan_catalog()
    assert "kitchen" in cat["rooms"] and "septic_tank" in cat["rooms"] and len(cat["zones"]) == 16 and len(cat["mandala"]["outer_32_clockwise_from_ne"]) == 32
