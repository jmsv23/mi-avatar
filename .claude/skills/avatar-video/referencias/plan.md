# plan.json — escenas y poses de un video

```json
{
  "escenas": [
    {"t0": 0.0, "t1": 3.2, "tipo": "avatar", "texto": "¿Sabías que…?"},
    {"t0": 3.2, "t1": 7.5, "tipo": "lista", "titulo": "3 errores", "items": [
      {"texto": "Precio sin valor", "t": 3.9}, {"texto": "Sin llamada a la acción", "t": 5.1}, {"texto": "Logo enorme", "t": 6.4}]},
    {"t0": 7.5, "t1": 10.0, "tipo": "dato", "valor": 80, "sufijo": " %", "texto": "de los clientes lo nota"},
    {"t0": 10.0, "t1": 14.0, "tipo": "video", "archivo": "original.mp4", "texto": "Así se ve"},
    {"t0": 14.0, "t1": 17.0, "tipo": "titulo", "titulo": "Sígueme para más", "subtitulo": "un tip cada semana"}
  ],
  "poses": [
    {"t": 0.0, "pose": "encogerse"}, {"t": 3.1, "pose": "contar"}, {"t": 7.4, "pose": "senalar"}, {"t": 13.9, "pose": "pulgar"}
  ],
  "gestos": [{"t": 15.0, "g": "asentir", "d": 0.7}]
}
```

Los tiempos van en segundos desde el inicio del audio; tómalos de `transcripcion.json` (`start` de cada palabra).
Las escenas deben cubrir todo el audio sin huecos: el `t1` de una es el `t0` de la siguiente.

## Tipos de escena

| tipo | campos | uso |
|---|---|---|
| `avatar` | `texto?` (título corto arriba) | el avatar como protagonista: gancho, saludo, cierre |
| `titulo` | `titulo`, `subtitulo?` | idea principal, cambio de tema |
| `lista` | `titulo?`, `items` (texto, o `{texto, t}` para que cada punto aparezca cuando lo dice) | enumeraciones, pasos |
| `dato` | `valor` (número), `prefijo?`, `sufijo?`, `texto?` | cifras: el número cuenta hacia arriba |
| `cita` | `texto`, `autor?` | frase memorable, testimonio |
| `imagen` | `archivo` (en `videos/<slug>/`), `texto?` | captura, producto, foto |
| `video` | `archivo`, `desde?` (segundo del clip donde empieza), `texto?` | clip propio; con `original.mp4` y sin `desde` queda sincronizado con el audio |

Campo común `avatar`, que define dónde va el narrador:
- `completo`: protagonista, es el valor por defecto en `avatar`.
- `narrador`: abajo en vertical o a un lado en horizontal, con los gráficos en el resto; es el valor por defecto en las demás.
- `oculto`: es el valor por defecto en `video`. El avatar sale de cuadro con una transición.

## Poses disponibles

`neutral`, `hablar`, `senalar`, `presentar`, `contar`, `pulgar`, `manos-abiertas`, `encogerse`, `pensar` (no habla), `saludo`.
Solo existen las que el usuario generó: revisa `personaje/manifest.json`.

Si el plan no trae `poses`, se eligen solas: pregunta → `encogerse`, enumeración → `contar`, exclamación → `senalar`,
el resto rota entre `hablar`, `manos-abiertas` y `neutral`.

## Reglas de ritmo

- Cambia de escena cada 2–5 s; en redes, que el primer cambio llegue antes de los 3 s.
- Cambia de pose como mucho una vez cada ~2 s, un poco antes de la frase (unos 0.15 s).
- Títulos de 2–6 palabras. Las listas, de 3–4 puntos como máximo. Escribe el texto de pantalla **resumido**, no la frase completa.
- `presentar` encaja justo antes de una escena de imagen o video ("mira esto…"). `pensar` y `saludo` van en silencios o en el saludo.
- `gestos`: `asentir` en un "sí" enfático, `negar` en un "no". Se generan solos si no los defines.
