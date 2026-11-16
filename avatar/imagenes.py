"""Genera las imágenes del personaje con la API de OpenAI (alternativa a copiar y pegar en ChatGPT).

  00            fotos del usuario (personaje/foto*.jpg|png|webp)  -> personaje/hoja-de-personaje.png
  01 (maestra)  hoja de personaje                                -> personaje/inbox/01-neutral.png
  02..10        maestra + hoja de personaje                       -> personaje/inbox/NN-<pose>.png

Una imagen que ya existe se mueve a inbox/_descartadas/ antes de regenerarla.
"""
import base64
import io
import os
from pathlib import Path

from PIL import Image

from .config import CONFIG, HOJA, INBOX, PERSONAJE, ROOT, die, ok, rel
from .prompts import POSES, destino, ficha, prompt_de

FOTOS = ("*.jpg", "*.jpeg", "*.png", "*.webp")


def fotos() -> list[Path]:
    out = sorted(p for pat in FOTOS for p in PERSONAJE.glob("foto" + pat))
    if not out:
        die(f"no hay fotos: guárdalas en {rel(PERSONAJE)}/ como foto1.jpg, foto2.jpg…")
    return out[:3]


def as_png(path: Path, max_side: int = 1536) -> tuple[str, bytes, str]:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return (path.stem + ".png", buf.getvalue(), "image/png")


def refs(numero: str) -> list[Path]:
    if numero == "00":
        return fotos()
    if not HOJA.exists():
        die(f"falta {rel(HOJA)} (genera primero la 00)")
    if numero == "01":
        return [HOJA]
    master = INBOX / "01-neutral.png"
    if not master.exists():
        die(f"falta la maestra {rel(master)} (genera y aprueba primero la 01)")
    return [master, HOJA]


def archivar(dest: Path) -> None:
    if not dest.exists():
        return
    old = dest.parent / "_descartadas"
    old.mkdir(parents=True, exist_ok=True)
    n = 1
    while (old / f"{dest.stem}-v{n}{dest.suffix}").exists():
        n += 1
    dest.rename(old / f"{dest.stem}-v{n}{dest.suffix}")


def generar_una(client, numero: str, f: dict, extra: str | None) -> Path:
    cfg = CONFIG["imagenes"]
    prompt = prompt_de(numero, f)
    if extra:
        prompt += f"\n\nAdditional correction: {extra}"
    kw = dict(model=cfg["modelo"], image=[as_png(p) for p in refs(numero)], prompt=prompt,
              size="1536x1024" if numero == "00" else "1024x1536", quality=cfg.get("calidad", "high"), n=1)
    try:
        r = client.images.edit(**kw, input_fidelity="high")
    except TypeError:  # SDK antiguo sin input_fidelity
        r = client.images.edit(**kw)
    except Exception as e:  # el modelo no acepta input_fidelity
        if "input_fidelity" not in str(e):
            raise
        r = client.images.edit(**kw)
    dest = ROOT / destino(numero)
    dest.parent.mkdir(parents=True, exist_ok=True)
    archivar(dest)
    dest.write_bytes(base64.b64decode(r.data[0].b64_json))
    return dest


def cmd_generar(a) -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        die("falta OPENAI_API_KEY en el archivo .env (o usa el modo ChatGPT: `avatar prompts`)")
    from openai import OpenAI

    f = ficha()
    todos = [p[0] for p in POSES]
    if a.cual == "poses":
        numeros = todos[1:]
    elif a.cual in ("hoja", "00"):
        numeros = ["00"]
    elif a.cual in ("maestra", "01"):
        numeros = ["01"]
    else:
        num = next((p[0] for p in POSES if a.cual in (p[0], p[1])), None)
        if not num:
            die(f"no conozco '{a.cual}'. Usa: hoja, maestra, poses o una pose ({', '.join(p[1] for p in POSES)})")
        numeros = [num]
    client = OpenAI()
    for n in numeros:
        dest = ROOT / destino(n)
        if a.cual == "poses" and dest.exists() and not a.rehacer:
            print(f"= {rel(dest)} ya existe (usa --rehacer para regenerarla)")
            continue
        print(f"… generando {rel(dest)}", flush=True)
        try:
            out = generar_una(client, n, f, a.correccion)
        except Exception as e:
            die(f"OpenAI no pudo generar {rel(dest)}: {e}")
        ok(rel(out))
