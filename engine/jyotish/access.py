"""Multi-tenant access layer: organisations, API keys and daily usage limits.

Identity model (same for every door into the API):
    request -> org  (API key today; a Supabase login token later resolves to the same org)
    org     -> plan -> daily request limit; usage is counted per org per day per endpoint.

Only the SHA-256 hash of a key is stored; the plain key is shown once at creation. Keys are long random
tokens, so a plain hash is sufficient (no password-style stretching needed).
SQLite is the dev/test store; production swaps in Postgres (Supabase) behind the same methods.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

PLANS = {"free": 200, "pro": 20000, "unlimited": None}      # requests per UTC day
KEY_PREFIX = "kd_"
HEADER = "x-api-key"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs(id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS api_keys(id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES orgs(id), prefix TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE, label TEXT, active INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, last_used TEXT);
CREATE TABLE IF NOT EXISTS usage(org_id TEXT NOT NULL, day TEXT NOT NULL, endpoint TEXT NOT NULL, count INTEGER NOT NULL,
  PRIMARY KEY(org_id, day, endpoint));
CREATE TABLE IF NOT EXISTS user_orgs(user_id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES orgs(id), email TEXT);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: str | os.PathLike = ":memory:", plans: dict | None = None):
        self.plans = dict(PLANS if plans is None else plans)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            from . import people
            self._db.executescript(people.SCHEMA)
            if "profile" not in [r[1] for r in self._db.execute("PRAGMA table_info(orgs)")]:      # migration: astrologer profile
                self._db.execute("ALTER TABLE orgs ADD COLUMN profile TEXT")
                self._db.commit()

    # ---- organisations and keys -------------------------------------------------
    def create_org(self, name: str, plan: str = "free") -> dict:
        if plan not in self.plans:
            raise ValueError(f"unknown plan '{plan}' (choose {', '.join(self.plans)})")
        if not name.strip():
            raise ValueError("organisation name is required")
        org = {"id": str(uuid.uuid4()), "name": name.strip(), "plan": plan, "created": _now().isoformat()}
        with self._lock:
            self._db.execute("INSERT INTO orgs(id, name, plan, created) VALUES (:id,:name,:plan,:created)", org)
            self._db.commit()
        return org

    def create_key(self, org_id: str, label: str = "") -> tuple[str, dict]:
        """Returns (plain_key, record). The plain key cannot be recovered later."""
        if self.get_org(org_id) is None:
            raise ValueError("unknown organisation")
        plain = KEY_PREFIX + secrets.token_urlsafe(32)
        rec = {"id": str(uuid.uuid4()), "org_id": org_id, "prefix": plain[:10], "key_hash": _hash(plain),
               "label": label, "created": _now().isoformat()}
        with self._lock:
            self._db.execute("INSERT INTO api_keys(id,org_id,prefix,key_hash,label,created) "
                             "VALUES (:id,:org_id,:prefix,:key_hash,:label,:created)", rec)
            self._db.commit()
        return plain, {k: v for k, v in rec.items() if k != "key_hash"}

    def revoke_key(self, key_id: str) -> bool:
        with self._lock:
            cur = self._db.execute("UPDATE api_keys SET active=0 WHERE id=? OR prefix=?", (key_id, key_id))
            self._db.commit()
            return cur.rowcount > 0

    def org_for_user(self, user_id: str, email: str = "") -> dict:
        """Personal organisation of a signed-in user (created on first login)."""
        with self._lock:
            r = self._db.execute("SELECT org_id FROM user_orgs WHERE user_id=?", (user_id,)).fetchone()
        if r:
            return self.get_org(r["org_id"])
        org = self.create_org(email or f"user-{user_id[:8]}")
        with self._lock:
            self._db.execute("INSERT OR IGNORE INTO user_orgs VALUES(?,?,?)", (user_id, org["id"], email))
            self._db.commit()
            r = self._db.execute("SELECT org_id FROM user_orgs WHERE user_id=?", (user_id,)).fetchone()
        return self.get_org(r["org_id"])

    PROFILE_FIELDS = {"brand_name": 80, "phone": 30, "line": 160, "address": 200, "website": 120}

    def get_profile(self, org_id: str) -> dict:
        with self._lock:
            r = self._db.execute("SELECT profile FROM orgs WHERE id=?", (org_id,)).fetchone()
        try:
            data = json.loads(r["profile"]) if r and r["profile"] else {}
        except ValueError:
            data = {}
        return {k: str(data.get(k, ""))[:n] for k, n in self.PROFILE_FIELDS.items()}

    def set_profile(self, org_id: str, data: dict) -> dict:
        clean = {k: str(data.get(k, "") or "").strip()[:n] for k, n in self.PROFILE_FIELDS.items()}
        with self._lock:
            self._db.execute("UPDATE orgs SET profile=? WHERE id=?", (json.dumps(clean, ensure_ascii=False), org_id))
            self._db.commit()
        return clean

    def get_org(self, org_id: str) -> dict | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM orgs WHERE id=?", (org_id,)).fetchone()
        return dict(r) if r else None

    def list_orgs(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._db.execute("SELECT * FROM orgs ORDER BY created")]

    def set_plan(self, org_id: str, plan: str) -> None:
        if plan not in self.plans:
            raise ValueError(f"unknown plan '{plan}'")
        with self._lock:
            self._db.execute("UPDATE orgs SET plan=? WHERE id=?", (plan, org_id))
            self._db.commit()

    def authenticate(self, key: str | None) -> dict | None:
        if not key or not key.startswith(KEY_PREFIX) or len(key) > 200:
            return None
        h = _hash(key)
        with self._lock:
            r = self._db.execute("SELECT k.id AS key_id, k.key_hash, o.* FROM api_keys k JOIN orgs o ON o.id=k.org_id "
                                 "WHERE k.key_hash=? AND k.active=1", (h,)).fetchone()
            if r is None or not hmac.compare_digest(r["key_hash"], h):
                return None
            self._db.execute("UPDATE api_keys SET last_used=? WHERE id=?", (_now().isoformat(), r["key_id"]))
            self._db.commit()
        return {"id": r["id"], "name": r["name"], "plan": r["plan"], "key_id": r["key_id"]}

    # ---- usage -----------------------------------------------------------------
    def hit(self, org: dict, endpoint: str, now: datetime | None = None) -> dict:
        """Count one request unless the org is over its daily limit."""
        now = now or _now()
        day = now.strftime("%Y-%m-%d")
        limit = self.plans.get(org["plan"])
        with self._lock:
            used = self._db.execute("SELECT COALESCE(SUM(count),0) FROM usage WHERE org_id=? AND day=?",
                                    (org["id"], day)).fetchone()[0]
            if limit is not None and used >= limit:
                reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                return {"allowed": False, "limit": limit, "used": used, "remaining": 0,
                        "retry_after": max(1, int((reset - now).total_seconds()))}
            self._db.execute("INSERT INTO usage VALUES (?,?,?,1) ON CONFLICT(org_id,day,endpoint) "
                             "DO UPDATE SET count=count+1", (org["id"], day, endpoint))
            self._db.commit()
        used += 1
        return {"allowed": True, "limit": limit, "used": used,
                "remaining": None if limit is None else limit - used, "retry_after": 0}

    def usage(self, org_id: str, days: int = 7, now: datetime | None = None) -> list[dict]:
        since = ((now or _now()) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        with self._lock:
            rows = self._db.execute("SELECT day, endpoint, count FROM usage WHERE org_id=? AND day>=? "
                                    "ORDER BY day DESC, endpoint", (org_id, since)).fetchall()
        return [dict(r) for r in rows]


# ---- request guard (shared by the dev server and FastAPI) ---------------------------
_store: Store | None = None


def default_store() -> Store:
    global _store
    if _store is None:
        _store = Store(os.environ.get("KUNDALI_DB", str(Path(__file__).resolve().parents[2] / "kundali_access.db")))
    return _store


def auth_mode() -> str:
    m = os.environ.get("KUNDALI_AUTH", "off").lower()
    return m if m in ("off", "optional", "required") else "off"


def resolve(headers, store, verifier=None):
    """-> (org | None, error | None). API key or Supabase Bearer token."""
    key = headers.get(HEADER) or headers.get("X-API-Key")
    if key:
        org = store.authenticate(key)
        return (org, None) if org else (None, "invalid or revoked API key")
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else None
    if token:
        if verifier is None:
            try:
                from . import auth_supabase                      # needs PyJWT; imported only when a login token arrives
            except ImportError:
                return None, "login tokens are not supported on this server (PyJWT missing)"
            verifier = auth_supabase.verify
        who = verifier(token)
        return (store.org_for_user(who["user_id"], who["email"]), None) if who else (None, "invalid or expired login token")
    return None, None


def guard(headers, path: str, store: Store | None = None, mode: str | None = None,
          now: datetime | None = None) -> tuple[int, dict, dict, dict | None]:
    """-> (status, body, response_headers, org). status 200 means 'go ahead'.

    off      : no checks (development).
    optional : a key, if sent, must be valid and is metered; no key means anonymous (the public web page).
    required : a valid key is mandatory for every /v1 call.
    """
    mode = mode or auth_mode()
    if mode == "off" or not path.startswith("/v1/"):
        return 200, {}, {}, None
    store = store or default_store()
    org, err = resolve(headers, store)
    if err:
        return 401, {"detail": err}, {}, None
    if org is None:
        if mode == "required":
            return 401, {"detail": "API key or login required (X-API-Key or Authorization: Bearer)"}, {}, None
        return 200, {}, {}, None
    h = store.hit(org, path, now)
    rl = {"X-RateLimit-Limit": "unlimited" if h["limit"] is None else str(h["limit"]),
          "X-RateLimit-Remaining": "unlimited" if h["remaining"] is None else str(h["remaining"])}
    if not h["allowed"]:
        rl["Retry-After"] = str(h["retry_after"])
        return 429, {"detail": "daily request limit reached for this plan"}, rl, org
    return 200, {}, rl, org
