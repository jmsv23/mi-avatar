"""personaje/inbox/NN-<pose>.png (fondo verde) -> personaje/poses/<pose>.png (RGBA normalizado).

1. Ajusta el lienzo a 1024x1536 (si el generador devolvió otro tamaño).
2. Recorta el verde con alpha suave y despill. El umbral se adapta al verde real del fondo.
3. Normaliza contra la maestra (01-neutral): mismo ancho de cabeza, misma altura de
   coronilla y cabeza centrada. La coronilla se busca en una franja central para que una
   mano levantada no se confunda con la cabeza.
4. Escribe poses/_metrics.json y la hoja de contacto _revision/poses.png.
"""
import re

import numpy as np
from PIL import Image, ImageDraw

from .config import CONFIG, INBOX, POSES, REVISION, H, W, die, ok, rel, write_json
from .prompts import POSE_IDS

MASTER = "01-neutral"
HEAD_PROBE = 0.1  # fracción del alto: fila debajo de la coronilla donde se mide el ancho de la cabeza
CENTER_X = W // 2


def fit_canvas(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    if img.size == (W, H):
        return img
    s = W / img.width
    img = img.resize((W, round(img.height * s)), Image.LANCZOS)
    if img.height >= H:  # demasiado alta: recorta abajo (la cadera)
        return img.crop((0, 0, W, H))
    canvas = Image.new("RGB", (W, H), img.getpixel((2, 2)))
    canvas.paste(img, (0, 0))
    return canvas


def key_green(img: Image.Image) -> tuple[np.ndarray, float]:
    a = np.asarray(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    greenness = g - np.maximum(r, b)
    border = np.concatenate([greenness[:8].ravel(), greenness[:, :8].ravel(), greenness[:, -8:].ravel()])
    g_bg = float(np.median(border))
    hi = float(np.clip(0.6 * g_bg, 60, 150))
    lo = hi * 0.27
    alpha = 1.0 - np.clip((greenness - lo) / (hi - lo), 0, 1)
    g2 = np.minimum(g, np.maximum(r, b))  # despill: el verde nunca supera al mayor de rojo/azul
    out = np.dstack([r, g2, b, alpha * 255]).round().clip(0, 255).astype(np.uint8)
    return out, g_bg


def head_metrics(rgba: np.ndarray, band: tuple[int, int] | None = None) -> dict:
    fg = rgba[..., 3] > 128
    x0, x1 = band or (0, W)
    ys = np.nonzero(fg[:, x0:x1].any(axis=1))[0]
    if not len(ys):
        die("no encontré al personaje (¿el fondo es verde?)")
    top = int(ys.min())
    mid = (x0 + x1) / 2
    widths, centers = [], []
    # mediana de varias filas: una sola fila es frágil (unas filas más abajo ya aparecen las orejas)
    for probe in range(top + int(H * HEAD_PROBE * 0.7), top + int(H * HEAD_PROBE * 1.1), 4):
        row = np.nonzero(fg[min(H - 1, probe)])[0]
        if not len(row):
            continue
        segs = np.split(row, np.nonzero(np.diff(row) > 1)[0] + 1)
        # el segmento de la cabeza es el que cruza la franja central (no la mano de al lado)
        span = min(segs, key=lambda s: 0 if s.min() <= mid <= s.max() else min(abs(s.min() - mid), abs(s.max() - mid)))
        widths.append(int(span.max() - span.min()))
        centers.append(float(span.min() + span.max()) / 2)
    return {"top": top, "head_w": int(np.median(widths)), "head_cx": float(np.median(centers))}


def edge_contact(rgba: np.ndarray) -> dict:
    fg = rgba[..., 3] > 128
    return {"izq": int(fg[:, 0].sum()), "der": int(fg[:, -1].sum()), "arriba": int(fg[0].sum())}


def normalize(rgba: np.ndarray, m: dict, ref: dict) -> tuple[np.ndarray, dict]:
    s = ref["head_w"] / m["head_w"]
    img = Image.fromarray(rgba, "RGBA")
    if abs(s - 1) > 0.005:
        img = img.resize((round(W * s), round(H * s)), Image.LANCZOS)
    else:
        s = 1.0
    dx = round(CENTER_X - m["head_cx"] * s)
    dy = round(ref["top"] - m["top"] * s)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(img, (dx, dy), img)
    out = np.asarray(canvas).copy()
    # si al escalar o mover queda hueco abajo, se estira la última fila (la cadera corta en el borde)
    filled = np.nonzero((out[..., 3] > 0).any(axis=1))[0].max()
    if filled < H - 1:
        out[filled + 1:] = out[filled]
    return out, {"escala": round(s, 4), "dx": dx, "dy": dy, "filas_estiradas": int(H - 1 - filled)}


def contact_sheet(ids: list[str]) -> None:
    cell_w, cell_h, cols = 256, 384, 5
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + 24)), CONFIG["marca"]["fondo"])
    d = ImageDraw.Draw(sheet)
    for i, pid in enumerate(ids):
        im = Image.open(POSES / f"{pid}.png").resize((cell_w, cell_h), Image.LANCZOS)
        x, y = (i % cols) * cell_w, (i // cols) * (cell_h + 24)
        sheet.paste(im, (x, y), im)
        d.rectangle((x, y + cell_h, x + cell_w, y + cell_h + 24), fill="#000000")
        d.text((x + 8, y + cell_h + 6), pid, fill="#ffffff")
    REVISION.mkdir(parents=True, exist_ok=True)
    sheet.save(REVISION / "poses.png")


def cmd_preparar(a) -> None:
    files = {p.stem: p for p in INBOX.glob("*.png") if re.match(r"\d\d-", p.name)}
    if MASTER not in files:
        die("falta la maestra personaje/inbox/01-neutral.png")
    POSES.mkdir(parents=True, exist_ok=True)
    keyed = {}
    for stem, p in sorted(files.items()):
        rgba, g_bg = key_green(fit_canvas(Image.open(p)))
        if g_bg < 80:
            print(f"! {p.name}: el fondo no parece verde (verdosidad {g_bg:.0f}); revisa el recorte")
        keyed[stem] = rgba
    ref = head_metrics(keyed[MASTER])
    band = (round(ref["head_cx"] - ref["head_w"] * 0.3), round(ref["head_cx"] + ref["head_w"] * 0.3))
    ref["head_cx"] = CENTER_X
    metrics, ids = {}, []
    for stem, rgba in keyed.items():
        pid = stem.split("-", 1)[1]
        m = head_metrics(rgba, band)
        out, t = normalize(rgba, m, ref)
        Image.fromarray(out, "RGBA").save(POSES / f"{pid}.png", optimize=True)
        e = edge_contact(rgba)
        metrics[pid] = {"fuente": f"inbox/{stem}.png", "medido": m, "transformacion": t, "toca_bordes": e}
        ids.append(pid)
        aviso = "  ! toca el borde (¿mano o codo cortado?)" if e["izq"] > 40 or e["der"] > 40 or e["arriba"] > 0 else ""
        aviso += "  ! cambio de escala grande: revisa" if abs(t["escala"] - 1) > 0.12 else ""
        print(f"  {pid:15s} escala={t['escala']} dx={t['dx']} dy={t['dy']}{aviso}")
    faltan = [p for p in POSE_IDS if p not in ids]
    write_json(POSES / "_metrics.json", {"referencia": ref, "poses": metrics})
    contact_sheet([p for p in POSE_IDS if p in ids] + [p for p in ids if p not in POSE_IDS])
    ok(f"{len(ids)} poses en {rel(POSES)}/ · hoja de contacto {rel(REVISION / 'poses.png')}")
    if faltan:
        print(f"  faltan: {', '.join(faltan)} (el avatar funciona con las que haya)")
