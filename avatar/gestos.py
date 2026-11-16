"""Gestos reutilizables: generar variantes, recortar, revisar y elegir sistema facial."""
import base64
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import CONFIG, ROOT, PERSONAJE, POSES, CARA, MANIFEST, LAYERS, die, ok, read_json, write_json, rel
from .rostro import aplicar, dentro, validar

GESTOS = {
    "a": ("A", "Change ONLY the mouth to a moderately open Spanish A, same full lips, subtle teeth and inner mouth shading. Avoid an exaggerated grin."),
    "e-i": ("E_I", "Change ONLY the mouth to Spanish E/I: horizontally spread lips with a narrow opening and subtly visible teeth. Smaller opening than A."),
    "o-u": ("O_U", "Change ONLY the mouth to Spanish O/U: pursed lips and a small rounded opening, no visible teeth. Remove the original wide lip shape within the local mouth region."),
    "f-v": ("FV", "Change ONLY the mouth to F/V: upper front teeth gently touching the inner lower lip, very narrow opening; anatomically plausible labiodental articulation."),
    "cons": ("CONS", "Change ONLY the mouth to a light consonant articulation: slightly parted lips, shallow opening, subtle upper teeth; smaller opening than A."),
    "ojos-medios": (None, "Change ONLY both eyes to halfway through a natural blink: lowered upper lids, narrow opening showing part of each original iris, eyelashes along the lowered lid seam. Do not alter the eyebrows or mouth."),
    "ojos-cerrados": (None, "Change ONLY both eyes to a gently closed natural blink. Preserve eyelid volume and shading, eyelashes along the CLOSED lid seam. No iris, white of the eye, duplicate lashes or flat skin patches. Do not alter the eyebrows or mouth."),
}


def carpeta() -> Path:
    return PERSONAJE / "gestos"


def maestra() -> Image.Image:
    if not (POSES / "neutral.png").exists():
        die("prepara y aprueba la pose neutral antes de crear sus gestos")
    return Image.open(POSES / "neutral.png").convert("RGBA")


def ajustes_iniciales(cara: dict) -> dict:
    b, ojo = cara["boca"], cara["ojo"]
    w = b["ancho"]
    return {
        "boca": [round(b["x"] - w * .68), round(b["y"] - w * .26), round(w * 1.36), round(w * .76)],
        "ojos": {side: [round(e["x"] - ojo["ancho"] * .59), round(e["y"] - ojo["alto"] * .7),
                        round(ojo["ancho"] * 1.18), round(ojo["alto"] * 1.85)] for side, e in cara["ojos"].items()},
        "suavizado": 2,
        "nota": "Rectángulos x,y,ancho,alto en la pose neutral preparada. Ajustar mirando la revisión; no incluir nariz, cejas o cabello.",
    }


def prompt(nombre: str) -> str:
    return ("Use case: precise-object-edit. Input image is the EDIT TARGET: the approved, aligned character master. "
            "Return ONE full image, with EXACTLY the same pixel dimensions, framing, scale, head angle and feature positions. "
            "Preserve character identity and original illustration finish: lip volume, skin shading, texture, colors and eyelashes. "
            "Keep ALL surrounding facial skin, nose, eyebrows, hair, jaw, clothes, body and green background unchanged. "
            "The result will be cropped into small local overlays on the ORIGINAL image, so pixel alignment is critical. "
            "No panels, captions, text, new accessories, reframing or flat vector patches. " + GESTOS[nombre][1])


def cmd_prompts(a) -> None:
    master = maestra()
    if master.size != (1024, 1536):
        die("la pose neutral preparada debe medir 1024 × 1536")
    c = read_json(CARA, "mide primero boca y ojos")
    folder = carpeta()
    fingerprint = hashlib.sha256((POSES / "neutral.png").read_bytes()).hexdigest()
    previous = folder / "referencia.json"
    if previous.exists() and read_json(previous).get("maestra_sha256") != fingerprint:
        n = 1
        while (folder / "_anteriores" / f"referencia-v{n}").exists():
            n += 1
        archive = folder / "_anteriores" / f"referencia-v{n}"
        archive.mkdir(parents=True)
        for name in ("inbox", "maestra.png", "referencia.json", "ajustes.json", "candidato.json"):
            if (folder / name).exists():
                (folder / name).rename(archive / name)
        print(f"= referencia anterior conservada en {rel(archive)}; prepara variantes de la nueva maestra")
    for sub in ("inbox", "prompts"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    bg = Image.new("RGBA", master.size, "#00ff00")
    bg.alpha_composite(master)
    bg.convert("RGB").save(folder / "maestra.png")
    write_json(folder / "referencia.json", {"maestra_sha256": fingerprint})
    settings = folder / "ajustes.json"
    if not settings.exists():
        write_json(settings, ajustes_iniciales(c))
    for name in GESTOS:
        (folder / "prompts" / f"{name}.md").write_text(prompt(name) + "\n", encoding="utf-8")
    guide = """# Gestos del avatar

Usa maestra.png como imagen de referencia en CADA edición. Guarda cada resultado
completo, sin recortarlo ni cambiar su tamaño, en inbox/ con el nombre indicado por
el archivo de instrucciones: a.png, e-i.png, o-u.png, f-v.png, cons.png,
ojos-medios.png y ojos-cerrados.png. No uses la última variante como nueva maestra.

El asistente recortará únicamente boca y ojos y los montará sobre la pose original.
Revisa cada imagen antes de seguir. Si cambia la cara o mueve los rasgos, rehace
esa variante. Los rectángulos de ajustes.json son una propuesta, no una garantía
de alineación. Se ajustan mirando la revisión ampliada.

La preparación no activa los recortes. Después de aprobar el conjunto, el asistente
los activa, revisa las diez poses y hace una prueba corta de movimiento.
Las imágenes solo se generan una vez; se reutilizan en todos los videos.
"""
    (folder / "LEEME.md").write_text(guide, encoding="utf-8")
    ok(f"{rel(folder)} · maestra, siete instrucciones y rectángulos de recorte")


def cmd_generar(a) -> None:
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        die("falta la clave de imágenes; también puedes usar `avatar gestos prompts` con ChatGPT")
    cmd_prompts(a)
    from openai import OpenAI
    from .imagenes import archivar
    names = list(GESTOS) if a.cual == "todos" else [a.cual]
    client = OpenAI()
    cfg = CONFIG["imagenes"]
    for name in names:
        dest = carpeta() / "inbox" / f"{name}.png"
        if dest.exists() and not a.rehacer:
            print(f"= {rel(dest)} ya existe")
            continue
        text = prompt(name) + (f" Additional correction: {a.correccion}" if a.correccion else "")
        print(f"… generando {name}", flush=True)
        try:
            with (carpeta() / "maestra.png").open("rb") as reference:
                result = client.images.edit(model=cfg["modelo"], image=reference, prompt=text,
                                            size="1024x1536", quality=cfg.get("calidad", "high"), n=1)
            data = base64.b64decode(result.data[0].b64_json)
            with Image.open(io.BytesIO(data)) as check:
                if check.size != (1024, 1536):
                    raise ValueError("la imagen generada cambió de tamaño")
                check.verify()
        except Exception:
            die(f"no se pudo generar {name}; revisa la conexión y el proveedor de imágenes")
        archivar(dest)
        dest.write_bytes(data)
        ok(rel(dest))


def rectangulo(values, size):
    if not isinstance(values, list) or len(values) != 4 or any(type(v) is not int for v in values):
        raise ValueError("cada recorte necesita cuatro números enteros: x, y, ancho y alto")
    x, y, w, h = values
    if min(x, y) < 0 or min(w, h) < 12 or x + w > size[0] or y + h > size[1]:
        raise ValueError("un rectángulo es demasiado pequeño o sale del lienzo")
    return x, y, x + w, y + h


def recortar(source, box, suavizado):
    im = source.crop(box).convert("RGBA")
    w, h = im.size
    inset = max(2, math.ceil(suavizado * 2))
    mask = Image.new("L", im.size)
    ImageDraw.Draw(mask).rounded_rectangle((inset, inset, w-inset-1, h-inset-1), radius=min(w,h)//4, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(suavizado))
    alpha = np.array(mask)
    alpha[:2] = alpha[-2:] = 0
    alpha[:, :2] = alpha[:, -2:] = 0
    im.putalpha(Image.fromarray(alpha))
    return im


def preparar() -> Path:
    master = maestra()
    manifest = read_json(MANIFEST, "prepara primero los anclajes")
    settings = read_json(carpeta() / "ajustes.json", "corre `avatar gestos prompts` primero")
    try:
        reference = read_json(carpeta() / "referencia.json", "exporta la referencia con `avatar gestos prompts`")
        if reference["maestra_sha256"] != hashlib.sha256((POSES / "neutral.png").read_bytes()).hexdigest():
            raise ValueError("la maestra cambió desde la exportación de referencia; revisa los gestos y exporta de nuevo")
        boxes = {"boca": rectangulo(settings["boca"], master.size),
                 **{side: rectangulo(settings["ojos"][side], master.size) for side in ("izq", "der")}}
        feather = settings.get("suavizado", 2)
        if type(feather) not in (int,float) or not math.isfinite(feather) or not 0 <= feather <= 5:
            raise ValueError("el suavizado debe estar entre 0 y 5")
        if any(min(box[2]-box[0], box[3]-box[1]) <= 2*max(2,math.ceil(feather*2))+2 for box in boxes.values()):
            raise ValueError("un recorte es demasiado pequeño para el suavizado elegido")
        sources = {}
        for name in GESTOS:
            with Image.open(carpeta() / "inbox" / f"{name}.png") as im:
                if im.size != master.size:
                    raise ValueError(f"{name}.png cambió el tamaño; debe coincidir exactamente con la maestra")
                sources[name] = im.convert("RGBA")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        die(f"no se pueden preparar los gestos: {exc}")
    # Cada revisión crea una versión nueva. Nunca sobrescribe piezas activas.
    n = 1
    while (LAYERS / f"gestos-v{n}").exists():
        n += 1
    dest = LAYERS / f"gestos-v{n}"
    dest.mkdir(parents=True)
    ref = manifest["poses"]["neutral"]
    descriptor = {"version": 1, "referencia": {"boca": ref["boca"], "ojos": ref["ojos"],
                  "maestra_sha256": hashlib.sha256((POSES/"neutral.png").read_bytes()).hexdigest()},
                  "bocas": {}, "ojos": {"izq": {}, "der": {}}}
    pieces = {}
    def save(name, source, box):
        im = recortar(source, box, feather)
        im.save(dest / f"{name}.png")
        frame = {"archivo": (dest / f"{name}.png").relative_to(PERSONAJE).as_posix(),
                 "x": box[0], "y": box[1], "ancho": im.width, "alto": im.height}
        pieces[name] = (im, box[:2])
        return frame
    for name, (key, _) in GESTOS.items():
        if key:
            descriptor["bocas"][key] = save(name, sources[name], boxes["boca"])
    for side in ("izq", "der"):
        for state, source in [("medio", "ojos-medios"), ("cerrado", "ojos-cerrados")]:
            descriptor["ojos"][side][state] = save(f"ojo-{side}-{state}", sources[source], boxes[side])
    validar(descriptor)
    write_json(dest / "recortes.json", descriptor)
    # La revisión se compone sobre la maestra; comprueba que el resto sea idéntico.
    states = [("Reposo / M B P", []), *[(key, [name]) for name,(key,_) in GESTOS.items() if key],
              ("Parpadeo medio", [f"ojo-{s}-medio" for s in ("izq","der")]),
              ("Ojos cerrados", [f"ojo-{s}-cerrado" for s in ("izq","der")]),
              ("Boca y ojos", ["a", "ojo-izq-cerrado", "ojo-der-cerrado"])]
    b = ref["boca"]
    cy = (b["y"] + (ref["ojos"]["izq"]["y"] + ref["ojos"]["der"]["y"]) / 2) / 2
    width = round(read_json(CARA)["boca"]["ancho"] * 2.7)
    crop = (round(b["x"]-width/2), round(cy-width/2), round(b["x"]-width/2)+width, round(cy-width/2)+width)
    sheet = Image.new("RGB", (1200, 1296), "#202633")
    draw = ImageDraw.Draw(sheet)
    for i,(label,names) in enumerate(states):
        image, support = master.copy(), Image.new("L",master.size)
        for name in names:
            im, pos = pieces[name]
            image.alpha_composite(im,pos)
            support.paste(im.getchannel("A"),pos)
        outside = np.array(support)==0
        if not np.array_equal(np.array(image)[outside],np.array(master)[outside]):
            die("la revisión modificó píxeles fuera de los recortes")
        bg = Image.new("RGBA", image.size, "#202633")
        bg.alpha_composite(image)
        x,y = i%3*400, i//3*432
        sheet.paste(bg.crop(crop).convert("RGB").resize((400,400),Image.Resampling.LANCZOS),(x,y+32))
        draw.text((x+12,y+10),label,fill="white")
    sheet.save(dest / "revision.png")
    write_json(carpeta() / "candidato.json", {"ruta": (dest / "recortes.json").relative_to(PERSONAJE).as_posix()})
    return dest


def cmd_preparar(a) -> None:
    dest = preparar()
    ok(f"{rel(dest / 'revision.png')} · revisa esta imagen antes de activar")


def guardar_sistema(sistema, face):
    cfg = read_json(ROOT / "avatar.json")
    cfg.setdefault("rostro", {})["sistema"] = sistema
    current = read_json(MANIFEST, "prepara primero los anclajes")
    updated = aplicar(current, face, cfg)  # valida antes de cambiar los archivos
    write_json(CARA, face)
    write_json(MANIFEST, updated)
    write_json(ROOT / "avatar.json", cfg)


def cmd_activar(a) -> None:
    if not a.aprobado:
        die("muestra primero revision.png y espera la aprobación; después usa --aprobado")
    candidate = read_json(carpeta() / "candidato.json", "prepara los gestos primero")
    face = read_json(CARA)
    face["recortes"] = candidate["ruta"]
    guardar_sistema("recortes", face)
    ok("recortes activados; revisa todas las poses con `avatar verificar` y una prueba corta de movimiento")


def cmd_usar(a) -> None:
    guardar_sistema(a.sistema, read_json(CARA))
    ok(f"sistema facial: {a.sistema} · los videos anteriores se actualizan al componer y renderizar otra vez")
