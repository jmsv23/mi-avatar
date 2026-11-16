# Avatar Studio — instrucciones para el agente

Este proyecto ayuda a una persona **sin formación técnica** a crear su avatar 2D animado y a producir
videos narrados por él (motion graphics con el avatar como narrador, con lip-sync).
Funciona igual en Claude Code (incluida la pestaña Code de Claude Desktop) y en Codex.

## Cómo trabajar con el usuario

- Habla en **español sencillo**, con pasos cortos. Nada de jerga: no digas "JSON", "CLI", "venv" ni "lint".
  Tú corres los comandos; el usuario solo aporta fotos, decisiones, audio y aprobaciones.
- Haz **una pregunta a la vez** y ofrece una opción recomendada.
- Muestra siempre las imágenes de revisión (léelas tú y descríbelas) antes de pedir una aprobación.
- Si un comando falla, explica el problema en una frase y arréglalo tú. No pegues trazas de error.
- Nunca muestres en el chat ni subas a ningún lado las claves de `.env`.
- Para que el usuario deje un archivo en una carpeta, ábrela por él:
  `open <carpeta>` (Mac), `explorer <carpeta>` (Windows) o `xdg-open <carpeta>` (Linux).
  Las imágenes que el usuario pega en el chat **no** quedan guardadas como archivos: pídele que las copie a la carpeta.

## Varios personajes

Cada personaje vive en `personaje/<nombre>/`. `avatar.json → personaje_activo` selecciona cuál usan todos los comandos. El actual es `presentador`.
Antes de trabajar revisa esa selección. Todas las rutas `personaje/...` de las skills se interpretan dentro de la carpeta del personaje activo, por ejemplo `personaje/presentador/inbox/01-neutral.png`. Nunca mezcles archivos de distintos personajes.
Usa `uv run avatar personajes listar` para listar y `uv run avatar personajes usar <nombre>` para elegir uno ya preparado. Para uno nuevo crea su carpeta y ficha, y luego selecciónalo. Proyectos anteriores sin `personaje_activo` conservan las rutas originales.
Los videos se componen con el personaje activo: comprueba la selección antes de componer o volver a componer un video.
Los personajes pueden ser inventados si el usuario lo pide. En ese caso las propuestas aprobadas sustituyen las fotos; conserva la hoja y la maestra como referencias.

## Las tres fases (cada una es una skill)

| Fase | Skill | Cuándo |
|---|---|---|
| Preparar el equipo | `.claude/skills/avatar-equipo/SKILL.md` | La primera vez, o si `uv run avatar doctor` falla |
| Crear el avatar | `.claude/skills/avatar-crear/SKILL.md` | "quiero crear mi avatar", o no existe `personaje/manifest.json` |
| Hacer un video | `.claude/skills/avatar-video/SKILL.md` | "quiero hacer un video", con el avatar ya listo |
| Elegir boca y párpados | `.claude/skills/avatar-gestos/SKILL.md` | Quiere mejorar la cara animada o elegir entre SVG y recortes |

**Lee la skill completa antes de empezar su fase** (en Codex, ábrela con la ruta de arriba).
Si el usuario solo dice "hola" o "¿qué hago?", corre `uv run avatar doctor --rapido` y llévalo a la fase que le toca.

## Herramienta

Todos los pasos son subcomandos de `uv run avatar <comando>`, ejecutados desde la raíz del proyecto
(`uv run avatar --help` muestra la lista). La configuración vive en `avatar.json` (idioma, proveedores,
formato, colores de marca) y las claves en `.env`.

```
personaje/<nombre>/   cada avatar (referencias, hoja de personaje, poses, cara.json, manifest.json)
videos/<slug>/        cada video: audio.wav, transcripcion.json, plan.json, timeline.json, video.mp4
motion/               proyecto HyperFrames (render); motion/shared/*.js es el avatar y las escenas
avatar/               código Python de los comandos
```

## Principios técnicos (no los rompas)

1. **Consistencia**: la IA solo crea las imágenes iniciales del personaje. Los videos nunca regeneran imágenes.
2. **Determinista**: el render es una función del tiempo (sin `Math.random`, `Date.now` ni animaciones CSS).
3. Las poses se generan con **boca cerrada** y **fondo verde #00FF00**; la boca y los párpados se colocan encima.
4. **Elección del usuario**: conserva el sistema facial elegido (`rostro.sistema`: `svg` o `recortes`).
   SVG es el valor inicial; los proyectos anteriores sin esa opción conservan su funcionamiento.
   Los recortes se generan y aprueban una sola vez desde la maestra; nunca se reemplazan las poses completas.
   No cambies de recortes a SVG para ocultar un error ni actives piezas sin mostrarlas y obtener aprobación.
