#!/usr/bin/env python3
"""Estados de datos remotos consistentes (SPEC-003 / T7.3 / AC4 + AC5).

AC4 pide que toda vista con datos remotos muestre un estado **cargando / vacío /
error** consistente y reutilizable. AC5 pide que eso sea comprobable. Este script
es esa comprobación, y corre en la CI.

Comprueba dos cosas, y las dos vienen de fallos reales que había en el repo:

1. **Nadie pinta un estado a mano.** Los `spinner spinner-lg` y `empty-state`
   sueltos son lo que hacía que cada página tuviera su versión: unas con icono y
   otras sin él, unas centradas y otras no, y ninguna con estado de error. Deben
   venir de `components/ui/states.jsx`.

2. **Nadie se traga un error de carga.** El patrón que motiva la tarea era
   `.catch(() => {})` seguido de un `toast`: el toast desaparece a los pocos
   segundos y lo que queda en pantalla es el estado **vacío**. La aplicación te
   dice que no tienes datos cuando lo que pasa es que no ha podido preguntarlos, y
   no te ofrece reintentar. Un `catch` que no ejecuta **ninguna** sentencia es
   exactamente eso.

   Hay fallos que sí se pueden ignorar —un desplegable auxiliar, un sondeo que se
   repite cada 30 s— pero tienen que decirlo: se marcan con un comentario
   `mejor-esfuerzo:` **y su razón**, en las tres líneas anteriores. La excepción
   así es revisable; un `catch {}` mudo no.

Uso:
    python scripts/check_async_states.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "frontend" / "src"
COMPONENTE = FUENTE / "components" / "ui" / "states.jsx"

EXTENSIONES = (".jsx", ".js")

#: Clases que solo puede escribir el componente de estados.
CLASES = re.compile(r"""['"`][^'"`]*\b(spinner-lg|empty-state)\b[^'"`]*['"`]""")

#: `catch` que no ejecuta ninguna sentencia: `catch {}`, `catch (e) { }`,
#: `catch { /* lo que sea */ }` y la forma en promesa `.catch(() => {})`.
CATCH_MUDO = re.compile(
    r"""catch\s*(\([^)]*\)\s*)?\{\s*(/\*.*?\*/|//[^\n]*)?\s*\}"""
    r"""|\.catch\(\s*\([^)]*\)\s*=>\s*\{\s*(/\*.*?\*/|//[^\n]*)?\s*\}\s*\)""",
    re.S,
)

MARCA = "mejor-esfuerzo:"
#: Cuántas líneas antes puede estar la marca. La marca se pone sobre la
#: **sentencia** que puede fallar, y un `.catch()` encadenado queda varias líneas
#: por debajo de su `fetch(...)`; ocho cubre los casos reales del repo sin llegar
#: a la sentencia anterior.
ALCANCE = 8

#: Los comentarios se vacían antes de buscar: este mismo fichero, y algún
#: comentario del código, **mencionan** `.catch(() => {})` al explicar por qué no
#: se hace. Hablar de un patrón no es usarlo.
COMENTARIO = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _ficheros() -> list[Path]:
    return [
        f
        for f in sorted(FUENTE.rglob("*"))
        if f.is_file() and f.suffix in EXTENSIONES and f != COMPONENTE
    ]


def estados_a_mano() -> list[tuple[str, int, str]]:
    hallazgos = []
    for fichero in _ficheros():
        for numero, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
            for encaje in CLASES.finditer(linea):
                hallazgos.append(
                    (str(fichero.relative_to(RAIZ)), numero, encaje.group(1))
                )
    return hallazgos


def _sin_comentarios(texto: str) -> str:
    """Vacía los comentarios conservando los saltos de línea y las llaves.

    Las llaves se conservan porque `catch { /* motivo */ }` tiene que seguir
    encajando como catch mudo: el comentario explica, no ejecuta.
    """
    def _blanquear(m: re.Match) -> str:
        return re.sub(r"[^\n{}]", " ", m.group(0))

    return COMENTARIO.sub(_blanquear, texto)


def errores_tragados() -> list[tuple[str, int, str]]:
    hallazgos = []
    for fichero in _ficheros():
        original = fichero.read_text(encoding="utf-8")
        texto = _sin_comentarios(original)
        lineas = original.splitlines()
        for encaje in CATCH_MUDO.finditer(texto):
            numero = texto.count("\n", 0, encaje.start()) + 1
            contexto = "\n".join(lineas[max(0, numero - 1 - ALCANCE):numero])
            if MARCA in contexto:
                continue
            hallazgos.append(
                (
                    str(fichero.relative_to(RAIZ)),
                    numero,
                    encaje.group(0).replace("\n", " ")[:60],
                )
            )
    return hallazgos


def main() -> int:
    a_mano = estados_a_mano()
    tragados = errores_tragados()

    if a_mano:
        print(f"[FALLO] {len(a_mano)} estado(s) pintado(s) a mano:\n")
        for ruta, numero, clase in a_mano:
            print(f"  {ruta}:{numero}  .{clase}")
        print(
            "\nUsa <LoadingState/>, <EmptyState/>, <ErrorState/> o <AsyncState/>\n"
            "de components/ui/states.jsx. Pintarlo a mano es cómo se acabó con una\n"
            "versión distinta por página y ninguna con estado de error.\n"
        )

    if tragados:
        print(f"[FALLO] {len(tragados)} error(es) de carga tragado(s) en silencio:\n")
        for ruta, numero, fragmento in tragados:
            print(f"  {ruta}:{numero}  {fragmento}")
        print(
            "\nGuarda el error para que la vista pueda enseñar <ErrorState/> con\n"
            "reintento. Si de verdad es un fallo ignorable, escribe encima un\n"
            f"comentario «{MARCA} <razón>» — la excepción tiene que ser revisable.\n"
        )

    if a_mano or tragados:
        return 1

    print(
        f"[OK] {FUENTE.relative_to(RAIZ)}: los estados de carga/vacío/error salen "
        "del componente compartido\n     y ningún error de carga se traga sin motivo escrito."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
