"""videos/<slug>/audio.wav -> transcripcion.json con tiempo por palabra (la base del lip-sync).

Proveedor (avatar.json -> transcripcion.proveedor):
  openai    API whisper-1 con timestamps por palabra (necesita OPENAI_API_KEY)
  whisperx  local y gratis, con `uvx whisperx` (la primera vez descarga ~2 GB)
  auto      openai si hay OPENAI_API_KEY, si no whisperx

Formato de salida (el mismo para los dos):
  {"idioma": "es", "proveedor": "...", "sentences": [{"sentence", "start", "end", "words": [{"word", "start", "end"}]}]}
"""
import difflib
import json
import os
import re
import shutil
import subprocess
import unicodedata

from .config import CONFIG, die, ok, rel, tool, video_dir, write_json

SENT_END = re.compile(r"[.?!…]+[\"»”)]*$")


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^a-z0-9ñ']", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def fill_missing(words: list[dict]) -> None:
    """Palabras sin tiempo (números, símbolos): se interpolan entre sus vecinas."""
    n = len(words)
    for i, w in enumerate(words):
        if "start" in w and "end" in w:
            continue
        prev_end = next((words[j]["end"] for j in range(i - 1, -1, -1) if "end" in words[j]), 0.0)
        j = next((j for j in range(i + 1, n) if "start" in words[j]), None)
        nxt = words[j]["start"] if j is not None else prev_end + 0.3 * (n - i)
        gap = j - i if j is not None else n - i
        step = max(0.05, (nxt - prev_end) / (gap + 1))
        w["start"] = round(prev_end + step * 0.1, 3)
        w["end"] = round(prev_end + step, 3)


def sentences_from_words(words: list[dict]) -> list[dict]:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if SENT_END.search(w["word"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"sentence": " ".join(w["word"] for w in s), "start": s[0]["start"], "end": s[-1]["end"],
             "words": [{"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in s]}
            for s in out]


def via_openai(wav) -> list[dict]:
    from openai import OpenAI

    with open(wav, "rb") as fh:
        r = OpenAI().audio.transcriptions.create(
            model="whisper-1", file=fh, language=CONFIG["idioma"], response_format="verbose_json",
            timestamp_granularities=["word", "segment"])
    timed = [{"word": w.word, "start": w.start, "end": w.end} for w in (r.words or [])]
    # las palabras con tiempo vienen sin puntuación; el texto de los segmentos la trae: se alinean
    tokens = " ".join(s.text.strip() for s in (r.segments or [])).split() or r.text.split()
    sm = difflib.SequenceMatcher(a=[norm(t) for t in tokens], b=[norm(w["word"]) for w in timed], autojunk=False)
    words = [{"word": t} for t in tokens]
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            src = timed[blk.b + k]
            words[blk.a + k].update(start=src["start"], end=src["end"])
    fill_missing(words)
    return sentences_from_words(words)


def via_whisperx(wav, d) -> list[dict]:
    uvx = tool("uvx", "Instala uv con la skill avatar-equipo.")
    tmp = d / ".whisperx"
    shutil.rmtree(tmp, ignore_errors=True)
    print("… WhisperX local (la primera vez descarga el modelo; puede tardar varios minutos)", flush=True)
    r = subprocess.run([uvx, "--python", "3.11", "--from", "whisperx", "whisperx", str(wav),
                        "--model", CONFIG["transcripcion"].get("whisperx_modelo", "small"),
                        "--language", CONFIG["idioma"], "--compute_type", "int8",
                        "--output_format", "json", "--output_dir", str(tmp)], capture_output=True, text=True)
    if r.returncode:
        die(f"WhisperX falló:\n{r.stderr[-2000:]}")
    data = json.loads(next(tmp.glob("*.json")).read_text(encoding="utf-8"))
    shutil.rmtree(tmp, ignore_errors=True)
    words = [{k: v for k, v in w.items() if k in ("word", "start", "end")}
             for s in data["segments"] for w in s.get("words", [])]
    fill_missing(words)
    return sentences_from_words(words)


def cmd_transcribir(a) -> None:
    d = video_dir(a.slug)
    wav = d / "audio.wav"
    if not wav.exists():
        die(f"falta {rel(wav)} (corre `avatar importar` o `avatar voz`)")
    prov = a.proveedor or CONFIG["transcripcion"].get("proveedor", "auto")
    if prov == "auto":
        prov = "openai" if os.environ.get("OPENAI_API_KEY") else "whisperx"
    if prov == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            die("falta OPENAI_API_KEY en .env (o usa --proveedor whisperx)")
        sents = via_openai(wav)
    elif prov == "whisperx":
        sents = via_whisperx(wav, d)
    else:
        die(f"proveedor '{prov}' no existe (openai | whisperx | auto)")
    write_json(d / "transcripcion.json", {"idioma": CONFIG["idioma"], "proveedor": prov, "sentences": sents})
    for s in sents:
        print(f"  {s['start']:6.2f}–{s['end']:6.2f}  {s['sentence']}")
    ok(f"{rel(d / 'transcripcion.json')} ({prov})")
