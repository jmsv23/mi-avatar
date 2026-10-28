"""Hoja de verificación de boca y párpados, renderizada con el mismo avatar.js del video.

Fila 1: cara de la maestra con cada visema + parpadeo a medias y cerrado.
Fila 2+: cada pose con visema A y ojos cerrados (si algo flota fuera de lugar, el anclaje está mal).

Se arma como un mini proyecto HyperFrames en personaje/_revision/hoja/ y se captura con
`hyperframes snapshot` (usa el Chrome que trae HyperFrames, no hace falta tener Chrome instalado).
Salida: personaje/_revision/verificacion.png
"""
import json
import shutil

from .config import CONFIG, LAYERS, MANIFEST, MOTION, POSES, REVISION, die, ok, read_json, rel, run, hf

CELL = 300
COLS = 6


def cmd_verificar(a) -> None:
    manifest = read_json(MANIFEST, "corre `avatar anclajes` primero")
    hoja = REVISION / "hoja"
    shutil.rmtree(hoja, ignore_errors=True)
    (hoja / "assets").mkdir(parents=True)
    shutil.copytree(POSES, hoja / "assets" / "poses", ignore=shutil.ignore_patterns("_*"))
    if LAYERS.exists():
        shutil.copytree(LAYERS, hoja / "assets" / "layers")
    shutil.copy2(MOTION / "shared" / "avatar.js", hoja / "avatar.js")

    poses = list(manifest["poses"])
    master = manifest["poses"].get("neutral") or manifest["poses"][poses[0]]
    b = master["boca"]
    ojos = master["ojos"]
    face = round(140 * b["escala"] * 2.4)  # recorte cuadrado de la cara, proporcional al ancho de boca
    cy = (b["y"] + (ojos["izq"]["y"] + ojos["der"]["y"]) / 2) / 2
    fx, fy = round(b["x"] - face / 2), round(cy - face / 2)

    cells = [(poses[0] if "neutral" not in poses else "neutral", v, 0, v) for v in manifest["visemas"]]
    cells += [("neutral" if "neutral" in poses else poses[0], "REST", 0.5, "parpadeo ½"),
              ("neutral" if "neutral" in poses else poses[0], "REST", 1, "parpadeo")]
    while len(cells) % COLS:
        cells.append(None)
    cells += [(p, "A", 1, f"{p} · A") for p in poses]
    rows = (len(cells) + COLS - 1) // COLS
    W, Hh = COLS * CELL, rows * (CELL + 28)
    scale = CELL / face
    bg = CONFIG["marca"]["fondo"]
    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={Hh}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
body{{margin:0;background:#111}}
#root{{position:relative;width:100%;height:100%;overflow:hidden;background:#111;font:600 15px sans-serif;color:#fff}}
.cell{{position:absolute;width:{CELL}px;height:{CELL + 28}px;overflow:hidden;background:{bg}}}
.stage{{position:absolute;left:{-fx * scale}px;top:{-fy * scale}px;transform:scale({scale});transform-origin:0 0}}
.label{{position:absolute;left:0;right:0;bottom:0;height:28px;background:#000;padding:5px 8px;box-sizing:border-box}}
</style>
</head>
<body>
<div id="root" data-composition-id="hoja" data-start="0" data-duration="1" data-width="{W}" data-height="{Hh}"></div>
<script src="avatar.js"></script>
<script>
const manifest = {json.dumps(manifest, ensure_ascii=False)};
const cells = {json.dumps(cells, ensure_ascii=False)};
const root = document.getElementById("root");
cells.forEach((c, i) => {{
  if (!c) return;
  const [pose, viseme, lids, label] = c;
  const cell = document.createElement("div");
  cell.className = "cell";
  cell.style.left = (i % {COLS}) * {CELL} + "px";
  cell.style.top = Math.floor(i / {COLS}) * {CELL + 28} + "px";
  root.appendChild(cell);
  const st = document.createElement("div"); st.className = "stage"; cell.appendChild(st);
  const l = document.createElement("div"); l.className = "label"; l.textContent = label; cell.appendChild(l);
  AVATAR.create(st, manifest, {{ base: "assets/" }}).set({{ pose, viseme, lids }});
}});
window.__timelines["hoja"] = gsap.timeline({{ paused: true }});
</script>
</body>
</html>
"""
    (hoja / "index.html").write_text(html, encoding="utf-8")
    out = hoja / "_snap"
    run(hf("snapshot", ".", "--at", "0.5", "--no-end", "--keep", "-o", "_snap", "--describe", "false"),
        cwd=hoja, capture_output=True, text=True)
    pngs = sorted(out.glob("*.png"))
    if not pngs:
        die("hyperframes snapshot no produjo imagen (corre `avatar doctor`)")
    dest = REVISION / "verificacion.png"
    shutil.copy2(pngs[0], dest)
    ok(f"{rel(dest)} · {len(poses)} poses")
