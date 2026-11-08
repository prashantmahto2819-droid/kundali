import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import devserver
from jyotish import access, ask, compute_chart, handlers

CH = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
BIRTH = {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}


def top(q, **kw):
    return [s["id"] for s in ask.ask(q, **kw)["sources"]]


def test_corpus_has_both_languages_and_no_sources_noise():
    c = ask.corpus()
    assert len(c) > 500 and {p["lang"] for p in c} == {"hi", "en"}
    assert all("review_status" not in p["id"] for p in c)


def test_retrieval_english_and_hindi():
    assert top("What does Saturn in the 10th house mean?")[0] == "rules/saturn_in_10"
    assert top("राहु 7वें भाव में क्या फल देता है")[0] == "rules/rahu_in_7"
    assert top("Jupiter retrograde")[0] == "rules/jupiter_retrograde"
    assert any("kitchen" in i for i in top("vastu kitchen direction"))
    assert top("tarot Tower card")[0].startswith("knowledge/tarot")


def test_chart_questions_use_the_persons_chart():
    assert top("What is my lagna and moon sign?", chart=CH)[0] == "chart/lagna"
    assert top("मेरा लग्न क्या है", chart=CH, lang="hi")[0] == "chart/lagna_hi"
    r = ask.ask("Where is my Saturn?", chart=CH)
    assert r["sources"][0]["id"] == "chart/saturn" and "Makara" in r["answer"]
    assert top("What does Mars in 10th mean for me?", chart=CH)[:2] == ["chart/mars", "chart/reading/mars_in_10"]
    assert "not present" in ask.ask("Is Gajakesari yoga in my chart?", chart=CH)["answer"]


@pytest.mark.parametrize("q,topic", [
    ("When will I die?", "death"), ("how long will I live", "death"), ("मेरी मृत्यु कब होगी", "death"),
    ("Will I get cancer?", "medical"), ("क्या मुझे बीमारी होगी", "medical"), ("which stock should I buy", "money"),
    ("will I win the case in court", "legal") if False else ("is there a lawsuit coming", "legal"),
    ("lottery numbers for me", "money"),
])
def test_guardrails_refuse_and_never_call_the_model(q, topic):
    called = []
    r = ask.ask(q, llm=lambda s, u: called.append(1) or "x")
    assert r["mode"] == "refused" and r["topic"] == topic and r["sources"] == [] and not called


def test_normal_questions_are_not_blocked():
    for q in ("What does the 8th house signify?", "Is my Moon strong?", "शनि की साढ़ेसाती क्या है", "Explain dasha"):
        assert ask.blocked_topic(q) is None


def test_llm_is_grounded_and_fallback_works():
    seen = {}

    def fake(system, user):
        seen["system"], seen["user"] = system, user
        return "Saturn in the 10th tends to bring slow, lasting progress [rules/saturn_in_10]."
    r = ask.ask("Saturn in the 10th house", llm=fake)
    assert r["mode"] == "llm" and "[rules/saturn_in_10]" in r["answer"]
    assert "ONLY the numbered passages" in seen["system"] and "never predict" in seen["system"]
    assert "[rules/saturn_in_10]" in seen["user"] and "Question: Saturn in the 10th house" in seen["user"]

    def broken(system, user):
        raise RuntimeError("network down")
    r2 = ask.ask("Saturn in the 10th house", llm=broken)
    assert r2["mode"] == "extractive" and r2["sources"][0]["id"] == "rules/saturn_in_10"


def test_no_match_and_validation(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ask.ask("zzzz qqqq xxxx")["mode"] == "no_match"
    with pytest.raises(ValueError):
        ask.ask("   ")
    with pytest.raises(ValueError):
        ask.ask("x" * 501)
    assert ask.env_llm() is None


def test_handler_and_http(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDALI_AUTH", "off")
    out = handlers.ask_from_payload({"question": "Where is my Moon?", "chart": BIRTH})
    assert out["sources"][0]["id"].startswith("chart/")
    with pytest.raises(handlers.BadRequest):
        handlers.ask_from_payload({"question": 5})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), devserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/v1/ask",
                                     data=json.dumps({"question": "When will I die?"}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            assert json.loads(r.read())["mode"] == "refused"
    finally:
        srv.shutdown()
