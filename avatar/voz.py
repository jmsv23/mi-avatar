"""Audio de un video: videos/<slug>/audio.wav.

  importar <slug> <archivo>   tu grabación (audio o video, cualquier formato) -> audio.wav
                              si es un video se guarda también como original.mp4 para usarlo en escenas
  voz <slug>                  videos/<slug>/guion.txt -> audio.wav con ElevenLabs o Voicebox (avatar.json -> voz)
"""
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import CONFIG, die, duracion, ffmpeg, ffprobe, ok, read_json, rel, run, video_dir, write_json

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


def to_wav(src: Path, dest: Path) -> None:
    run([ffmpeg(), "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "48000",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", dest], capture_output=True, text=True)


def has_video(src: Path) -> bool:
    out = subprocess.run([ffprobe(), "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type",
                          "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout
    return "video" in out and src.suffix.lower() in VIDEO_EXT


def cmd_importar(a) -> None:
    src = Path(a.archivo).expanduser().resolve()
    if not src.exists():
        die(f"no existe {src}")
    d = video_dir(a.slug, crear=True)
    if has_video(src):
        # el video se normaliza a H.264 para que el navegador del render lo decodifique sin sorpresas
        run([ffmpeg(), "-v", "error", "-y", "-i", src, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", d / "original.mp4"], capture_output=True, text=True)
        print(f"  video guardado como {rel(d / 'original.mp4')}")
    to_wav(src, d / "audio.wav")
    write_json(d / "audio.meta.json", {"fuente": src.name, "proveedor": "grabacion", "duracion": duracion(d / "audio.wav")})
    ok(f"{rel(d / 'audio.wav')} · {duracion(d / 'audio.wav')} s")


# ---------- ElevenLabs ----------

def elevenlabs(text: str, dest: Path) -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    cfg = CONFIG["voz"]["elevenlabs"]
    if not key:
        die("falta ELEVENLABS_API_KEY en .env")
    if not cfg.get("voice_id"):
        die("falta voz.elevenlabs.voice_id en avatar.json (cópialo de ElevenLabs → Voices → tu voz → ID)")
    body = json.dumps({"text": text, "model_id": cfg.get("modelo", "eleven_multilingual_v2")}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['voice_id']}?output_format=mp3_44100_128",
        data=body, method="POST", headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            mp3 = r.read()
    except urllib.error.HTTPError as e:
        die(f"ElevenLabs → {e.code}: {e.read().decode()[:400]}")
    tmp = dest.with_suffix(".mp3")
    tmp.write_bytes(mp3)
    to_wav(tmp, dest)
    tmp.unlink()
    return {"proveedor": "elevenlabs", "voz": cfg["voice_id"], "modelo": cfg.get("modelo")}


# ---------- Voicebox (local) ----------

def vb(method: str, path: str, body: dict | None = None, raw: bool = False, timeout: int = 120):
    url = CONFIG["voz"]["voicebox"]["url"].rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read() if raw else json.load(r)
    except urllib.error.HTTPError as e:
        die(f"Voicebox {method} {path} → {e.code}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        die(f"Voicebox no responde en {url} ({e.reason}). ¿Está abierta la app?")


def voicebox(text: str, dest: Path, instruct: str | None) -> dict:
    name = CONFIG["voz"]["voicebox"].get("perfil")
    profs = vb("GET", "/profiles")
    prof = next((p for p in profs if name and (p["name"] == name or p["id"] == name)), None)
    if not prof:
        die(f"perfil de Voicebox '{name}' no existe. Perfiles: {', '.join(p['name'] for p in profs)} "
            "→ ponlo en avatar.json (voz.voicebox.perfil)")
    body = {"profile_id": prof["id"], "text": text, "language": CONFIG["idioma"], "personality": False, "normalize": True}
    engine = prof.get("default_engine") or prof.get("preset_engine") or ""
    if instruct and engine.startswith("qwen"):
        body["instruct"] = instruct[:500]
    t0 = time.time()
    gen = vb("POST", "/generate", body)
    while gen["status"] not in ("completed", "failed", "error", "cancelled"):
        if time.time() - t0 > 900:
            die("Voicebox tardó más de 15 min")
        time.sleep(1)
        gen = vb("GET", f"/history/{gen['id']}")
    if gen["status"] != "completed":
        die(f"Voicebox falló: {gen.get('error')}")
    tmp = dest.with_name("voicebox.wav")
    tmp.write_bytes(vb("GET", f"/audio/{gen['id']}", raw=True, timeout=300))
    to_wav(tmp, dest)
    tmp.unlink()
    return {"proveedor": "voicebox", "voz": prof["name"], "motor": engine}


def cmd_voz(a) -> None:
    d = video_dir(a.slug)
    guion = d / "guion.txt"
    if not guion.exists():
        die(f"falta {rel(guion)}")
    text = guion.read_text(encoding="utf-8").strip()
    prov = a.proveedor or CONFIG["voz"]["proveedor"]
    if prov == "grabacion":
        die("tu avatar.json dice que grabas tu voz: graba el guion y corre `avatar importar <slug> <archivo>` "
            "(o usa --proveedor elevenlabs|voicebox)")
    wav, meta_f = d / "audio.wav", d / "audio.meta.json"
    sha = hashlib.sha256(f"{text}|{prov}|{json.dumps(CONFIG['voz'].get(prov, {}), sort_keys=True)}|{a.instruct or ''}".encode()).hexdigest()[:16]
    if wav.exists() and meta_f.exists() and not a.force and read_json(meta_f).get("sha") == sha:
        print(f"= {rel(wav)} ya está al día (usa --force para rehacerlo)")
        return
    print(f"… generando voz con {prov}", flush=True)
    if prov == "elevenlabs":
        meta = elevenlabs(text, wav)
    elif prov == "voicebox":
        meta = voicebox(text, wav, a.instruct)
    else:
        die(f"proveedor de voz '{prov}' no existe (grabacion | elevenlabs | voicebox)")
    meta.update({"sha": sha, "duracion": duracion(wav), "palabras": len(text.split()), "generado": time.strftime("%Y-%m-%d %H:%M:%S")})
    write_json(meta_f, meta)
    ok(f"{rel(wav)} · {meta['duracion']} s · {meta['palabras']} palabras")
