#!/usr/bin/env python3
"""Los colores de `frontend/src` salen del design system (SPEC-003 / T7.1 / AC1+AC5).

AC1 pide que todo color use un token del design system; AC5, que exista una
comprobación **automatizable** que lo valide. Este script es esa comprobación, y
corre en la CI (job `frontend-build`).

Comprueba dos cosas, porque hay dos formas de saltarse el design system y la
segunda es la que no se ve:

1. **Sin hexadecimales literales.** Un `#2e844a` suelto no se ve mal, se ve
   **bien** — hasta que alguien cambia la paleta y ese componente se queda con el
   color viejo, o hasta que hay que soportar tema oscuro y ese valor no responde.
   El daño de un hex literal no es estético: rompe el único punto de cambio.

2. **Sin `var(--token)` que no exista.** Es el fallo silencioso: `var(--sin-definir)`
   sin fallback es inválido en tiempo de cómputo, así que la propiedad se descarta
   y el elemento hereda o vuelve al valor inicial. Parece tokenizado, no pinta nada
   y no avisa. Un hex al menos es honesto sobre lo que hace.

Excepciones, con motivo y no por conveniencia:

* `src/paperTheme.js` — son los colores del **paper impreso**, espejo de
  `_THEME_ACCENTS` del backend. La muestra tiene que enseñar el color del PDF, no
  el de la aplicación.
* Comentarios — mencionar un hex al explicar algo no lo pinta.

Uso:
    python scripts/check_design_tokens.py          # falla si encuentra algo
    python scripts/check_design_tokens.py --list   # lista los tokens disponibles
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "frontend" / "src"
DESIGN_SYSTEM = RAIZ / "frontend" / "ds" / "colors_and_type.css"

EXTENSIONES = (".jsx", ".js", ".css", ".tsx", ".ts")

#: Ficheros exentos, cada uno con su razón. Añadir aquí exige explicar por qué ese
#: color **no** puede ser un token, no que resulte incómodo cambiarlo.
EXCEPCIONES = {
    "paperTheme.js": (
        "colores del paper impreso; espejo de _THEME_ACCENTS del backend, la "
        "muestra debe enseñar el color del PDF y no el de la aplicación"
    ),
}

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
USO_VAR = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
DEF_VAR = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
COMENTARIO = re.compile(r"//.*$|/\*.*?\*/", re.S)


def _sin_comentarios(texto: str) -> str:
    """Vacía los comentarios conservando los saltos de línea, para no mover números."""
    def _blanquear(m: re.Match) -> str:
        return re.sub(r"\S", " ", m.group(0))

    return COMENTARIO.sub(_blanquear, texto)


def _ficheros() -> list[Path]:
    return [
        f
        for f in sorted(FUENTE.rglob("*"))
        if f.is_file() and f.suffix in EXTENSIONES and f.name not in EXCEPCIONES
    ]


def tokens_definidos() -> set[str]:
    """Tokens declarados en el design system y en los shims de `src/`."""
    definidos: set[str] = set()
    fuentes = [DESIGN_SYSTEM] if DESIGN_SYSTEM.exists() else []
    fuentes += sorted(FUENTE.rglob("*.css"))
    for fichero in fuentes:
        definidos |= set(DEF_VAR.findall(fichero.read_text(encoding="utf-8")))
    return definidos


def hexes_literales() -> list[tuple[str, int, str]]:
    encontrados: list[tuple[str, int, str]] = []
    for fichero in _ficheros():
        limpio = _sin_comentarios(fichero.read_text(encoding="utf-8"))
        for numero, linea in enumerate(limpio.splitlines(), start=1):
            for coincidencia in HEX.finditer(linea):
                encontrados.append(
                    (str(fichero.relative_to(RAIZ)), numero, coincidencia.group(0))
                )
    return encontrados


def tokens_rotos() -> list[tuple[str, int, str]]:
    definidos = tokens_definidos()
    encontrados: list[tuple[str, int, str]] = []
    for fichero in _ficheros():
        limpio = _sin_comentarios(fichero.read_text(encoding="utf-8"))
        for numero, linea in enumerate(limpio.splitlines(), start=1):
            for coincidencia in USO_VAR.finditer(linea):
                token = coincidencia.group(1)
                if token not in definidos:
                    encontrados.append(
                        (str(fichero.relative_to(RAIZ)), numero, token)
                    )
    return encontrados


def _informe(titulo: str, hallazgos: list[tuple[str, int, str]]) -> None:
    print(f"[FALLO] {titulo} ({len(hallazgos)}):\n")
    for ruta, numero, valor in hallazgos:
        print(f"  {ruta}:{numero}  {valor}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida que los colores de frontend/src usen tokens del design system"
    )
    parser.add_argument(
        "--list", action="store_true", help="Lista los tokens disponibles y sale"
    )
    args = parser.parse_args()

    if args.list:
        for token in sorted(tokens_definidos()):
            print(token)
        return 0

    hexes = hexes_literales()
    rotos = tokens_rotos()

    if hexes:
        _informe("color(es) hexadecimal(es) literal(es)", hexes)
    if rotos:
        _informe("referencia(s) a tokens que no existen", rotos)

    if not hexes and not rotos:
        print(f"[OK] {FUENTE.relative_to(RAIZ)}: sin hex literales y todos los var(--…) resuelven.")
        if EXCEPCIONES:
            print("     Exentos con motivo:")
            for nombre, motivo in sorted(EXCEPCIONES.items()):
                print(f"       - {nombre}: {motivo}")
        return 0

    print(
        "Usa un token del design system: `var(--nombre)`.\n"
        "Para ver los disponibles:  python scripts/check_design_tokens.py --list\n"
        "Si de verdad no puede ser un token, añádelo a EXCEPCIONES en este script\n"
        "**con el motivo**, para que la excepción sea revisable."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
