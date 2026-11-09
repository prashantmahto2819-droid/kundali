"""Model providers for the AI features (chat, palm photo reading), with a fallback chain and per-user daily quota.

Configuration (deploy/.env). Any number of providers, tried in order until one answers:
  AI_PROVIDERS=openai,groq,gemini,openrouter,ollama           # order of preference (default: openai first, then groq); names below
  GEMINI_API_KEY=...        GEMINI_MODEL=gemini-2.0-flash          (free tier)
  GROQ_API_KEY=...          GROQ_MODEL=llama-3.3-70b-versatile     (free tier; vision: llama-3.2-11b-vision-preview)
  OPENROUTER_API_KEY=...    OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free
  DEEPSEEK_API_KEY=...      DEEPSEEK_MODEL=deepseek-chat           (paid, cheap)
  OLLAMA_URL=http://host:11434   OLLAMA_MODEL=qwen2.5:7b   OLLAMA_VISION_MODEL=llama3.2-vision:11b   (self-hosted, free)
  OPENAI_API_KEY=...        OPENAI_MODEL=gpt-4o-mini
  ANTHROPIC_API_KEY=...     ANTHROPIC_MODEL=claude-sonnet-5-5
  AI_BASE_URL / AI_API_KEY / AI_MODEL                                 any other OpenAI-compatible endpoint ("custom")
  AI_DAILY_QUOTA=30          answers per user (phone / login / IP) per day; AI_TIMEOUT=45 seconds
Everything except Gemini and Anthropic speaks the OpenAI chat-completions format, so one client covers Groq, OpenRouter,
DeepSeek, Ollama, OpenAI and custom. Images (palm photos) are sent as data URLs where the provider supports vision.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

OPENAI_STYLE = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile", "GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free", "OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct:free"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "deepseek-chat", "DEEPSEEK_VISION_MODEL", ""),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini", "OPENAI_VISION_MODEL", "gpt-4o-mini"),
    "ollama": ("", "", "OLLAMA_MODEL", "qwen2.5:7b", "OLLAMA_VISION_MODEL", "llama3.2-vision:11b"),
    "custom": ("", "AI_API_KEY", "AI_MODEL", "", "AI_VISION_MODEL", ""),
}


class ProviderError(Exception):
    pass


def configured() -> list[dict]:
    """Providers that have what they need, in AI_PROVIDERS order (default order: free tiers first)."""
    order = [x.strip().lower() for x in os.environ.get("AI_PROVIDERS", "openai,groq,gemini,openrouter,deepseek,anthropic,ollama,custom").split(",") if x.strip()]
    out = []
    for name in order:
        if name == "gemini" and os.environ.get("GEMINI_API_KEY"):
            out.append({"name": name, "model": os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"), "vision": True})
        elif name == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            out.append({"name": name, "model": os.environ.get("ANTHROPIC_MODEL", os.environ.get("KUNDALI_LLM_MODEL", "claude-sonnet-5-5")), "vision": True})
        elif name in OPENAI_STYLE:
            base, key_env, model_env, model_default, vis_env, vis_default = OPENAI_STYLE[name]
            if name == "ollama":
                base = os.environ.get("OLLAMA_URL", "").rstrip("/")
                if not base:
                    continue
                base += "/v1"
                key = "ollama"
            elif name == "custom":
                base = os.environ.get("AI_BASE_URL", "").rstrip("/")
                key = os.environ.get("AI_API_KEY", "")
                if not base:
                    continue
            else:
                key = os.environ.get(key_env, "")
                if not key:
                    continue
            vision_model = os.environ.get(vis_env, vis_default)
            out.append({"name": name, "base": base, "key": key, "model": os.environ.get(model_env, model_default), "vision_model": vision_model, "vision": bool(vision_model)})
    return out


def available() -> bool:
    return bool(configured())


def _post(url: str, body: dict, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        raise ProviderError(f"HTTP {exc.code} {detail}") from exc
    except Exception as exc:
        raise ProviderError(f"{type(exc).__name__}: {exc}") from exc


def _openai_chat(p: dict, system: str, messages: list[dict], image: bytes | None, mime: str, max_tokens: int, timeout: float) -> str:
    msgs = [{"role": "system", "content": system}]
    for m in messages:
        msgs.append({"role": m["role"], "content": m["content"]})
    if image is not None:
        data_url = f"data:{mime};base64," + base64.b64encode(image).decode()
        msgs[-1] = {"role": "user", "content": [{"type": "text", "text": messages[-1]["content"]}, {"type": "image_url", "image_url": {"url": data_url}}]}
    model = p["vision_model"] if image is not None else p["model"]
    headers = {"Authorization": f"Bearer {p['key']}"}
    if p["name"] == "openrouter":
        headers["HTTP-Referer"] = os.environ.get("KUNDALI_SITE_URL", "https://kundali.vividbrandify.com"); headers["X-Title"] = "Kundali"
    data = _post(f"{p['base']}/chat/completions", {"model": model, "messages": msgs, "max_tokens": max_tokens, "temperature": 0.4}, headers, timeout)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        raise ProviderError(f"unexpected response: {json.dumps(data)[:200]}") from exc


def _gemini_chat(p: dict, system: str, messages: list[dict], image: bytes | None, mime: str, max_tokens: int, timeout: float) -> str:
    key = os.environ["GEMINI_API_KEY"]
    contents = []
    for i, m in enumerate(messages):
        parts = [{"text": m["content"]}]
        if image is not None and i == len(messages) - 1:
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(image).decode()}})
        contents.append({"role": "user" if m["role"] == "user" else "model", "parts": parts})
    body = {"system_instruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4}}
    data = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{p['model']}:generateContent?key={key}", body, {}, timeout)
    try:
        return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"]).strip()
    except (KeyError, IndexError) as exc:
        raise ProviderError(f"unexpected response: {json.dumps(data)[:200]}") from exc


def _anthropic_chat(p: dict, system: str, messages: list[dict], image: bytes | None, mime: str, max_tokens: int, timeout: float) -> str:
    key = os.environ["ANTHROPIC_API_KEY"]
    msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
    if image is not None:
        msgs[-1] = {"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(image).decode()}}, {"type": "text", "text": messages[-1]["content"]}]}
    data = _post("https://api.anthropic.com/v1/messages", {"model": p["model"], "max_tokens": max_tokens, "system": system, "messages": msgs},
                 {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout)
    try:
        return "".join(b.get("text", "") for b in data["content"]).strip()
    except (KeyError, TypeError) as exc:
        raise ProviderError(f"unexpected response: {json.dumps(data)[:200]}") from exc


def complete(system: str, messages: list[dict], image: bytes | None = None, mime: str = "image/jpeg", max_tokens: int = 700) -> dict:
    """Try each configured provider in order; returns {text, provider, model, tried:[...]}; raises ProviderError when all fail."""
    timeout = float(os.environ.get("AI_TIMEOUT", "45"))
    tried = []
    for p in configured():
        if image is not None and not p.get("vision"):
            continue
        t0 = time.time()
        try:
            if p["name"] == "gemini":
                text = _gemini_chat(p, system, messages, image, mime, max_tokens, timeout)
            elif p["name"] == "anthropic":
                text = _anthropic_chat(p, system, messages, image, mime, max_tokens, timeout)
            else:
                text = _openai_chat(p, system, messages, image, mime, max_tokens, timeout)
            if not text:
                raise ProviderError("empty answer")
            return {"text": text, "provider": p["name"], "model": p.get("vision_model") if image is not None else p["model"], "seconds": round(time.time() - t0, 1), "tried": tried}
        except ProviderError as exc:
            tried.append({"provider": p["name"], "error": str(exc)[:160]})
    raise ProviderError("no provider answered: " + "; ".join(f"{t['provider']}: {t['error']}" for t in tried) if tried else "no AI provider configured")


# ---------------------------------------------------------------- quota
def quota_check(store, who: str, cost: int = 1) -> dict:
    """Per-user daily quota kept in the access store (table ai_usage). Returns {ok, used, limit}."""
    limit = int(os.environ.get("AI_DAILY_QUOTA", "30"))
    day = datetime.now(timezone.utc).date().isoformat()
    with store._lock:
        store._db.execute("CREATE TABLE IF NOT EXISTS ai_usage(who TEXT, day TEXT, used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(who, day))")
        row = store._db.execute("SELECT used FROM ai_usage WHERE who=? AND day=?", (who, day)).fetchone()
        used = row[0] if row else 0
        if used + cost > limit:
            return {"ok": False, "used": used, "limit": limit}
        store._db.execute("INSERT INTO ai_usage(who, day, used) VALUES (?,?,?) ON CONFLICT(who, day) DO UPDATE SET used=used+excluded.used", (who, day, cost))
        store._db.commit()
    return {"ok": True, "used": used + cost, "limit": limit}


# ---------------------------------------------------------------- embeddings (semantic search)
EMBED_MODELS = {"openai": "text-embedding-3-small", "ollama": "nomic-embed-text", "gemini": "text-embedding-004", "custom": ""}


def embed_provider() -> dict | None:
    """First configured provider that offers embeddings (EMBED_PROVIDER forces one). OpenAI-style: /embeddings; Gemini: embedContent."""
    want = os.environ.get("EMBED_PROVIDER", "").lower()
    for p in configured():
        if want and p["name"] != want:
            continue
        if p["name"] in ("openai", "ollama", "gemini") or (p["name"] == "custom" and os.environ.get("AI_EMBED_MODEL")):
            model = os.environ.get("EMBED_MODEL") or os.environ.get("AI_EMBED_MODEL") or EMBED_MODELS.get(p["name"], "")
            return {**p, "embed_model": model}
    return None


def embed(texts: list[str]) -> list[list[float]]:
    p = embed_provider()
    if p is None:
        raise ProviderError("no embedding provider configured")
    timeout = float(os.environ.get("AI_TIMEOUT", "45"))
    if p["name"] == "gemini":
        key = os.environ["GEMINI_API_KEY"]
        out = []
        for t in texts:
            data = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{p['embed_model']}:embedContent?key={key}",
                         {"model": f"models/{p['embed_model']}", "content": {"parts": [{"text": t[:6000]}]}}, {}, timeout)
            out.append(data["embedding"]["values"])
        return out
    out = []
    for i in range(0, len(texts), 64):
        chunk = [t[:6000] for t in texts[i:i + 64]]
        data = _post(f"{p['base']}/embeddings", {"model": p["embed_model"], "input": chunk}, {"Authorization": f"Bearer {p['key']}"}, timeout)
        rows = sorted(data["data"], key=lambda r: r.get("index", 0))
        out += [r["embedding"] for r in rows]
    return out


def cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)
