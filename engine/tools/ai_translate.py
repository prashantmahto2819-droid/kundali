"""Translate the web UI dictionary into another language with the configured AI provider → data/i18n_<lang>.json.
The app's English dictionary (data/i18n_en.json, built by build_i18n.py) maps Hindi UI strings → English; this tool asks the
model for <lang> renderings of the same Hindi strings (with the English as a gloss), in batches, keeping {n} placeholders,
and writes the same JSON shape. Run once per language (≈ 3,000 strings ≈ ₹10–30 on OpenAI; free on Ollama/Groq within limits):
    cd engine && OPENAI_API_KEY=... python3 tools/ai_translate.py te        # te kn mr gu bn ta ml or any BCP-47 code
Re-running only translates strings missing from the existing file. Review the result; it is a draft until a speaker checks it."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jyotish import llm  # noqa: E402

NAMES = {"te": "Telugu", "kn": "Kannada", "mr": "Marathi", "gu": "Gujarati", "bn": "Bengali", "ta": "Tamil", "ml": "Malayalam", "pa": "Punjabi", "or": "Odia", "ne": "Nepali", "en": "English"}
lang = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
if not lang:
    sys.exit("usage: ai_translate.py <lang>")
if not llm.available():
    sys.exit("no AI provider configured")
root = Path(__file__).resolve().parents[2] / "data"
src = json.loads((root / "i18n_en.json").read_text("utf-8"))
exact, patterns = src.get("exact", {}), src.get("patterns", [])
out_path = root / f"i18n_{lang}.json"
done = json.loads(out_path.read_text("utf-8")) if out_path.exists() else {"exact": {}, "patterns": []}
todo = [(hi, en) for hi, en in exact.items() if hi not in done["exact"]]
print(f"{len(todo)} strings to translate into {NAMES.get(lang, lang)} ({len(done['exact'])} already done)")
SYSTEM = (f"You translate UI strings of a Hindi astrology app into {NAMES.get(lang, lang)}. Input: JSON array of [hindi, english_gloss]. "
          f"Output: STRICT JSON array of the {NAMES.get(lang, lang)} strings in the same order, same length. Keep placeholders like {{n}}, {{1}}, numbers, "
          "punctuation and emoji unchanged; keep Sanskrit astrology terms in their usual local spelling (not transliterated English). No markdown.")
B = 60
for i in range(0, len(todo), B):
    batch = todo[i:i + B]
    for attempt in range(3):
        try:
            res = llm.complete(SYSTEM, [{"role": "user", "content": json.dumps(batch, ensure_ascii=False)}], max_tokens=4000)
            txt = res["text"]
            m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
            arr = json.loads(m.group(1) if m else txt[txt.find("["): txt.rfind("]") + 1])
            if len(arr) != len(batch):
                raise ValueError(f"length {len(arr)} != {len(batch)}")
            for (hi, _), tr in zip(batch, arr):
                if isinstance(tr, str) and tr.strip():
                    done["exact"][hi] = tr.strip()
            break
        except Exception as exc:
            print("  retry", attempt + 1, str(exc)[:80])
    done["patterns"] = patterns if not done.get("patterns") else done["patterns"]
    out_path.write_text(json.dumps({"lang": lang, "name": NAMES.get(lang, lang), "review_status": "draft", **done}, ensure_ascii=False, indent=0), "utf-8")
    print(f"  {min(i + B, len(todo))}/{len(todo)} → {out_path.name}", flush=True)
print("done:", len(done["exact"]), "strings")
