# Avatar Studio

**Crea tu avatar animado y haz videos para tu marca, narrados por él.**
No necesitas saber programar: tu asistente de IA (Claude o Codex) hace todo el trabajo técnico y te guía paso a paso.

- Tu avatar se crea **a partir de tus fotos**, en estilo cartoon.
- **Habla con tu voz**, con la boca sincronizada.
- Hace gestos: señala, cuenta con los dedos, saluda…
- Tus videos llevan títulos, listas, cifras e imágenes animadas, y tu avatar los narra.
- Formato vertical (TikTok, Reels, Shorts), horizontal (YouTube) o cuadrado.

## Empieza en 4 pasos

1. **Instala tu asistente**: [Claude Desktop](https://claude.ai/download) (plan Pro o superior; usa la pestaña **Code**)
   o [Codex](https://openai.com/codex) (incluido en ChatGPT Plus).
2. **Descarga este proyecto**: botón verde **Code → Download ZIP** y descomprímelo donde quieras
   (por ejemplo, en Documentos).
3. **Abre la carpeta en tu asistente**: en Claude Desktop, pestaña **Code** → elige la carpeta `avatar-studio`.
   En Codex, abre la carpeta como proyecto.
4. **Escribe:** `Quiero crear mi avatar`

Tu asistente instala lo necesario (te pedirá permiso), te pide tus fotos y te guía hasta tener tu avatar listo.
Después escribe `Quiero hacer un video` cada vez que quieras uno nuevo.

## Qué vas a necesitar

| | Opción gratis o incluida | Opción de pago (más rápida) |
|---|---|---|
| Imágenes del avatar | ChatGPT Plus: copias y pegas los prompts que te prepara tu asistente | API de OpenAI: tu asistente las genera solo (unos USD 2–3 por avatar) |
| Voz | Tu propia grabación, con el celular | ElevenLabs con tu voz clonada |
| Transcripción | En tu computadora (la primera vez tarda en instalarse) | API de OpenAI (centavos por video) |

También necesitas una computadora con Mac, Windows o Linux, unos 3 GB libres y conexión a internet.

## Cómo funciona

1. **Tu personaje**: de tus fotos sale una hoja de personaje; de ahí, una imagen maestra y 10 poses, todas con la boca cerrada.
2. **La animación**: eliges entre formas dibujadas (SVG) o pequeños recortes de boca y ojos basados en tu maestra.
   Los recortes conservan mejor el acabado de labios y pestañas en personajes con volumen y textura;
   requieren preparar y revisar imágenes adicionales una sola vez. Ambas opciones conservan las poses originales.
   Tu personaje no cambia nunca, porque no se generan imágenes nuevas en cada video.
3. **Tus videos**: tú pones la voz (o un guion), tu asistente propone las escenas y tú las apruebas.
   El video se renderiza en tu computadora con [HyperFrames](https://hyperframes.heygen.com).

## Preguntas frecuentes

**¿Puedo elegir cómo se anima la cara?**
Sí. Las formas SVG siguen disponibles y son la opción inicial. Si tu personaje tiene labios con volumen,
sombras o pestañas detalladas, dile al asistente: **«Quiero probar boca y párpados con recortes de mi maestra»**.
Te guiará para crear las variantes, verlas sobre tu imagen original y aprobarlas antes de usarlas.
No hace falta generar gestos nuevos para cada video y puedes volver a SVG cuando quieras.

**¿Mis fotos y mi voz se suben a algún lado?**
Solo a los servicios que tú elijas: ChatGPT u OpenAI para crear las imágenes y, si los usas, OpenAI o ElevenLabs para la voz y la transcripción.
Todo lo demás se queda en tu computadora.

**¿Puedo cambiar mis colores de marca o el formato después?**
Sí. Pídeselo a tu asistente ("cambia mis colores a verde y negro"). No hace falta rehacer el avatar.

**Una pose no me gustó.**
Dile a tu asistente cuál y qué cambiar: rehace solo esa.

---

Código: `avatar/` (Python, se ejecuta con [uv](https://docs.astral.sh/uv/)) y `motion/` (HyperFrames).
Las instrucciones para el agente están en `AGENTS.md` y en `.claude/skills/`.
La fuente Montserrat se distribuye bajo la licencia SIL Open Font License (`motion/assets/fonts/OFL.txt`).

Para contribuir al sistema facial, consulta [el flujo técnico y las pruebas](docs/gestos.md).
