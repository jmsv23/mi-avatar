"""Lista personajes y guarda la selección para los siguientes comandos."""
from .config import CONFIG, PERSONAJES, ROOT, carpeta_personaje, die, ok, rel, write_json


def cmd_listar(a) -> None:
    activo = CONFIG.get("personaje_activo")
    for path in sorted(PERSONAJES.iterdir()):
        if path.is_dir() and (path / "personaje.json").is_file():
            print(f"{'*' if path.name == activo else ' '} {path.name}")
    if activo is None and (PERSONAJES / "personaje.json").exists():
        print("* personaje/ (estructura anterior)")


def cmd_usar(a) -> None:
    try:
        path = carpeta_personaje(a.nombre)
    except ValueError as error:
        die(str(error))
    if not (path / "personaje.json").is_file():
        die(f"no existe un personaje preparado en {rel(path)}")
    write_json(ROOT / "avatar.json", {**CONFIG, "personaje_activo": a.nombre})
    ok(f"personaje activo: {a.nombre}")
