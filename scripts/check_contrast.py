#!/usr/bin/env python3
"""Contraste WCAG 2.1 AA de los componentes base (SPEC-003 / T7.2 / AC3 + AC5).

AC3 pide que los pares texto/fondo de los componentes base (botones, badges,
inputs) cumplan **WCAG 2.1 AA**: ≥ 4.5:1 en texto normal, ≥ 3:1 en texto grande y
en elementos no textuales (bordes, indicadores de foco — SC 1.4.11).

Por qué un script y no una extensión de navegador: la medición manual comprueba lo
que hay hoy en la pantalla de quien mide, en el tema en el que lo mire. Esto
comprueba **los dos temas** en cada PR, y falla nombrando el par. El checklist
verificable que pide AC5 para AC3 es, literalmente, la tabla `PARES` de abajo:
está escrita, es revisable, y cada fila se mide sola.

Resolución de tokens: se leen las declaraciones de `ds/colors_and_type.css` y de
los shims de `src/index.css`, y se siguen las cadenas `var(--a) → var(--b) → #hex`
por tema. `rgba()` se compone sobre el fondo del par (así es como se ve de verdad
un borde translúcido sobre su superficie).

Uso:
    python scripts/check_contrast.py            # falla si algún par no llega
    python scripts/check_contrast.py --table    # imprime la tabla medida
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESIGN_SYSTEM = RAIZ / "frontend" / "ds" / "colors_and_type.css"
SHIMS = RAIZ / "frontend" / "src" / "index.css"

#: Umbrales WCAG 2.1 AA.
AA_TEXTO_NORMAL = 4.5
AA_TEXTO_GRANDE = 3.0   # ≥ 18.66px bold o ≥ 24px
AA_NO_TEXTUAL = 3.0     # SC 1.4.11: bordes de control, indicadores de estado

# ─────────────────────────────────────────────────────────────────────────────
# El checklist de AC3. Cada fila: (qué es, primer plano, fondo, umbral).
# Añadir un componente base nuevo obliga a añadir su par aquí.
# ─────────────────────────────────────────────────────────────────────────────
#: El fondo puede ser un token o una **pila** de capas, de abajo arriba: un
#: `rgba()` translúcido solo tiene contraste si se sabe sobre qué se posa.
Fondo = str | tuple[str, ...]

#: Nivel de cada fila. `AA` bloquea la CI: es lo que exige AC3 (pares texto/fondo
#: de los componentes base) más el indicador de foco, que AC2 pide **visible** y
#: que solo lo es si cumple SC 1.4.11. `AVISO` se mide y se informa pero no
#: bloquea: son separadores decorativos, que no son contorno de ningún control y
#: por tanto no tienen umbral en WCAG. Se miden igualmente para que un cambio de
#: paleta no los hunda sin que nadie se entere.
AA, AVISO = "AA", "aviso"

PARES: list[tuple[str, str, Fondo, float, str]] = [
    # ── Botones ──────────────────────────────────────────────────────────────
    ("btn-primary · texto",        "--brand-on",       "--brand",        AA_TEXTO_NORMAL, AA),
    ("btn-primary:hover · texto",  "--brand-on",       "--brand-hover",  AA_TEXTO_NORMAL, AA),
    ("btn-secondary · texto",      "--text-body",      "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("btn-secondary · contorno",   "--border-control", "--bg-surface",   AA_NO_TEXTUAL,   AA),
    ("btn-ghost · texto",          "--text-secondary", "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("btn-ghost:hover · texto",    "--text-body",      ("--bg-surface", "--bg-hover"),  AA_TEXTO_NORMAL, AA),
    ("btn-danger · texto",         "--error",          ("--bg-surface", "--error-bg"),  AA_TEXTO_NORMAL, AA),
    ("btn-danger:hover · texto",   "--text-on-error",  "--error",        AA_TEXTO_NORMAL, AA),

    # ── Inputs ───────────────────────────────────────────────────────────────
    ("input · texto",              "--text-body",      "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("input · placeholder",        "--text-muted",     "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("input · contorno",           "--border-control", "--bg-surface",   AA_NO_TEXTUAL,   AA),
    ("input · contorno en panel",  "--border-control", "--bg-inset",     AA_NO_TEXTUAL,   AA),
    ("input:focus · contorno",     "--border-focus",   "--bg-surface",   AA_NO_TEXTUAL,   AA),
    ("input-label · texto",        "--text-secondary", "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("toggle · contorno",          "--border-control", "--bg-surface",   AA_NO_TEXTUAL,   AA),

    # ── Badges (texto de 11px en mayúscula → texto normal, no grande) ────────
    ("badge-draft",                "--status-draft",   ("--bg-surface", "--neutral-15"), AA_TEXTO_NORMAL, AA),
    ("badge-pending",              "--warning",        ("--bg-surface", "--warning-bg"), AA_TEXTO_NORMAL, AA),
    ("badge-approved",             "--success",        ("--bg-surface", "--success-bg"), AA_TEXTO_NORMAL, AA),
    ("badge-published",            "--brand-on-tint",  ("--bg-surface", "--brand-tint"), AA_TEXTO_NORMAL, AA),
    ("badge-running",              "--info",           ("--bg-surface", "--info-bg"),    AA_TEXTO_NORMAL, AA),
    ("badge-error",                "--error",          ("--bg-surface", "--error-bg"),   AA_TEXTO_NORMAL, AA),

    # ── Texto sobre las superficies de la aplicación ─────────────────────────
    ("texto cuerpo · canvas",      "--text-body",      "--bg-canvas",    AA_TEXTO_NORMAL, AA),
    ("titulares · superficie",     "--text-heading",   "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("texto secundario · canvas",  "--text-secondary", "--bg-canvas",    AA_TEXTO_NORMAL, AA),
    ("texto atenuado · superficie","--text-muted",     "--bg-surface",   AA_TEXTO_NORMAL, AA),
    ("texto atenuado · canvas",    "--text-muted",     "--bg-canvas",    AA_TEXTO_NORMAL, AA),
    ("enlaces · superficie",       "--text-link",      "--bg-surface",   AA_TEXTO_NORMAL, AA),

    # ── Modales y foco (T7.2) ────────────────────────────────────────────────
    # AC2 pide que el foco sea **visible**; un indicador que no llega a 3:1 no lo
    # es, así que estas filas bloquean igual que las de texto.
    ("anillo de foco · panel",     "--border-focus",   "--bg-surface",   AA_NO_TEXTUAL,   AA),
    ("anillo de foco · canvas",    "--border-focus",   "--bg-canvas",    AA_NO_TEXTUAL,   AA),
    ("modal · texto de cabecera",  "--text-heading",   "--bg-surface",   AA_TEXTO_NORMAL, AA),

    # ── Estados de datos remotos (T7.3) ──────────────────────────────────────
    ("estado de error · título",   "--error",          "--bg-canvas",    AA_TEXTO_NORMAL, AA),
    ("estado de error · icono",    "--error",          ("--bg-canvas", "--error-bg"), AA_NO_TEXTUAL, AA),
    ("estado vacío · título",      "--text-secondary", "--bg-canvas",    AA_TEXTO_NORMAL, AA),
    ("estado vacío · descripción", "--text-muted",     "--bg-canvas",    AA_TEXTO_NORMAL, AA),

    # ── Separadores decorativos (no son contorno de control: solo se informan) ─
    ("separador de modal",         "--border-default", "--bg-surface",   AA_NO_TEXTUAL,   AVISO),
    ("separador sutil",            "--border-subtle",  "--bg-surface",   AA_NO_TEXTUAL,   AVISO),
]

TEMAS = ("light", "dark")

DECL = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+);")
SELECTOR_OSCURO = re.compile(r'\[data-theme\s*=\s*"dark"\][^{}]*\{')


# ── Lectura de tokens ────────────────────────────────────────────────────────

def _texto(fichero: Path) -> str:
    return fichero.read_text(encoding="utf-8")


def _partir_por_tema(contenido: str) -> tuple[str, str]:
    """Separa el CSS en (fuera del tema oscuro, dentro del tema oscuro).

    Se cuentan llaves en vez de usar una regex: el selector real es
    `[data-theme="dark"], .dark {` y el bloque cierra con ` }` a media línea, así
    que cualquier atajo textual se come el bloque entero o ninguno — y fallar aquí
    en silencio significa medir el tema claro con los colores del oscuro.
    """
    claro: list[str] = []
    oscuro: list[str] = []
    posicion = 0
    for encaje in SELECTOR_OSCURO.finditer(contenido):
        claro.append(contenido[posicion:encaje.start()])
        profundidad = 1
        indice = encaje.end()
        while indice < len(contenido) and profundidad:
            if contenido[indice] == "{":
                profundidad += 1
            elif contenido[indice] == "}":
                profundidad -= 1
            indice += 1
        oscuro.append(contenido[encaje.end():indice - 1])
        posicion = indice
    claro.append(contenido[posicion:])
    return "".join(claro), "".join(oscuro)


def tokens_por_tema() -> dict[str, dict[str, str]]:
    """Devuelve {tema: {token: valor crudo}}, con el oscuro sobrescribiendo al claro."""
    claro: dict[str, str] = {}
    oscuro_extra: dict[str, str] = {}

    for fichero in (DESIGN_SYSTEM, SHIMS):
        if not fichero.exists():
            continue
        fuera, dentro = _partir_por_tema(_texto(fichero))
        for token, valor in DECL.findall(fuera):
            claro[token] = valor.strip()
        for token, valor in DECL.findall(dentro):
            oscuro_extra[token] = valor.strip()

    return {"light": claro, "dark": {**claro, **oscuro_extra}}


# ── Resolución de color ──────────────────────────────────────────────────────

class NoResoluble(Exception):
    pass


def resolver(token: str, tabla: dict[str, str], visitados: frozenset[str] = frozenset()) -> str:
    """Sigue la cadena `var(--a) → var(--b) → color literal`."""
    if token in visitados:
        raise NoResoluble(f"ciclo de tokens en {token}")
    if token not in tabla:
        raise NoResoluble(f"token no definido: {token}")
    valor = tabla[token]
    referencia = re.fullmatch(r"var\(\s*(--[A-Za-z0-9_-]+)\s*\)", valor)
    if referencia:
        return resolver(referencia.group(1), tabla, visitados | {token})
    return valor


def a_rgb(valor: str, fondo: tuple[float, float, float] | None = None) -> tuple[float, float, float]:
    """Color CSS → RGB 0-255. `rgba()` se compone sobre `fondo`."""
    valor = valor.strip()
    if valor.startswith("#"):
        h = valor[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            raise NoResoluble(f"hex no soportado: {valor}")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    rgba = re.fullmatch(r"rgba?\(([^)]+)\)", valor)
    if rgba:
        partes = [p.strip() for p in rgba.group(1).replace("/", ",").split(",")]
        r, g, b = (float(p) for p in partes[:3])
        alfa = float(partes[3]) if len(partes) > 3 else 1.0
        if alfa >= 1.0:
            return (r, g, b)
        if fondo is None:
            raise NoResoluble(f"{valor} necesita un fondo para componerse")
        return tuple(alfa * c + (1 - alfa) * f for c, f in zip((r, g, b), fondo))  # type: ignore[return-value]

    if valor == "white":
        return (255.0, 255.0, 255.0)
    if valor == "black":
        return (0.0, 0.0, 0.0)
    raise NoResoluble(f"color no soportado: {valor}")


def luminancia(rgb: tuple[float, float, float]) -> float:
    def canal(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = luminancia(a), luminancia(b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


# ── Medición ─────────────────────────────────────────────────────────────────

def componer(fondo: Fondo, tabla: dict[str, str]) -> tuple[float, float, float]:
    """Apila las capas de fondo de abajo arriba y devuelve el color resultante."""
    capas = (fondo,) if isinstance(fondo, str) else fondo
    resultado: tuple[float, float, float] | None = None
    for capa in capas:
        resultado = a_rgb(resolver(capa, tabla), fondo=resultado)
    assert resultado is not None, "la pila de fondo no puede estar vacía"
    return resultado


def _nombrar(fondo: Fondo) -> str:
    return fondo if isinstance(fondo, str) else " sobre ".join(reversed(fondo))


def medir() -> list[tuple[str, str, str, float, float, bool, str]]:
    """[(tema, nombre, detalle, ratio, umbral, pasa, nivel)] para cada par y tema."""
    tablas = tokens_por_tema()
    filas = []
    for tema in TEMAS:
        tabla = tablas[tema]
        for nombre, frente, atras, umbral, nivel in PARES:
            try:
                rgb_fondo = componer(atras, tabla)
                rgb_frente = a_rgb(resolver(frente, tabla), fondo=rgb_fondo)
            except NoResoluble as exc:
                filas.append((tema, nombre, f"{frente} / {_nombrar(atras)} — {exc}", 0.0, umbral, False, nivel))
                continue
            ratio = contraste(rgb_frente, rgb_fondo)
            filas.append(
                (tema, nombre, f"{frente} / {_nombrar(atras)}", ratio, umbral, ratio >= umbral, nivel)
            )
    return filas


def main() -> int:
    parser = argparse.ArgumentParser(description="Contraste WCAG AA de los componentes base")
    parser.add_argument("--table", action="store_true", help="Imprime todos los pares medidos")
    args = parser.parse_args()

    filas = medir()
    fallos = [f for f in filas if not f[5] and f[6] == AA]
    avisos = [f for f in filas if not f[5] and f[6] == AVISO]

    if args.table:
        for tema in TEMAS:
            print(f"\n── tema {tema} ──")
            for t, nombre, detalle, ratio, umbral, pasa, nivel in filas:
                if t != tema:
                    continue
                marca = "  ok " if pasa else ("FALLA" if nivel == AA else "aviso")
                print(f"  {marca} {ratio:5.2f}:1  (min {umbral})  {nombre:30s} {detalle}")
        print()

    for tema, nombre, detalle, ratio, umbral, _, _ in avisos:
        print(f"[aviso] [{tema}] {nombre}: {ratio:.2f}:1 — {detalle}"
              " (separador decorativo: WCAG no le fija umbral)")
    if avisos:
        print()

    if fallos:
        print(f"[FALLO] {len(fallos)} par(es) por debajo de WCAG 2.1 AA:\n")
        for tema, nombre, detalle, ratio, umbral, _, _ in fallos:
            print(f"  [{tema}] {nombre}: {ratio:.2f}:1 < {umbral} — {detalle}")
        print(
            "\nSube el contraste del **token** del design system, no el del componente:\n"
            "un par que falla aquí falla en todos los sitios donde se usa ese token.\n"
            "Para ver la tabla entera:  python scripts/check_contrast.py --table"
        )
        return 1

    bloqueantes = sum(1 for f in filas if f[6] == AA)
    print(f"[OK] {bloqueantes} pares cumplen WCAG 2.1 AA en {' y '.join(TEMAS)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
