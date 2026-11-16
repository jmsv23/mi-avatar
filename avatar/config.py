"""Rutas, configuración (avatar.json + .env) y utilidades compartidas por todos los comandos."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "avatar.json").read_text(encoding="utf-8"))
PERSONAJES = ROOT / "personaje"


def carpeta_personaje(nombre: str | None, base: Path = PERSONAJES) -> Path:
    """Sin selección conserva la estructura de los proyectos anteriores."""
    if nombre is None:
        return base
    if not isinstance(nombre, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", nombre):
        raise ValueError("el nombre del personaje debe usar minúsculas, números y guiones")
    path = base / nombre
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("la carpeta del personaje debe estar dentro de personaje/")
    return path


PERSONAJE = carpeta_personaje(CONFIG.get("personaje_activo"))
INBOX = PERSONAJE / "inbox"
POSES = PERSONAJE / "poses"
LAYERS = PERSONAJE / "layers"
REVISION = PERSONAJE / "_revision"
PROMPTS = PERSONAJE / "prompts"
MANIFEST = PERSONAJE / "manifest.json"
CARA = PERSONAJE / "cara.json"
FICHA = PERSONAJE / "personaje.json"
HOJA = PERSONAJE / "hoja-de-personaje.png"
VIDEOS = ROOT / "videos"
MOTION = ROOT / "motion"

# Lienzo de cada pose normalizada (2:3, el formato vertical de los generadores de imagen)
W, H = 1024, 1536

FORMATOS = {"vertical": (1080, 1920), "horizontal": (1920, 1080), "cuadrado": (1080, 1080)}


def _load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()


def die(msg: str) -> None:
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"✓ {msg}")


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def tool(name: str, hint: str) -> str:
    """Ruta absoluta de un ejecutable (en Windows resuelve npx.cmd, ffmpeg.exe…)."""
    path = shutil.which(name)
    if not path:
        die(f"no encuentro `{name}`. {hint}")
    return path


def ffmpeg() -> str:
    return tool("ffmpeg", "Instálalo con la skill avatar-equipo (o pídeselo a tu agente).")


def ffprobe() -> str:
    return tool("ffprobe", "Viene junto con ffmpeg: reinstala ffmpeg con la skill avatar-equipo.")


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode:
        detail = ""
        if kw.get("capture_output"):
            detail = "\n" + ((r.stderr or "") if isinstance(r.stderr, str) else "")[-1500:]
        die(f"falló: {' '.join(map(str, cmd[:4]))} …{detail}")
    return r


def hf(*args) -> list:
    npx = tool("npx", "Instala Node.js 22 o superior con la skill avatar-equipo.")
    return [npx, "--yes", f"hyperframes@{CONFIG['render']['hyperframes']}", *args]


def duracion(path: Path) -> float:
    out = run([ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
              capture_output=True, text=True).stdout
    return round(float(out), 3)


def read_json(p: Path, what: str = "") -> dict:
    if not p.exists():
        die(f"falta {rel(p)}{' — ' + what if what else ''}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data, indent: int = 2) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")


def video_dir(slug: str, crear: bool = False) -> Path:
    d = VIDEOS / slug
    if crear:
        d.mkdir(parents=True, exist_ok=True)
    elif not d.is_dir():
        die(f"no existe {rel(d)}")
    return d


def lienzo() -> tuple[int, int, str]:
    fmt = CONFIG["lienzo"].get("formato", "vertical")
    if fmt not in FORMATOS:
        die(f"formato '{fmt}' no válido en avatar.json (usa {', '.join(FORMATOS)})")
    return (*FORMATOS[fmt], fmt)
