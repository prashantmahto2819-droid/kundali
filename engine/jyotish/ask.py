"""Question answering over the app's OWN content (retrieval first, language model optional).

    ask(question, lang="hi", chart=None, llm=None) -> {answer, sources, mode, ...}

Design
* Retrieval: BM25 over passages harvested from data/knowledge/*.json, data/rules/*.json and data/lalkitab.json,
  plus facts and readings of the person's chart when one is given (these are boosted).
* mode "extractive": no model needed; the answer is the best passages, each with its source id.
* mode "llm": if a callable `llm(system, user) -> str` is supplied (or ANTHROPIC_API_KEY is set, see `env_llm`),
  the model must answer ONLY from the retrieved passages and cite their ids.
* Guardrails run before anything else: questions that ask for death, lifespan, illness, pregnancy or lottery
  predictions, or for medical/legal/financial decisions, get a fixed safe reply and the model is never called.
Everything returned is DRAFT guidance in tendency language, never a prediction.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
_TOKEN = re.compile(r"[A-Za-z0-9ऀ-ॿ]+")
_DEV = re.compile(r"[ऀ-ॿ]")
STOP = {"the", "a", "an", "of", "in", "is", "are", "and", "or", "to", "what", "does", "do", "my", "me", "how", "why",
        "for", "on", "with", "it", "this", "that", "be", "at", "as", "से", "में", "का", "की", "के", "है", "हैं", "और",
        "क्या", "कि", "को", "पर", "यह", "वह", "मेरा", "मेरी", "मेरे", "कौन", "कैसे", "क्यों"}

BLOCK = [  # (pattern, topic)
    (r"\b(when|how long|age)\b.*\b(die|death|dead)\b|\b(will|am)\s+i\s+die\b|\blife\s?span\b|\bhow long (will|do) i live\b", "death"),
    (r"मृत्यु|मौत|कब मरूँ|कब मरूंगा|आयु कितनी|कितना जीऊँ|कितने साल जी", "death"),
    (r"\b(cancer|disease|illness|diagnos|cure|medicine|medication|surgery|pregnan|miscarriage)\b", "medical"),
    (r"कैंसर|बीमारी|रोग|इलाज|दवा|ऑपरेशन|गर्भ|प्रेग्नेंसी", "medical"),
    (r"\b(lottery|jackpot|gambl|betting|stock tip|which stock|crypto to buy)\b", "money"),
    (r"लॉटरी|जुआ|सट्टा|शेयर खरीद", "money"),
    (r"\b(lawsuit|court case|will i win the case|divorce case|legal advice)\b", "legal"),
    (r"मुक़दमा|मुकदमा|कोर्ट केस|तलाक का केस", "legal"),
]
SAFE = {
    "hi": "इस विषय पर मैं भविष्यवाणी नहीं कर सकता। ज्योतिष परंपरागत मार्गदर्शन है, स्वास्थ्य, आयु, धन या क़ानूनी फ़ैसलों का आधार नहीं। "
          "कृपया इसके लिए डॉक्टर, वित्तीय सलाहकार या वकील जैसे विशेषज्ञ से मिलिए। चाहें तो मैं कुंडली के स्वभाव, दशा या भाव के बारे में समझा सकता हूँ।",
    "en": "I can't make predictions on this. Astrology is traditional guidance, not a basis for decisions about health, lifespan, money or the law. "
          "Please consult a doctor, financial adviser or lawyer as appropriate. I can explain the chart's temperament, dasha or houses if you like.",
}
DISCLAIMER = {"hi": "यह परंपरागत मार्गदर्शन (ड्राफ़्ट) है, भविष्यवाणी या पेशेवर सलाह नहीं।",
              "en": "This is traditional guidance (draft), not a prediction or professional advice."}


_ORD = re.compile(r"(\d+)(?:st|nd|rd|th|वाँ|वें|वीं|वा)(?![A-Za-z0-9\u0900-\u097f])", re.I)


def tokens(text: str) -> list[str]:
    text = _ORD.sub(r"\1 ", text)                      # '10th', '10वें' -> '10'
    return [t for t in (w.lower() for w in _TOKEN.findall(text)) if t not in STOP and (len(t) > 1 or t.isdigit())]


def lang_of(text: str) -> str:
    return "hi" if _DEV.search(text) else "en"


def blocked_topic(question: str) -> str | None:
    q = question.lower()
    for pat, topic in BLOCK:
        if re.search(pat, q):
            return topic
    return None


# ---- corpus ---------------------------------------------------------------------------
def _walk(obj, label, src, out):
    if isinstance(obj, dict):
        name = next((obj[k] for k in ("name_en", "name", "en", "hi", "name_hi") if isinstance(obj.get(k), str)), label)
        for k, v in obj.items():
            if k in ("source", "review_status", "when", "minors", "hi_t", "en_t") or k.startswith("_"):   # minors / templates: added below
                continue
            _walk(v, name if isinstance(name, str) else label, f"{src}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk(v, label, f"{src}[{i}]", out)
    elif isinstance(obj, str) and len(obj) >= 25 and not obj.startswith("http"):
        out.append({"id": src, "text": f"{label}: {obj}" if label and label not in obj else obj, "lang": lang_of(obj)})


@lru_cache(maxsize=1)
def corpus() -> tuple[dict, ...]:
    out: list[dict] = []
    for f in sorted((DATA / "knowledge").glob("*.json")):
        if f.stem in ("numbers", "glossary"):
            continue                                        # labelled below so "Moolank 5" is findable; glossary gets its own prefix
        _walk(json.loads(f.read_text(encoding="utf-8")), "", f"knowledge/{f.stem}", out)
    for num, d in json.loads((DATA / "knowledge" / "numbers.json").read_text(encoding="utf-8"))["numbers"].items():
        out.append({"id": f"numbers/{num}", "lang": "en",
                    "text": f"Number {num} (Moolank / Bhagyank / root number {num}, ruling planet {d['planet']}): {d['traits_en']}"})
        out.append({"id": f"numbers/{num}_hi", "lang": "hi",
                    "text": f"अंक {num} (मूलांक / भाग्यांक {num}, स्वामी ग्रह {d['planet_hi']}): {d['traits_hi']}"})
    from . import tarot as _tarot
    for c in _tarot.deck():
        if c["arcana"] == "minor":
            out.append({"id": f"knowledge/tarot.{c['id']}.up", "lang": "en", "text": f"{c['name']} (upright): {c['upright']}"})
            out.append({"id": f"knowledge/tarot.{c['id']}.rev", "lang": "en", "text": f"{c['name']} (reversed): {c['reversed']}"})
            out.append({"id": f"knowledge/tarot.{c['id']}.up_hi", "lang": "hi", "text": f"{c['name_hi']} (सीधा): {c['upright_hi']}"})
            out.append({"id": f"knowledge/tarot.{c['id']}.rev_hi", "lang": "hi", "text": f"{c['name_hi']} (उलटा): {c['reversed_hi']}"})
    for f in sorted((DATA / "rules").glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")).get("rules", []):
            for lg, key in (("hi", "text_hi"), ("en", "text_en")):
                if r.get(key):
                    out.append({"id": f"rules/{r['id']}", "text": r[key], "lang": lg})
    _walk(json.loads((DATA / "lalkitab.json").read_text(encoding="utf-8")), "Lal Kitab", "lalkitab", out)
    for t in json.loads((DATA / "knowledge" / "glossary.json").read_text(encoding="utf-8"))["terms"]:
        out.append({"id": f"glossary/{t['key']}", "lang": "hi", "text": f"{t['hi']} ({t['en']}): {t['definition_hi']}"})
        out.append({"id": f"glossary/{t['key']}_en", "lang": "en", "text": f"{t['en']} ({t['hi']}): {t['definition_en']}"})
    # palm marks x lines (templated texts), pattern yogas
    pk = json.loads((DATA / "knowledge" / "palm.json").read_text(encoding="utf-8"))
    for mk, m in pk.get("marks", {}).items():
        for lk, ln in pk.get("lines", {}).items():
            out.append({"id": f"palm/mark.{mk}.{lk}", "lang": "hi", "text": m["hi_t"].replace("{line}", ln["hi"])})
            out.append({"id": f"palm/mark.{mk}.{lk}_en", "lang": "en", "text": m["en_t"].replace("{line}", ln["en"])})
    from . import yogas_nabhasa as _yn
    for _pl, (yid, nm, hi, thi, ten) in _yn.MAHAPURUSHA.items():
        out.append({"id": f"yoga/{yid}", "lang": "hi", "text": f"{hi} महापुरुष योग ({_yn.PLANETS_HI[_pl]} स्वराशि/उच्च में केंद्र में): {thi}"})
        out.append({"id": f"yoga/{yid}_en", "lang": "en", "text": f"{nm} Mahapurusha Yoga ({_pl} in own/exalted sign in a kendra): {ten}"})
    for yid, (nm, hi, grp, thi, ten) in _yn.NABHASA_TEXT.items():
        out.append({"id": f"yoga/{yid}", "lang": "hi", "text": f"{hi} नाभस योग: {thi}"}); out.append({"id": f"yoga/{yid}_en", "lang": "en", "text": f"{nm} Nabhasa yoga: {ten}"})
    for yid, (nm, hi, thi, ten) in _yn.CONJ_TEXT.items():
        out.append({"id": f"yoga/{yid}", "lang": "hi", "text": f"{hi} योग: {thi}"}); out.append({"id": f"yoga/{yid}_en", "lang": "en", "text": f"{nm} yoga: {ten}"})
    seen, uniq = set(), []
    for p in out:
        if p["text"] not in seen:
            seen.add(p["text"])
            uniq.append(p)
    return tuple(uniq)


def numerology_passages(birth_date: str, name: str | None = None) -> list[dict]:
    """Moolank / bhagyank / personal year / name number of this person (boosted like chart facts)."""
    from datetime import date
    from . import numerology
    y, m, d = (int(x) for x in birth_date[:10].split("-"))
    r = numerology.analyse(date(y, m, d), name)
    mo, bh, py = r["moolank"], r["bhagyank"], r["personal_year"]
    nums = json.loads((DATA / "knowledge" / "numbers.json").read_text(encoding="utf-8"))["numbers"]
    tr = lambda n, lg: nums.get(str(n), {}).get(f"traits_{lg}", "")
    out = [
        {"id": "chart/moolank", "lang": "en", "text": f"Your Moolank (root number, from the birth day) is {mo['number']}, ruled by {mo['planet']}. {tr(mo['number'], 'en')}"},
        {"id": "chart/moolank_hi", "lang": "hi", "text": f"आपका मूलांक (जन्म-दिन से) {mo['number']} है, स्वामी ग्रह {mo['planet']}। {tr(mo['number'], 'hi')}"},
        {"id": "chart/bhagyank", "lang": "en", "text": f"Your Bhagyank (destiny number, from the full birth date) is {bh['number']}, ruled by {bh['planet']}. {tr(bh['number'], 'en')}"},
        {"id": "chart/bhagyank_hi", "lang": "hi", "text": f"आपका भाग्यांक (पूरी जन्म-तारीख़ से) {bh['number']} है, स्वामी ग्रह {bh['planet']}। {tr(bh['number'], 'hi')}"},
        {"id": "chart/personal_year", "lang": "en", "text": f"Your personal year number for {py['year']} is {py['number']} ({py['planet']})."},
        {"id": "chart/personal_year_hi", "lang": "hi", "text": f"{py['year']} के लिए आपका वैयक्तिक वर्ष अंक {py['number']} ({py['planet']}) है।"},
    ]
    ls = r.get("lo_shu") or {}
    if ls:
        miss, rep = ls.get("missing", []), ls.get("repeated", [])
        out.append({"id": "chart/lo_shu", "lang": "en", "text": "Your Lo Shu grid (numbers of the birth date): missing numbers "
                    + (", ".join(map(str, miss)) or "none") + "; repeated numbers " + (", ".join(map(str, rep)) or "none")
                    + ". A missing number is read as a quality to develop, a repeated one as an emphasised quality."})
        out.append({"id": "chart/lo_shu_hi", "lang": "hi", "text": "आपका लो-शू ग्रिड (जन्म-तारीख़ के अंक): अनुपस्थित अंक "
                    + (", ".join(map(str, miss)) or "कोई नहीं") + "; दोहराए अंक " + (", ".join(map(str, rep)) or "कोई नहीं")
                    + "। अनुपस्थित अंक को विकसित करने योग्य गुण और दोहराए अंक को प्रबल गुण के रूप में पढ़ा जाता है।"})
    if name and r.get("namank"):
        c = r["namank"]["chaldean"]
        out.append({"id": "chart/namank", "lang": "en", "text": f"Your name number (Chaldean) is {c['number']} (compound {c['compound']}), ruled by {c['planet']}."})
        out.append({"id": "chart/namank_hi", "lang": "hi", "text": f"आपका नामांक (कैल्डियन) {c['number']} है (योग {c['compound']}), स्वामी ग्रह {c['planet']}।"})
    return out


def chart_passages(chart: dict) -> list[dict]:
    """Facts and readings of this person's chart (boosted during retrieval)."""
    p = {x["name"]: x for x in chart["planets"]}
    lg, mo = chart["lagna"], p["Moon"]
    out = [
        {"id": "chart/lagna", "lang": "en", "text": f"Your Lagna (ascendant) is {lg['sign_name']} at {lg['dms']} in {lg['nakshatra']} nakshatra; the lord is {lg['lord']}."},
        {"id": "chart/lagna_hi", "lang": "hi", "text": f"आपका लग्न {lg['sign_name_hi']} है ({lg['dms']}, {lg['nakshatra_hi']} नक्षत्र); लग्नेश {lg['lord']} है।"},
        {"id": "chart/moon", "lang": "en", "text": f"Your Moon is in {mo['sign_name']} in {mo['nakshatra']} nakshatra, house {mo['house']}."},
        {"id": "chart/moon_hi", "lang": "hi", "text": f"आपका चंद्र {mo['sign_name_hi']} राशि में, {mo['nakshatra_hi']} नक्षत्र और {mo['house']}वें भाव में है।"},
    ]
    for n, pl in p.items():
        out.append({"id": f"chart/{n.lower()}", "lang": "en", "text": f"Your {n} is in {pl['sign_name']} ({pl['dms']}), house {pl['house']}" + (", retrograde." if pl["retrograde"] else ".")})
        out.append({"id": f"chart/{n.lower()}_hi", "lang": "hi", "text": f"आपका {pl['name_hi']} {pl['sign_name_hi']} राशि ({pl['dms']}) में, {pl['house']}वें भाव में है" + (" और वक्री है।" if pl["retrograde"] else "।")})
    run = chart.get("dasha_running") or {}
    if run:
        md = next((d for d in run if d["level"] == 1), None)
        ad = next((d for d in run if d["level"] == 2), None)
        if md:
            out.append({"id": "chart/dasha", "lang": "en", "text": f"Your running Vimshottari dasha is {md['lord']} mahadasha ({md['start'][:10]} to {md['end'][:10]})"
                        + (f", {ad['lord']} antardasha ({ad['start'][:10]} to {ad['end'][:10]})." if ad else ".")})
            out.append({"id": "chart/dasha_hi", "lang": "hi", "text": f"आपकी चल रही विंशोत्तरी दशा {md['lord']} महादशा है ({md['start'][:10]} से {md['end'][:10]})"
                        + (f", अंतर्दशा {ad['lord']} ({ad['start'][:10]} से {ad['end'][:10]})।" if ad else "।")})
    for y in chart.get("yogas", []):
        out.append({"id": f"chart/yoga_{y['id']}", "lang": "en",
                    "text": f"{y['name']} {'is present' if y['present'] else 'is not present'} in your chart. {y['why']}"})
        out.append({"id": f"chart/yoga_{y['id']}_hi", "lang": "hi",
                    "text": f"{y['name_hi']} आपकी कुंडली में {'बना है' if y['present'] else 'नहीं बना है'}। {y['why_hi']}"})
    for r in chart.get("readings", []):
        for lg2, key in (("hi", "text_hi"), ("en", "text_en")):
            if r.get(key):
                out.append({"id": f"chart/reading/{r['rule_id']}", "text": r[key], "lang": lg2})
    for nb in chart.get("relations", {}).get("neecha_bhanga", []):
        out.append({"id": f"chart/neecha_{nb['planet'].lower()}", "lang": "hi", "text": nb["text_hi"]})
    return out


# ---- BM25 -----------------------------------------------------------------------------
def rank(query: str, passages: list[dict], k: int = 5, boost: dict | None = None) -> list[dict]:
    q = tokens(query)
    if not q or not passages:
        return []
    docs = [Counter(tokens(p["text"])) for p in passages]
    n = len(docs)
    avg = sum(sum(d.values()) for d in docs) / n or 1.0
    df = Counter(t for d in docs for t in set(d))
    scored = []
    for p, d in zip(passages, docs):
        ln = sum(d.values()) or 1
        s = 0.0
        for t in set(q):
            if t in d:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * d[t] * 2.2 / (d[t] + 1.2 * (0.25 + 0.75 * ln / avg))
        if s > 0:
            w = (boost or {}).get(p["id"].split("/")[0], 1.0) * (boost or {}).get("yoga" if p["id"].startswith("chart/yoga_") else "", 1.0)
            scored.append((s * w, p))
    scored.sort(key=lambda x: -x[0])
    return [{**p, "score": round(s, 3)} for s, p in scored[:k]]


# ---- model (optional) -----------------------------------------------------------------
SYSTEM = ("You answer questions about Vedic astrology for an educational app. Use ONLY the numbered passages given. "
          "If they do not contain the answer, say so. Use tendency language ('tends to', 'is traditionally said'); never predict "
          "death, lifespan, illness, pregnancy, lottery or legal outcomes; never give medical, legal or financial advice. "
          "Cite passage ids in square brackets, e.g. [rules/sun_in_10]. Reply in {lang}. Keep it under 150 words.")


def env_llm():
    """A caller for the Anthropic Messages API, or None when ANTHROPIC_API_KEY is not set. (Untested offline.)"""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    import urllib.request

    def call(system: str, user: str) -> str:
        body = json.dumps({"model": os.environ.get("KUNDALI_LLM_MODEL", "claude-sonnet-5-5"), "max_tokens": 600,
                           "system": system, "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return "".join(b.get("text", "") for b in json.loads(r.read())["content"])
    return call


def ask(question: str, lang: str | None = None, chart: dict | None = None, llm=None, k: int = 5) -> dict:
    question = (question or "").strip()
    if not question or len(question) > 500:
        raise ValueError("question must be 1-500 characters")
    lang = lang if lang in ("hi", "en") else lang_of(question)
    topic = blocked_topic(question)
    if topic:
        return {"answer": SAFE[lang], "sources": [], "mode": "refused", "topic": topic, "lang": lang, "disclaimer": DISCLAIMER[lang]}
    passages = [p for p in corpus() if p["lang"] == lang]
    if chart:
        mine = chart_passages(chart)
        if chart.get("input", {}).get("date"):
            mine += numerology_passages(chart["input"]["date"], chart["input"].get("name"))
        passages = [p for p in mine if p["lang"] == lang] + passages
    personal = bool(re.search(r"\b(my|mine|me|i)\b|मेरा|मेरी|मेरे|मुझे|मैं", question.lower()))
    yoga_q = bool(re.search(r"yoga|dosha|dosh|combination|योग|दोष", question.lower()))
    hits = rank(question, passages, k, boost={"chart": 3.0 if personal else 1.6, "yoga": 1.0 if yoga_q else 0.35, "glossary": 0.75})
    if not hits:
        msg = {"hi": "इस प्रश्न का उत्तर मेरी सामग्री में नहीं मिला। कृपया ग्रह, भाव, राशि, नक्षत्र या दशा के बारे में पूछिए।",
               "en": "I could not find this in my material. Please ask about a planet, house, sign, nakshatra or dasha."}[lang]
        return {"answer": msg, "sources": [], "mode": "no_match", "lang": lang, "disclaimer": DISCLAIMER[lang]}
    sources = [{"id": h["id"], "text": h["text"], "score": h["score"]} for h in hits]
    llm = llm if llm is not None else env_llm()
    if llm:
        user = "Passages:\n" + "\n".join(f"[{s['id']}] {s['text']}" for s in sources) + f"\n\nQuestion: {question}"
        try:
            answer = llm(SYSTEM.format(lang="Hindi" if lang == "hi" else "English"), user).strip()
            if answer:
                return {"answer": answer, "sources": sources, "mode": "llm", "lang": lang, "disclaimer": DISCLAIMER[lang]}
        except Exception:                                   # model unavailable: fall back to the passages
            pass
    answer = "\n".join(f"• {s['text']}" for s in sources[:3])
    return {"answer": answer, "sources": sources, "mode": "extractive", "lang": lang, "disclaimer": DISCLAIMER[lang]}
