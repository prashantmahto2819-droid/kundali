import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import pytest

from jyotish import access

NOW = datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc)


def make(limit=3):
    st = access.Store(plans={"free": limit, "pro": 10, "unlimited": None})
    org = st.create_org("Acme")
    key, rec = st.create_key(org["id"], "web")
    return st, org, key, rec


def test_key_is_random_hashed_and_authenticates():
    st, org, key, rec = make()
    assert key.startswith("kd_") and len(key) > 40 and rec["prefix"] == key[:10]
    assert st.authenticate(key)["id"] == org["id"]
    assert st.authenticate(key + "x") is None and st.authenticate("") is None and st.authenticate(None) is None
    assert st.authenticate("kd_" + "a" * 300) is None
    dump = "\n".join(st._db.iterdump())
    assert key not in dump                       # only the hash is stored
    assert access._hash(key) in dump


def test_quota_denies_after_limit_and_resets_next_day():
    st, org, key, _ = make(limit=3)
    o = st.authenticate(key)
    res = [st.hit(o, "/v1/chart", NOW) for _ in range(4)]
    assert [r["allowed"] for r in res] == [True, True, True, False]
    assert res[0]["remaining"] == 2 and res[3]["remaining"] == 0 and res[3]["retry_after"] > 0
    assert st.hit(o, "/v1/tarot", NOW)["allowed"] is False          # limit is per org, not per endpoint
    assert st.hit(o, "/v1/chart", NOW + timedelta(days=1))["allowed"] is True


def test_usage_summary_and_plans():
    st, org, key, _ = make(limit=50)
    o = st.authenticate(key)
    for _ in range(3):
        st.hit(o, "/v1/chart", NOW)
    st.hit(o, "/v1/tarot", NOW)
    u = st.usage(org["id"], 7, NOW)
    assert {(r["endpoint"], r["count"]) for r in u} == {("/v1/chart", 3), ("/v1/tarot", 1)}
    st.set_plan(org["id"], "unlimited")
    o = st.authenticate(key)
    assert all(st.hit(o, "/v1/chart", NOW)["allowed"] for _ in range(100))
    with pytest.raises(ValueError):
        st.set_plan(org["id"], "gold")


def test_revocation():
    st, org, key, rec = make()
    assert st.revoke_key(rec["id"]) and st.authenticate(key) is None
    assert not st.revoke_key("nope")


def test_orgs_are_isolated():
    st = access.Store(plans={"free": 2})
    a, b = st.create_org("A"), st.create_org("B")
    ka, _ = st.create_key(a["id"])
    kb, _ = st.create_key(b["id"])
    oa, ob = st.authenticate(ka), st.authenticate(kb)
    assert oa["id"] != ob["id"]
    st.hit(oa, "/v1/chart", NOW); st.hit(oa, "/v1/chart", NOW)
    assert st.hit(oa, "/v1/chart", NOW)["allowed"] is False
    assert st.hit(ob, "/v1/chart", NOW)["allowed"] is True


def test_concurrent_hits_are_counted_exactly():
    st, org, key, _ = make(limit=1000)
    o = st.authenticate(key)
    ts = [threading.Thread(target=lambda: [st.hit(o, "/v1/chart", NOW) for _ in range(25)]) for _ in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sum(r["count"] for r in st.usage(org["id"], 1, NOW)) == 200


def test_guard_modes():
    st, org, key, _ = make(limit=2)
    g = lambda headers, path="/v1/chart", mode="required": access.guard(headers, path, st, mode, NOW)
    assert g({}, mode="off")[0] == 200
    assert g({}, "/health")[0] == 200 and g({}, "/")[0] == 200                      # not an API path
    assert g({})[0] == 401 and g({"X-API-Key": "kd_wrong"})[0] == 401
    assert g({}, mode="optional")[0] == 200                                          # anonymous web page
    assert g({"X-API-Key": "kd_wrong"}, mode="optional")[0] == 401                   # a bad key is still an error
    s1, _, h1, o1 = g({"X-API-Key": key})
    assert s1 == 200 and h1["X-RateLimit-Remaining"] == "1" and o1["id"] == org["id"]
    g({"X-API-Key": key})
    s3, body, h3, _ = g({"X-API-Key": key})
    assert s3 == 429 and "Retry-After" in h3 and "limit" in body["detail"]


def test_admin_cli_flow(tmp_path, monkeypatch, capsys):
    import importlib.util, sys
    from pathlib import Path
    monkeypatch.setenv("KUNDALI_DB", str(tmp_path / "a.db"))
    monkeypatch.setattr(access, "_store", None)
    spec = importlib.util.spec_from_file_location("admin", Path(__file__).resolve().parents[1] / "tools" / "admin.py")
    admin = importlib.util.module_from_spec(spec); spec.loader.exec_module(admin)
    run = lambda *a: (monkeypatch.setattr(sys, "argv", ["admin", *a]), admin.main())[1]
    assert run("create-org", "Acme", "--plan", "pro") == 0
    org_id = capsys.readouterr().out.split()[1]
    assert run("create-key", org_id, "--label", "web") == 0
    out = capsys.readouterr().out
    assert "kd_" in out and "shown once" in out
    assert run("create-org", "Bad", "--plan", "gold") == 1
    assert run("list-orgs") == 0 and "Acme" in capsys.readouterr().out
