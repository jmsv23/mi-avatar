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

## Las tres fases (cada una es una skill)

| Fase | Skill | Cuándo |
|---|---|---|
| Preparar el equipo | `.claude/skills/avatar-equipo/SKILL.md` | La primera vez, o si `uv run avatar doctor` falla |
| Crear el avatar | `.claude/skills/avatar-crear/SKILL.md` | "quiero crear mi avatar", o no existe `personaje/manifest.json` |
| Hacer un video | `.claude/skills/avatar-video/SKILL.md` | "quiero hacer un video", con el avatar ya listo |

**Lee la skill completa antes de empezar su fase** (en Codex, ábrela con la ruta de arriba).
Si el usuario solo dice "hola" o "¿qué hago?", corre `uv run avatar doctor --rapido` y llévalo a la fase que le toca.

## Herramienta

Todos los pasos son subcomandos de `uv run avatar <comando>`, ejecutados desde la raíz del proyecto
(`uv run avatar --help` muestra la lista). La configuración vive en `avatar.json` (idioma, proveedores,
formato, colores de marca) y las claves en `.env`.

```
personaje/            el avatar del usuario (fotos, hoja de personaje, poses, cara.json, manifest.json)
videos/<slug>/        cada video: audio.wav, transcripcion.json, plan.json, timeline.json, video.mp4
motion/               proyecto HyperFrames (render); motion/shared/*.js es el avatar y las escenas
avatar/               código Python de los comandos
```

## Principios técnicos (no los rompas)

1. **Consistencia**: la IA solo crea las imágenes iniciales del personaje. Los videos nunca regeneran imágenes.
2. **Determinista**: el render es una función del tiempo (sin `Math.random`, `Date.now` ni animaciones CSS).
3. Las poses se generan con **boca cerrada** y **fondo verde #00FF00**; la boca y los párpados se dibujan encima.
