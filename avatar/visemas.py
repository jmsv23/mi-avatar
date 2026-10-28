"""Palabras con tiempo -> visemas, a partir de las letras (method: grapheme).

Español: se lee casi como se escribe; cada letra (o dígrafo) da un visema.
  a → A · e i y(final) → E_I · o u → O_U · m b p v → MBP · f → FV · resto → CONS · h → muda
Inglés: reglas aproximadas de dígrafos (th, sh, ch, ph, oo, ee, ea, ou, ow, w…) y e final muda.
La duración de cada palabra se reparte con más peso para las vocales. Entre palabras separadas
por más de GAP_REST segundos la boca vuelve a REST.
"""
import re
import unicodedata

GAP_REST = 0.12
MIN_DUR = 1 / 30
W_VOWEL, W_CONS = 1.0, 0.55

VOWELS = {"a": "A", "e": "E_I", "i": "E_I", "o": "O_U", "u": "O_U"}
LIPS_ES = set("mbpv")
LIPS_EN = set("mbp")

NUM = {
    "es": ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"],
    "en": ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
}

# dígrafos del inglés: secuencia -> visemas
EN_DIGRAPHS = [
    ("tch", ["CONS"]), ("th", ["CONS"]), ("sh", ["CONS"]), ("ch", ["CONS"]), ("ph", ["FV"]), ("gh", []),
    ("ck", ["CONS"]), ("ng", ["CONS"]), ("qu", ["CONS", "O_U"]), ("wh", ["O_U"]),
    ("oo", ["O_U"]), ("ou", ["A", "O_U"]), ("ow", ["O_U"]), ("ee", ["E_I"]), ("ea", ["E_I"]),
    ("ai", ["E_I"]), ("ay", ["E_I"]), ("oa", ["O_U"]), ("ie", ["E_I"]), ("ey", ["E_I"]),
]


def normalize(word: str, lang: str) -> str:
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    nums = NUM.get(lang, NUM["es"])
    w = "".join(nums[int(c)] if c.isdigit() else c for c in w)
    return re.sub(r"[^a-z]", "", w)


def units_es(w: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(w):
        c, nxt = w[i], w[i + 1: i + 2]
        if c == "h":
            i += 1
            continue
        if c == "c" and nxt == "h":
            out.append("CONS"); i += 2; continue
        if c in "lr" and nxt == c:
            out.append("CONS"); i += 2; continue
        if c in "qg" and nxt == "u" and w[i + 2: i + 3] in ("e", "i"):
            out.append("CONS"); i += 2; continue
        if c == "y":
            out.append("E_I" if i == len(w) - 1 or w[i + 1: i + 2] not in VOWELS else "CONS")
        elif c in VOWELS:
            out.append(VOWELS[c])
        elif c in LIPS_ES:
            out.append("MBP")
        elif c == "f":
            out.append("FV")
        else:
            out.append("CONS")
        i += 1
    return out


def units_en(w: str) -> list[str]:
    if len(w) > 2 and w.endswith("e") and w[-2] not in VOWELS and w[-2] != "l":
        w = w[:-1]  # e final muda (make, time, love)
    out: list[str] = []
    i = 0
    while i < len(w):
        for seq, vs in EN_DIGRAPHS:
            if w.startswith(seq, i):
                out.extend(vs)
                i += len(seq)
                break
        else:
            c = w[i]
            if c == "h":
                pass
            elif c == "w":
                out.append("O_U")
            elif c == "y":
                out.append("E_I" if i == len(w) - 1 or w[i + 1: i + 2] not in VOWELS else "CONS")
            elif c in VOWELS:
                out.append(VOWELS[c])
            elif c in LIPS_EN:
                out.append("MBP")
            elif c in "fv":
                out.append("FV")
            else:
                out.append("CONS")
            i += 1
    return out


def units(word: str, lang: str = "es") -> list[str]:
    w = normalize(word, lang)
    return units_en(w) if lang == "en" else units_es(w)


def word_visemes(word: str, start: float, end: float, lang: str) -> list[dict]:
    us = units(word, lang) or ["A"]
    weights = [W_VOWEL if u in ("A", "E_I", "O_U") else W_CONS for u in us]
    total = sum(weights)
    dur = max(end - start, MIN_DUR * len(us))
    out, t = [], start
    for u, w in zip(us, weights):
        d = dur * w / total
        out.append({"t": round(t, 3), "d": round(d, 3), "v": u})
        t += d
    return out


def from_words(words: list[dict], lang: str = "es") -> list[dict]:
    """words: [{word, start, end}] en orden. Devuelve visemas sin huecos innecesarios, con REST en pausas."""
    vis: list[dict] = []
    prev_end = None
    for w in words:
        if "start" not in w or "end" not in w:
            continue
        if prev_end is not None and w["start"] - prev_end > GAP_REST:
            vis.append({"t": round(prev_end, 3), "d": round(w["start"] - prev_end, 3), "v": "REST"})
        vis.extend(word_visemes(w["word"], w["start"], w["end"], lang))
        prev_end = w["end"]
    merged: list[dict] = []
    for v in vis:
        if merged and (merged[-1]["v"] == v["v"] or v["d"] < MIN_DUR):
            merged[-1]["d"] = round(v["t"] + v["d"] - merged[-1]["t"], 3)
        else:
            merged.append(dict(v))
    return merged
