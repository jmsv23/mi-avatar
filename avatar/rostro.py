"""Selección y validación del sistema facial, compartidas por revisión y video."""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

from .config import CONFIG, PERSONAJE, read_json, die

BOCAS = ("A", "E_I", "O_U", "FV", "CONS")


def dentro(ruta: str) -> Path:
    if not isinstance(ruta, str) or not ruta:
        raise ValueError("la ruta de una pieza está vacía")
    path = (PERSONAJE / ruta).resolve()
    if not path.is_relative_to(PERSONAJE.resolve()):
        raise ValueError("las piezas deben estar dentro de personaje/")
    return path


def numero(value, nombre, positivo=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{nombre} debe ser un número finito")
    if positivo and value <= 0:
        raise ValueError(f"{nombre} debe ser mayor que cero")


def validar(data: dict) -> dict:
    if data.get("version") != 1:
        raise ValueError("versión de recortes no compatible")
    ref = data["referencia"]
    for name, anchor in [("boca", ref["boca"]), *ref["ojos"].items()]:
        for axis in ("x", "y"):
            numero(anchor[axis], f"{name}.{axis}")
    numero(ref["boca"]["escala"], "escala de boca", positivo=True)
    if ref["ojos"]["izq"]["x"] == ref["ojos"]["der"]["x"] and ref["ojos"]["izq"]["y"] == ref["ojos"]["der"]["y"]:
        raise ValueError("los ojos no pueden tener el mismo centro")
    huella = ref.get("maestra_sha256")
    if huella and hashlib.sha256((PERSONAJE / "poses/neutral.png").read_bytes()).hexdigest() != huella:
        raise ValueError("la maestra cambió: revisa y prepara otra vez sus gestos")
    frames = [data["bocas"][key] for key in BOCAS]
    frames += [data["ojos"][side][state] for side in ("izq", "der") for state in ("medio", "cerrado")]
    for frame in frames:
        for key in ("x", "y", "ancho", "alto"):
            numero(frame[key], key, positivo=key in ("ancho", "alto"))
        with Image.open(dentro(frame["archivo"])) as img:
            if img.mode != "RGBA" or img.size != (frame["ancho"], frame["alto"]):
                raise ValueError("una pieza no coincide con su tamaño o no tiene transparencia")
            img.verify()
    return data


def aplicar(manifest: dict, cara: dict, config=None) -> dict:
    config = CONFIG if config is None else config
    # Compatibilidad con avatares anteriores que ya guardaban recortes en cara.json.
    sistema = config.get("rostro", {}).get("sistema") or ("recortes" if cara.get("recortes") else "svg")
    result = {k: v for k, v in manifest.items() if k != "recortes"}
    if sistema == "svg":
        return result
    if sistema != "recortes":
        die("elige el rostro con `avatar gestos usar svg` o `avatar gestos usar recortes`")
    try:
        if not cara.get("recortes"):
            raise ValueError("faltan gestos aprobados; prepara y activa los recortes primero")
        data = json.loads(dentro(cara["recortes"]).read_text(encoding="utf-8"))
        result["recortes"] = validar(data)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        die(f"no se pueden usar los recortes: {exc}. No se cambió a SVG.")
    return result


def actual(manifest: dict) -> dict:
    from .config import CARA
    return aplicar(manifest, read_json(CARA) if CARA.exists() else {})
