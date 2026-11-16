# Sistemas faciales

`avatar.json` permite elegir `"rostro": {"sistema": "svg"}` (valor inicial) o `"recortes"`.
En proyectos que no incluyen esta opción, se conserva el comportamiento anterior: SVG salvo que
ya haya una referencia `recortes` en `personaje/cara.json`.

## Flujo reproducible

1. Crear, preparar, medir y aprobar la maestra mediante el flujo habitual.
2. `uv run avatar gestos prompts`: exporta la maestra alineada sobre verde, siete instrucciones y
   `personaje/gestos/ajustes.json`. Su boca y ojos usan rectángulos `[x,y,ancho,alto]` en coordenadas
   de la pose **normalizada**, no de la imagen original antes de preparar.
3. Generar una imagen completa por gesto desde esa misma referencia. Usar ChatGPT, las herramientas
   integradas del asistente o `uv run avatar gestos generar todos` si se ha elegido la API configurada.
   No se requiere ningún nuevo proveedor ni biblioteca de generación.
4. Guardar las siete imágenes en `personaje/gestos/inbox/`: `a.png`, `e-i.png`, `o-u.png`, `f-v.png`,
   `cons.png`, `ojos-medios.png`, `ojos-cerrados.png`. Deben conservar las dimensiones de la maestra.
5. `uv run avatar gestos preparar`: crea una versión nueva en `personaje/layers/gestos-vN/`.
   Nunca sobrescribe la activa. Genera nueve piezas RGBA, descriptor y `revision.png`.
   Los rectángulos iniciales son estimaciones: revisar contornos, sombras, pestañas, comisuras y alineación.
   Ajustar y repetir si hace falta. La aprobación visual no se puede sustituir por coincidencia de tamaño.
6. Con aprobación: `uv run avatar gestos activar --aprobado`, después `uv run avatar verificar`.
   Revisar las poses y una prueba breve de narración antes de dar por terminado el personaje.
7. `uv run avatar componer <slug>` incorpora el sistema elegido; renderizar normalmente.

Cambiar con `uv run avatar gestos usar svg` o `uv run avatar gestos usar recortes`.
La segunda opción requiere un conjunto previamente aprobado. Volver a SVG no borra las piezas.
Recomponer y renderizar para actualizar videos existentes.

## Datos y render

El descriptor `recortes.json` incluye `version:1`, los anclajes de referencia y las cinco entradas
`bocas.A`, `E_I`, `O_U`, `FV`, `CONS`; cada ojo tiene estados `medio` y `cerrado`.
Cada pieza declara `archivo` (relativo a `personaje/`), `x`, `y`, `ancho` y `alto`.
Reposo y M/B/P no llevan parche: se usan los labios originales; los ojos abiertos también son originales.
Los conjuntos preparados incluyen una huella de la pose maestra para detectar cambios posteriores.

`rostro.py` centraliza la selección y validación para anclajes, composición y revisión.
Rechaza piezas ausentes, rutas fuera de `personaje/`, tamaños incorrectos y una maestra distinta.
Si se eligen recortes, nunca se sustituye silenciosamente el sistema por SVG.
Los conjuntos anteriores sin huella siguen siendo compatibles.

El reproductor conserva la boca de origen, destino y mezcla temporal; selecciona una sola pieza
en cada instante, sin fundir dientes o labios distintos. Los ojos siguen la secuencia
abierto → medio → cerrado → medio → abierto. Todas las decisiones son funciones del tiempo;
los recortes se precargan y se alinean con escala y rotación relativas a los anclajes de cada pose.
Se respetan `habla:false` y `parpadeo:false`.

## Límites

- La generación puede desplazar rasgos incluso si el tamaño coincide: necesita revisión visual.
- Los cambios de boca son por sustitución de imágenes, sin la interpolación geométrica de SVG.
- Cabezas giradas y manos cerca de la cara pueden necesitar ajustes particulares o desactivar un gesto.
- Las fotos, piezas, voces y videos del usuario siguen excluidos del repositorio por `.gitignore`.

## Pruebas sin credenciales ni datos personales

```bash
python -m unittest discover -s tests -p 'test_*.py'
node tests/avatar-recortes.cjs
```

Las pruebas Python crean imágenes sintéticas temporales para comprobar preparación, activación,
cambio de sistema, versiones y errores. Las pruebas del reproductor verifican los estados faciales,
la reproducción al retroceder y la compatibilidad con SVG.
