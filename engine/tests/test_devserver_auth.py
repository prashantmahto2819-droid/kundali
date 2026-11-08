import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import devserver
from jyotish import access

BODY = json.dumps({"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}).encode()


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDALI_DB", str(tmp_path / "t.db"))
    monkeypatch.setattr(access, "_store", None)
    st = access.default_store()
    st.plans["free"] = 2
    org = st.create_org("Acme")
    key, _ = st.create_key(org["id"])
    srv = ThreadingHTTPServer(("127.0.0.1", 0), devserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", key
    srv.shutdown()


def call(url, path, key=None, data=BODY):
    req = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json", **({"X-API-Key": key} if key else {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_required_mode_over_http(server, monkeypatch):
    url, key = server
    monkeypatch.setenv("KUNDALI_AUTH", "required")
    assert call(url, "/v1/chart")[0] == 401
    assert call(url, "/v1/chart", "kd_nope")[0] == 401
    s, h, b = call(url, "/v1/chart", key)
    assert s == 200 and h["X-RateLimit-Remaining"] == "1" and json.loads(b)["lagna"]["sign_name"] == "Vrishabha"
    assert call(url, "/v1/chart", key)[0] == 200
    s, h, b = call(url, "/v1/chart", key)
    assert s == 429 and int(h["Retry-After"]) > 0
    with urllib.request.urlopen(url + "/health") as r:                    # health is never guarded
        assert r.status == 200


def test_optional_and_off_modes_keep_the_public_page_working(server, monkeypatch):
    url, key = server
    monkeypatch.setenv("KUNDALI_AUTH", "optional")
    assert call(url, "/v1/chart")[0] == 200                               # anonymous, like the web page
    monkeypatch.setenv("KUNDALI_AUTH", "off")
    assert call(url, "/v1/chart", "kd_whatever")[0] == 200


def test_people_over_http(server, monkeypatch):
    url, key = server
    monkeypatch.setenv("KUNDALI_AUTH", "off")                 # saved people need a key even so
    payload = json.dumps({"name": "Sita", **json.loads(BODY)}).encode()
    assert call(url, "/v1/people", None, payload)[0] == 401
    s, _, b = call(url, "/v1/people", key, payload)
    pid = json.loads(b)["id"]
    assert s == 201
    req = urllib.request.Request(f"{url}/v1/people/{pid}/chart", headers={"X-API-Key": key})
    with urllib.request.urlopen(req) as r:
        assert json.loads(r.read())["chart"]["lagna"]["sign_name"] == "Vrishabha"
    req = urllib.request.Request(f"{url}/v1/people/{pid}", method="DELETE", headers={"X-API-Key": key})
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
