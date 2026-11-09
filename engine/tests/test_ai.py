"""AI layer: provider chain with a local fake OpenAI-compatible server, quota, retrieval fallback, palm JSON parsing."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from jyotish import access, ai, llm


class _Fake(BaseHTTPRequestHandler):
    calls = []
    fail_first = {"n": 0}
    reply = "सूर्य दसवें भाव में अधिकार की प्रवृत्ति देता है [rules/sun_in_10]।"

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Fake.calls.append((self.path, self.headers.get("Authorization"), body))
        if _Fake.fail_first["n"] > 0:
            _Fake.fail_first["n"] -= 1
            self.send_response(429); self.end_headers(); self.wfile.write(b'{"error":"rate limit"}'); return
        has_image = any(isinstance(m.get("content"), list) for m in body["messages"])
        text = json.dumps({"choices": {"life_length": "long", "head_slope": "straight", "bogus": "x"}, "notes": ["clear life line", "square palm"]}) if has_image else _Fake.reply
        out = {"choices": [{"message": {"role": "assistant", "content": text}}], "model": body["model"]}
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(out).encode())

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def fake_server():
    srv = HTTPServer(("127.0.0.1", 0), _Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture
def env(monkeypatch, fake_server):
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("AI_PROVIDERS", "groq,custom")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("AI_BASE_URL", fake_server + "/v1")
    monkeypatch.setenv("AI_API_KEY", "k-custom")
    monkeypatch.setenv("AI_MODEL", "fake-model")
    monkeypatch.setenv("AI_VISION_MODEL", "fake-vision")
    monkeypatch.setenv("AI_TIMEOUT", "5")
    # point groq at the fake too so both providers are reachable offline
    monkeypatch.setitem(llm.OPENAI_STYLE, "groq", (fake_server + "/v1", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile", "GROQ_VISION_MODEL", ""))
    _Fake.calls.clear()


def test_configured_order_and_models(env):
    provs = llm.configured()
    assert [p["name"] for p in provs] == ["groq", "custom"]
    assert provs[0]["model"] == "llama-3.3-70b-versatile" and provs[1]["model"] == "fake-model" and provs[1]["vision"] and not provs[0]["vision"]


def test_fallback_chain_on_429(env):
    _Fake.fail_first["n"] = 1                      # groq fails once → custom answers
    res = llm.complete("sys", [{"role": "user", "content": "hi"}])
    assert res["provider"] == "custom" and res["tried"][0]["provider"] == "groq" and "429" in res["tried"][0]["error"]
    assert _Fake.calls[0][1] == "Bearer gsk_test" and _Fake.calls[1][1] == "Bearer k-custom"


def test_chat_grounded_with_sources_and_quota(env, tmp_path, monkeypatch):
    store = access.Store(str(tmp_path / "a.db"))
    monkeypatch.setenv("AI_DAILY_QUOTA", "2")
    payload = {"messages": [{"role": "user", "content": "मेरे दसवें भाव में सूर्य है?"}], "birth": {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2}}
    r = ai.chat(payload, store=store, who="u1")
    assert r["mode"] == "ai" and r["provider"] == "groq" and r["lang"] == "hi" and r["disclaimer"]
    sys_prompt = _Fake.calls[-1][2]["messages"][0]["content"]
    assert "PASSAGES" in sys_prompt and "chart/" in sys_prompt and "panchang/today" in sys_prompt and "भविष्यवाणी कभी न करें" in sys_prompt
    assert any(s["id"] == "rules/sun_in_10" for s in r["sources"]) or r["sources"] == []
    ai.chat(payload, store=store, who="u1")
    r3 = ai.chat(payload, store=store, who="u1")           # third call → quota → retrieval answer
    assert r3["mode"] == "quota" and r3["quota"]["limit"] == 2 and "सीमा" in r3["notice"]
    # blocked topic never reaches a model
    n = len(_Fake.calls)
    rb = ai.chat({"messages": [{"role": "user", "content": "मेरी मृत्यु कब होगी?"}]}, store=store, who="u2")
    assert rb["mode"] == "refused" and len(_Fake.calls) == n


def test_chat_without_provider_falls_back(monkeypatch):
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_URL", "AI_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    r = ai.chat({"messages": [{"role": "user", "content": "What does Sun in the 10th house mean?"}]})
    assert r["mode"] == "retrieval" and r["lang"] == "en" and r["answer"]


def test_palm_scan_parses_choices_and_reads(env, tmp_path):
    store = access.Store(str(tmp_path / "b.db"))
    r = ai.palm_scan(b"\xff\xd8fakejpeg", store=store, who="p1")
    assert r["provider"] == "custom" and r["recognised"] == 2 and "bogus" not in r["choices"]
    assert r["reading"]["traits"] and r["notes"] == ["clear life line", "square palm"]
    sent = _Fake.calls[-1][2]
    assert sent["model"] == "fake-vision" and isinstance(sent["messages"][-1]["content"], list) and sent["messages"][-1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
