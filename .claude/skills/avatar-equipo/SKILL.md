---
name: avatar-equipo
description: Prepara la computadora del usuario para Avatar Studio (uv, Node.js 22+, FFmpeg, navegador de HyperFrames) y configura sus preferencias (imágenes por ChatGPT o API, voz, formato, colores de marca, claves). Úsala la primera vez, cuando el usuario dice "instalar", "configurar" o "empezar", o cuando `uv run avatar doctor` falla.
---

# Preparar el equipo

El usuario no es técnico: tú instalas, él solo aprueba. Explica cada instalación en una línea
("Voy a instalar FFmpeg, que sirve para trabajar con audio y video").

## 1. Revisa qué hay

```bash
uv run avatar doctor
```

Si `uv` no existe, el comando falla antes de empezar: instálalo primero (paso 2) y vuelve a correrlo.

## 2. Instala lo que falte

Detecta el sistema operativo y usa **un solo** método por herramienta. Después de instalar en Windows,
las herramientas nuevas a veces no aparecen hasta abrir una terminal nueva: si `doctor` sigue sin verlas,
pide al usuario que cierre y vuelva a abrir la app.

| Herramienta | Mac | Windows | Linux |
|---|---|---|---|
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` | igual que Mac |
| Node.js 22+ | `brew install node` (si no hay Homebrew: instalador LTS de nodejs.org) | `winget install OpenJS.NodeJS.LTS` | nvm o el gestor de la distribución |
| FFmpeg | `brew install ffmpeg` | `winget install Gyan.FFmpeg` | `sudo apt install ffmpeg` |

En Mac sin Homebrew, ofrece instalarlo (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`);
pide la contraseña de la Mac en la terminal, así que explícale al usuario que la escriba ahí si se la pide.

Luego instala el navegador que usa el render:

```bash
uv run avatar doctor --arreglar
```

Repite `uv run avatar doctor` hasta que diga "todo listo".

## 3. Preferencias (una pregunta a la vez)

Guarda las respuestas en `avatar.json`. Edítalo tú; el usuario no toca archivos.

1. **Imágenes del personaje** (`imagenes.proveedor`):
   - `chatgpt` (recomendado si tiene ChatGPT Plus): tú preparas los prompts y él los pega en ChatGPT. No cuesta extra.
   - `api`: tú las generas con la API de OpenAI. Necesita una clave de API con saldo (unos USD 2–3 por avatar completo).
2. **Voz de los videos** (`voz.proveedor`):
   - `grabacion` (recomendado): graba su voz con el celular o la computadora. Es su voz real y no cuesta nada.
   - `elevenlabs`: clona su voz en ElevenLabs (plan de pago). Pide el ID de la voz y guárdalo en `voz.elevenlabs.voice_id`.
   - `voicebox`: clonación local con la app Voicebox (solo usuarios avanzados). Pide el nombre del perfil para `voz.voicebox.perfil`.
3. **Idioma** (`idioma`): `es` o `en`. Se usa para la transcripción y el lip-sync.
4. **Formato** (`lienzo.formato`): `vertical` (TikTok, Reels y Shorts, el recomendado), `horizontal` (YouTube) o `cuadrado`.
5. **Colores de marca** (`marca.fondo`, `marca.acento`, `marca.texto`): pídele sus colores o el link de su logo o su web
   y propón una paleta. Valores por defecto: azul `#1e6ee6`, amarillo `#ffc928`, texto blanco.

## 4. Claves (solo si eligió API o ElevenLabs)

- **OpenAI** (imágenes por API, y transcripción rápida): platform.openai.com → API keys → Create new secret key.
  Sin clave, la transcripción usa WhisperX en la computadora: es gratis, pero la primera vez descarga unos 2 GB y tarda más.
- **ElevenLabs**: elevenlabs.io → Profile → API keys.

Copia `.env.example` a `.env` y escribe ahí las claves que te pase el usuario. Nunca las repitas en el chat.
Explícale que el archivo `.env` se queda solo en su computadora.

## 5. Cierre

Corre `uv run avatar doctor` y resume en 3 líneas lo que quedó configurado. Después propone:
"¿Creamos tu avatar? Necesito 1 a 3 fotos tuyas de frente y con buena luz" → skill `avatar-crear`.
