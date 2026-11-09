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


# ---------------------------------------------------------------- more AI tools (all optional, all grounded in app data)
def _facts_for_chart(chart: dict, lang: str) -> str:
    hi = lang == "hi"
    L = []
    lg = chart["lagna"]
    L.append((f"लग्न {lg['sign_name_hi']} ({lg['nakshatra_hi']})" if hi else f"Lagna {lg['sign_name']} ({lg['nakshatra']})"))
    for p in chart["planets"]:
        L.append((f"{p['name_hi']} {p['sign_name_hi']} भाव {p['house']} {p['nakshatra_hi']}{' वक्री' if p['retrograde'] else ''}{' ' + p['dignity'] if p.get('dignity') else ''}" if hi else
                  f"{p['name']} in {p['sign_name']} house {p['house']} {p['nakshatra']}{' retro' if p['retrograde'] else ''}{' ' + p['dignity'] if p.get('dignity') else ''}"))
    run = chart.get("dasha_running") or []
    if run:
        L.append(("चल रही दशा: " if hi else "Running dasha: ") + " / ".join(f"{r['lord']} ({r['end'][:10]} तक)" if hi else f"{r['lord']} (until {r['end'][:10]})" for r in run[:2]))
    yp = [y for y in chart.get("yogas", []) if y.get("present")][:8]
    if yp:
        L.append(("योग: " if hi else "Yogas: ") + ", ".join(y["name_hi"] if hi else y["name"] for y in yp))
    d = chart.get("doshas") or {}
    for k in ("mangal", "kaal_sarp", "pitru"):
        if d.get(k):
            L.append(d[k]["text_hi"] if hi else d[k]["text_en"])
    ss = (chart.get("gochara") or {}).get("sade_sati") or {}
    if ss.get("active"):
        L.append(("साढ़ेसाती चल रही (" + ss.get("phase", "") + ")") if hi else ("Sade Sati running (" + ss.get("phase", "") + ")"))
    for ev in (chart.get("alerts") or {}).get("today", [])[:3]:
        L.append(("आज: " if hi else "Today: ") + (ev["hi"] if hi else ev["en"]))
    return "\n".join("- " + x for x in L)


def summary(payload: dict, store=None, who: str = "anon") -> dict:
    """Short plain-language summary of a chart / match / varshaphal from the app's computed facts (no new claims)."""
    lang = payload.get("lang") if payload.get("lang") in ("hi", "en") else "hi"
    kind = str(payload.get("kind") or "chart")
    from .handlers import chart_from_payload, match_from_payload, varshaphal_from_payload
    if kind == "match":
        m = match_from_payload(payload["body"])
        facts = (f"अष्टकूट {m['total']}/36 ({m['band_hi']}) — " if lang == "hi" else f"Ashtakoota {m['total']}/36 ({m['band_en']}) — ") + "; ".join(f"{k['name_hi' if lang == 'hi' else 'name']} {k['score']}/{k['max']}" for k in m["kootas"]) + "\n" + \
                "\n".join("- " + (d.get("text_hi") if lang == "hi" else d.get("text_en", "")) for d in (m.get("doshas") or []) if isinstance(d, dict))[:1500] + \
                ("\n- " + (m["parihara_note_hi"] if lang == "hi" else m["parihara_note_en"]) if m.get("parihara") else "") + \
                ("\n- " + str(m["manglik"].get("text_hi" if lang == "hi" else "text_en", "")) if isinstance(m.get("manglik"), dict) else "")
        title_hi, title_en = "मिलान का सार", "Matching summary"
    elif kind == "varshaphal":
        v = varshaphal_from_payload(payload["body"])
        t = v.get("tajika") or {}
        yg = t.get("yogas") or {}
        formed = [h for h in yg.get("by_house", []) if h.get("yogas")]
        facts = (f"वर्ष {v['year']} (आयु {v['age']}): वर्ष-लग्न {v['lagna']['sign_name_hi']}, मुंथा {v['muntha']['sign_hi']} राशि भाव {v['muntha']['house']}, वर्षेश {t.get('varshesha_hi', '')}" if lang == "hi" else
                 f"Year {v['year']} (age {v['age']}): year lagna {v['lagna']['sign_name']}, Muntha in {v['muntha']['sign_hi']} house {v['muntha']['house']}, Varshesha {t.get('varshesha', '')}") + "\n" + \
                "\n".join("- " + (h["text_hi"] if lang == "hi" else h["text_en"]) for h in formed[:6]) + \
                ("\n- " + (t.get("varshesha_why_hi") if lang == "hi" else t.get("varshesha_why_en") or "") if t.get("varshesha_why_hi") else "")
        title_hi, title_en = "वर्षफल का सार", "Varshaphal summary"
    else:
        ch = payload.get("chart") if isinstance(payload.get("chart"), dict) else chart_from_payload(payload["body"])
        facts = _facts_for_chart(ch, lang)
        title_hi, title_en = "कुंडली का सार", "Chart summary"
    if not llm.available():
        return {"summary": None, "mode": "unavailable", "facts": facts, "title": title_hi if lang == "hi" else title_en}
    if store is not None:
        q = llm.quota_check(store, who)
        if not q["ok"]:
            return {"summary": None, "mode": "quota", "facts": facts, "quota": q}
    system = (("आप ज्योतिष ऐप के लिए सरल हिंदी में सार लिखते हैं। केवल दिए गए तथ्यों को 6–9 छोटी पंक्तियों में, आम पाठक की भाषा में समझाइए; कोई नया दावा, कोई भविष्यवाणी, कोई डर नहीं; "
               "'प्रवृत्ति', 'परंपरा में' जैसी भाषा; अंत में एक पंक्ति: 'यह परंपरागत मार्गदर्शन है, भविष्यवाणी नहीं।' बुलेट चिह्न • प्रयोग करें।") if lang == "hi" else
              ("You write plain-English summaries for an astrology app. Explain ONLY the given facts in 6–9 short lines for a lay reader; no new claims, no predictions, no fear; "
               "use 'tends to' / 'traditionally'; end with: 'Traditional guidance, not a prediction.' Use • bullets."))
    try:
        res = llm.complete(system, [{"role": "user", "content": facts}], max_tokens=500)
    except llm.ProviderError as exc:
        return {"summary": None, "mode": "error", "error": str(exc)[:200], "facts": facts}
    return {"summary": res["text"], "mode": "ai", "provider": res["provider"], "model": res["model"], "facts": facts, "title": title_hi if lang == "hi" else title_en, "disclaimer": DISCLAIMER[lang]}


def calendar_text(payload: dict, store=None, who: str = "anon") -> dict:
    """Monthly greeting lines / taglines / festival blurbs for the calendar studio."""
    lang = payload.get("lang") if payload.get("lang") in ("hi", "en") else "hi"
    business = str(payload.get("business") or "")[:120]
    tone = str(payload.get("tone") or ("भक्तिपूर्ण, सरल" if lang == "hi" else "devotional, simple"))[:80]
    months = payload.get("months") or list(range(1, 13))
    fests = payload.get("festivals") or {}
    if not llm.available():
        raise ValueError("no AI provider configured")
    if store is not None and not llm.quota_check(store, who, cost=2)["ok"]:
        raise ValueError("daily AI quota used up")
    system = ("आप कैलेंडर-डिज़ाइन के लिए छोटे, सुंदर हिंदी वाक्य लिखते हैं। STRICT JSON दीजिए: {\"tagline\": \"…\", \"months\": {\"1\": {\"line\": \"…\", \"note\": \"…\"}, …}} — "
              "हर माह के लिए 'line' (एक पंक्ति शुभ-संदेश/सूक्ति, ≤ 12 शब्द) और 'note' (उस माह के मुख्य पर्व पर 1 वाक्य)। कोई markdown नहीं।" if lang == "hi" else
              "You write short, elegant English lines for a printed calendar. Return STRICT JSON: {\"tagline\": \"…\", \"months\": {\"1\": {\"line\": \"…\", \"note\": \"…\"}, …}} — "
              "per month a 'line' (one-line greeting/aphorism, ≤ 12 words) and a 'note' (one sentence on that month's main festival). No markdown.")
    user = (f"व्यवसाय: {business or 'सामान्य'}; स्वर: {tone}; माह: {', '.join(map(str, months))}; पर्व: " if lang == "hi" else f"Business: {business or 'general'}; tone: {tone}; months: {', '.join(map(str, months))}; festivals: ") + json.dumps(fests, ensure_ascii=False)[:2500]
    res = llm.complete(system, [{"role": "user", "content": user}], max_tokens=1200)
    m = _FENCE.search(res["text"])
    raw = m.group(1) if m else res["text"][res["text"].find("{"): res["text"].rfind("}") + 1]
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("the model did not return readable JSON; try again")
    return {"tagline": str(data.get("tagline") or "")[:160], "months": {str(k): {"line": str(v.get("line", ""))[:160], "note": str(v.get("note", ""))[:300]} for k, v in (data.get("months") or {}).items() if isinstance(v, dict)},
            "provider": res["provider"], "model": res["model"]}


def quiz(payload: dict, store=None, who: str = "anon") -> dict:
    """Five multiple-choice questions on a topic, grounded in the glossary/rules passages for that topic."""
    lang = payload.get("lang") if payload.get("lang") in ("hi", "en") else "hi"
    topic = str(payload.get("topic") or "").strip()[:120]
    if len(topic) < 2:
        raise ValueError("topic required")
    if not llm.available():
        raise ValueError("no AI provider configured")
    if store is not None and not llm.quota_check(store, who)["ok"]:
        raise ValueError("daily AI quota used up")
    passages = [p for p in ask_mod.corpus() if p["lang"] == lang]
    hits = ask_mod.rank(topic, passages, 10, boost={"glossary": 1.5})
    ctx = "\n".join(f"[{h['id']}] {h['text']}" for h in hits)
    system = ("आप ज्योतिष-शिक्षण ऐप के लिए प्रश्नोत्तरी बनाते हैं। केवल दिए गए अंशों से 5 बहुविकल्पीय प्रश्न बनाइए। STRICT JSON: {\"questions\": [{\"q\": \"…\", \"options\": [\"…\",\"…\",\"…\",\"…\"], \"answer\": 0, \"why\": \"…\", \"source\": \"id\"}]}। कोई markdown नहीं।" if lang == "hi" else
              "You make quizzes for an astrology-learning app. From the passages only, write 5 multiple-choice questions. STRICT JSON: {\"questions\": [{\"q\": \"…\", \"options\": [\"…\",\"…\",\"…\",\"…\"], \"answer\": 0, \"why\": \"…\", \"source\": \"id\"}]}. No markdown.")
    res = llm.complete(system + "\n\nPASSAGES:\n" + ctx, [{"role": "user", "content": topic}], max_tokens=1200)
    m = _FENCE.search(res["text"])
    raw = m.group(1) if m else res["text"][res["text"].find("{"): res["text"].rfind("}") + 1]
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("the model did not return readable JSON; try again")
    qs = []
    for q in (data.get("questions") or [])[:5]:
        opts = [str(o)[:160] for o in (q.get("options") or [])][:4]
        if len(opts) == 4 and isinstance(q.get("answer"), int) and 0 <= q["answer"] < 4:
            qs.append({"q": str(q.get("q", ""))[:300], "options": opts, "answer": q["answer"], "why": str(q.get("why", ""))[:300], "source": str(q.get("source", ""))[:60]})
    if not qs:
        raise ValueError("no usable questions returned")
    return {"topic": topic, "questions": qs, "provider": res["provider"], "model": res["model"], "sources": [{"id": h["id"], "text": h["text"]} for h in hits[:5]]}


def consult_draft(request: dict, store=None, who: str = "anon") -> dict:
    """First draft of an answer for the astrologer, from the seeker's question and chart facts; the astrologer edits before sending."""
    lang = request.get("lang") if request.get("lang") in ("hi", "en") else "hi"
    if not llm.available():
        raise ValueError("no AI provider configured")
    if store is not None and not llm.quota_check(store, who)["ok"]:
        raise ValueError("daily AI quota used up")
    facts = ""
    if request.get("birth"):
        from .handlers import chart_from_payload
        try:
            facts = _facts_for_chart(chart_from_payload(request["birth"]), lang)
        except Exception:
            facts = ""
    question = next((m["text"] for m in request.get("messages", []) if m["sender"] == "seeker"), "")
    system = ("आप एक अनुभवी ज्योतिषी के सहायक हैं। सीकर के प्रश्न और कुंडली-तथ्यों से उत्तर का पहला मसौदा लिखिए (120–180 शब्द, सम्मानजनक, प्रवृत्ति-भाषा, कोई तारीख़-विशेष भविष्यवाणी नहीं, "
              "उपाय हों तो परंपरागत और वैकल्पिक)। ज्योतिषी इसे सुधारकर भेजेंगे।" if lang == "hi" else
              "You assist an experienced astrologer. Draft a first reply from the seeker's question and chart facts (120–180 words, respectful, tendency language, no date-specific predictions, remedies only as traditional options). The astrologer will edit it.")
    res = llm.complete(system, [{"role": "user", "content": ("प्रश्न: " if lang == "hi" else "Question: ") + question + "\n\n" + facts}], max_tokens=500)
    return {"draft": res["text"], "provider": res["provider"], "model": res["model"], "facts": facts}


def extract_rules(text: str, source: str, lang: str = "hi") -> dict:
    """Admin tool: turn a passage of a classical/commentary text into draft rules in the app's rules JSON shape (reviewed before use)."""
    if not llm.available():
        raise ValueError("no AI provider configured")
    text = (text or "").strip()
    if len(text) < 50 or len(text) > 12000:
        raise ValueError("text must be 50–12000 characters")
    system = ("आप ज्योतिष ग्रंथ के पाठ से नियम निकालते हैं। STRICT JSON दीजिए: {\"rules\": [{\"id\": \"snake_case\", \"planet\": \"Sun|Moon|…|null\", \"house\": 1-12|null, \"sign\": 0-11|null, "
              "\"condition\": \"…\", \"text_hi\": \"प्रवृत्ति-भाषा में फल\", \"text_en\": \"…\", \"source\": \"…\", \"confidence\": \"high|medium|low\"}]}। केवल पाठ में जो है; कोई markdown नहीं।")
    res = llm.complete(system, [{"role": "user", "content": f"स्रोत: {source}\n\n{text}"}], max_tokens=1800)
    m = _FENCE.search(res["text"])
    raw = m.group(1) if m else res["text"][res["text"].find("{"): res["text"].rfind("}") + 1]
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("the model did not return readable JSON")
    rules = [r for r in (data.get("rules") or []) if isinstance(r, dict) and r.get("id") and r.get("text_hi")]
    for r in rules:
        r["review_status"] = "draft"; r["source"] = r.get("source") or source
    return {"rules": rules, "count": len(rules), "provider": res["provider"], "model": res["model"]}
