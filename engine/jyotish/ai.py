"""AI features on top of the model providers (llm.py):

- chat(): multi-turn conversation grounded in the app's own material — the asker's chart passages (ask.chart_passages), the
  rule/glossary corpus ranked for the question (ask.rank), today's panchang — with the same safety topics refused as ask.py.
  Without any configured provider it falls back to the retrieval answer of ask.ask(), so the feature always works.
- palm_scan(): a palm photo → the model fills the app's 16-feature palm checklist as JSON → palm.read() produces the reading
  from our knowledge file (the model only *observes*, the interpretation stays ours), plus the model's observation notes.
Every answer carries a disclaimer; quota is per user per day (llm.quota_check).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from . import ask as ask_mod, llm, palm as palm_mod

CHAT_SYSTEM = {
    "hi": ("आप 'कुंडली' ऐप के ज्योतिष-सहायक हैं। केवल दिए गए अंशों (कुंडली-तथ्य, नियम, शब्दकोश, पंचांग) के आधार पर हिंदी में उत्तर दीजिए; "
           "जो अंशों में नहीं है उसे स्पष्ट कहिए कि सामग्री में नहीं है। प्रवृत्ति की भाषा रखिए ('प्रवृत्ति रहती है', 'परंपरा में माना गया है'); "
           "मृत्यु, आयु, गंभीर रोग, गर्भ, लॉटरी, मुक़दमे के परिणाम की भविष्यवाणी कभी न करें; चिकित्सा, क़ानूनी या वित्तीय सलाह न दें; "
           "डराने वाली भाषा न रखें, उपाय बताएँ तो केवल परंपरागत (दान, मंत्र, व्रत) और 'विकल्प' के रूप में। अंश-संदर्भ कोष्ठक में दें, जैसे [rules/sun_in_10]। "
           "उत्तर 180 शब्दों से कम, सरल हिंदी।"),
    "en": ("You are the astrology assistant of the 'Kundali' app. Answer in English only from the passages given (chart facts, rules, glossary, "
           "panchang); say plainly when something is not in the material. Use tendency language ('tends to', 'is traditionally said'); never predict "
           "death, lifespan, serious illness, pregnancy, lottery or legal outcomes; no medical, legal or financial advice; no fear-mongering; "
           "remedies only as traditional options (charity, mantra, vrat). Cite passage ids in brackets like [rules/sun_in_10]. Under 180 words.")}
PALM_SYSTEM = ("You are observing a photograph of a human palm for a palmistry app. Describe only what is visible; do not interpret. "
               "Return STRICT JSON with two keys: \"choices\" — an object mapping feature keys to exactly one option key from the allowed list, "
               "only for features you can actually see (omit the rest) — and \"notes\" — up to 5 short observations (English). No markdown, no extra text.")
DISCLAIMER = ask_mod.DISCLAIMER
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def _history(messages: list[dict], limit: int = 8) -> list[dict]:
    out = []
    for m in messages[-limit:]:
        role = "user" if m.get("role") == "user" else "assistant"
        text = str(m.get("content") or "").strip()[:1500]
        if text:
            out.append({"role": role, "content": text})
    if not out or out[-1]["role"] != "user":
        raise ValueError("the last message must be from the user")
    return out


def chat(payload: dict, store=None, who: str = "anon") -> dict:
    messages = payload.get("messages") or ([{"role": "user", "content": payload.get("question", "")}] if payload.get("question") else [])
    hist = _history(messages)
    question = hist[-1]["content"]
    if len(question) > 1000:
        raise ValueError("message too long (max 1000 characters)")
    lang = payload.get("lang") if payload.get("lang") in ("hi", "en") else ask_mod.lang_of(question)
    topic = ask_mod.blocked_topic(question)
    if topic:
        return {"answer": ask_mod.SAFE[lang], "mode": "refused", "topic": topic, "lang": lang, "sources": [], "disclaimer": DISCLAIMER[lang]}
    chart = payload.get("chart") if isinstance(payload.get("chart"), dict) else None
    if chart is None and isinstance(payload.get("birth"), dict):
        from .handlers import chart_from_payload
        try:
            chart = chart_from_payload(payload["birth"])
        except Exception:
            chart = None
    # grounding passages
    passages = [p for p in ask_mod.corpus() if p["lang"] == lang]
    mine = []
    if chart:
        mine = [p for p in ask_mod.chart_passages(chart) if p["lang"] == lang]
        if chart.get("input", {}).get("date"):
            mine += [p for p in ask_mod.numerology_passages(chart["input"]["date"], chart["input"].get("name")) if p["lang"] == lang]
    convo = " ".join(m["content"] for m in hist[-3:])
    hits = ask_mod.rank(convo, mine + passages, 8, boost={"chart": 2.5, "yoga": 0.8, "glossary": 0.6})
    ctx = [{"id": h["id"], "text": h["text"]} for h in hits] + [{"id": p["id"], "text": p["text"]} for p in mine[:12] if p["id"] not in {h["id"] for h in hits}]
    try:
        tz = (chart or {}).get("input", {}).get("tz") or payload.get("tz") or "Asia/Kolkata"
        from . import panchang_month
        d = datetime.now(ZoneInfo(tz)).date()
        row = panchang_month.month(d.year, d.month, float(payload.get("lat", 28.61)), float(payload.get("lon", 77.2)), tz, only_day=d.day)["days"][0]
        ctx.append({"id": "panchang/today", "text": (f"आज {row['vara_hi']}, {row['paksha_hi']} {row['tithi_hi']} ({row['tithi_ends'] or '—'} तक), नक्षत्र {row['nakshatra_hi']}, {row['masa_purnimanta_hi']} मास" if lang == "hi" else
                                                     f"Today {row['vara']}, {row['paksha']} {row['tithi']} (until {row['tithi_ends'] or '—'}), nakshatra {row['nakshatra']}, month {row['masa_purnimanta']}")})
    except Exception:
        pass
    if not llm.available():
        base = ask_mod.ask(question, lang=lang, chart=chart)
        return {**base, "mode": "retrieval", "provider": None, "disclaimer": DISCLAIMER[lang]}
    if store is not None:
        q = llm.quota_check(store, who)
        if not q["ok"]:
            base = ask_mod.ask(question, lang=lang, chart=chart)
            return {**base, "mode": "quota", "quota": q, "disclaimer": DISCLAIMER[lang],
                    "notice": ("आज की AI सीमा पूरी हो गई; यह उत्तर ऐप की सामग्री से सीधे दिया गया है।" if lang == "hi" else "Today's AI quota is used up; this answer comes straight from the app's material.")}
    system = CHAT_SYSTEM[lang] + "\n\nPASSAGES:\n" + "\n".join(f"[{c['id']}] {c['text']}" for c in ctx[:24])
    try:
        res = llm.complete(system, hist, max_tokens=600)
    except llm.ProviderError as exc:
        base = ask_mod.ask(question, lang=lang, chart=chart)
        return {**base, "mode": "retrieval", "provider": None, "error": str(exc)[:200], "disclaimer": DISCLAIMER[lang]}
    cited = re.findall(r"\[([a-z0-9_/\.\-:]+)\]", res["text"])
    sources = [c for c in ctx if c["id"] in set(cited)]
    return {"answer": res["text"], "mode": "ai", "provider": res["provider"], "model": res["model"], "seconds": res["seconds"], "lang": lang,
            "sources": sources, "disclaimer": DISCLAIMER[lang]}


def palm_scan(image: bytes, mime: str = "image/jpeg", lang: str = "hi", hand: str = "right", store=None, who: str = "anon") -> dict:
    if not llm.available() or not any(p.get("vision") for p in llm.configured()):
        raise ValueError("no vision-capable AI provider configured")
    if len(image) > 6 * 1024 * 1024:
        raise ValueError("image too large (max 6 MB)")
    if store is not None:
        q = llm.quota_check(store, who, cost=2)
        if not q["ok"]:
            raise ValueError("daily AI quota used up")
    k = palm_mod.knowledge()
    allowed = "\n".join(f"- {f['key']}: {', '.join(f['options'])}  ({f['en']}; {f.get('where', f.get('where_hi', ''))})" for f in k["features"])
    user = (f"This is the {hand} hand. Allowed features and option keys:\n{allowed}\n\nReturn the JSON now.")
    res = llm.complete(PALM_SYSTEM, [{"role": "user", "content": user}], image=image, mime=mime, max_tokens=500)
    text = res["text"]
    m = _FENCE.search(text)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("the model did not return readable JSON; try a clearer, well-lit photo of the whole palm")
    by_key = {f["key"]: f for f in k["features"]}
    choices = {kk: v for kk, v in (data.get("choices") or {}).items() if kk in by_key and v in by_key[kk]["options"]}
    if not choices:
        raise ValueError("no palm features could be recognised; take the photo from straight above with fingers slightly apart")
    reading = palm_mod.read(choices)
    return {"choices": choices, "recognised": len(choices), "of": len(by_key), "notes": [str(n)[:200] for n in (data.get("notes") or [])][:5],
            "reading": reading, "provider": res["provider"], "model": res["model"], "mode": "ai_observed_app_interpreted",
            "note_hi": "AI ने केवल फ़ोटो में दिखने वाले लक्षण पहचाने; अर्थ ऐप की हस्तरेखा-सामग्री से है। फ़ोटो की गुणवत्ता से पहचान बदल सकती है — चुनाव ऊपर जाँचें/बदलें।",
            "note_en": "The model only recognised visible features; the meanings come from the app's palmistry material. Recognition depends on the photo — review the choices."}
