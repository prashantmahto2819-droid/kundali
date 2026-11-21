"""Browser push notifications for the daily panchang — no WhatsApp needed, works on Android Chrome, desktop browsers and
installed iPhone web apps (iOS 16.4+).

Standards only: VAPID (RFC 8292) for the sender identity and aes128gcm payload encryption (RFC 8291/8188), implemented
on `cryptography`. VAPID keys come from VAPID_PRIVATE_KEY (base64url, 32-byte P-256 scalar) or are generated once and kept
in vapid.json next to the access database.

Subscriptions live in table push_subs; the notify worker calls run_once() every minute and sends each subscriber one
notification at their chosen local time (tithi with end time, nakshatra, Rahu kaal, today's vrat/festival, tomorrow's
festival). Endpoints that answer 404/410 are removed.
"""
from __future__ import annotations

import base64
import json
import os
import struct
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SCHEMA = """
CREATE TABLE IF NOT EXISTS push_subs(endpoint TEXT PRIMARY KEY, p256dh TEXT NOT NULL, auth TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
  tz TEXT NOT NULL, place TEXT, lang TEXT NOT NULL DEFAULT 'hi', daily_time TEXT NOT NULL DEFAULT '06:30', moon_sign INTEGER,
  last_daily TEXT, fails INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
"""


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ------------------------------------------------------------------ keys
_KEY = None


def _key_file() -> str:
    db = os.environ.get("KUNDALI_DB", "")
    return os.path.join(os.path.dirname(db) if db else ".", "vapid.json")


def vapid_key() -> ec.EllipticCurvePrivateKey:
    global _KEY
    if _KEY is not None:
        return _KEY
    raw = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not raw:
        f = _key_file()
        try:
            raw = json.load(open(f))["private"]
        except (OSError, ValueError, KeyError):
            k = ec.generate_private_key(ec.SECP256R1())
            raw = b64u(k.private_numbers().private_value.to_bytes(32, "big"))
            try:
                with open(f, "w") as fh:
                    json.dump({"private": raw}, fh)
                os.chmod(f, 0o600)
            except OSError:
                pass
    _KEY = ec.derive_private_key(int.from_bytes(unb64u(raw), "big"), ec.SECP256R1())
    return _KEY


def _pub_bytes(k) -> bytes:
    return k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def public_key() -> str:
    """The applicationServerKey the browser needs for PushManager.subscribe()."""
    return b64u(_pub_bytes(vapid_key()))


def vapid_header(endpoint: str, subject: str | None = None) -> str:
    from urllib.parse import urlsplit
    u = urlsplit(endpoint)
    sub = subject or os.environ.get("VAPID_SUBJECT") or ("mailto:" + os.environ["KUNDALI_CONTACT_EMAIL"] if os.environ.get("KUNDALI_CONTACT_EMAIL") else
                                                         os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com"))
    head = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64u(json.dumps({"aud": f"{u.scheme}://{u.netloc}", "exp": int(time.time()) + 12 * 3600, "sub": sub}, separators=(",", ":")).encode())
    der = vapid_key().sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    sig = b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={head}.{body}.{sig}, k={public_key()}"


# ------------------------------------------------------------------ RFC 8291 encryption
def _hkdf(salt: bytes, ikm: bytes, info: bytes, n: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=n, salt=salt, info=info).derive(ikm)


def encrypt(payload: bytes, p256dh: str, auth: str, *, _eph=None, _salt=None) -> bytes:
    ua_pub = unb64u(p256dh); auth_secret = unb64u(auth)
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub)
    eph = _eph or ec.generate_private_key(ec.SECP256R1())
    as_pub = _pub_bytes(eph)
    shared = eph.exchange(ec.ECDH(), ua_key)
    ikm = _hkdf(auth_secret, shared, b"WebPush: info\x00" + ua_pub + as_pub, 32)
    salt = _salt or os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    ct = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)          # single record, 0x02 = last-record delimiter
    rs = 4096
    return salt + struct.pack("!IB", rs, len(as_pub)) + as_pub + ct


def decrypt(body: bytes, ua_priv: ec.EllipticCurvePrivateKey, auth: str) -> bytes:
    """Receiver side (used by the tests to prove the encryption is right)."""
    salt, rs, idlen = body[:16], struct.unpack("!I", body[16:20])[0], body[20]
    as_pub = body[21:21 + idlen]; ct = body[21 + idlen:]
    ua_pub = _pub_bytes(ua_priv)
    shared = ua_priv.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    ikm = _hkdf(unb64u(auth), shared, b"WebPush: info\x00" + ua_pub + as_pub, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    pt = AESGCM(cek).decrypt(nonce, ct, None)
    return pt.rstrip(b"\x00")[:-1]


def send(sub: dict, message: dict, ttl: int = 6 * 3600) -> dict:
    body = encrypt(json.dumps(message, ensure_ascii=False).encode(), sub["p256dh"], sub["auth"])
    req = urllib.request.Request(sub["endpoint"], data=body, method="POST", headers={
        "TTL": str(ttl), "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", "Urgency": "normal",
        "Authorization": vapid_header(sub["endpoint"])})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return {"ok": 200 <= r.status < 300, "status": r.status}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "gone": e.code in (404, 410), "detail": e.read()[:200].decode("utf-8", "replace")}
    except OSError as e:
        return {"ok": False, "status": 0, "detail": str(e)[:200]}


# ------------------------------------------------------------------ store
class Subs:
    def __init__(self, store):
        self.db = store._db
        self.db.executescript(SCHEMA); self.db.commit()

    def upsert(self, row: dict):
        cols = ["endpoint", "p256dh", "auth", "lat", "lon", "tz", "place", "lang", "daily_time", "moon_sign", "created"]
        self.db.execute(f"INSERT INTO push_subs({','.join(cols)}) VALUES({','.join('?' * len(cols))}) ON CONFLICT(endpoint) DO UPDATE SET "
                        + ",".join(f"{c}=excluded.{c}" for c in cols if c not in ("endpoint", "created")) + ", fails=0",
                        [row.get(c) for c in cols])
        self.db.commit()

    def get(self, endpoint: str) -> dict | None:
        cur = self.db.execute("SELECT * FROM push_subs WHERE endpoint=?", (endpoint,)); r = cur.fetchone()
        return dict(zip([d[0] for d in cur.description], r)) if r else None

    def all(self) -> list[dict]:
        cur = self.db.execute("SELECT * FROM push_subs"); names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def set(self, endpoint: str, **kw):
        self.db.execute("UPDATE push_subs SET " + ",".join(f"{k}=?" for k in kw) + " WHERE endpoint=?", [*kw.values(), endpoint]); self.db.commit()

    def delete(self, endpoint: str):
        self.db.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,)); self.db.commit()

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM push_subs").fetchone()[0]


_subs = None


def subs() -> Subs:
    global _subs
    if _subs is None:
        from . import access
        _subs = Subs(access.default_store())
    return _subs


# ------------------------------------------------------------------ content
def compose(sub: dict, d: date) -> dict:
    from . import notify
    hi = sub.get("lang", "hi") != "en"
    day = notify._day(sub, d)
    if not day:
        return {}
    tithi = f'{day["paksha_hi"]} {day["tithi_hi"]}' if hi else f'{day["paksha"]} {day["tithi"]}'
    te = (day["tithi_ends"] or "—") + ("+" if day["tithi_ends_next_day"] else "")
    nak = day["nakshatra_hi"] if hi else day["nakshatra"]
    rk = day.get("rahu_kaal")
    lines = [(f"तिथि: {tithi} ({te} तक) · नक्षत्र: {nak}" if hi else f"Tithi: {tithi} (until {te}) · Nakshatra: {nak}"),
             (f"☀️ {day['sunrise']}–{day['sunset']} · राहु काल {rk['start']}–{rk['end']}" if hi else f"☀️ {day['sunrise']}–{day['sunset']} · Rahu kaal {rk['start']}–{rk['end']}") if rk else ""]
    kinds = ("grahan", "festival", "ekadashi", "purnima", "amavasya", "pradosh", "chaturthi", "shivaratri", "national")
    ev = [x for x in day["events"] if x["kind"] in kinds]
    if ev:
        lines.append("🪔 " + ", ".join(x["name_hi"] if hi else x["name_en"] for x in ev))
    tm = notify._day(sub, d + timedelta(days=1))
    if tm:
        ev2 = [x for x in tm["events"] if x["kind"] in kinds]
        if ev2:
            lines.append(("कल: " if hi else "Tomorrow: ") + ", ".join(x["name_hi"] if hi else x["name_en"] for x in ev2))
    vara = day["vara_hi"] if hi else day["vara"]
    title = (f"🌅 आज का पंचांग — {vara}" if hi else f"🌅 Today's panchang — {vara}") + (f" ({sub['place']})" if sub.get("place") else "")
    return {"title": title, "body": "\n".join(x for x in lines if x), "url": "/#t-today", "tag": "panchang-" + d.isoformat()}


# ------------------------------------------------------------------ API
def subscribe(payload: dict) -> dict:
    s = payload.get("subscription") or {}
    ep = str(s.get("endpoint") or ""); keys = s.get("keys") or {}
    if not ep.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        raise ValueError("subscription must have an https endpoint and keys.p256dh / keys.auth")
    try:
        unb64u(keys["p256dh"]); unb64u(keys["auth"])
    except Exception:
        raise ValueError("bad subscription keys")
    lat, lon = float(payload.get("lat", 28.61)), float(payload.get("lon", 77.2))
    tz = str(payload.get("tz") or "Asia/Kolkata"); ZoneInfo(tz)
    t = str(payload.get("daily_time") or "06:30")
    hh, mm = (int(x) for x in t.split(":")); assert 0 <= hh < 24 and 0 <= mm < 60
    row = {"endpoint": ep, "p256dh": keys["p256dh"], "auth": keys["auth"], "lat": lat, "lon": lon, "tz": tz, "place": str(payload.get("place") or "")[:60],
           "lang": "en" if payload.get("lang") == "en" else "hi", "daily_time": f"{hh:02d}:{mm:02d}",
           "moon_sign": int(payload["moon_sign"]) % 12 if payload.get("moon_sign") not in (None, "") else None,
           "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    subs().upsert(row)
    return {"subscribed": True, "daily_time": row["daily_time"], "count": subs().count()}


def unsubscribe(payload: dict) -> dict:
    subs().delete(str(payload.get("endpoint") or "")); return {"subscribed": False}


def test(payload: dict, sender=send) -> dict:
    sub = subs().get(str(payload.get("endpoint") or ""))
    if not sub:
        raise ValueError("not subscribed")
    d = datetime.now(ZoneInfo(sub["tz"])).date()
    return sender(sub, compose(sub, d))


def due(sub: dict, now_utc: datetime) -> bool:
    local = now_utc.astimezone(ZoneInfo(sub["tz"]))
    hh, mm = (int(x) for x in sub["daily_time"].split(":"))
    return (local.hour, local.minute) >= (hh, mm) and sub.get("last_daily") != local.date().isoformat()


def run_once(now_utc: datetime | None = None, sender=send) -> list[dict]:
    now_utc = now_utc or datetime.now(timezone.utc)
    out = []
    for sub in subs().all():
        if not due(sub, now_utc):
            continue
        d = now_utc.astimezone(ZoneInfo(sub["tz"])).date()
        msg = compose(sub, d)
        res = sender(sub, msg) if msg else {"ok": False, "detail": "no panchang"}
        if res.get("gone") or (not res.get("ok") and sub.get("fails", 0) >= 6):
            subs().delete(sub["endpoint"])
        elif res.get("ok"):
            subs().set(sub["endpoint"], last_daily=d.isoformat(), fails=0)
        else:                                   # skip today (no retry storm); drop after ~a week of failed days
            subs().set(sub["endpoint"], last_daily=d.isoformat(), fails=sub.get("fails", 0) + 1)
        out.append({"endpoint": sub["endpoint"][-24:], **{k: v for k, v in res.items() if k != "detail"}})
    return out
