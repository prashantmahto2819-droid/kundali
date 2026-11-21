"""रत्न-शॉप: a small catalogue (gemstones, uparatna, rudraksha, yantra, mala …) managed from admin.html, a cart in the browser,
and orders paid by UPI (deep link / QR to the owner's UPI ID) or cash on delivery.

There is no payment gateway: the order is saved with status "new", the owner gets a WhatsApp alert (Vivid Relay) and marks it
paid → packed → shipped → delivered from the admin page after checking the UPI reference. Settings:
  KUNDALI_UPI_ID, KUNDALI_UPI_NAME      where UPI payments go
  KUNDALI_SHOP_WHATSAPP                 the owner's number for new-order alerts and the "ask on WhatsApp" button
  KUNDALI_SHOP_COD=1                    allow cash on delivery
  KUNDALI_SHOP_SHIPPING                 flat shipping in rupees (default 0), KUNDALI_SHOP_FREE_ABOVE (free above this total)
Images are uploaded from admin (JPEG/PNG/WebP ≤ 1.5 MB) and stored next to the database.
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import urllib.parse
from datetime import datetime, timezone

CATEGORIES = {"gemstone": ("रत्न", "Gemstone"), "uparatna": ("उपरत्न", "Semi-precious"), "rudraksha": ("रुद्राक्ष", "Rudraksha"),
              "yantra": ("यंत्र", "Yantra"), "mala": ("माला", "Mala"), "puja": ("पूजा सामग्री", "Puja items"), "other": ("अन्य", "Other")}
UNITS = {"ratti": ("रत्ती", "ratti"), "carat": ("कैरेट", "carat"), "piece": ("नग", "piece")}
STATUSES = ["new", "paid", "packed", "shipped", "delivered", "cancelled"]
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS shop_products(id TEXT PRIMARY KEY, name_hi TEXT NOT NULL, name_en TEXT, category TEXT NOT NULL, planet TEXT,
  price REAL NOT NULL, mrp REAL, unit TEXT NOT NULL DEFAULT 'piece', min_qty REAL NOT NULL DEFAULT 1, max_qty REAL NOT NULL DEFAULT 10, step REAL NOT NULL DEFAULT 1,
  stock INTEGER, origin TEXT, certificate TEXT, desc_hi TEXT, desc_en TEXT, images TEXT NOT NULL DEFAULT '[]', active INTEGER NOT NULL DEFAULT 1,
  sort INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shop_orders(id TEXT PRIMARY KEY, items TEXT NOT NULL, subtotal REAL NOT NULL, shipping REAL NOT NULL, total REAL NOT NULL,
  name TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, city TEXT, pincode TEXT, note TEXT, payment TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new', pay_ref TEXT, track TEXT, history TEXT NOT NULL DEFAULT '[]', created TEXT NOT NULL, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shop_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL, order_id TEXT NOT NULL, name TEXT NOT NULL,
  rating INTEGER NOT NULL, text TEXT, visible INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, UNIQUE(order_id, product_id));
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Shop:
    def __init__(self, store):
        self.db = store._db
        self.dir = os.path.join(os.path.dirname(os.environ.get("KUNDALI_DB", "") or "./x"), "shop_images")
        self.db.executescript(SCHEMA)
        cols = [r[1] for r in self.db.execute("PRAGMA table_info(shop_products)")]
        for c, t in (("hsn", "TEXT"), ("gst_rate", "REAL")):          # migration: tax fields for invoices
            if c not in cols:
                self.db.execute(f"ALTER TABLE shop_products ADD COLUMN {c} {t}")
        self.db.commit()

    def _rows(self, sql, args=()):
        cur = self.db.execute(sql, args); names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]


_shop = None


def shop() -> Shop:
    global _shop
    if _shop is None:
        from . import access
        _shop = Shop(access.default_store())
    return _shop


def settings() -> dict:
    return {"upi_id": os.environ.get("KUNDALI_UPI_ID", ""), "upi_name": os.environ.get("KUNDALI_UPI_NAME", "") or os.environ.get("KUNDALI_BRAND_NAME", "") or "Kundali",
            "whatsapp": re.sub(r"\D", "", os.environ.get("KUNDALI_SHOP_WHATSAPP", "")), "cod": os.environ.get("KUNDALI_SHOP_COD", "0") in ("1", "true", "yes"),
            "shipping": float(os.environ.get("KUNDALI_SHOP_SHIPPING", "0") or 0), "free_above": float(os.environ.get("KUNDALI_SHOP_FREE_ABOVE", "0") or 0)}


def _public(p: dict) -> dict:
    p = dict(p); p["images"] = json.loads(p.get("images") or "[]")
    p["category_hi"], p["category_en"] = CATEGORIES.get(p["category"], CATEGORIES["other"])
    p["unit_hi"], p["unit_en"] = UNITS.get(p["unit"], UNITS["piece"])
    p["in_stock"] = p.get("stock") is None or p["stock"] > 0
    return p


# ---------------------------------------------------------------- public API
def products(q: dict | None = None) -> dict:
    q = q or {}
    sql, args = "SELECT * FROM shop_products WHERE active=1", []
    if q.get("category"):
        sql += " AND category=?"; args.append(str(q["category"]))
    if q.get("planet"):
        sql += " AND planet=?"; args.append(str(q["planet"]))
    rows = [_public(p) for p in shop()._rows(sql + " ORDER BY sort, name_hi", args)]
    agg = {r["product_id"]: r for r in shop()._rows("SELECT product_id, COUNT(*) n, AVG(rating) avg FROM shop_reviews WHERE visible=1 GROUP BY product_id")}
    for p in rows:
        a = agg.get(p["id"]); p["rating"] = round(a["avg"], 1) if a else None; p["reviews"] = a["n"] if a else 0
    s = settings()
    return {"products": rows, "categories": [{"key": k, "hi": v[0], "en": v[1]} for k, v in CATEGORIES.items()],
            "settings": {"upi": bool(s["upi_id"]), "cod": s["cod"], "shipping": s["shipping"], "free_above": s["free_above"], "whatsapp": s["whatsapp"]}}


def product(pid: str) -> dict:
    r = shop()._rows("SELECT * FROM shop_products WHERE id=? AND active=1", (pid,))
    if not r:
        raise ValueError("product not found")
    return _public(r[0])


def _phone(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 10:
        d = "91" + d
    if not 11 <= len(d) <= 13:
        raise ValueError("enter a valid mobile number")
    return d


def upi_link(amount: float, order_id: str) -> str:
    s = settings()
    if not s["upi_id"]:
        return ""
    return "upi://pay?" + urllib.parse.urlencode({"pa": s["upi_id"], "pn": s["upi_name"], "am": f"{amount:.2f}", "cu": "INR", "tn": f"Order {order_id}"}, quote_via=urllib.parse.quote)


def place_order(payload: dict, notifier=None) -> dict:
    items_in = payload.get("items") or []
    if not isinstance(items_in, list) or not items_in or len(items_in) > 20:
        raise ValueError("cart is empty")
    name = str(payload.get("name") or "").strip()[:80]
    address = str(payload.get("address") or "").strip()[:400]
    pincode = re.sub(r"\D", "", str(payload.get("pincode") or ""))[:6]
    if len(name) < 2 or len(address) < 8 or len(pincode) != 6:
        raise ValueError("name, full address and a 6-digit pincode are required")
    phone = _phone(payload.get("phone"))
    s = settings()
    payment = "cod" if payload.get("payment") == "cod" else "upi"
    if payment == "cod" and not s["cod"]:
        raise ValueError("cash on delivery is not available")
    if payment == "upi" and not s["upi_id"]:
        payment = "cod" if s["cod"] else "whatsapp"
    items, subtotal = [], 0.0
    for it in items_in:
        p = product(str(it.get("id")))
        qty = float(it.get("qty") or p["min_qty"])
        if qty < p["min_qty"] or qty > p["max_qty"]:
            raise ValueError(f"{p['name_hi']}: quantity must be {p['min_qty']:g}–{p['max_qty']:g} {p['unit_hi']}")
        if p.get("stock") is not None and p["stock"] < (1 if p["unit"] != "piece" else qty):
            raise ValueError(f"{p['name_hi']}: out of stock")
        amt = round(p["price"] * qty, 2)
        items.append({"id": p["id"], "name_hi": p["name_hi"], "name_en": p.get("name_en") or "", "qty": qty, "unit_hi": p["unit_hi"], "price": p["price"], "amount": amt,
                      "hsn": p.get("hsn") or "", "gst_rate": p.get("gst_rate"),
                      "option": str(it.get("option") or "")[:80]})
        subtotal += amt
    shipping = 0.0 if (s["free_above"] and subtotal >= s["free_above"]) else s["shipping"]
    total = round(subtotal + shipping, 2)
    oid = "K" + datetime.now(timezone.utc).strftime("%y%m%d") + secrets.token_hex(2).upper()
    now = _now()
    db = shop().db
    db.execute("INSERT INTO shop_orders(id, items, subtotal, shipping, total, name, phone, address, city, pincode, note, payment, status, history, created, updated) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (oid, json.dumps(items, ensure_ascii=False), subtotal, shipping, total, name, phone, address, str(payload.get("city") or "")[:60], pincode,
                str(payload.get("note") or "")[:300], payment, "new", json.dumps([{"at": now, "status": "new"}]), now, now))
    for it in items:                                    # pieces reduce stock; ratti/carat items are cut from one stone lot
        db.execute("UPDATE shop_products SET stock=stock-? WHERE id=? AND stock IS NOT NULL", (it["qty"] if it["unit_hi"] == UNITS["piece"][0] else 1, it["id"]))
    db.commit()
    lines = "\n".join(f"• {it['name_hi']} × {it['qty']:g} {it['unit_hi']} = ₹{it['amount']:,.0f}" + (f" ({it['option']})" if it["option"] else "") for it in items)
    alert = (f"🛒 *नया ऑर्डर {oid}*\n{lines}\nकुल: *₹{total:,.0f}* ({'UPI' if payment == 'upi' else 'COD' if payment == 'cod' else 'WhatsApp'})\n"
             f"{name} · +{phone}\n{address}, {payload.get('city') or ''} {pincode}")
    sent = False
    if s["whatsapp"]:
        try:
            if notifier is None:
                from .notify import send_whatsapp as notifier
            sent = bool(notifier(s["whatsapp"], alert).get("ok"))
        except Exception:
            sent = False
    wa_text = f"नमस्ते, मेरा ऑर्डर {oid} (₹{total:,.0f})।"
    return {"order_id": oid, "total": total, "subtotal": subtotal, "shipping": shipping, "payment": payment, "upi_link": upi_link(total, oid) if payment == "upi" else "",
            "upi_id": s["upi_id"] if payment == "upi" else "", "owner_alerted": sent,
            "whatsapp_link": f"https://wa.me/{s['whatsapp']}?text={urllib.parse.quote(wa_text)}" if s["whatsapp"] else ""}


def order_status(payload: dict) -> dict:
    oid = str(payload.get("order_id") or "").strip().upper(); phone = _phone(payload.get("phone"))
    r = shop()._rows("SELECT id, items, total, payment, status, track, history, created FROM shop_orders WHERE id=? AND phone=?", (oid, phone))
    if not r:
        raise ValueError("order not found for this phone number")
    o = r[0]; o["items"] = json.loads(o["items"]); o["history"] = json.loads(o["history"])
    return o


# ---------------------------------------------------------------- admin
def admin(payload: dict) -> dict:
    a = str(payload.get("action") or "list")
    db = shop().db
    if a == "list":
        prods = [_public(p) for p in shop()._rows("SELECT * FROM shop_products ORDER BY active DESC, sort, name_hi")]
        orders = shop()._rows("SELECT * FROM shop_orders ORDER BY created DESC LIMIT 300")
        for o in orders:
            o["items"] = json.loads(o["items"]); o["history"] = json.loads(o["history"])
        return {"products": prods, "orders": orders, "settings": settings(), "categories": CATEGORIES, "units": UNITS, "statuses": STATUSES, "planets": PLANETS}
    if a == "save_product":
        p = payload.get("product") or {}
        if not str(p.get("name_hi") or "").strip():
            raise ValueError("name_hi required")
        if p.get("category") not in CATEGORIES:
            raise ValueError("category must be one of " + ", ".join(CATEGORIES))
        price = float(p.get("price") or 0)
        if price <= 0:
            raise ValueError("price must be > 0")
        unit = p.get("unit") if p.get("unit") in UNITS else "piece"
        pid = str(p.get("id") or "") or ("p" + secrets.token_hex(4))
        planet = p.get("planet") if p.get("planet") in PLANETS else None
        stock = None if p.get("stock") in (None, "") else int(p["stock"])
        fields = {"name_hi": str(p["name_hi"]).strip()[:120], "name_en": str(p.get("name_en") or "")[:120], "category": p["category"], "planet": planet, "price": price,
                  "mrp": float(p["mrp"]) if p.get("mrp") not in (None, "") else None, "unit": unit, "min_qty": float(p.get("min_qty") or 1), "max_qty": float(p.get("max_qty") or 10),
                  "step": float(p.get("step") or 1), "stock": stock, "origin": str(p.get("origin") or "")[:80], "certificate": str(p.get("certificate") or "")[:120],
                  "desc_hi": str(p.get("desc_hi") or "")[:2000], "desc_en": str(p.get("desc_en") or "")[:2000], "active": 1 if p.get("active", True) else 0, "sort": int(p.get("sort") or 0),
                  "hsn": re.sub(r"\D", "", str(p.get("hsn") or ""))[:8] or None, "gst_rate": float(p["gst_rate"]) if p.get("gst_rate") not in (None, "") else None}
        now = _now()
        if shop()._rows("SELECT id FROM shop_products WHERE id=?", (pid,)):
            db.execute("UPDATE shop_products SET " + ",".join(f"{k}=?" for k in fields) + ", updated=? WHERE id=?", [*fields.values(), now, pid])
        else:
            db.execute(f"INSERT INTO shop_products(id, {','.join(fields)}, created, updated) VALUES(?{',?' * len(fields)},?,?)", [pid, *fields.values(), now, now])
        db.commit()
        return {"saved": pid}
    if a == "delete_product":
        db.execute("UPDATE shop_products SET active=0 WHERE id=?", (str(payload.get("id")),)); db.commit(); return {"hidden": payload.get("id")}
    if a == "upload_image":
        pid = str(payload.get("id") or ""); data = str(payload.get("data") or "")
        m = re.match(r"data:image/(jpeg|png|webp);base64,(.+)$", data, re.S)
        if not m or not shop()._rows("SELECT id FROM shop_products WHERE id=?", (pid,)):
            raise ValueError("send a JPEG/PNG/WebP data URL for an existing product")
        raw = base64.b64decode(m.group(2))
        if len(raw) > 1_500_000:
            raise ValueError("image too large (max 1.5 MB)")
        os.makedirs(shop().dir, exist_ok=True)
        name = f"{pid}_{secrets.token_hex(3)}.{'jpg' if m.group(1) == 'jpeg' else m.group(1)}"
        with open(os.path.join(shop().dir, name), "wb") as f:
            f.write(raw)
        imgs = json.loads(shop()._rows("SELECT images FROM shop_products WHERE id=?", (pid,))[0]["images"] or "[]") + [f"/v1/shop/img/{name}"]
        db.execute("UPDATE shop_products SET images=? WHERE id=?", (json.dumps(imgs[-6:]), pid)); db.commit()
        return {"images": imgs[-6:]}
    if a == "remove_image":
        pid = str(payload.get("id") or ""); url = str(payload.get("url") or "")
        imgs = [x for x in json.loads(shop()._rows("SELECT images FROM shop_products WHERE id=?", (pid,))[0]["images"] or "[]") if x != url]
        db.execute("UPDATE shop_products SET images=? WHERE id=?", (json.dumps(imgs), pid)); db.commit(); return {"images": imgs}
    if a == "order_status":
        oid = str(payload.get("id") or ""); st = payload.get("status")
        if st not in STATUSES:
            raise ValueError("status must be one of " + ", ".join(STATUSES))
        r = shop()._rows("SELECT history FROM shop_orders WHERE id=?", (oid,))
        if not r:
            raise ValueError("order not found")
        hist = json.loads(r[0]["history"]) + [{"at": _now(), "status": st, "note": str(payload.get("note") or "")[:200]}]
        db.execute("UPDATE shop_orders SET status=?, pay_ref=COALESCE(?, pay_ref), track=COALESCE(?, track), history=?, updated=? WHERE id=?",
                   (st, payload.get("pay_ref") or None, payload.get("track") or None, json.dumps(hist, ensure_ascii=False), _now(), oid))
        db.commit()
        told = False
        if payload.get("notify", True) and st != "new":
            o = shop()._rows("SELECT phone, total, track FROM shop_orders WHERE id=?", (oid,))[0]
            msg = {"paid": f"✅ आपका ऑर्डर *{oid}* — ₹{o['total']:,.0f} का भुगतान मिल गया। जल्द पैक करके भेजेंगे। 🙏",
                   "packed": f"📦 आपका ऑर्डर *{oid}* पैक हो गया है, जल्द रवाना होगा।",
                   "shipped": f"🚚 आपका ऑर्डर *{oid}* भेज दिया गया है।" + (f"\nट्रैकिंग: {o['track']}" if o.get("track") else ""),
                   "delivered": f"🎉 आपका ऑर्डर *{oid}* पहुँच गया। धारण विधि ऐप के 'उपाय व रत्न' में देखें। धन्यवाद! 🙏",
                   "cancelled": f"आपका ऑर्डर *{oid}* रद्द कर दिया गया है। कोई प्रश्न हो तो इसी नंबर पर लिखें।"}[st]
            try:
                sender = payload.get("_sender")
                if sender is None:
                    from .notify import send_whatsapp as sender
                told = bool(sender(o["phone"], msg).get("ok"))
            except Exception:
                told = False
        return {"id": oid, "status": st, "customer_notified": told}
    if a == "reviews":
        return {"reviews": shop()._rows("SELECT r.*, p.name_hi FROM shop_reviews r LEFT JOIN shop_products p ON p.id=r.product_id ORDER BY r.created DESC LIMIT 300")}
    if a == "review_visible":
        db.execute("UPDATE shop_reviews SET visible=? WHERE id=?", (1 if payload.get("visible") else 0, int(payload.get("id") or 0))); db.commit()
        return {"id": payload.get("id"), "visible": bool(payload.get("visible"))}
    if a == "invoice":
        r = shop()._rows("SELECT * FROM shop_orders WHERE id=?", (str(payload.get("id") or ""),))
        if not r:
            raise ValueError("order not found")
        return {"html": invoice_html(r[0])}
    raise ValueError("unknown action")


def image_path(name: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9_]+\.(jpg|png|webp)", name or ""):
        return None
    p = os.path.join(shop().dir, name)
    return p if os.path.exists(p) else None



# ---------------------------------------------------------------- verified reviews (delivered orders only)
def add_review(payload: dict) -> dict:
    oid = str(payload.get("order_id") or "").strip().upper(); phone = _phone(payload.get("phone")); pid = str(payload.get("product_id") or "")
    r = shop()._rows("SELECT name, items, status FROM shop_orders WHERE id=? AND phone=?", (oid, phone))
    if not r:
        raise ValueError("order not found for this phone number")
    if r[0]["status"] != "delivered":
        raise ValueError("you can review after the order is delivered")
    if pid not in [i["id"] for i in json.loads(r[0]["items"])]:
        raise ValueError("this product is not in the order")
    rating = int(payload.get("rating") or 0)
    if not 1 <= rating <= 5:
        raise ValueError("rating must be 1-5")
    name = (str(payload.get("name") or "").strip() or r[0]["name"]).split()[0][:30]          # first name only
    try:
        shop().db.execute("INSERT INTO shop_reviews(product_id, order_id, name, rating, text, created) VALUES(?,?,?,?,?,?)",
                          (pid, oid, name, rating, str(payload.get("text") or "").strip()[:600], _now()))
        shop().db.commit()
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise ValueError("already reviewed") from exc
        raise
    return {"saved": True}


def reviews(pid: str, limit: int = 20) -> list[dict]:
    return shop()._rows("SELECT name, rating, text, created FROM shop_reviews WHERE product_id=? AND visible=1 ORDER BY created DESC LIMIT ?", (pid, limit))


# ---------------------------------------------------------------- invoice (tax invoice when a GSTIN is set, else a receipt)
# first two digits of a PIN code → state (for CGST+SGST vs IGST)
PIN_STATE = {**{k: "Delhi" for k in ("11",)}, **{k: "Haryana" for k in ("12", "13")}, **{k: "Punjab" for k in ("14", "15")}, "16": "Chandigarh",
             "17": "Himachal Pradesh", **{k: "Jammu & Kashmir" for k in ("18", "19")}, **{k: "Uttar Pradesh" for k in ("20", "21", "22", "23", "24", "25", "26", "27", "28")},
             **{k: "Rajasthan" for k in ("30", "31", "32", "33", "34")}, **{k: "Gujarat" for k in ("36", "37", "38", "39")}, **{k: "Maharashtra" for k in ("40", "41", "42", "43", "44")},
             **{k: "Madhya Pradesh" for k in ("45", "46", "47", "48")}, "49": "Chhattisgarh", **{k: "Telangana" for k in ("50",)}, **{k: "Andhra Pradesh" for k in ("51", "52", "53")},
             **{k: "Karnataka" for k in ("56", "57", "58", "59")}, **{k: "Tamil Nadu" for k in ("60", "61", "62", "63", "64")}, **{k: "Kerala" for k in ("67", "68", "69")},
             **{k: "West Bengal" for k in ("70", "71", "72", "73", "74")}, **{k: "Odisha" for k in ("75", "76", "77")}, "78": "Assam", "79": "North East",
             **{k: "Bihar" for k in ("80", "81", "82", "83", "84", "85")}}


def invoice_html(o: dict) -> str:
    import html as _h
    e = lambda x: _h.escape(str(x if x is not None else ""))
    items = json.loads(o["items"]) if isinstance(o["items"], str) else o["items"]
    gstin = os.environ.get("KUNDALI_SHOP_GSTIN", "").strip().upper()
    seller = os.environ.get("KUNDALI_SHOP_LEGAL_NAME", "") or settings()["upi_name"]
    saddr = os.environ.get("KUNDALI_SHOP_ADDRESS", "")
    sstate = os.environ.get("KUNDALI_SHOP_STATE", "")
    bstate = PIN_STATE.get(str(o.get("pincode") or "")[:2], "")
    inter = bool(sstate and bstate and sstate.lower() != bstate.lower())
    rows, tax_total, taxable_total = "", 0.0, 0.0
    for i, it in enumerate(items, 1):
        r = float(it.get("gst_rate") or 0) if gstin else 0.0
        taxable = round(it["amount"] / (1 + r / 100), 2); tax = round(it["amount"] - taxable, 2)
        taxable_total += taxable; tax_total += tax
        rows += (f"<tr><td>{i}</td><td>{e(it['name_hi'])}{(' / ' + e(it.get('name_en'))) if it.get('name_en') else ''}{('<br><small>' + e(it['option']) + '</small>') if it.get('option') else ''}</td>"
                 f"<td>{e(it.get('hsn') or '')}</td><td>{it['qty']:g} {e(it['unit_hi'])}</td><td>{it['price']:,.2f}</td>"
                 + (f"<td>{taxable:,.2f}</td><td>{r:g}%</td><td>{tax:,.2f}</td>" if gstin else "") + f"<td>{it['amount']:,.2f}</td></tr>")
    ship = float(o.get("shipping") or 0)
    tax_lines = ""
    if gstin:
        tax_lines = (f"<tr><td colspan=7>IGST</td><td colspan=2>{tax_total:,.2f}</td></tr>" if inter else
                     f"<tr><td colspan=7>CGST</td><td colspan=2>{tax_total / 2:,.2f}</td></tr><tr><td colspan=7>SGST</td><td colspan=2>{tax_total / 2:,.2f}</td></tr>")
    span = 7 if gstin else 4
    title = "TAX INVOICE / कर बीजक" if gstin else "रसीद / RECEIPT"
    head_cols = "<th>#</th><th>विवरण</th><th>HSN</th><th>मात्रा</th><th>दर ₹</th>" + ("<th>कर-योग्य ₹</th><th>GST</th><th>कर ₹</th>" if gstin else "") + "<th>राशि ₹</th>"
    return f"""<!doctype html><html lang="hi"><head><meta charset="utf-8"><title>{e(o['id'])} — {title}</title>
<style>body{{font:14px/1.5 'Noto Sans Devanagari','Noto Sans',sans-serif;color:#222;max-width:820px;margin:20px auto;padding:0 16px}}h1{{font-size:18px;margin:0}}
table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px;text-align:left;vertical-align:top}}th{{background:#f6efe6}}
.top{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}}.muted{{color:#666;font-size:12px}}.tot td{{font-weight:700}}@media print{{button{{display:none}}}}</style></head><body>
<div class="top"><div><h1>{e(seller)}</h1><div>{e(saddr)}</div>{f'<div>GSTIN: <b>{e(gstin)}</b></div>' if gstin else ''}{f'<div>राज्य: {e(sstate)}</div>' if sstate else ''}</div>
<div style="text-align:right"><h1>{title}</h1><div>क्रमांक: <b>{e(o['id'])}</b></div><div>दिनांक: {e(o['created'][:10])}</div><div>भुगतान: {e(o['payment'].upper())}{(' · ' + e(o['pay_ref'])) if o.get('pay_ref') else ''}</div></div></div>
<p><b>ग्राहक:</b> {e(o['name'])} · +{e(o['phone'])}<br>{e(o['address'])}, {e(o.get('city') or '')} {e(o.get('pincode') or '')}{(' · ' + e(bstate)) if bstate else ''}</p>
<table><tr>{head_cols}</tr>{rows}
{f'<tr><td colspan={span}>डिलीवरी</td><td colspan=2>{ship:,.2f}</td></tr>' if ship else ''}{tax_lines}
<tr class="tot"><td colspan={span}>कुल (सभी कर सहित)</td><td colspan=2>₹{o['total']:,.2f}</td></tr></table>
<p class="muted">{'दरें GST सहित हैं; कर-योग्य राशि और कर ऊपर अलग दिखाए गए हैं।' if gstin else 'यह भुगतान की रसीद है (GST पंजीकरण के बिना)।'} रत्न परंपरागत आस्था के अनुसार बेचे जाते हैं; किसी परिणाम की गारंटी नहीं।</p>
<button onclick="print()">प्रिंट / PDF</button></body></html>"""


def customer_invoice(payload: dict) -> dict:
    oid = str(payload.get("order_id") or "").strip().upper(); phone = _phone(payload.get("phone"))
    r = shop()._rows("SELECT * FROM shop_orders WHERE id=? AND phone=?", (oid, phone))
    if not r:
        raise ValueError("order not found for this phone number")
    if r[0]["status"] in ("new", "cancelled"):
        raise ValueError("the invoice is available after payment is confirmed")
    return {"html": invoice_html(r[0])}
