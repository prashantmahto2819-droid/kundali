"""Consultation with human astrologers, plus a wallet — built so the app can stay free (KUNDALI_PAID=0 by default).

Tables (in the access SQLite): astrologers (admin-managed profiles), consult_requests (a seeker's booking / question),
consult_messages (in-app thread between seeker and astrologer), wallet_ledger (credits/debits per phone; top-ups are
recorded by the admin after verifying a UPI/bank reference — there is no payment gateway here, by design).

Flow: seeker picks an astrologer and a mode (chat / call / report), posts a request with phone + question (+ birth details) →
the astrologer is pinged on WhatsApp through Vivid Relay (and the seeker gets a confirmation) → the astrologer answers in
the in-app thread or over the phone/WhatsApp directly → status open → answered → closed. When KUNDALI_PAID=1, a request costs
the astrologer's price in wallet credits (₹), debited on acceptance; otherwise prices are shown as "free / dakshina optional".
Admin calls need the header X-Admin-Key = KUNDALI_ADMIN_KEY.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone

from . import access, notify

SCHEMA = """
CREATE TABLE IF NOT EXISTS astrologers(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, name_hi TEXT, phone TEXT, photo TEXT, languages TEXT, specialities TEXT, bio_hi TEXT, bio_en TEXT,
  experience_years INTEGER, price_chat INTEGER NOT NULL DEFAULT 0, price_call INTEGER NOT NULL DEFAULT 0, price_report INTEGER NOT NULL DEFAULT 0,
  hours TEXT, active INTEGER NOT NULL DEFAULT 1, rating REAL, ratings_count INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consult_requests(
  id TEXT PRIMARY KEY, astrologer_id TEXT NOT NULL, phone TEXT NOT NULL, name TEXT, mode TEXT NOT NULL, question TEXT, birth TEXT, lang TEXT,
  status TEXT NOT NULL DEFAULT 'open', price INTEGER NOT NULL DEFAULT 0, paid INTEGER NOT NULL DEFAULT 0, rating INTEGER, created TEXT NOT NULL, updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consult_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL, sender TEXT NOT NULL, text TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS wallet_ledger(id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL, amount INTEGER NOT NULL, kind TEXT NOT NULL, ref TEXT, note TEXT, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_req_phone ON consult_requests(phone);
"""
MODES = {"chat": ("चैट (ऐप में संदेश)", "chat (in-app messages)"), "call": ("फ़ोन/WhatsApp कॉल", "phone / WhatsApp call"), "report": ("लिखित विश्लेषण", "written analysis")}
_store: access.Store | None = None


def paid() -> bool:
    return os.environ.get("KUNDALI_PAID", "0") in ("1", "true", "yes")


def db() -> access.Store:
    global _store
    if _store is None:
        _store = access.default_store()
        with _store._lock:
            _store._db.executescript(SCHEMA)
    return _store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rows(sql: str, args=()) -> list[dict]:
    s = db()
    with s._lock:
        return [dict(r) for r in s._db.execute(sql, args).fetchall()]


def _exec(sql: str, args=()):
    s = db()
    with s._lock:
        s._db.execute(sql, args)
        s._db.commit()


def is_admin(headers: dict) -> bool:
    key = os.environ.get("KUNDALI_ADMIN_KEY", "")
    h = {k.lower(): v for k, v in (headers or {}).items()}
    return bool(key) and secrets.compare_digest(h.get("x-admin-key", ""), key)


# ---------------------------------------------------------------- astrologers
def _pub(a: dict) -> dict:
    out = {k: a.get(k) for k in ("id", "name", "name_hi", "photo", "experience_years", "bio_hi", "bio_en", "hours", "rating", "ratings_count", "active")}
    out["languages"] = (a.get("languages") or "").split(",") if a.get("languages") else []
    out["specialities"] = (a.get("specialities") or "").split(",") if a.get("specialities") else []
    out["prices"] = {m: (a.get(f"price_{m}") or 0) if paid() else 0 for m in MODES}
    out["paid"] = paid()
    return out


def list_astrologers(include_inactive: bool = False) -> list[dict]:
    rows = _rows("SELECT * FROM astrologers" + ("" if include_inactive else " WHERE active=1") + " ORDER BY rating DESC NULLS LAST, created")
    return [_pub(a) for a in rows]


def upsert_astrologer(data: dict) -> dict:
    aid = re.sub(r"[^a-z0-9_-]", "", str(data.get("id") or data.get("name", "")).lower().replace(" ", "-"))[:40]
    if not aid or not data.get("name"):
        raise ValueError("id/name required")
    old = _rows("SELECT * FROM astrologers WHERE id=?", (aid,))
    row = old[0] if old else {"created": _now(), "active": 1, "ratings_count": 0}
    for k in ("name", "name_hi", "phone", "photo", "bio_hi", "bio_en", "hours"):
        if k in data:
            row[k] = str(data[k])[:600] if data[k] is not None else None
    for k in ("languages", "specialities"):
        if k in data:
            row[k] = ",".join(str(x).strip() for x in data[k]) if isinstance(data[k], list) else str(data[k])
    for k in ("experience_years", "price_chat", "price_call", "price_report", "active"):
        if k in data:
            row[k] = int(data[k])
    if row.get("phone"):
        row["phone"] = notify.normalize_phone(row["phone"])
    row["id"] = aid
    cols = ["id", "name", "name_hi", "phone", "photo", "languages", "specialities", "bio_hi", "bio_en", "experience_years", "price_chat", "price_call", "price_report", "hours", "active", "rating", "ratings_count", "created"]
    _exec(f"INSERT OR REPLACE INTO astrologers({','.join(cols)}) VALUES ({','.join(':' + c for c in cols)})", {c: row.get(c) for c in cols})
    return _pub(_rows("SELECT * FROM astrologers WHERE id=?", (aid,))[0])


# ---------------------------------------------------------------- wallet
def balance(phone: str) -> int:
    r = _rows("SELECT COALESCE(SUM(amount),0) AS b FROM wallet_ledger WHERE phone=?", (phone,))
    return int(r[0]["b"]) if r else 0


def ledger(phone: str, n: int = 20) -> list[dict]:
    return _rows("SELECT amount, kind, ref, note, at FROM wallet_ledger WHERE phone=? ORDER BY id DESC LIMIT ?", (phone, n))


def topup(phone: str, amount: int, ref: str, note: str = "") -> dict:
    """Admin records a verified top-up (UPI/bank reference). Idempotent on the reference."""
    phone = notify.normalize_phone(phone)
    if amount <= 0 or amount > 100000:
        raise ValueError("amount must be 1..100000")
    if ref and _rows("SELECT 1 FROM wallet_ledger WHERE ref=? AND kind='topup'", (ref,)):
        raise ValueError("this reference was already credited")
    _exec("INSERT INTO wallet_ledger(phone, amount, kind, ref, note, at) VALUES (?,?,?,?,?,?)", (phone, int(amount), "topup", ref, note[:200], _now()))
    return {"phone": phone, "balance": balance(phone)}


# ---------------------------------------------------------------- requests
def create_request(payload: dict) -> dict:
    phone = notify.normalize_phone(payload.get("phone"))
    aid = str(payload.get("astrologer_id") or "")
    a = _rows("SELECT * FROM astrologers WHERE id=? AND active=1", (aid,))
    if not a:
        raise ValueError("astrologer not found")
    a = a[0]
    mode = str(payload.get("mode") or "chat")
    if mode not in MODES:
        raise ValueError("mode must be chat, call or report")
    question = str(payload.get("question") or "").strip()[:2000]
    if len(question) < 5:
        raise ValueError("please write the question (at least 5 characters)")
    lang = "en" if payload.get("lang") == "en" else "hi"
    price = int(a.get(f"price_{mode}") or 0) if paid() else 0
    if price and balance(phone) < price:
        raise ValueError(f"insufficient wallet balance: need ₹{price}, have ₹{balance(phone)}")
    rid = "c" + secrets.token_hex(5)
    birth = payload.get("birth") if isinstance(payload.get("birth"), dict) else None
    _exec("INSERT INTO consult_requests(id, astrologer_id, phone, name, mode, question, birth, lang, status, price, paid, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (rid, aid, phone, str(payload.get("name") or "")[:60], mode, question, json.dumps(birth, ensure_ascii=False) if birth else None, lang, "open", price, 0, _now(), _now()))
    if price:
        _exec("INSERT INTO wallet_ledger(phone, amount, kind, ref, note, at) VALUES (?,?,?,?,?,?)", (phone, -price, "consult", rid, f"{a['name']} / {mode}", _now()))
        _exec("UPDATE consult_requests SET paid=1 WHERE id=?", (rid,))
    _exec("INSERT INTO consult_messages(request_id, sender, text, at) VALUES (?,?,?,?)", (rid, "seeker", question, _now()))
    # notify astrologer and seeker over WhatsApp (best effort)
    site = os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com")
    b = f"\nजन्म: {birth.get('date')} {birth.get('time')} ({birth.get('lat')},{birth.get('lon')})" if birth else ""
    sent_a = notify.send_whatsapp(a["phone"], f"🪔 नया परामर्श अनुरोध #{rid} ({MODES[mode][0]})\nसे: {payload.get('name') or phone} ({phone}){b}\nप्रश्न: {question}\n\nउत्तर ऐप में दीजिए: {site}/?consult={rid}") if a.get("phone") else {"ok": False, "detail": "astrologer has no phone"}
    seeker_txt = (f"🙏 आपका अनुरोध #{rid} {a.get('name_hi') or a['name']} जी को भेज दिया गया ({MODES[mode][0]})। उत्तर आने पर यहीं सूचना मिलेगी; ऐप में देखें: {site}/?consult={rid}" if lang == "hi" else
                  f"🙏 Your request #{rid} has been sent to {a['name']} ({MODES[mode][1]}). You will be notified here when there is a reply; see it in the app: {site}/?consult={rid}")
    sent_s = notify.send_whatsapp(phone, seeker_txt)
    return {"id": rid, "status": "open", "price": price, "balance": balance(phone) if paid() else None, "astrologer": _pub(a),
            "notified_astrologer": sent_a["ok"], "notified_seeker": sent_s["ok"], "relay_ready": notify.relay_ready()}


def get_request(rid: str, phone: str | None = None, admin: bool = False) -> dict:
    r = _rows("SELECT * FROM consult_requests WHERE id=?", (rid,))
    if not r:
        raise ValueError("request not found")
    r = r[0]
    a = _rows("SELECT * FROM astrologers WHERE id=?", (r["astrologer_id"],))
    role = "admin" if admin else None
    if not admin and phone:
        ph = notify.normalize_phone(phone)
        if ph == r["phone"]:
            role = "seeker"
        elif a and a[0].get("phone") == ph:
            role = "astrologer"
        else:
            raise ValueError("this request belongs to another number")
    msgs = _rows("SELECT sender, text, at FROM consult_messages WHERE request_id=? ORDER BY id", (rid,))
    out = {k: r[k] for k in ("id", "astrologer_id", "mode", "status", "price", "paid", "rating", "created", "updated", "lang", "name")}
    out["role"] = role
    out["phone"] = r["phone"] if role in ("admin", "astrologer") else r["phone"][:4] + "…" + r["phone"][-2:]
    out["birth"] = json.loads(r["birth"]) if r["birth"] else None
    out["messages"] = msgs
    out["astrologer"] = _pub(a[0]) if a else None
    return out


def my_requests(phone: str) -> list[dict]:
    phone = notify.normalize_phone(phone)
    rows = _rows("SELECT id, astrologer_id, mode, status, price, created, updated FROM consult_requests WHERE phone=? ORDER BY created DESC LIMIT 30", (phone,))
    names = {a["id"]: a.get("name_hi") or a["name"] for a in _rows("SELECT id, name, name_hi FROM astrologers")}
    return [{**r, "astrologer_name": names.get(r["astrologer_id"], r["astrologer_id"])} for r in rows]


def post_message(rid: str, sender: str, text: str, phone: str | None = None, admin: bool = False) -> dict:
    r = _rows("SELECT * FROM consult_requests WHERE id=?", (rid,))
    if not r:
        raise ValueError("request not found")
    r = r[0]
    text = (text or "").strip()[:3000]
    if not text:
        raise ValueError("empty message")
    if sender == "seeker":
        if not admin and (not phone or notify.normalize_phone(phone) != r["phone"]):
            raise ValueError("this request belongs to another number")
    elif sender == "astrologer":
        a = _rows("SELECT phone FROM astrologers WHERE id=?", (r["astrologer_id"],))
        if not admin and not (phone and a and a[0]["phone"] and notify.normalize_phone(phone) == a[0]["phone"]):
            raise ValueError("only the assigned astrologer (or admin) can answer")
    else:
        raise ValueError("sender must be seeker or astrologer")
    _exec("INSERT INTO consult_messages(request_id, sender, text, at) VALUES (?,?,?,?)", (rid, sender, text, _now()))
    status = "answered" if sender == "astrologer" else r["status"]
    _exec("UPDATE consult_requests SET status=?, updated=? WHERE id=?", (status, _now(), rid))
    site = os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com")
    if sender == "astrologer":
        notify.send_whatsapp(r["phone"], (f"💬 आपके परामर्श #{rid} का उत्तर आ गया:\n\n{text[:900]}\n\nपूरा देखें: {site}/?consult={rid}" if r["lang"] != "en" else f"💬 Reply to your consultation #{rid}:\n\n{text[:900]}\n\nSee it: {site}/?consult={rid}"))
    else:
        a = _rows("SELECT phone FROM astrologers WHERE id=?", (r["astrologer_id"],))
        if a and a[0]["phone"]:
            notify.send_whatsapp(a[0]["phone"], f"💬 #{rid} पर नया संदेश: {text[:500]}\n{site}/?consult={rid}")
    return get_request(rid, admin=True) if (admin or sender == "astrologer") else get_request(rid, phone)


def close_request(rid: str, phone: str | None, rating: int | None = None, admin: bool = False) -> dict:
    r = _rows("SELECT * FROM consult_requests WHERE id=?", (rid,))
    if not r:
        raise ValueError("request not found")
    r = r[0]
    if not admin and (not phone or notify.normalize_phone(phone) != r["phone"]):
        raise ValueError("this request belongs to another number")
    if rating is not None:
        rating = max(1, min(5, int(rating)))
        _exec("UPDATE consult_requests SET rating=? WHERE id=?", (rating, rid))
        a = _rows("SELECT rating, ratings_count FROM astrologers WHERE id=?", (r["astrologer_id"],))
        if a:
            n = int(a[0]["ratings_count"] or 0); avg = float(a[0]["rating"] or 0)
            _exec("UPDATE astrologers SET rating=?, ratings_count=? WHERE id=?", (round((avg * n + rating) / (n + 1), 2), n + 1, r["astrologer_id"]))
    _exec("UPDATE consult_requests SET status='closed', updated=? WHERE id=?", (_now(), rid))
    return get_request(rid, phone, admin=admin)


def wallet_view(phone: str) -> dict:
    phone = notify.normalize_phone(phone)
    return {"phone": phone, "paid": paid(), "balance": balance(phone), "ledger": ledger(phone),
            "topup_note_hi": os.environ.get("KUNDALI_TOPUP_NOTE_HI", "टॉप-अप के लिए UPI से भुगतान कर संदर्भ संख्या WhatsApp पर भेजें; सत्यापन के बाद राशि जुड़ती है।"),
            "upi_id": os.environ.get("KUNDALI_UPI_ID", "")}


def admin_overview() -> dict:
    return {"astrologers": list_astrologers(include_inactive=True),
            "open_requests": _rows("SELECT id, astrologer_id, phone, mode, status, price, created FROM consult_requests WHERE status!='closed' ORDER BY created DESC LIMIT 100"),
            "recent_topups": _rows("SELECT phone, amount, ref, note, at FROM wallet_ledger WHERE kind='topup' ORDER BY id DESC LIMIT 50"), "paid": paid()}
