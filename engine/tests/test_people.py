import pytest

from jyotish import access, handlers, people

BIRTH = {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}


@pytest.fixture
def st():
    s = access.Store()
    a, b = s.create_org("A"), s.create_org("B")
    ka, _ = s.create_key(a["id"])
    kb, _ = s.create_key(b["id"])
    return s, {"X-API-Key": ka}, {"X-API-Key": kb}


def test_save_list_get_chart_delete(st):
    s, ha, _ = st
    code, p = people.api("POST", "/v1/people", ha, {"name": "Ram", "place": "Jabalpur", **BIRTH}, s)
    assert code == 201 and p["id"].startswith("p_") and p["birth"]["date"] == "1990-05-17"
    assert people.api("GET", "/v1/people", ha, None, s)[1]["people"][0]["name"] == "Ram"
    code, body = people.api("GET", f"/v1/people/{p['id']}/chart", ha, None, s)
    assert code == 200 and body["chart"]["lagna"]["sign_name"] == "Vrishabha"
    assert people.api("DELETE", f"/v1/people/{p['id']}", ha, None, s)[0] == 200
    assert people.api("GET", f"/v1/people/{p['id']}", ha, None, s)[0] == 404


def test_orgs_are_isolated(st):
    s, ha, hb = st
    pid = people.api("POST", "/v1/people", ha, {"name": "Ram", **BIRTH}, s)[1]["id"]
    assert people.api("GET", f"/v1/people/{pid}", hb, None, s)[0] == 404
    assert people.api("GET", f"/v1/people/{pid}/chart", hb, None, s)[0] == 404
    assert people.api("DELETE", f"/v1/people/{pid}", hb, None, s)[0] == 404
    assert people.api("GET", "/v1/people", hb, None, s)[1]["people"] == []
    assert people.api("GET", f"/v1/people/{pid}", ha, None, s)[0] == 200   # still there


def test_validation_and_auth(st):
    s, ha, _ = st
    assert people.api("POST", "/v1/people", {}, {"name": "x", **BIRTH}, s)[0] == 401
    assert people.api("GET", "/v1/people", {"X-API-Key": "kd_bad"}, None, s)[0] == 401
    assert people.api("POST", "/v1/people", ha, {"name": "", **BIRTH}, s)[0] == 422
    assert people.api("POST", "/v1/people", ha, {"name": "x", **{**BIRTH, "lat": 999}}, s)[0] == 422
    assert people.api("GET", "/v1/people/../../etc", ha, None, s)[0] == 404


def test_cap(st, monkeypatch):
    s, ha, _ = st
    monkeypatch.setattr(people, "MAX_PEOPLE", 2)
    for i in range(2):
        assert people.api("POST", "/v1/people", ha, {"name": f"n{i}", **BIRTH}, s)[0] == 201
    assert people.api("POST", "/v1/people", ha, {"name": "n3", **BIRTH}, s)[0] == 422
