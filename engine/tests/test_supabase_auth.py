import time

import jwt
import pytest

from jyotish import access, auth_supabase, people

SECRET = "x" * 40
BIRTH = {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}


def token(sub="u1", email="a@b.com", exp=3600, aud="authenticated", secret=SECRET):
    return jwt.encode({"sub": sub, "email": email, "aud": aud, "exp": int(time.time()) + exp}, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)


def test_verify_accepts_good_and_rejects_bad():
    assert auth_supabase.verify(token()) == {"user_id": "u1", "email": "a@b.com"}
    assert auth_supabase.verify(token(exp=-10)) is None
    assert auth_supabase.verify(token(aud="anon")) is None
    assert auth_supabase.verify(token(secret="y" * 40)) is None
    assert auth_supabase.verify("garbage") is None
    none_alg = jwt.encode({"sub": "u1", "aud": "authenticated", "exp": int(time.time()) + 99}, None, algorithm="none")
    assert auth_supabase.verify(none_alg) is None            # unsigned tokens are never accepted


def test_user_gets_own_org_and_isolation():
    s = access.Store()
    h1 = {"Authorization": f"Bearer {token('u1')}"}
    h2 = {"Authorization": f"Bearer {token('u2', 'c@d.com')}"}
    pid = people.api("POST", "/v1/people", h1, {"name": "Ram", **BIRTH}, s)[1]["id"]
    assert people.api("GET", "/v1/people", h1, None, s)[1]["people"][0]["name"] == "Ram"
    assert people.api("GET", f"/v1/people/{pid}", h2, None, s)[0] == 404
    assert len(s.list_orgs()) == 2
    people.api("GET", "/v1/people", h1, None, s)
    assert len(s.list_orgs()) == 2                           # same user, same org
    assert people.api("GET", "/v1/people", {"Authorization": "Bearer nope"}, None, s)[0] == 401


def test_guard_meters_login_and_required_mode():
    s = access.Store(plans={"free": 1})
    h = {"Authorization": f"Bearer {token()}"}
    assert access.guard({}, "/v1/chart", s, "required")[0] == 401
    assert access.guard(h, "/v1/chart", s, "required")[0] == 200
    assert access.guard(h, "/v1/chart", s, "required")[0] == 429
    assert access.guard({"Authorization": "Bearer bad"}, "/v1/chart", s, "optional")[0] == 401
