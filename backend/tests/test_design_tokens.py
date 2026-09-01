"""Colores del frontend tokenizados y con guardia automática (SPEC-003 / T7.1).

Criterios cubiertos:

* **AC1** — ningún color hexadecimal literal en `frontend/src`; todo color sale de
  un token del design system.
* **AC5** — existe una comprobación automatizable que valida AC1, y **muerde**: los
  tests de abajo la ejecutan contra código sembrado a propósito, porque un lint que
  no se prueba solo demuestra que hoy no hay hallazgos, no que sepa encontrarlos.

La excepción de `paperTheme.js` se prueba en los dos sentidos: que el lint la exime
y que sigue siendo cierta —esos hexes son el espejo de `_THEME_ACCENTS` del
backend—. Una excepción que deja de tener motivo es peor que no tenerla.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

SCRIPT = REPO_DIR / "scripts" / "check_design_tokens.py"
FUENTE = REPO_DIR / "frontend" / "src"
PAPER_THEME_JS = FUENTE / "paperTheme.js"
CI_WORKFLOW = REPO_DIR / ".github" / "workflows" / "ci.yml"


def _cargar_script():
    spec = importlib.util.spec_from_file_location("check_design_tokens", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def lint():
    return _cargar_script()


def _ejecutar() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=str(REPO_DIR)
    )


# ── AC5: la comprobación existe y está en la CI ──────────────────────────────

def test_el_script_existe_y_es_ejecutable_sin_dependencias():
    """Solo stdlib: si necesitara instalar algo, la CI tendría que pagarlo."""
    assert SCRIPT.exists(), "falta scripts/check_design_tokens.py (AC5)"
    fuente = SCRIPT.read_text(encoding="utf-8")
    importados = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_][\w.]*)", fuente, re.M))
    externos = importados - set(sys.stdlib_module_names) - {"__future__"}
    assert not externos, f"el lint importa dependencias externas: {sorted(externos)}"


def test_la_ci_ejecuta_la_comprobacion():
    """AC5 pide una comprobación *automatizada*: un script que nadie corre no lo es."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/check_design_tokens.py" in workflow


# ── AC1: el estado actual pasa ───────────────────────────────────────────────

def test_el_frontend_actual_pasa_el_lint():
    resultado = _ejecutar()
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_no_hay_hexes_literales(lint):
    assert lint.hexes_literales() == []


def test_todos_los_var_resuelven(lint):
    """Un `var(--inexistente)` sin fallback no pinta nada y no avisa."""
    assert lint.tokens_rotos() == []


# ── AC5: el lint muerde de verdad ────────────────────────────────────────────

@pytest.fixture
def fichero_sembrado():
    """Crea y borra un fichero dentro de `frontend/src` para probar el lint."""
    creados: list[Path] = []

    def _crear(nombre: str, contenido: str) -> Path:
        ruta = FUENTE / nombre
        assert not ruta.exists(), f"{nombre} ya existe; el test lo pisaría"
        ruta.write_text(contenido, encoding="utf-8")
        creados.append(ruta)
        return ruta

    yield _crear
    for ruta in creados:
        ruta.unlink(missing_ok=True)


def test_detecta_un_hex_literal_reintroducido(fichero_sembrado):
    fichero_sembrado("__lint_probe__.jsx", "export const c = { color: '#2e844a' };\n")
    resultado = _ejecutar()
    assert resultado.returncode == 1
    assert "#2e844a" in resultado.stdout
    assert "__lint_probe__.jsx" in resultado.stdout


def test_detecta_un_token_inexistente(fichero_sembrado):
    fichero_sembrado(
        "__lint_probe_var__.jsx",
        "export const c = { color: 'var(--token-que-no-existe)' };\n",
    )
    resultado = _ejecutar()
    assert resultado.returncode == 1
    assert "--token-que-no-existe" in resultado.stdout


def test_ignora_los_hexes_en_comentarios(fichero_sembrado):
    fichero_sembrado(
        "__lint_probe_comment__.jsx",
        "// antes esto era #2e844a, ahora es un token\n"
        "export const c = { color: 'var(--agent-format)' };\n",
    )
    resultado = _ejecutar()
    assert resultado.returncode == 0, resultado.stdout


def test_acepta_tokens_definidos_en_los_shims_de_src(fichero_sembrado):
    """`--paper-surface` vive en `src/index.css`, no en `ds/`: también cuenta."""
    fichero_sembrado(
        "__lint_probe_shim__.jsx",
        "export const c = { background: 'var(--paper-surface)' };\n",
    )
    resultado = _ejecutar()
    assert resultado.returncode == 0, resultado.stdout


# ── La excepción documentada sigue teniendo motivo ───────────────────────────

def test_paper_theme_esta_exento_con_motivo(lint):
    assert PAPER_THEME_JS.name in lint.EXCEPCIONES
    motivo = lint.EXCEPCIONES[PAPER_THEME_JS.name]
    assert len(motivo) > 40, "la excepción debe explicar por qué, no solo eximir"


def test_paper_theme_js_es_espejo_de_los_acentos_del_backend():
    """Si el backend cambia la paleta del PDF, la muestra debe cambiar con él."""
    from app.modules.agents.adapters.paper_layout import _THEME_ACCENTS

    js = PAPER_THEME_JS.read_text(encoding="utf-8")
    pares = re.findall(
        r"value:\s*'([a-z]+)'\s*,\s*label:\s*'[^']*'\s*,\s*hex:\s*'(#[0-9a-fA-F]{6})'", js
    )
    assert pares, "no se pudo leer PAPER_ACCENTS de paperTheme.js"
    del_js = {clave: valor.lower() for clave, valor in pares}
    del_backend = {clave: valor.lower() for clave, valor in _THEME_ACCENTS.items()}
    assert del_js == del_backend


def test_paper_design_page_usa_la_constante_compartida():
    """Y no una copia local que se desincronice en silencio."""
    pagina = (FUENTE / "pages" / "PaperDesignPage.jsx").read_text(encoding="utf-8")
    assert "PAPER_ACCENTS" in pagina
    assert "paperTheme" in pagina
