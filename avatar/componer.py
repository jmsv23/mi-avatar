"""timeline.json -> composición HyperFrames (motion/<slug>.html) y render.

  componer <slug>   copia avatar, audio y medios a motion/assets/ y escribe la composición del video
                    (motion/_composiciones/<slug>.html; motion/index.html es la copia activa que ven preview y render)
  check <slug>      hyperframes lint de la composición
  preview <slug>    abre HyperFrames Studio en el navegador para ver el video antes de renderizar
  render <slug>     MP4 -> videos/<slug>/video.mp4  (--calidad draft|standard|high)
  revisar <slug>    hoja de contacto del render -> videos/<slug>/_revision/frames.png
"""
import json
import shutil
import subprocess

from .config import (CONFIG, LAYERS, MANIFEST, MOTION, POSES, die, ffmpeg, ffprobe, hf, lienzo, ok, read_json,
                     rel, run, video_dir)

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{slug}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script src="shared/avatar.js"></script>
<script src="shared/avatar-player.js"></script>
<script src="shared/escenas.js"></script>
<script src="assets/avatar/manifest.js"></script>
<script src="assets/videos/{slug}/timeline.js"></script>
<style>
@font-face {{ font-family: "Montserrat"; src: url("assets/fonts/Montserrat.ttf") format("truetype"); font-weight: 100 900; }}
body {{ margin: 0; background: {fondo}; }}
#root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: {fondo}; font-family: "Montserrat", sans-serif; color: var(--texto); }}
.bg {{ position: absolute; inset: 0; background: radial-gradient(120% 80% at 50% 30%, color-mix(in srgb, var(--fondo), white 14%) 0%, var(--fondo) 45%, color-mix(in srgb, var(--fondo), black 22%) 100%); }}
.graficos {{ position: absolute; inset: 0; }}
.sc {{ position: absolute; display: flex; flex-direction: column; justify-content: center; gap: 28px; }}
.sc-avatar {{ justify-content: flex-start; }}
.title {{ font-weight: 900; line-height: 1.08; letter-spacing: -0.01em; text-shadow: 0 6px 24px rgba(0,0,0,.22); }}
.title .w {{ display: inline-block; }}
.title.small {{ text-align: center; }}
.bar {{ width: 220px; height: 16px; border-radius: 8px; background: var(--acento); transform-origin: 0 50%; }}
.sub {{ font-weight: 600; line-height: 1.2; opacity: .95; }}
.list-title {{ margin-bottom: 8px; }}
.item {{ display: flex; align-items: center; gap: 28px; font-weight: 700; line-height: 1.15; }}
.item .num {{ flex: none; width: 1.5em; height: 1.5em; border-radius: 50%; background: var(--acento); color: var(--fondo); display: grid; place-items: center; font-weight: 900; }}
.num-big {{ font-weight: 900; line-height: 1; color: var(--acento); text-shadow: 0 8px 30px rgba(0,0,0,.25); transform-origin: 0 50%; }}
.quote-mark {{ font-size: 220px; line-height: .6; font-weight: 900; color: var(--acento); height: 110px; }}
.quote {{ font-weight: 700; line-height: 1.18; }}
.author {{ font-size: 40px; color: var(--acento); }}
.card {{ position: relative; flex: 1; border-radius: 28px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,.35); }}
.card img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.sc-imagen {{ justify-content: flex-start; }}
.sc-video {{ justify-content: flex-start; }}
.caption {{ font-weight: 900; line-height: 1.12; }}
.caption .hl {{ display: inline; background: var(--acento); color: #111; padding: 0.05em 0.3em; box-decoration-break: clone; -webkit-box-decoration-break: clone; border-radius: 0.15em; }}
.sc-imagen .caption, .sc-video .caption {{ position: relative; z-index: 2; margin-top: 10px; }}
.vwrap {{ position: absolute; border-radius: 28px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,.35); background: #000; }}
.vwrap.full {{ border-radius: 0; box-shadow: none; }}
.vwrap video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.avatar-place {{ position: absolute; left: 0; top: 0; width: 1024px; height: 1536px; transform-origin: 0 0; }}
.avatar-body {{ position: absolute; left: 0; top: 0; width: 1024px; height: 1536px; transform-origin: 50% 100%; }}
.sparks {{ position: absolute; left: 190px; top: 40px; width: 30px; height: 90px; transform-origin: 50% 300%; }}
.sparks i {{ position: absolute; left: 0; top: 0; width: 22px; height: 64px; border-radius: 11px; background: var(--acento); transform-origin: 50% 330%; }}
</style>
</head>
<body>
<div id="root" data-composition-id="{cid}" data-start="0" data-duration="{dur}" data-width="{W}" data-height="{H}" data-fps="{fps}">
  <div class="bg"></div>
{videos}
  <div class="graficos"></div>
  <div class="avatar-place">
    <div class="sparks"><i style="rotate:-62deg"></i><i style="rotate:-25deg"></i><i style="rotate:12deg"></i></div>
    <div class="avatar-body"><div class="avatar-stage"></div></div>
  </div>
  <audio id="{cid}-vo" src="assets/videos/{slug}/audio.wav" data-start="0" data-duration="{dur}" data-track-index="9"></audio>
</div>
<script>
  (function () {{
    const root = document.getElementById("root");
    const render = ESCENAS.mount(root, {{
      manifest: window.AVATAR_MANIFEST, timeline: window.AVATAR_TIMELINES["{slug}"], marca: {marca},
      ancho: {W}, alto: {H}, base: "assets/avatar/",
    }});
    const tl = gsap.timeline({{ paused: true }});
    ESCENAS.drive(tl, render, {dur});
    window.__timelines["{cid}"] = tl;
  }})();
</script>
</body>
</html>
"""

VIDEO_TAG = ('  <div class="vwrap" data-vwrap="{i}"><video id="{cid}-v{i}" class="clip" src="{src}" muted '
             'data-start="{t0}" data-duration="{d}" data-media-start="{desde}" data-track-index="{track}"></video></div>')


def cid(slug: str) -> str:
    return f"av-{slug}"


def sync_avatar() -> None:
    """personaje/{poses,layers,manifest.json} -> motion/assets/avatar/ (el render solo ve motion/)."""
    from .rostro import actual
    manifest = actual(read_json(MANIFEST, "el avatar no está listo (skill avatar-crear)"))
    dest = MOTION / "assets" / "avatar"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(POSES, dest / "poses", ignore=shutil.ignore_patterns("_*"))
    if LAYERS.exists():
        shutil.copytree(LAYERS, dest / "layers")
    (dest / "manifest.js").write_text(f"window.AVATAR_MANIFEST = {json.dumps(manifest, ensure_ascii=False)};\n", encoding="utf-8")


def page(slug: str, tl: dict, videos: str) -> str:
    W, H, _ = lienzo()
    return PAGE.format(slug=slug, cid=cid(slug), dur=tl["duracion"], W=W, H=H, fps=CONFIG["render"]["fps"],
                       lang=tl.get("idioma", "es"), fondo=CONFIG["marca"]["fondo"], videos=videos,
                       marca=json.dumps(CONFIG["marca"]))


def cmd_componer(a) -> None:
    d = video_dir(a.slug)
    tl = read_json(d / "timeline.json", f"corre `avatar timeline {a.slug}`")
    sync_avatar()
    vdest = MOTION / "assets" / "videos" / a.slug
    shutil.rmtree(vdest, ignore_errors=True)
    vdest.mkdir(parents=True)
    shutil.copy2(d / tl["audio"], vdest / "audio.wav")
    videos = []
    for i, sc in enumerate(tl["escenas"]):
        if sc["tipo"] in ("imagen", "video"):
            src = d / sc["archivo"]
            name = f"{i:02d}-{src.name}"
            shutil.copy2(src, vdest / name)
            sc["_src"] = f"assets/videos/{a.slug}/{name}"
        if sc["tipo"] == "video":
            desde = sc.get("desde", sc["t0"] if sc["archivo"] == "original.mp4" else 0)
            videos.append(VIDEO_TAG.format(i=i, cid=cid(a.slug), src=sc["_src"], t0=sc["t0"],
                                           d=round(sc["t1"] - sc["t0"], 3), desde=desde, track=2 + i % 2))
    (vdest / "timeline.js").write_text(
        "window.AVATAR_TIMELINES = window.AVATAR_TIMELINES || {};\n"
        f"window.AVATAR_TIMELINES[{json.dumps(a.slug)}] = {json.dumps(tl, ensure_ascii=False)};\n", encoding="utf-8")
    html = page(a.slug, tl, "\n".join(videos))
    comp = MOTION / "_composiciones" / f"{a.slug}.html"
    comp.parent.mkdir(exist_ok=True)
    comp.write_text(html, encoding="utf-8")
    (MOTION / "index.html").write_text(html, encoding="utf-8")
    ok(f"{rel(comp)} · {tl['duracion']} s · {len(tl['escenas'])} escenas (index.html = {a.slug})")


def ensure_index(slug: str) -> None:
    """HyperFrames admite una sola composición raíz por carpeta: index.html es el video activo."""
    comp = MOTION / "_composiciones" / f"{slug}.html"
    if not comp.exists():
        die(f"falta {rel(comp)} (corre `avatar componer {slug}`)")
    shutil.copy2(comp, MOTION / "index.html")


def cmd_check(a) -> None:
    ensure_index(a.slug)
    r = subprocess.run(hf("lint", "--json"), cwd=MOTION, capture_output=True, text=True, encoding="utf-8")
    try:
        res = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        die(f"no pude leer la salida de lint:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    found = res.get("findings", [])
    errs = [f for f in found if f.get("severity") == "error"]
    print(f"{'✓' if not errs else '✗'} {a.slug}: {len(errs)} errores, {len(found) - len(errs)} avisos")
    for f in found:
        print(f"  [{f.get('severity')}] {f.get('code')}: {f.get('message', '')[:220]}")
    if errs:
        raise SystemExit(1)


def cmd_preview(a) -> None:
    ensure_index(a.slug)
    run(hf("preview", "--background"), cwd=MOTION)


def cmd_render(a) -> None:
    d = video_dir(a.slug)
    ensure_index(a.slug)
    tl = read_json(d / "timeline.json")
    quality = a.calidad or CONFIG["render"]["calidad"]
    draft = quality == "draft"
    out = MOTION / "renders" / f"{a.slug}{'.draft' if draft else ''}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"… {a.slug}: render {quality} ({tl['duracion']} s). Puede tardar unos minutos.", flush=True)
    r = subprocess.run(hf("render", "-o", out.relative_to(MOTION).as_posix(), "--quality", quality, "--quiet"),
                       cwd=MOTION)
    if r.returncode:
        die("falló el render (corre `avatar doctor`)")
    probe = subprocess.run([ffprobe(), "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True).stdout.split()
    if "audio" not in probe:
        die(f"el MP4 salió sin audio ({rel(out)})")
    dest = d / f"video{'.draft' if draft else ''}.mp4"
    shutil.copy2(out, dest)
    ok(rel(dest))


def cmd_revisar(a) -> None:
    d = video_dir(a.slug)
    src = next((p for p in (d / "video.mp4", d / "video.draft.mp4") if p.exists()), None)
    if not src:
        die(f"{a.slug}: no hay render")
    tl = read_json(d / "timeline.json")
    rev = d / "_revision"
    shutil.rmtree(rev, ignore_errors=True)
    rev.mkdir()
    # un frame poco después de cada escena y cada cambio de pose (máx. 12)
    marks = []
    for x in sorted(round(min(x + 0.7, tl["duracion"] - 0.1), 2) for x in [e["t0"] for e in tl["escenas"]] + [p["t"] for p in tl["poses"]]):
        if not marks or x - marks[-1] > 0.6:  # escena y pose que cambian casi juntas: un solo frame
            marks.append(x)
    times = marks if len(marks) <= 12 else [marks[round(i * (len(marks) - 1) / 11)] for i in range(12)]
    for i, t in enumerate(times):
        run([ffmpeg(), "-v", "error", "-ss", t, "-i", src, "-frames:v", "1", "-vf", "scale=270:-1", rev / f"f{i:02d}.png"])
    cols = 6
    run([ffmpeg(), "-v", "error", "-y", "-i", rev / "f%02d.png", "-vf",
         f"tile={cols}x{(len(times) + cols - 1) // cols}", "-frames:v", "1", rev / "frames.png"])
    for p in rev.glob("f??.png"):
        p.unlink()
    ok(f"{rel(rev / 'frames.png')} · frames en " + ", ".join(f"{t:.1f}" for t in times))
