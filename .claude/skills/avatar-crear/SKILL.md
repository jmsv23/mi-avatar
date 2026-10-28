---
name: avatar-crear
description: Crea el avatar 2D animado del usuario a partir de sus fotos. Primero la hoja de personaje y la imagen maestra, después 10 poses (por API de OpenAI o pegando prompts en ChatGPT); luego recorta el fondo verde, revisa la consistencia, mide boca y ojos y verifica el lip-sync. Úsala cuando el usuario dice "crear mi avatar", "mi personaje" o "rehacer una pose", o cuando no existe personaje/manifest.json.
---

# Crear el avatar

Resultado: `personaje/manifest.json` + `personaje/poses/*.png`, listos para narrar videos.
Antes de empezar, revisa el estado: `uv run avatar doctor --rapido` y `ls personaje personaje/inbox`.
Si ya hay avances, retoma desde el primer paso que falte.

Modo de imágenes: `avatar.json → imagenes.proveedor` (`chatgpt` = el usuario pega los prompts; `api` = tú corres `avatar generar`).

## 1. Fotos y ficha del personaje

1. Abre la carpeta `personaje/` y pide 1 a 3 fotos **de frente, buena luz, cara visible**, guardadas como
   `foto1.jpg`, `foto2.jpg`… (sirven png, jpg o webp; si tiene HEIC del iPhone, que la exporte como JPG).
2. Mira las fotos (léelas con tu herramienta de imágenes).
3. Pregunta, una cosa a la vez:
   - **Estilo**: `plano` (cartoon plano tipo vector, el recomendado), `anime` (suave, estilo anime) o `comic` (contornos gruesos).
     Los tres son 2D con contorno, así la boca animada combina.
   - **Ropa**: la de la foto, o la de su marca (p. ej. "playera con mi color de marca").
4. Escribe `personaje/personaje.json`:

```json
{
  "nombre": "Ana",
  "estilo": "plano",
  "descripcion": "Adult woman in her 30s, shoulder-length wavy dark brown hair with side part, warm brown eyes, round black glasses, light olive skin, friendly smile, slim build.",
  "ropa": "Mustard yellow sweater over a white collared shirt, dark jeans."
}
```

`descripcion` y `ropa` van **en inglés** y son físicas y concretas: pelo, vello facial, lentes, tono de piel, complexión.
Esto fija la identidad en todos los prompts.

## 2. Hoja de personaje → maestra → poses

Orden obligatorio: **hoja** (de las fotos) → **maestra** `01-neutral` (de la hoja) → **poses 02–10** (de la maestra).
No avances sin la aprobación del usuario en la hoja y en la maestra.

**Modo API**

```bash
uv run avatar generar hoja                  # -> personaje/hoja-de-personaje.png
uv run avatar generar maestra               # -> personaje/inbox/01-neutral.png
uv run avatar generar poses                 # 02..10 (salta las que ya existen)
uv run avatar generar senalar --correccion "the index finger must point straight up"
```

Cada imagen tarda alrededor de un minuto. Una imagen regenerada mueve la anterior a `inbox/_descartadas/`.

**Modo ChatGPT**

```bash
uv run avatar prompts                       # -> personaje/prompts/*.md
```

Guía al usuario con `personaje/prompts/00-como-usar.md`: muéstrale **el texto del prompt** de cada paso
(copiado del archivo) y dile con qué nombre guardar la imagen y en qué carpeta (ábrela por él).
Todo va en **una sola conversación** de ChatGPT.

**Revisa cada imagen tú mismo** (léela) con este checklist y dile al usuario qué ves:

- Es el mismo personaje (cara, pelo, ropa, proporciones).
- **Boca cerrada**, sin dientes. Esto es crítico: la boca se anima aparte.
- Fondo verde plano, sin sombras ni piso. No hay verde en el personaje.
- Encuadre de cintura para arriba, centrado, la cabeza completa. Manos y codos dentro del cuadro.
- Las manos no tapan la boca ni los ojos (en `pensar` la mano puede tocar el mentón).
- En `saludo`, los dos ojos abiertos.

Si algo falla, regenera solo esa imagen con una corrección concreta, en inglés.

## 3. Recorte y consistencia

```bash
uv run avatar preparar
```

Abre `personaje/_revision/poses.png` (la hoja de contacto) y compara las poses entre sí:
cara, tamaño de la cabeza y colores deben coincidir. Atiende los avisos `toca el borde` y `cambio de escala grande`.
Una pose inconsistente se regenera; las demás se quedan.

## 4. Medir la cara (solo en la maestra)

```bash
uv run avatar cuadricula                    # -> personaje/_revision/cuadricula-neutral.png
```

La imagen es la cara ampliada con líneas cada 25 px; los números amarillos son coordenadas del PNG
(las líneas magenta caen cada 100). Lee la imagen y estima:

- `boca.x`, `boca.y`: el **centro de la línea donde se juntan los labios** (no el centro del bigote ni el de la barbilla).
- `boca.ancho`: la distancia de comisura a comisura, en px.
- `ojos.izq` / `ojos.der`: el centro del iris de cada ojo; izq y der son los **lados de la imagen**.
- `ojo.ancho` / `ojo.alto`: el tamaño de la abertura visible de un ojo (blanco + iris), en px.
- `vello_facial`: `true` si tiene bigote o barba encima de la boca.

Escribe `personaje/cara.json`:

```json
{
  "boca": {"x": 530, "y": 400, "ancho": 140},
  "ojos": {"izq": {"x": 472, "y": 293}, "der": {"x": 598, "y": 298}},
  "ojo": {"ancho": 76, "alto": 44},
  "vello_facial": true
}
```

Vuelve a correr `uv run avatar cuadricula`: ahora aparecen cruces rojas donde dijiste. Ajusta hasta que
caigan justo en su sitio. Para más precisión, haz zoom: `uv run avatar cuadricula --zona 450,350,160,100`
(x, y, ancho, alto; las líneas pasan a cada 10 px).

## 5. Anclajes en todas las poses

```bash
uv run avatar anclajes
```

Encuentra boca y ojos en cada pose comparándolas con la maestra. Si una pose sale con `← revisar`
(coincidencia baja: cabeza muy girada, guiño o una mano cerca), mídela a mano con `uv run avatar cuadricula <pose>`
y agrega la corrección en `cara.json`:

```json
"poses": {
  "pensar": {"boca": {"x": 488, "y": 387}, "rotacion": 11, "escala": 1.0,
             "ojos": {"izq": {"x": 439, "y": 265}, "der": {"x": 567, "y": 296}}}
}
```

- `rotacion`: la inclinación de la línea de labios en grados (positivo = la comisura derecha más baja).
- `escala`: el tamaño de la boca relativo a la maestra.
- Opcionales: `"parpadeo": false` si la pose tiene un ojo cerrado, y `"borrado_extra": "M 50 -6 L 70 -13"` para tapar una
  comisura dibujada que asoma fuera de la boca animada (trazo SVG en unidades de la boca).

## 6. Verificación final

```bash
uv run avatar verificar                     # -> personaje/_revision/verificacion.png
```

- Fila 1: la maestra con los 7 visemas (formas de boca) y el parpadeo.
- Filas siguientes: cada pose con la boca abierta en "A" y los ojos cerrados.

Revisa:
- La boca abierta queda sobre los labios, centrada y del ancho correcto.
- No asoman labios dibujados por los lados.
- Los párpados cubren los ojos completos.
- El color de piel de los párpados coincide.
- El bigote, si hay, se pinta encima de la boca.

Corrige `cara.json` y repite los pasos 5 y 6 hasta que esté bien. Enséñale la hoja al usuario y pide su aprobación.

## 7. Listo

Dile al usuario que su avatar quedó listo y que no hace falta volver a generarlo. Propón el primer video:
"¿Hacemos tu primer video? Puede ser una presentación de 20 segundos: quién eres y qué vas a compartir" → skill `avatar-video`.

## Rehacer una pose después

Regenera la imagen de esa pose, luego corre `preparar`, `anclajes` y `verificar`. Los videos ya hechos no cambian
hasta que se vuelvan a renderizar.
