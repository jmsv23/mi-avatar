"""avatar — crea tu avatar 2D animado y produce videos narrados por él.

Se corre desde la carpeta del proyecto con:  uv run avatar <comando>

Equipo
  doctor [--arreglar]             revisa Node, FFmpeg, uv, Chrome de HyperFrames y claves

Crear el avatar (una sola vez)
  prompts                         escribe los prompts para ChatGPT en personaje/prompts/
  generar <hoja|maestra|poses|pose> [--correccion "..."] [--rehacer]   imágenes por API de OpenAI
  preparar                        inbox (fondo verde) -> poses transparentes normalizadas + hoja de contacto
  cuadricula [pose] [--zona x,y,w,h]   recorte de la cara con cuadrícula para medir boca y ojos
  anclajes                        cara.json -> manifest.json (boca y ojos en todas las poses)
  verificar                       hoja con la boca y los párpados montados en cada pose
  gestos prompts                  instrucciones para crear bocas y párpados desde la maestra
  gestos generar [gesto|todos]     alternativa por API para las siete variantes
  gestos preparar                 recortes y hoja de revisión, sin activar
  gestos activar --aprobado       activa el conjunto revisado
  gestos usar <svg|recortes>       elige y guarda el sistema facial

Hacer un video (cada vez)
  importar <slug> <archivo>       tu grabación (audio o video) -> videos/<slug>/audio.wav
  voz <slug> [--proveedor elevenlabs|voicebox] [--force]   guion.txt -> audio.wav
  transcribir <slug> [--proveedor openai|whisperx]
  timeline <slug>                 transcripción + plan.json -> timeline.json
  componer <slug>                 composición HyperFrames
  check <slug>                    lint de la composición
  preview <slug>                  abre el video en HyperFrames Studio
  render <slug> [--calidad draft|standard|high]
  revisar <slug>                  hoja de frames del render
"""
import argparse
import sys


def main() -> None:
    for s in (sys.stdout, sys.stderr):  # consolas de Windows: que ✓ y acentos no truenen
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    from . import cara, componer, doctor, gestos, imagenes, preparar, prompts, timeline, transcribir, verificar, voz

    ap = argparse.ArgumentParser(prog="avatar", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor")
    p.add_argument("--arreglar", action="store_true", help="instala el navegador de HyperFrames")
    p.add_argument("--rapido", action="store_true", help="no consulta a HyperFrames")
    p.set_defaults(fn=doctor.cmd_doctor)

    sub.add_parser("prompts").set_defaults(fn=prompts.cmd_prompts)
    p = sub.add_parser("generar")
    p.add_argument("cual", help="hoja | maestra | poses | <pose>")
    p.add_argument("--correccion", help="corrección extra para esta imagen (en inglés funciona mejor)")
    p.add_argument("--rehacer", action="store_true", help="con 'poses': regenera también las que ya existen")
    p.set_defaults(fn=imagenes.cmd_generar)
    sub.add_parser("preparar").set_defaults(fn=preparar.cmd_preparar)
    p = sub.add_parser("cuadricula")
    p.add_argument("pose", nargs="?")
    p.add_argument("--zona", help="x,y,ancho,alto en px del PNG")
    p.set_defaults(fn=cara.cmd_cuadricula)
    sub.add_parser("anclajes").set_defaults(fn=cara.cmd_anclajes)
    sub.add_parser("verificar").set_defaults(fn=verificar.cmd_verificar)

    p = sub.add_parser("gestos", help="bocas y párpados recortados de la maestra")
    steps = p.add_subparsers(dest="paso", required=True)
    steps.add_parser("prompts").set_defaults(fn=gestos.cmd_prompts)
    q = steps.add_parser("generar")
    q.add_argument("cual", nargs="?", default="todos", choices=["todos", *gestos.GESTOS])
    q.add_argument("--rehacer", action="store_true")
    q.add_argument("--correccion")
    q.set_defaults(fn=gestos.cmd_generar)
    steps.add_parser("preparar").set_defaults(fn=gestos.cmd_preparar)
    q = steps.add_parser("activar")
    q.add_argument("--aprobado", action="store_true", help="el usuario ya revisó y aprobó el conjunto")
    q.set_defaults(fn=gestos.cmd_activar)
    q = steps.add_parser("usar")
    q.add_argument("sistema", choices=["svg", "recortes"])
    q.set_defaults(fn=gestos.cmd_usar)

    p = sub.add_parser("importar")
    p.add_argument("slug")
    p.add_argument("archivo")
    p.set_defaults(fn=voz.cmd_importar)
    p = sub.add_parser("voz")
    p.add_argument("slug")
    p.add_argument("--proveedor", choices=["elevenlabs", "voicebox"])
    p.add_argument("--force", action="store_true")
    p.add_argument("--instruct", help="dirección de voz (solo Voicebox con motores qwen)")
    p.set_defaults(fn=voz.cmd_voz)
    p = sub.add_parser("transcribir")
    p.add_argument("slug")
    p.add_argument("--proveedor", choices=["openai", "whisperx"])
    p.set_defaults(fn=transcribir.cmd_transcribir)
    for name, fn in [("timeline", timeline.cmd_timeline), ("componer", componer.cmd_componer),
                     ("check", componer.cmd_check), ("preview", componer.cmd_preview), ("revisar", componer.cmd_revisar)]:
        p = sub.add_parser(name)
        p.add_argument("slug")
        p.set_defaults(fn=fn)
    p = sub.add_parser("render")
    p.add_argument("slug")
    p.add_argument("--calidad", choices=["draft", "standard", "high"])
    p.set_defaults(fn=componer.cmd_render)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
