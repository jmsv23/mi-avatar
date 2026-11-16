"""Catálogo de poses y prompts de imagen (los mismos para la API de OpenAI y para pegar en ChatGPT).

personaje/personaje.json (lo escribe el agente al crear el avatar):
  nombre        cómo se llama el usuario o su marca
  estilo        plano | anime | comic
  descripcion   descripción física en inglés (la usa cada prompt para fijar la identidad)
  ropa          ropa en inglés
"""
from .config import FICHA, HOJA, INBOX, PERSONAJE, PROMPTS, die, ok, read_json, rel

ESTILOS = {
    "plano": "modern flat 2D cartoon, vector look, clean dark outlines of consistent thickness, "
             "solid colors with soft cel shading, light coming from the upper left",
    "anime": "soft anime-inspired 2D illustration, clean dark lineart of consistent thickness, "
             "flat cel shading, warm friendly colors, light coming from the upper left",
    "comic": "bold comic-book 2D cartoon, thick black outlines of consistent thickness, "
             "flat vibrant colors with minimal shading, light coming from the upper left",
}

# (número, id, ¿habla?, descripción en español, pose en inglés)
POSES = [
    ("01", "neutral", True, "frente, brazos relajados (maestra)",
     "Standing straight, relaxed, arms hanging naturally at the sides, hands relaxed. "
     "Eyes open looking straight at the camera, neutral eyebrows."),
    ("02", "hablar", True, "mano explicando",
     "Explaining gesture: the right hand (on the left side of the image) raised to chest level, palm open and "
     "slightly up, as if explaining something. The other arm relaxed at the side. Engaged, friendly look."),
    ("03", "senalar", True, "dedo índice arriba",
     "Making a point: one hand raised to shoulder height with the index finger pointing up, the other arm relaxed. "
     "Confident look, eyebrows slightly raised."),
    ("04", "presentar", True, "brazo a un lado, palma arriba",
     "Presenting something beside him: one arm extended out to the side at waist height, palm up, as if "
     "introducing something next to him. The other arm relaxed. Looking at the camera, smiling."),
    ("05", "contar", True, "dos dedos",
     "Counting: one hand raised beside the chest showing two fingers (index and middle) to the camera, "
     "the other arm relaxed."),
    ("06", "pulgar", True, "pulgar arriba",
     "Thumbs up: one hand in front of the chest giving a clear thumbs up, the other arm relaxed. Happy look."),
    ("07", "manos-abiertas", True, "ambas palmas arriba",
     "Both hands open at waist height, palms up, arms slightly away from the body, welcoming and honest gesture."),
    ("08", "encogerse", True, "hombros arriba, duda",
     "Shrugging: shoulders raised, both palms up at the sides, eyebrows raised, a doubtful 'who knows?' look."),
    ("09", "pensar", False, "mano al mentón, mirada arriba",
     "Thinking: one hand on the chin, looking slightly up and to the side, the other arm crossed under it."),
    ("10", "saludo", True, "mano arriba saludando",
     "Waving hello: one arm raised with the open palm facing the camera, fingers spread, BESIDE the head "
     "(never above the head, never in front of the face). The other arm relaxed. Both eyes open, cheerful."),
]
POSE_IDS = [p[1] for p in POSES]

RULES = """Rules for every image:
- MOUTH CLOSED and relaxed, lips together, a very slight friendly smile, NO teeth visible (the mouth is animated separately).
- Hands and arms never cover the mouth, chin or eyes{pensar}. Nothing is cut off by the frame edges: head, hands and elbows fully visible.
- Vertical image, 2:3 aspect ratio (1024x1536).
- Background: a single flat pure green color #00FF00, completely uniform. No gradient, no shadows, no floor, no vignette.
- No green anywhere on the character.
- No text, labels, border, sparkles, motion lines or extra objects."""

FRAMING = ("Front view, facing the camera. Waist-up framing cropped at the hips, character centered horizontally, "
           "the top of the head about 8% below the top edge, the head always in the same place and size.")


def ficha() -> dict:
    f = read_json(FICHA, "el agente la crea en el paso 'hoja de personaje' (skill avatar-crear)")
    for k in ("estilo", "descripcion", "ropa"):
        if not f.get(k):
            die(f"personaje.json: falta '{k}'")
    if f["estilo"] not in ESTILOS:
        die(f"personaje.json: estilo '{f['estilo']}' no existe (usa {', '.join(ESTILOS)})")
    return f


def prompt_hoja(f: dict) -> str:
    return f"""I'm attaching photo(s) of me. Turn me into a 2D cartoon character for my personal brand and draw a CHARACTER SHEET of that character.

Keep me recognizable: same face shape, hairstyle and hairline, facial hair, glasses (if any), skin tone, eye color and body build. Friendly, charismatic expression.
Character: {f['descripcion']}
Outfit: {f['ropa']}

Style: {ESTILOS[f['estilo']]}.

Sheet layout (landscape 3:2, 1536x1024, clean light-gray background, small labels allowed):
- Top left: a large waist-up portrait, smiling.
- Top: full-body turnaround (front, 3/4 front, profile).
- Top right: 6 facial expressions (neutral, smile, laugh, surprised, doubtful, thinking).
- Bottom: 6 waist-up gestures (explaining, pointing up, thumbs up, both hands open, shrugging, waving).
The character must be identical in every drawing: same proportions, colors and outline thickness."""


def prompt_maestra(f: dict) -> str:
    return f"""I'm attaching the character sheet of my 2D cartoon avatar. Use it as the exact character reference. I want a CANONICAL MASTER image of this character that I will reuse to build an animated avatar. Every later image must match it exactly.

Character (match the sheet exactly): {f['descripcion']}
Outfit: {f['ropa']}
Style (match the sheet): {ESTILOS[f['estilo']]}.

Pose and framing:
- {FRAMING}
- {POSES[0][4]}

{RULES.format(pensar='')}"""


def prompt_pose(f: dict, numero: str) -> str:
    _, pid, _, _, pose = next(p for p in POSES if p[0] == numero)
    excepcion = " (exception: in this pose the hand may touch the chin, but must not cover the mouth)" if pid == "pensar" else ""
    return f"""Using the attached MASTER image as the EXACT same character (same face, hair, facial hair, head shape, proportions, clothing, colors, outline thickness, shading and lighting), generate a new image with the same camera and framing.

Character: {f['descripcion']} Outfit: {f['ropa']}
Framing: {FRAMING}

New pose:
- {pose}

{RULES.format(pensar=excepcion)}"""


def prompt_de(numero: str, f: dict) -> str:
    if numero == "00":
        return prompt_hoja(f)
    if numero == "01":
        return prompt_maestra(f)
    return prompt_pose(f, numero)


COMO_USAR = """# Cómo generar tus imágenes en ChatGPT

1. Abre **una conversación nueva** de ChatGPT y usa **esa misma** para todas las imágenes.
2. **Hoja de personaje**: sube 1 a 3 fotos tuyas (de frente, buena luz) y pega el prompt `00-hoja-de-personaje.md`.
   Guarda la imagen como `personaje/hoja-de-personaje.png`. Si no te gusta, pide cambios en el mismo chat.
3. **Maestra**: sube la hoja de personaje y pega `01-neutral.md`. Guárdala como `personaje/inbox/01-neutral.png`
   y avisa a tu agente: la revisa contigo **antes** de seguir.
4. **Poses**: pega los prompts `02` a `10` en orden, uno por mensaje, y guarda cada imagen con el nombre que indica.

Copia solo el texto que está dentro del bloque gris.

## Checklist de cada imagen

- [ ] Es el mismo personaje que la maestra: cara, pelo, ropa, proporciones.
- [ ] La **boca está cerrada** (sin dientes).
- [ ] El fondo es verde plano, sin sombras ni piso.
- [ ] Las manos no tapan la boca ni los ojos.
- [ ] Nada se sale del cuadro: cabeza, manos y codos completos.
- [ ] La imagen es vertical.

Si una imagen falla, pide en el mismo chat:
`Regenerate the last image keeping everything identical, but fix: <problema>.`
"""


def destino(numero: str) -> str:
    if numero == "00":
        return rel(HOJA)
    return rel(INBOX / f"{numero}-{next(p[1] for p in POSES if p[0] == numero)}.png")


def adjuntos(numero: str) -> str:
    if numero == "00":
        return "Adjunta 1 a 3 fotos tuyas en el mismo mensaje."
    if numero == "01":
        return f"Adjunta `{rel(HOJA)}` en el mismo mensaje."
    return f"Pégalo en la misma conversación, después de aprobar la maestra (si es un chat nuevo, adjunta `{rel(INBOX / '01-neutral.png')}`)."


def cmd_prompts(a) -> None:
    f = ficha()
    PROMPTS.mkdir(parents=True, exist_ok=True)
    (PROMPTS / "00-como-usar.md").write_text(COMO_USAR.replace("personaje/", rel(PERSONAJE) + "/"), encoding="utf-8")
    for numero in ["00"] + [p[0] for p in POSES]:
        name = "hoja-de-personaje" if numero == "00" else next(p[1] for p in POSES if p[0] == numero)
        body = f"# {numero} · {name}  →  guardar como `{destino(numero)}`\n\n{adjuntos(numero)}\n\n```\n{prompt_de(numero, f)}\n```\n"
        (PROMPTS / f"{numero}-{name}.md").write_text(body, encoding="utf-8")
    ok(f"prompts en {rel(PROMPTS)}/ (empieza por 00-como-usar.md)")
