"""avatar doctor: revisa que el equipo tenga todo lo necesario y dice cómo instalar lo que falte."""
import json
import os
import platform
import re
import shutil
import subprocess

from .config import CONFIG, MANIFEST, MOTION, ROOT, hf, rel

SYS = platform.system()  # Darwin | Windows | Linux

INSTALL = {
    "node": {
        "Darwin": "brew install node   (o descarga el instalador LTS de https://nodejs.org)",
        "Windows": "winget install OpenJS.NodeJS.LTS   (luego cierra y vuelve a abrir la app)",
        "Linux": "instala Node 22+ con tu gestor (nvm, asdf o https://nodejs.org)",
    },
    "ffmpeg": {
        "Darwin": "brew install ffmpeg",
        "Windows": "winget install Gyan.FFmpeg   (luego cierra y vuelve a abrir la app)",
        "Linux": "sudo apt install ffmpeg   (o el gestor de tu distribución)",
    },
}


def version(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=30)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return None


def cmd_doctor(a) -> None:
    rows, faltan = [], []

    def check(nombre: str, okv: bool, detalle: str, arreglo: str = "") -> None:
        rows.append((nombre, okv, detalle))
        if not okv:
            faltan.append((nombre, arreglo))

    nv = version(["node", "--version"])
    major = int(re.sub(r"[^\d.]", "", nv).split(".")[0]) if nv else 0
    check("Node.js 22+", major >= 22, nv or "no instalado", INSTALL["node"][SYS])
    fv = version(["ffmpeg", "-version"])
    check("FFmpeg", bool(fv), (fv or "no instalado")[:60], INSTALL["ffmpeg"][SYS])
    check("FFprobe", bool(shutil.which("ffprobe")), "ok" if shutil.which("ffprobe") else "no instalado", INSTALL["ffmpeg"][SYS])
    check("uv", bool(shutil.which("uv")), version(["uv", "--version"]) or "no instalado", "ver skill avatar-equipo")

    if major >= 22 and not a.rapido:
        r = subprocess.run(hf("doctor", "--json"), cwd=MOTION, capture_output=True, text=True, encoding="utf-8")
        try:
            res = json.loads(r.stdout[r.stdout.index("{"):])
            chrome = next((c for c in res.get("checks", []) if c.get("name") == "Chrome"), None)
            if chrome:
                check("Chrome de HyperFrames", bool(chrome.get("ok")), "ok" if chrome.get("ok") else str(chrome.get("detail"))[:60],
                      "npx hyperframes browser ensure (lo hace `avatar doctor --arreglar`)")
        except ValueError:
            check("HyperFrames", False, "no pude ejecutar hyperframes doctor", "revisa tu conexión a internet")

    env = {
        "OPENAI_API_KEY": "imágenes por API y transcripción rápida",
        "ELEVENLABS_API_KEY": "voz con ElevenLabs",
    }
    claves = {k: bool(os.environ.get(k)) for k in env}

    print(f"Sistema: {SYS} · proyecto: {ROOT}")
    for nombre, okv, detalle in rows:
        print(f"  {'✓' if okv else '✗'} {nombre:24s} {detalle}")
    for k, uso in env.items():
        print(f"  {'✓' if claves[k] else '·'} {k:24s} {'configurada' if claves[k] else 'opcional — ' + uso}")
    print(f"  · avatar: {'listo (' + rel(MANIFEST) + ')' if MANIFEST.exists() else 'todavía no creado'}")
    print(f"  · voz: {CONFIG['voz']['proveedor']} · imágenes: {CONFIG['imagenes']['proveedor']} · "
          f"transcripción: {CONFIG['transcripcion']['proveedor']} · formato: {CONFIG['lienzo']['formato']}")

    if a.arreglar and major >= 22:
        print("… instalando el navegador de HyperFrames", flush=True)
        subprocess.run(hf("browser", "ensure"), cwd=MOTION)
    if faltan:
        print("\nFalta instalar:")
        for nombre, arreglo in faltan:
            print(f"  - {nombre}: {arreglo}")
        raise SystemExit(1)
    print("\n✓ todo listo")
