"""Plain-ASCII romanization of Hindi names (Bholanath, Janakinath, Jagrit) for the English UI.
Simple Hindi rules: inherent 'a' after each consonant, dropped at the end of a word; no diacritics."""

_V = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}
_M = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o"}
_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh",
      "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l",
      "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l", "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y"}
_NUKTA, _VIRAMA = "़", "्"
_NASAL = {"ं": "n", "ँ": "n", "ः": "h"}


def roman(text: str) -> str:
    out, i, s = [], 0, text
    while i < len(s):
        ch = s[i]
        if i + 1 < len(s) and s[i + 1] == _NUKTA and ch + _NUKTA in _C:
            ch, i = ch + _NUKTA, i + 1
        if ch in _C:
            out.append(_C[ch])
            nxt = s[i + 1] if i + 1 < len(s) else ""
            if nxt in _M:
                out.append(_M[nxt]); i += 2; continue
            if nxt == _VIRAMA:
                i += 2; continue
            # inherent a, dropped at the end of a word (Hindi schwa deletion, final position only)
            if (nxt and (nxt in _C or nxt in _NASAL or "ऀ" <= nxt <= "ॿ")) or (not nxt.strip() and i > 0 and s[i - 1] == _VIRAMA):
                out.append("a")                                   # ...but kept after a conjunct: Krishna, Aditya
            i += 1; continue
        if ch in _V:
            out.append(_V[ch])
        elif ch in _NASAL:
            out.append(_NASAL[ch])
        elif ch in _M:
            out.append(_M[ch])
        else:
            out.append(ch)
        i += 1
    r = "".join(out)
    return " ".join(w[:1].upper() + w[1:] if w else w for w in r.split(" "))
