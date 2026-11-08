"""Hindi -> English post-processing (partial; unknown Hindi stays Hindi).

Uses data/i18n_en.json built by tools/build_i18n.py. Phrases are replaced only at Devanagari word
boundaries, so 'योग' never changes the inside of a longer Hindi word. Only text outside HTML tags is touched.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "i18n_en.json"
_DEV = "ऀ-ॿ"
_TAG = re.compile(r"(<[^>]+>)")
_PATS: list = []
_ORD = re.compile(r"(\d+)(?:वाँ|वें|वीं)(?![" + _DEV + "])")


def _ordinal(m):
    n = int(m.group(1))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


@lru_cache(maxsize=1)
def _dict() -> tuple[dict, dict, re.Pattern]:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    phrases = d["phrases"]
    pats = []
    for hi, en in d.get("patterns", []):
        parts = re.split(r"\{(\d+)\}", hi)               # literal, idx, literal, idx, ...
        rx_p = "".join(re.escape(x) if i % 2 == 0 else "(.+?)" for i, x in enumerate(parts))
        pats.append((re.compile("^" + rx_p + "$"), en, [int(x) for x in parts[1::2]]))
    _PATS.clear()
    _PATS.extend(pats)
    rx = re.compile(f"(?<![{_DEV}])(" + "|".join(re.escape(k) for k in sorted(phrases, key=len, reverse=True)) + f")(?![{_DEV}])")
    return d["exact"], phrases, rx


def _try(core: str) -> str | None:
    """Translate one Devanagari-containing string completely, or return None."""
    exact, phrases, rx = _dict()
    if not re.search(f"[{_DEV}]", core):
        return core
    if core in exact:
        return exact[core]
    for pat, en, order in _PATS:
        m = pat.match(core)
        if m:
            groups = [_try(g) for g in m.groups()]
            if None in groups:
                continue
            return re.sub(r"\{(\d+)\}", lambda x: groups[order.index(int(x.group(1)))], en)
    out = _ORD.sub(_ordinal, rx.sub(lambda mm: phrases[mm.group(1)], core))
    if not re.search(f"[{_DEV}]", out):
        return out
    for key in sorted((k for k in exact if len(k) >= 30 and core.startswith(k + " ")), key=len, reverse=True):
        rest = _try(core[len(key) + 1:])           # two long sentences joined by the page
        if rest is not None:
            return exact[key] + " " + rest
    for sep in ("; ", ", ", " / "):
        if sep in core:
            parts = [_try(x) for x in core.split(sep)]
            if None not in parts:
                return sep.join(parts)
    return None


def translate_text(text: str) -> str:
    """All-or-nothing per text: translated only when no Devanagari is left, so output never mixes the languages
    inside one sentence."""
    _dict()
    core = " ".join(text.split())
    core = core.replace("&#x27;", "'").replace("&amp;", "&")
    out = _try(core)
    return text if out is None else text.replace(text.strip(), out) if text.strip() else text


def translate_html(html: str) -> str:
    parts = _TAG.split(html)
    return "".join(p if p.startswith("<") else translate_text(p) for p in parts)


def coverage(html: str) -> float:
    """Share of Devanagari characters that are NOT left after translation (0..1)."""
    before = len(re.findall(f"[{_DEV}]", re.sub(r"<[^>]+>", "", html)))
    after = len(re.findall(f"[{_DEV}]", re.sub(r"<[^>]+>", "", translate_html(html))))
    return 1 - after / before if before else 1.0
