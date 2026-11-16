"""Anclajes de boca y ojos -> personaje/manifest.json + capas de vello facial.

El agente mide la maestra UNA vez mirando la cuadrícula (`avatar cuadricula`) y escribe personaje/cara.json:

  {
    "boca":  {"x": 530, "y": 400, "ancho": 140},          centro de la línea de labios cerrada; ancho comisura a comisura
    "ojos":  {"izq": {"x": 472, "y": 293}, "der": {"x": 598, "y": 298}},   centro de cada ojo (lados DE LA IMAGEN)
    "ojo":   {"ancho": 76, "alto": 44},                    tamaño de la abertura visible del ojo
    "vello_facial": true,                                  bigote/barba que debe pintarse encima de la boca animada
    "poses": {"saludo": {"boca": {"x":..,"y":..}, "ojos": {..}, "rotacion": 8, "escala": 0.9}}   correcciones opcionales
  }

En las demás poses boca y ojos se encuentran por template matching (correlación normalizada) contra la maestra.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from .config import CARA, LAYERS, MANIFEST, POSES, REVISION, die, ok, read_json, rel, write_json
from .prompts import POSES as CATALOGO

REF_MOUTH_W = 140  # ancho de boca del diseño de referencia de avatar.js (los visemas están en esas unidades)
REF_EYE = (76, 44)
SEARCH = 45
ROT_MIN = 2.0  # grados; menos que esto = cabeza derecha
MATCH_OK = 0.6

# Línea de labios relativa al ancla (unidades de referencia): parábola por las comisuras (±70, -13) y el centro (0, +5)
LIP_HALF_W, LIP_CENTER_Y, LIP_CORNER_Y = 70, 5, -13
MUSTACHE_BOX = (-88, -38, 88, 8)
THIN_PX = 2
MUSTACHE_LUMA = 90


def load(pose: str) -> np.ndarray:
    return np.asarray(Image.open(POSES / f"{pose}.png").convert("RGBA")).astype(np.float32)


def luma(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def crop(img: np.ndarray, cx: int, cy: int, box) -> np.ndarray:
    x0, y0, x1, y1 = box
    return img[cy + y0: cy + y1, cx + x0: cx + x1]


def scaled(box, s: float) -> tuple:
    return tuple(round(v * s) for v in box)


def match(img_l: np.ndarray, tpl: np.ndarray, cx: int, cy: int, box) -> tuple[int, int, float]:
    t = tpl - tpl.mean()
    tn = np.sqrt((t * t).sum())
    best = (-2.0, 0, 0)
    for dy in range(-SEARCH, SEARCH + 1, 1):
        for dx in range(-SEARCH, SEARCH + 1, 1):
            p = crop(img_l, cx + dx, cy + dy, box)
            if p.shape != tpl.shape:
                continue
            p = p - p.mean()
            score = float((p * t).sum() / (np.sqrt((p * p).sum()) * tn + 1e-6))
            if score > best[0]:
                best = (score, dx, dy)
    return cx + best[1], cy + best[2], round(best[0], 3)


def eye_angle(izq, der) -> float:
    return math.degrees(math.atan2(der[1] - izq[1], der[0] - izq[0]))


def match_rotated(img, tpl, guess, box, rot, pivot) -> tuple[int, int, float]:
    """Endereza la pose (gira -rot alrededor de pivot), busca ahí y devuelve el punto en la pose original."""
    upright = Image.fromarray(img.astype(np.uint8), "RGBA").rotate(rot, resample=Image.BICUBIC, center=pivot)
    ux, uy, score = match(luma(np.asarray(upright).astype(np.float32)), tpl, *guess, box)
    a = math.radians(rot)
    dx, dy = ux - pivot[0], uy - pivot[1]
    return round(pivot[0] + dx * math.cos(a) - dy * math.sin(a)), round(pivot[1] + dx * math.sin(a) + dy * math.cos(a)), score


def _shift_all(m, r, op):
    out = m.copy()
    p = np.pad(m, r, constant_values=op is np.logical_and)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = op(out, p[r + dy: r + dy + m.shape[0], r + dx: r + dx + m.shape[1]])
    return out


def lip_y(dx):
    k = np.clip(np.abs(dx) / LIP_HALF_W, 0, 1.4)
    return LIP_CENTER_Y + (LIP_CORNER_Y - LIP_CENTER_Y) * k * k


def mustache_layer(img, mx, my, rot, s) -> tuple[Image.Image, list[int], list[int]]:
    """Píxeles de pelo arriba de la línea de labios, en el marco de la boca (sin rotar). Vacía si no hay vello."""
    x0, y0, x1, y1 = scaled(MUSTACHE_BOX, s)
    if rot:
        img = np.asarray(Image.fromarray(img.astype(np.uint8), "RGBA").rotate(rot, resample=Image.BICUBIC, center=(mx, my))).astype(np.float32)
    patch = crop(img, mx, my, (x0, y0, x1, y1))
    ys, xs = np.mgrid[y0:y1, x0:x1] / s
    hair = (luma(patch) < MUSTACHE_LUMA) & (ys < lip_y(xs) - 5) & (patch[..., 3] > 128)
    thick = _shift_all(_shift_all(hair, THIN_PX, np.logical_and), THIN_PX, np.logical_or)  # quita trazos finos (labio)
    hair &= _shift_all(thick, 2, np.logical_or)
    out = patch.copy().astype(np.uint8)
    out[..., 3] = np.where(hair, 255, 0).astype(np.uint8)
    return Image.fromarray(out, "RGBA"), [x0, y0], [x1 - x0, y1 - y0]


def hexc(c) -> str:
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, v))) for v in c)


def lid_color(img, ex, ey, rx, ry) -> str:
    """Piel alrededor del ojo: anillo en los lados y abajo (arriba están las cejas)."""
    ys, xs = np.mgrid[-2 * ry: 2 * ry + 1, -int(1.45 * rx): int(1.45 * rx) + 1]
    r = (xs / (rx * 1.2)) ** 2 + (ys / (ry * 1.27)) ** 2
    ring = (r > 1.0) & (r < 1.6) & (ys > -ry * 0.35)
    px = img[ey - 2 * ry: ey + 2 * ry + 1, ex - int(1.45 * rx): ex + int(1.45 * rx) + 1, :3][ring]
    light = px[luma(px) > np.percentile(luma(px), 40)]
    return hexc(np.median(light if len(light) else px, axis=0))


def skin_near_mouth(img, mx, my, rot, s) -> np.ndarray:
    a = math.radians(rot)
    samples = []
    for dx, dy in [(-45, 22), (45, 22), (-30, 26), (30, 26), (-60, 8), (60, 8)]:
        dx, dy = dx * s, dy * s
        x = round(mx + dx * math.cos(a) - dy * math.sin(a))
        y = round(my + dx * math.sin(a) + dy * math.cos(a))
        w = img[y - 3: y + 4, x - 3: x + 4, :3].reshape(-1, 3)
        samples.append(w)
    px = np.concatenate(samples)
    return px[luma(px) >= np.percentile(luma(px), 50)].mean(0)


def line_color(img, mx, my, s) -> str:
    """Color del contorno del dibujo: los píxeles más oscuros alrededor de la boca."""
    p = crop(img, mx, my, scaled((-70, -10, 70, 12), s)).reshape(-1, 4)
    p = p[p[:, 3] > 200][:, :3]
    dark = p[luma(p) <= np.percentile(luma(p), 4)]
    return hexc(np.median(dark, axis=0) if len(dark) else (36, 19, 12))


def cara() -> dict:
    c = read_json(CARA, "mídela con `avatar cuadricula` (skill avatar-crear, paso de la cara)")
    for k in ("boca", "ojos", "ojo"):
        if k not in c:
            die(f"cara.json: falta '{k}'")
    return c


def cmd_anclajes(a) -> None:
    c = cara()
    LAYERS.mkdir(parents=True, exist_ok=True)
    s = c["boca"].get("ancho", REF_MOUTH_W) / REF_MOUTH_W
    rx, ry = c["ojo"]["ancho"] / 2, c["ojo"]["alto"] / 2
    es = rx / (REF_EYE[0] / 2)
    mouth_box = scaled((-90, -35, 90, 45), s)
    eye_box = scaled((-45, -30, 45, 28), es)
    m_mouth = (c["boca"]["x"], c["boca"]["y"])
    m_eyes = {k: (v["x"], v["y"]) for k, v in c["ojos"].items()}
    m_angle = eye_angle(m_eyes["izq"], m_eyes["der"])
    eye_mid = ((m_eyes["izq"][0] + m_eyes["der"][0]) / 2, (m_eyes["izq"][1] + m_eyes["der"][1]) / 2)

    master = load("neutral")
    ml = luma(master)
    mouth_tpl = crop(ml, *m_mouth, mouth_box)
    eye_tpls = {k: crop(ml, *v, eye_box) for k, v in m_eyes.items()}
    skin = skin_near_mouth(master, *m_mouth, 0, s)
    lip = skin * 0.65 + np.array([224, 80, 90]) * 0.35
    colores = {"labio": hexc(lip), "linea": line_color(master, *m_mouth, s),
               "interior": "#3b1110", "lengua": "#d0525a", "dientes": "#fbf6ef"}

    poses, revisar = {}, []
    for num, pid, habla, desc, _ in CATALOGO + [("99", p.stem, True, "pose extra", "") for p in sorted(POSES.glob("*.png"))
                                                if p.stem not in {x[1] for x in CATALOGO}]:
        if not (POSES / f"{pid}.png").exists():
            continue
        img = load(pid)
        il = luma(img)
        manual = c.get("poses", {}).get(pid, {})
        eyes = {}
        for k, (ex0, ey0) in m_eyes.items():
            if k in manual.get("ojos", {}):
                ex, ey, sc = manual["ojos"][k]["x"], manual["ojos"][k]["y"], "manual"
            else:
                ex, ey, sc = match(il, eye_tpls[k], ex0, ey0, eye_box)
            eyes[k] = {"x": ex, "y": ey, "piel": lid_color(img, ex, ey, round(rx), round(ry)), "match": sc}
        rot = round(eye_angle((eyes["izq"]["x"], eyes["izq"]["y"]), (eyes["der"]["x"], eyes["der"]["y"])) - m_angle, 1)
        escala = manual.get("escala", 1.0)
        if "rotacion" in manual:
            rot = manual["rotacion"]
        if "boca" in manual:
            mx, my, ms = manual["boca"]["x"], manual["boca"]["y"], "manual"
        elif abs(rot) < ROT_MIN:
            rot = 0.0 if "rotacion" not in manual else rot
            mx, my, ms = match(il, mouth_tpl, *m_mouth, mouth_box)
        else:
            pivot = ((eyes["izq"]["x"] + eyes["der"]["x"]) / 2, (eyes["izq"]["y"] + eyes["der"]["y"]) / 2)
            guess = (round(pivot[0] + m_mouth[0] - eye_mid[0]), round(pivot[1] + m_mouth[1] - eye_mid[1]))
            mx, my, ms = match_rotated(img, mouth_tpl, guess, mouth_box, rot, pivot)
        entry = {
            "habla": habla, "descripcion": desc, "archivo": f"poses/{pid}.png",
            "boca": {"x": mx, "y": my, "escala": round(s * escala, 4), "rotacion": rot, "match": ms},
            "piel_boca": hexc(skin_near_mouth(img, mx, my, rot, s * escala)),
            "ojos": eyes,
        }
        if manual.get("borrado_extra"):
            entry["borrado_extra"] = manual["borrado_extra"]
        if manual.get("parpadeo") is False:
            entry["parpadeo"] = False
        if c.get("vello_facial", True):
            layer, pos, size = mustache_layer(img, mx, my, rot, s * escala)
            layer.save(LAYERS / f"{pid}-vello.png", optimize=True)
            entry["vello"] = {"archivo": f"layers/{pid}-vello.png", "x": pos[0], "y": pos[1], "ancho": size[0], "alto": size[1]}
        poses[pid] = entry
        scores = [v for v in [ms] + [e["match"] for e in eyes.values()] if isinstance(v, float)]
        flag = "  ← revisar" if scores and min(scores) < MATCH_OK else ""
        if flag:
            revisar.append(pid)
        print(f"  {pid:15s} rot={rot:5.1f} boca=({mx},{my}) m={ms}  ojos=" +
              " ".join(f"{k}({e['x']},{e['y']}) m={e['match']}" for k, e in eyes.items()) + flag)

    from .rostro import aplicar
    write_json(MANIFEST, aplicar({
        "version": 2,
        "lienzo": {"ancho": 1024, "alto": 1536},
        "visemas": ["REST", "A", "E_I", "O_U", "MBP", "FV", "CONS"],
        "ojo": {"rx": rx, "ry": ry},
        "colores": colores,
        "nota": "Anclajes en píxeles del PNG normalizado. 'izq'/'der' = lados de la imagen. match < 0.6 = revisar.",
        "poses": poses,
    }, c))
    ok(f"{rel(MANIFEST)} · {len(poses)} poses")
    if revisar:
        print(f"! revisa a mano (match bajo): {', '.join(revisar)} → `avatar cuadricula <pose>` y corrige en cara.json → poses")


def cmd_cuadricula(a) -> None:
    """Recorte ampliado de la cara con cuadrícula en coordenadas del PNG, para que el agente mida a ojo."""
    pose = a.pose or "neutral"
    path = POSES / f"{pose}.png"
    if not path.exists():
        die(f"no existe {rel(path)} (corre `avatar preparar`)")
    img = Image.open(path).convert("RGBA")
    if a.zona:
        x, y, w, h = (int(v) for v in a.zona.split(","))
    else:
        met = read_json(POSES / "_metrics.json")["referencia"]
        hw = met["head_w"]
        x, y, w, h = round(512 - hw * 0.8), max(0, met["top"] - 20), round(hw * 1.6), round(hw * 1.5)
    zoom = max(1, min(4, round(900 / max(w, h))))
    bg = Image.new("RGBA", img.size, (40, 40, 48, 255))
    bg.alpha_composite(img)
    face = bg.crop((x, y, x + w, y + h)).resize((w * zoom, h * zoom), Image.NEAREST)
    d = ImageDraw.Draw(face)
    step = 10 if w <= 220 else 25
    for gx in range((x // step + 1) * step, x + w, step):
        major = gx % 100 == 0
        d.line([((gx - x) * zoom, 0), ((gx - x) * zoom, h * zoom)], fill=(255, 0, 255, 255) if major else (0, 255, 255, 110), width=2 if major else 1)
        if major or step == 10 and gx % 50 == 0:
            d.text(((gx - x) * zoom + 3, 3), str(gx), fill=(255, 255, 0, 255))
    for gy in range((y // step + 1) * step, y + h, step):
        major = gy % 100 == 0
        d.line([(0, (gy - y) * zoom), (w * zoom, (gy - y) * zoom)], fill=(255, 0, 255, 255) if major else (0, 255, 255, 110), width=2 if major else 1)
        if major or step == 10 and gy % 50 == 0:
            d.text((3, (gy - y) * zoom + 3), str(gy), fill=(255, 255, 0, 255))
    # marca los anclajes actuales (del manifiesto si existe la pose, si no de cara.json)
    marks = []
    if MANIFEST.exists() and pose in read_json(MANIFEST)["poses"]:
        p = read_json(MANIFEST)["poses"][pose]
        marks = [(p["boca"]["x"], p["boca"]["y"], "boca")] + [(e["x"], e["y"], k) for k, e in p["ojos"].items()]
    elif CARA.exists() and pose == "neutral":
        c = read_json(CARA)
        marks = [(c["boca"]["x"], c["boca"]["y"], "boca")] + [(e["x"], e["y"], k) for k, e in c["ojos"].items()]
    for mx, my, label in marks:
        px, py = (mx - x) * zoom, (my - y) * zoom
        d.line([(px - 12, py), (px + 12, py)], fill=(255, 30, 30, 255), width=3)
        d.line([(px, py - 12), (px, py + 12)], fill=(255, 30, 30, 255), width=3)
        d.text((px + 8, py + 6), label, fill=(255, 60, 60, 255))
    REVISION.mkdir(parents=True, exist_ok=True)
    out = REVISION / f"cuadricula-{pose}.png"
    face.convert("RGB").save(out)
    ok(f"{rel(out)} · zona x={x} y={y} {w}x{h} · zoom {zoom}x · líneas cada {step}px (magenta = cada 100)")
