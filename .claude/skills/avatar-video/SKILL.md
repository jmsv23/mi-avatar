---
name: avatar-video
description: Produce un video narrado por el avatar del usuario. Parte de su grabación de voz, de un video suyo o de un guion (voz con ElevenLabs o Voicebox), transcribe con tiempos por palabra, propone escenas de motion graphics (títulos, listas, datos, citas, imágenes, clips) con el avatar como narrador y lip-sync, y renderiza el MP4. Úsala cuando el usuario dice "hacer un video", "tengo un audio" o "tengo un guion", con el avatar ya creado.
---

# Hacer un video

Requisito: existe `personaje/manifest.json` (si no, ve a la skill `avatar-crear`).
Cada video vive en `videos/<slug>/`. El slug es corto, en minúsculas y con guiones (p. ej. `presentacion`, `tip-01-precios`).

Respeta el sistema facial que ya eligió el usuario. `componer` incluye automáticamente sus recortes
cuando están activados, y comprueba que existan y pertenezcan a la maestra actual.
No generes gestos para cada video ni cambies a SVG si falta una pieza: recupera el conjunto aprobado
o sigue la skill `../avatar-gestos/SKILL.md` si el usuario pide cambiarlo.

## 1. Entrada

Pregunta qué tiene el usuario:

- **Una grabación** (audio o video suyo): abre `videos/` y pídele que deje ahí el archivo. Luego:
  `uv run avatar importar <slug> <ruta-del-archivo>`. Si era un video, queda como `original.mp4` para usar tramos en escenas.
- **Una idea o un guion**: ayúdale a escribirlo (60–90 s para redes ≈ 150–220 palabras, frases cortas, un gancho al inicio,
  una llamada a la acción al final). Guárdalo en `videos/<slug>/guion.txt`. Luego, según `avatar.json → voz.proveedor`:
  - `grabacion`: pídele que lea el guion en voz alta con el celular y deje el audio en `videos/`; después usa `importar`.
  - `elevenlabs` / `voicebox`: corre `uv run avatar voz <slug>`.

Escucha de calidad: si el audio tiene mucho ruido o eco, díselo antes de seguir. El lip-sync depende de una voz clara.

## 2. Transcripción

```bash
uv run avatar transcribir <slug>
```

Revisa el texto que sale. Si un nombre propio quedó mal escrito, no importa para el lip-sync; sí importa para los títulos
(escríbelos bien en el plan).

## 3. Proponer escenas (lo más importante)

Lee `videos/<slug>/transcripcion.json` y propón una tabla. Lee `referencias/plan.md` (en esta misma carpeta) para conocer los tipos de escena
y las reglas de ritmo. Ejemplo de tabla para el usuario:

| tiempo | lo que dice | escena | avatar | pose |
|---|---|---|---|---|
| 0.0–3.2 | "¿Sabías que…?" | avatar + texto "¿Sabías que…?" | completo | encogerse |
| 3.2–7.5 | "tres errores…" | lista: 3 errores | narrador | contar |
| 7.5–10 | "el 80 % de…" | dato 80 % | narrador | senalar |

Ajústala con el usuario en el chat. Cuando la apruebe, escribe `videos/<slug>/plan.json` (formato en `referencias/plan.md`).
Si el usuario no quiere decidir, usa solo `escenas` y deja que las poses salgan automáticas.

## 4. Construir y revisar

```bash
uv run avatar timeline <slug>               # poses, visemas, parpadeos
uv run avatar componer <slug>               # composición HyperFrames
uv run avatar check <slug>                  # debe dar 0 errores
uv run avatar render <slug> --calidad draft # borrador rápido
uv run avatar revisar <slug>                # -> videos/<slug>/_revision/frames.png
```

Mira `frames.png` antes de enseñárselo al usuario. Revisa:
- Ningún texto se corta ni tapa la cara del avatar.
- Las escenas cambian en el momento correcto.
- La pose corresponde a lo que dice.

Para ver el video completo, abre `videos/<slug>/video.draft.mp4` en su reproductor
(o `uv run avatar preview <slug>` para el editor de HyperFrames en el navegador).

Iteración: cambia `plan.json` y repite desde `timeline`. No hace falta regenerar audio ni transcripción.

## 5. Video final

```bash
uv run avatar render <slug>                 # calidad de avatar.json (standard); --calidad high para la mejor
```

Entrega `videos/<slug>/video.mp4` y abre la carpeta. Sugiere el siguiente video o una serie.

## Problemas comunes

- La boca no se mueve: el audio no tiene voz clara, o la transcripción salió vacía. Revisa `transcripcion.json`.
- El avatar habla tapándose la cara: hay una pose con `"habla": false` (pensar) en un tramo con voz. Cámbiala en `plan.json`.
- El render falla: corre `uv run avatar doctor` y, si falta el navegador, `uv run avatar doctor --arreglar`.
- Para mostrar un tramo del video original del usuario, usa una escena `video` con `"archivo": "original.mp4"`.
  Sin `desde`, el clip se sincroniza solo con el audio.
