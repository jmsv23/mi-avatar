---
name: avatar-gestos
description: Permite elegir SVG o recortes de boca y ojos generados desde la maestra; prepara, revisa y activa piezas faciales reutilizables sin sustituir las poses originales.
---

# Boca y párpados: elegir y preparar

Lee esta skill completa. Requiere la pose neutral preparada, sus anclajes y la aprobación de la maestra.
Habla en español sencillo; tú ejecutas los comandos. No vuelvas a preguntar si el usuario ya eligió.

## 1. Elección

Ofrece una pregunta con dos opciones:

- **Formas dibujadas (SVG)**: no necesitan generar imágenes adicionales; adecuadas para cartoon plano.
- **Recortes de la maestra**: conservan mejor labios, sombras y pestañas de un dibujo detallado;
  necesitan siete ediciones y una revisión de alineación, hechas una sola vez.

Recomienda según el estilo, sin prometer que los recortes siempre se verán mejor.
Para SVG: `uv run avatar gestos usar svg`, luego `uv run avatar verificar`. Revisa y muestra la imagen.
Para recortes, sigue los pasos siguientes. El sistema elegido vive en `avatar.json → rostro.sistema`.

## 2. Preparar las referencias

```bash
uv run avatar gestos prompts
```

Se crea `personaje/gestos/maestra.png`: la pose neutral ya alineada, sobre verde.
También crea siete instrucciones en `personaje/gestos/prompts/` y rectángulos iniciales en
`personaje/gestos/ajustes.json`. Usa **siempre esa maestra** como referencia de cada edición.
No encadenes las variantes entre sí. No sustituyas las poses originales por las imágenes generadas.

Elige el mismo modo de imágenes que usa el proyecto:

- **ChatGPT**: abre `personaje/gestos/inbox/` por el usuario. Copia las instrucciones y pídele guardar
  cada imagen completa allí como `a.png`, `e-i.png`, `o-u.png`, `f-v.png`, `cons.png`,
  `ojos-medios.png`, `ojos-cerrados.png`. Lee cada imagen tú antes de seguir.
- **API**, si el usuario la ha elegido: `uv run avatar gestos generar todos`.
  Omite resultados existentes. Rehacer uno: `uv run avatar gestos generar o-u --rehacer --correccion "..."`.
- Si el asistente dispone de edición de imágenes integrada y el usuario desea usarla, sigue sus reglas,
  usa las mismas instrucciones y guarda cada resultado con esos nombres. No requiere cambiar de proveedor.

Cada imagen debe conservar exactamente el tamaño y la posición de los rasgos. Si mueve la cara,
cambia su tamaño o altera el estilo, rehace solo esa variante. No la estires para forzar el encaje.

## 3. Recortar y revisar

```bash
uv run avatar gestos preparar
```

Crea nueve piezas con transparencia en una **versión nueva** dentro de `personaje/layers/gestos-vN/`:
cinco bocas y cada ojo a medias y cerrado. Reposo y M/B/P conservan los labios originales;
ojos abiertos conservan los ojos originales. Nunca sobrescribe el conjunto activo.

Lee `revision.png` de esa carpeta y muéstrala al usuario. Verifica:

- Labios, piel y pestañas coinciden con el acabado de la maestra.
- Las formas A, E/I, O/U, F/V y consonantes son distinguibles y plausibles.
- No asoman labios, iris o pestañas originales debajo de los recortes.
- Los bordes no dejan parches visibles ni alcanzan nariz, cejas o cabello.

Los rectángulos iniciales son una estimación. Ajusta `personaje/gestos/ajustes.json` mirando
la cuadrícula de la pose neutral: boca y cada ojo usan `[x,y,ancho,alto]` en la imagen preparada.
Repite `gestos preparar` después de ajustar. La revisión se monta sobre la maestra original y comprueba
que los píxeles fuera de los recortes sean idénticos. Esto no sustituye la revisión visual.

## 4. Activar tras aprobación

Solo después de que el usuario vea y apruebe el conjunto:

```bash
uv run avatar gestos activar --aprobado
uv run avatar verificar
```

Revisa y muestra la hoja de todas las poses. Ajusta anclajes si hace falta; las poses inclinadas y las
que tienen manos cerca de la cara merecen especial atención. Una pose con `habla:false` conserva su boca;
`parpadeo:false` conserva sus ojos. No tapes las manos con un parche.

Con la aprobación para probar movimiento, usa una narración corta existente o pide una, sigue
`../avatar-video/SKILL.md` y revisa boca y parpadeo en movimiento. No mezcles por transparencia dos
bocas distintas: produce labios y dientes dobles. Los cambios de recorte dependen del tiempo del video.

## 5. Reutilización y cambios

`componer` copia automáticamente las piezas elegidas. No vuelve a generar imágenes.
`anclajes` conserva la referencia del conjunto al recalcular la cara.
Si faltan piezas o cambió la maestra, detén la producción y corrige el conjunto; no cambies a SVG en silencio.

Se puede alternar sin borrar las piezas:

```bash
uv run avatar gestos usar svg
uv run avatar gestos usar recortes
```

La segunda opción requiere un conjunto ya aprobado. Los videos antiguos no cambian hasta volver
a componerlos y renderizarlos. Las piezas permanecen en `personaje/` y no se incluyen en contribuciones al código.
