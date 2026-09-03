"""Estados consistentes de carga / vacío / error (SPEC-003 / T7.3 / AC4 + AC5).

Dos capas, como en T7.2:

* **Estructural** (siempre corre): que ninguna vista pinte un estado a mano y que
  ningún error de carga se trague en silencio. Lo comprueba
  `scripts/check_async_states.py`, que además corre en la CI.
* **De navegador** (se salta si no hay Chromium): que los tres estados sean
  **distinguibles** y que el reintento funcione. Eso no se lee en el código: el
  fallo que motiva la tarea era precisamente que error y vacío se pintaban igual.

El defecto original: las páginas hacían `catch { setLoading(false) }` más un
`toast`. El toast se va a los pocos segundos y lo que queda es el estado vacío —
«Sin artículos, ejecuta un pipeline para generar tu primero»— cuando lo que ha
pasado es que no se ha podido preguntar. Y sin forma de reintentar.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

FRONT = REPO_DIR / "frontend"
FUENTE = FRONT / "src"
ESTADOS = FUENTE / "components" / "ui" / "states.jsx"
BANCO = FRONT / "a11y"
LINT = REPO_DIR / "scripts" / "check_async_states.py"
CI_WORKFLOW = REPO_DIR / ".github" / "workflows" / "ci.yml"

CHROMIUM = os.environ.get("A11Y_CHROMIUM") or next(
    (
        str(p)
        for p in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    ),
    None,
)


# ── Capa estructural ─────────────────────────────────────────────────────────

def test_existen_los_tres_componentes():
    """SPEC-003 §4 los nombra: LoadingState, EmptyState, ErrorState."""
    fuente = ESTADOS.read_text(encoding="utf-8")
    for componente in ("LoadingState", "EmptyState", "ErrorState", "AsyncState"):
        assert f"export function {componente}" in fuente


def test_el_lint_pasa_sobre_el_codigo_actual():
    resultado = subprocess.run(
        [sys.executable, str(LINT)], capture_output=True, text=True, cwd=str(REPO_DIR)
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_la_ci_ejecuta_el_lint():
    assert "scripts/check_async_states.py" in CI_WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture
def fichero_sembrado():
    creados = []

    def _crear(nombre: str, contenido: str) -> Path:
        ruta = FUENTE / nombre
        assert not ruta.exists(), f"{nombre} ya existe"
        ruta.write_text(contenido, encoding="utf-8")
        creados.append(ruta)
        return ruta

    yield _crear
    for ruta in creados:
        ruta.unlink(missing_ok=True)


def _ejecutar_lint():
    return subprocess.run(
        [sys.executable, str(LINT)], capture_output=True, text=True, cwd=str(REPO_DIR)
    )


def test_el_lint_detecta_un_estado_pintado_a_mano(fichero_sembrado):
    fichero_sembrado(
        "__probe_estado__.jsx",
        'export const X = () => <div className="empty-state">nada</div>;\n',
    )
    resultado = _ejecutar_lint()
    assert resultado.returncode == 1
    assert "__probe_estado__.jsx" in resultado.stdout


def test_el_lint_detecta_un_error_tragado(fichero_sembrado):
    fichero_sembrado(
        "__probe_catch__.js",
        "export const cargar = () => fetch('/x').then(r => r.json()).catch(() => {});\n",
    )
    resultado = _ejecutar_lint()
    assert resultado.returncode == 1
    assert "__probe_catch__.js" in resultado.stdout


def test_el_lint_acepta_un_fallo_ignorable_con_motivo(fichero_sembrado):
    """La excepción existe, pero obliga a escribir por qué."""
    fichero_sembrado(
        "__probe_marcado__.js",
        "export const sondeo = () =>\n"
        "  // mejor-esfuerzo: se reintenta cada 30 s por su cuenta\n"
        "  fetch('/x').catch(() => {});\n",
    )
    resultado = _ejecutar_lint()
    assert resultado.returncode == 0, resultado.stdout


def test_el_lint_no_confunde_hablar_del_patron_con_usarlo(fichero_sembrado):
    """Los comentarios de este repo mencionan `.catch(() => {})` al explicarlo."""
    fichero_sembrado(
        "__probe_comentario__.js",
        "// Antes esto era `.catch(() => {})` y se tragaba el error.\n"
        "export const cargar = () => fetch('/x').catch(e => { throw e; });\n",
    )
    resultado = _ejecutar_lint()
    assert resultado.returncode == 0, resultado.stdout


# ── Los stores guardan el error, que es lo que permite distinguir ───────────

@pytest.mark.parametrize(
    "store", ["articleStore.js", "flowStore.js", "projectStore.js"]
)
def test_los_stores_guardan_el_error_de_carga(store):
    fuente = (FUENTE / "store" / store).read_text(encoding="utf-8")
    assert re.search(r"set\(\{[^}]*error:", fuente), (
        f"{store} declara `error` pero nunca lo escribe: la página no puede "
        "distinguir «no hay datos» de «no he podido preguntarlo»"
    )


# ── Capa de navegador ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pagina():
    playwright = pytest.importorskip("playwright.sync_api", reason="playwright no instalado")
    if not CHROMIUM or not Path(CHROMIUM).exists():
        pytest.skip("no hay Chromium; exporta A11Y_CHROMIUM con la ruta del binario")
    if not shutil.which("npx"):
        pytest.skip("no hay npx para construir el banco de pruebas")

    construccion = subprocess.run(
        ["npx", "vite", "build", "--config", "a11y/vite.config.js"],
        cwd=str(FRONT), capture_output=True, text=True,
    )
    assert construccion.returncode == 0, construccion.stdout + construccion.stderr

    servidor = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8908", "--bind", "127.0.0.1"],
        cwd=str(BANCO / "dist"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    with playwright.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=CHROMIUM)
        pg = navegador.new_page()
        for _ in range(50):
            try:
                pg.goto("http://127.0.0.1:8908/states.html")
                break
            except Exception:
                pg.wait_for_timeout(100)
        yield pg
        navegador.close()
    servidor.terminate()
    servidor.wait(timeout=10)


@pytest.fixture
def banco(pagina):
    pagina.goto("http://127.0.0.1:8908/states.html")
    return pagina


def test_navegador_cargando_se_anuncia_como_estado(banco):
    banco.click("#modo-cargando")
    banco.wait_for_selector("[role=status]")
    assert banco.eval_on_selector("[role=status]", "e => e.getAttribute('aria-live')") == "polite"
    # El spinner solo no dice nada: hace falta texto para quien no lo ve.
    assert "Cargando" in banco.text_content("[role=status]")
    assert banco.eval_on_selector(
        "[role=status] .spinner", "e => e.getAttribute('aria-hidden')"
    ) == "true"


def test_navegador_el_error_interrumpe_y_el_vacio_no(banco):
    banco.click("#modo-vacio")
    banco.wait_for_selector("#zona .empty-state")
    assert banco.eval_on_selector_all("[role=alert]", "e => e.length") == 0, (
        "el vacío es un estado legítimo: no debe anunciarse como alerta"
    )
    banco.click("#modo-error")
    banco.wait_for_selector("[role=alert]")


def test_navegador_el_error_no_se_parece_al_vacio(banco):
    """El fallo original: los dos se pintaban igual y uno se leía como el otro."""
    banco.click("#modo-vacio")
    banco.wait_for_selector("#zona .empty-state")
    vacio = banco.eval_on_selector(
        "#zona .empty-state h3", "e => getComputedStyle(e).color"
    )
    texto_vacio = banco.text_content("#zona .empty-state")
    banco.click("#modo-error")
    banco.wait_for_selector("[role=alert]")
    error = banco.eval_on_selector("[role=alert] h3", "e => getComputedStyle(e).color")
    assert error != vacio, "el título del error usa el mismo color que el del vacío"
    assert banco.text_content("[role=alert]") != texto_vacio


def test_navegador_el_error_ofrece_reintentar_y_funciona(banco):
    banco.click("#modo-error")
    banco.wait_for_selector("[role=alert]")
    assert banco.text_content("#reintentos") == "0"
    banco.click("[role=alert] button")
    banco.wait_for_function("() => document.getElementById('reintentos').textContent === '1'")


def test_navegador_los_datos_ganan_a_cualquier_estado(banco):
    """Si hay algo que leer, ni el spinner ni el error lo tapan."""
    banco.click("#modo-datos")
    banco.wait_for_selector("#datos")
    assert banco.eval_on_selector_all("#zona .empty-state", "e => e.length") == 0
