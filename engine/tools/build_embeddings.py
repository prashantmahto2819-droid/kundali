"""Build data/embeddings.json — one vector per corpus passage — with the configured embedding provider (OpenAI
text-embedding-3-small, Ollama nomic-embed-text, or Gemini). Run once after changing the knowledge/rule files:
    cd engine && OPENAI_API_KEY=... python3 tools/build_embeddings.py
About 2,000 passages ≈ 300k tokens ≈ ₹0.5–2 on OpenAI; free on Ollama. The app then ranks "पूछिए"/AI-chat passages semantically."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jyotish import ask, llm  # noqa: E402

p = llm.embed_provider()
if p is None:
    sys.exit("no embedding provider: set OPENAI_API_KEY, OLLAMA_URL or GEMINI_API_KEY")
corpus = list(ask.corpus())
ids = [(c["id"] + ("_en" if c["lang"] == "en" and not c["id"].endswith("_en") else "")) for c in corpus]
print(f"{len(corpus)} passages → {p['name']} / {p['embed_model']}")
vectors = {}
for i in range(0, len(corpus), 64):
    vs = llm.embed([c["text"] for c in corpus[i:i + 64]])
    for cid, v in zip(ids[i:i + 64], vs):
        vectors[cid] = [round(x, 5) for x in v]
    print(f"  {min(i + 64, len(corpus))}/{len(corpus)}", flush=True)
out = Path(__file__).resolve().parents[2] / "data" / "embeddings.json"
out.write_text(json.dumps({"model": f"{p['name']}/{p['embed_model']}", "count": len(vectors), "vectors": vectors}), encoding="utf-8")
print("wrote", out, out.stat().st_size // 1024, "KB")
