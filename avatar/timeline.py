"""transcripcion.json [+ plan.json] -> timeline.json del avatar.

timeline.json (tiempos en segundos desde el inicio del audio):
  version, fps, duracion, audio, idioma
  lipsync:   {"method": "grapheme"}
  escenas:   [{t0, t1, tipo, avatar, ...}]   (sin plan: una sola escena "avatar")
  poses:     [{t, pose}]                       la pose vale desde t hasta la siguiente
  gestos:    [{t, g: asentir|negar, d}]
  parpadeos: [t, ...]
  visemas:   [{t, d, v}]                       v en REST A E_I O_U MBP FV CONS

Sin "poses" en el plan, salen de reglas por oración: pregunta -> encogerse, enumeración -> contar,
exclamación -> senalar, el resto rota hablar/manos-abiertas/neutral, con un mínimo de MIN_POSE s.
"""
import random
import re

from .config import CONFIG, MANIFEST, die, duracion, ok, read_json, rel, video_dir, write_json
from .visemas import from_words

MIN_POSE = 2.0
LONG_SENTENCE = 5.0
LEAD = 0.15
ROTATION = ["hablar", "manos-abiertas", "hablar", "neutral"]
ENUM = re.compile(r"\b(primero|segundo|tercero|uno|dos|tres|cuatro|cinco|first|second|third|one|two|three|four|five)\b", re.I)
YES = {"sí", "si", "yes", "yeah"}
NO = {"no", "nope"}
TIPOS = {"avatar", "titulo", "lista", "dato", "cita", "imagen", "video"}
AVATAR_MODOS = {"completo", "narrador", "oculto"}


def pose_for(sentence: str, i: int, rotation: list[str], have: set[str]) -> str:
    s = sentence.strip()
    if (s.endswith("?") or s.startswith("¿")) and "encogerse" in have:
        return "encogerse"
    if ENUM.search(s) and "contar" in have:
        return "contar"
    if (s.endswith("!") or s.startswith("¡")) and "senalar" in have:
        return "senalar"
    return rotation[i % len(rotation)]


def auto_poses(sentences: list[dict], dur: float, have: set[str]) -> list[dict]:
    rotation = [p for p in ROTATION if p in have] or sorted(have)
    first = "neutral" if "neutral" in have else rotation[0]
    poses = [{"t": 0.0, "pose": first}]
    rot = 0

    def add(t: float, pose: str) -> None:
        if pose == poses[-1]["pose"]:
            return
        if t - poses[-1]["t"] < MIN_POSE:
            if len(poses) == 1 and t < MIN_POSE:
                poses[0]["pose"] = pose
            return
        poses.append({"t": round(t, 3), "pose": pose})

    for s in sentences:
        p = pose_for(s["sentence"], rot, rotation, have)
        if p in rotation:
            rot += 1
        add(max(0.0, s["start"] - LEAD), p)
        if s["end"] - s["start"] > LONG_SENTENCE:
            mid = s["start"] + (s["end"] - s["start"]) / 2
            w = min(s["words"], key=lambda w: abs(w["start"] - mid))
            add(w["start"] - LEAD, rotation[rot % len(rotation)])
            rot += 1
    last_end = sentences[-1]["end"] if sentences else 0
    if dur - last_end > 0.6:
        add(last_end + 0.2, first)
    return poses


def gestures(sentences: list[dict]) -> list[dict]:
    out = []
    for s in sentences:
        for w in s["words"]:
            word = re.sub(r"[^\wáéíóúñ]", "", w["word"].lower())
            if word in YES:
                out.append({"t": round(w["start"], 3), "g": "asentir", "d": 0.7})
            elif word in NO and w is s["words"][0]:
                out.append({"t": round(w["start"], 3), "g": "negar", "d": 0.7})
    return out


def blinks(dur: float, poses: list[dict], seed: int) -> list[float]:
    rng = random.Random(seed)  # semilla fija: mismo audio, mismos parpadeos
    out, t = [], rng.uniform(0.8, 2.0)
    while t < dur - 0.3:
        out.append(round(t, 3))
        t += rng.uniform(2.4, 5.2)
    for p in poses[1::2]:
        if all(abs(p["t"] + 0.05 - b) > 0.8 for b in out):
            out.append(round(p["t"] + 0.05, 3))
    return sorted(out)


def check_escenas(escenas: list[dict], dur: float, d) -> list[dict]:
    out = []
    for i, e in enumerate(sorted(escenas, key=lambda e: e["t0"])):
        tipo = e.get("tipo", "avatar")
        if tipo not in TIPOS:
            die(f"plan.json escena {i}: tipo '{tipo}' no existe ({', '.join(sorted(TIPOS))})")
        modo = e.get("avatar", {"avatar": "completo", "video": "oculto"}.get(tipo, "narrador"))
        if modo not in AVATAR_MODOS:
            die(f"plan.json escena {i}: avatar '{modo}' no existe ({', '.join(AVATAR_MODOS)})")
        if tipo in ("imagen", "video"):
            if not e.get("archivo") or not (d / e["archivo"]).exists():
                die(f"plan.json escena {i}: no existe videos/{d.name}/{e.get('archivo')}")
        out.append({**e, "tipo": tipo, "avatar": modo, "t0": round(max(0, e["t0"]), 3), "t1": round(min(dur, e["t1"]), 3)})
    return out


def build(d) -> dict:
    tr = read_json(d / "transcripcion.json", "corre `avatar transcribir`")
    manifest = read_json(MANIFEST, "el avatar no está listo (skill avatar-crear)")
    have = set(manifest["poses"])
    sentences = tr["sentences"]
    words = [w for s in sentences for w in s["words"]]
    dur = duracion(d / "audio.wav")
    plan = read_json(d / "plan.json") if (d / "plan.json").exists() else {}
    poses = plan.get("poses") or auto_poses(sentences, dur, have)
    for p in poses:
        if p["pose"] not in have:
            die(f"la pose '{p['pose']}' (t={p['t']}) no existe en tu avatar ({', '.join(sorted(have))})")
    lang = tr.get("idioma", CONFIG["idioma"])
    return {
        "version": 2,
        "fps": CONFIG["render"]["fps"],
        "duracion": dur,
        "audio": "audio.wav",
        "idioma": lang,
        "lipsync": {"method": "grapheme"},
        "escenas": check_escenas(plan.get("escenas") or [{"t0": 0.0, "t1": dur, "tipo": "avatar"}], dur, d),
        "poses": poses,
        "gestos": plan.get("gestos") or gestures(sentences),
        "parpadeos": blinks(dur, poses, seed=len(words)),
        "visemas": from_words(words, lang),
    }


def cmd_timeline(a) -> None:
    d = video_dir(a.slug)
    tl = build(d)
    write_json(d / "timeline.json", tl, indent=1)
    ok(f"{rel(d / 'timeline.json')} · {tl['duracion']} s · {len(tl['escenas'])} escenas · {len(tl['poses'])} poses · "
       f"{len(tl['visemas'])} visemas · {len(tl['parpadeos'])} parpadeos")
    for p in tl["poses"]:
        print(f"  {p['t']:7.2f}  {p['pose']}")
