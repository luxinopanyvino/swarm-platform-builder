"""Accesibilidad AA en modales (SPEC-003 / T7.2 / AC2 + AC3).

Dos capas, porque cada una coge lo que la otra no puede:

* **Estructural** (siempre corre): que ninguna página vuelva a montar un modal a
  mano. El contrato de teclado solo se cumple si todos pasan por `<Modal>`; un
  `div.modal-backdrop` suelto lo salta entero y no rompe nada visible.
* **De teclado, en un navegador de verdad** (se salta si no hay Chromium): un
  focus trap no se puede comprobar leyendo el código. Depende de qué considera
  enfocable el navegador, de en qué orden, y de heurísticas como `:focus-visible`.
  El banco `frontend/a11y/` construye el componente **real** y lo conduce con
  teclas de verdad.

Esta segunda capa encontró tres fallos que la lectura del código no dio:
el `overflow` del body no se restauraba al cerrar dos modales anidados, `Esc`
cerraba los dos de golpe, y `transition: all` en `.btn` hacía que el anillo de
foco entrase animado —durante ~200 ms no era ni azul ni de 2px—.
"""
import json
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
MODAL = FUENTE / "components" / "ui" / "Modal.jsx"
INDEX_CSS = FUENTE / "index.css"
BANCO = FRONT / "a11y"
CI_WORKFLOW = REPO_DIR / ".github" / "workflows" / "ci.yml"
CONTRASTE = REPO_DIR / "scripts" / "check_contrast.py"

CHROMIUM = os.environ.get("A11Y_CHROMIUM") or next(
    (
        str(p)
        for p in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    ),
    None,
)


# ── Capa estructural: nadie monta un modal a mano ────────────────────────────

def _paginas():
    return [
        f
        for f in sorted(FUENTE.rglob("*.jsx"))
        if f != MODAL and f.is_relative_to(FUENTE)
    ]


def test_solo_el_componente_pinta_el_velo():
    """`modal-backdrop` fuera de `Modal.jsx` es un modal que se salta el contrato."""
    culpables = [
        str(f.relative_to(REPO_DIR))
        for f in _paginas()
        if "modal-backdrop" in f.read_text(encoding="utf-8")
    ]
    assert culpables == [], (
        "estos ficheros montan el velo a mano en vez de usar <Modal>: " + str(culpables)
    )


def test_ninguna_pagina_declara_su_propio_dialog():
    """`role="dialog"` a mano implica un diálogo sin trampa de foco ni Esc."""
    culpables = []
    for f in _paginas():
        texto = f.read_text(encoding="utf-8")
        if re.search(r'role\s*=\s*[\'"]dialog[\'"]', texto):
            culpables.append(str(f.relative_to(REPO_DIR)))
    assert culpables == []


def test_el_dialogo_se_anuncia_en_el_panel_y_no_en_el_velo():
    """El velo es la parte oscurecida; anunciarlo como diálogo mete el fondo dentro."""
    fuente = MODAL.read_text(encoding="utf-8")
    velo = fuente[fuente.index('className="modal-backdrop"'):fuente.index("ref={panelRef}")]
    assert "role=" not in velo and "aria-modal" not in velo
    panel = fuente[fuente.index("ref={panelRef}"):]
    assert 'role="dialog"' in panel
    assert 'aria-modal="true"' in panel
    assert "aria-labelledby" in panel


@pytest.mark.parametrize(
    "pieza",
    [
        "Escape",                    # AC2: Esc cierra
        "evento.key !== 'Tab'",      # AC2: trampa de foco
        "disparadorRef",             # AC2: el foco vuelve al disparador
        "document.body.style.overflow",  # el fondo no se desplaza detrás
    ],
)
def test_el_componente_implementa_el_contrato(pieza):
    assert pieza in MODAL.read_text(encoding="utf-8")


# ── Foco visible ─────────────────────────────────────────────────────────────

def test_hay_estilo_de_foco_visible():
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert ":focus-visible {" in css
    bloque = css[css.index(":focus-visible {"):]
    bloque = bloque[:bloque.index("}")]
    assert "outline:" in bloque and "var(--border-focus)" in bloque
    assert "outline-offset:" in bloque, (
        "el anillo debe dibujarse fuera del control: pegado a un botón del mismo "
        "color no se distingue"
    )


#: Cubre tanto el CSS (`outline: none`) como el estilo en línea de JSX
#: (`outline: 'none'`), que además gana a cualquier regla de la hoja.
APAGA_OUTLINE = re.compile(r"""outline\s*:\s*['"]?(none|0)\b""")
COMENTARIO = re.compile(r"//.*$|/\*.*?\*/", re.S | re.M)


def test_nadie_apaga_el_outline_sin_reemplazarlo():
    """`outline: none` es la forma habitual de dejar la aplicación sin foco visible."""
    culpables = []
    for fichero in list(FUENTE.rglob("*.css")) + list(FUENTE.rglob("*.jsx")):
        texto = COMENTARIO.sub(
            lambda m: re.sub(r"\S", " ", m.group(0)),
            fichero.read_text(encoding="utf-8"),
        )
        for numero, linea in enumerate(texto.splitlines(), 1):
            if APAGA_OUTLINE.search(linea):
                culpables.append(f"{fichero.relative_to(REPO_DIR)}:{numero}")
    assert culpables == [], f"outline apagado sin indicador alternativo: {culpables}"


def test_la_transicion_de_los_botones_no_arrastra_el_outline():
    """Con `transition: all`, el anillo de foco entra animado y tarda en existir."""
    css = INDEX_CSS.read_text(encoding="utf-8")
    bloque = css[css.index(".btn {"):]
    bloque = bloque[:bloque.index("}")]
    assert "transition: all" not in bloque


# ── AC3: contraste ───────────────────────────────────────────────────────────

def test_los_pares_base_cumplen_aa():
    resultado = subprocess.run(
        [sys.executable, str(CONTRASTE)], capture_output=True, text=True, cwd=str(REPO_DIR)
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_la_ci_mide_el_contraste():
    assert "scripts/check_contrast.py" in CI_WORKFLOW.read_text(encoding="utf-8")


def test_el_checklist_de_contraste_cubre_los_componentes_base():
    """AC3 nombra botones, badges e inputs: los tres tienen que estar medidos."""
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_contrast", CONTRASTE)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    nombres = " ".join(fila[0] for fila in modulo.PARES)
    for componente in ("btn-primary", "btn-secondary", "badge-", "input ·"):
        assert componente in nombres, f"sin medir: {componente}"


# ── Capa de teclado: el componente real, en Chromium ─────────────────────────

@pytest.fixture(scope="module")
def pagina():
    playwright = pytest.importorskip(
        "playwright.sync_api", reason="playwright no instalado"
    )
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
        [sys.executable, "-m", "http.server", "8907", "--bind", "127.0.0.1"],
        cwd=str(BANCO / "dist"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    with playwright.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=CHROMIUM)
        pg = navegador.new_page()
        for _ in range(50):
            try:
                pg.goto("http://127.0.0.1:8907/index.html")
                break
            except Exception:  # el servidor aún no escucha
                pg.wait_for_timeout(100)
        yield pg
        navegador.close()
    servidor.terminate()
    servidor.wait(timeout=10)


def _esperar_foco_en_el_modal_de_arriba(pg):
    """El primer enfocable de un modal es su botón de cerrar, no su primer campo."""
    pg.wait_for_function(
        "() => { const ds = document.querySelectorAll('[role=dialog]');"
        " const arriba = ds[ds.length - 1];"
        " return arriba && arriba.contains(document.activeElement); }"
    )


def _activo(pg):
    return pg.evaluate("() => document.activeElement?.id || document.activeElement?.tagName")


@pytest.fixture
def modal_abierto(pagina):
    pagina.goto("http://127.0.0.1:8907/index.html")
    pagina.click("#disparador")
    pagina.wait_for_selector("[role=dialog]")
    pagina.wait_for_function(
        "() => document.querySelector('.modal').contains(document.activeElement)"
    )
    return pagina


def test_teclado_el_foco_entra_al_abrir(modal_abierto):
    dentro = modal_abierto.eval_on_selector(
        ".modal", "e => e.contains(document.activeElement)"
    )
    assert dentro, "sin esto, Tab sigue recorriendo la página de detrás"


def test_teclado_el_foco_no_se_escapa_con_tab(modal_abierto):
    visitados = []
    for _ in range(12):
        modal_abierto.keyboard.press("Tab")
        visitados.append(_activo(modal_abierto))
        assert modal_abierto.eval_on_selector(
            ".modal", "e => e.contains(document.activeElement)"
        ), f"el foco salió del modal en {visitados}"
    # Y da la vuelta en vez de quedarse clavado en el último.
    assert len(set(visitados)) > 1
    assert visitados[0] in visitados[1:]


def test_teclado_shift_tab_da_la_vuelta_hacia_atras(modal_abierto):
    for _ in range(10):
        modal_abierto.keyboard.press("Shift+Tab")
        assert modal_abierto.eval_on_selector(
            ".modal", "e => e.contains(document.activeElement)"
        )


def test_teclado_el_anillo_de_foco_es_visible_e_inmediato(modal_abierto):
    modal_abierto.keyboard.press("Tab")
    contorno = modal_abierto.evaluate(
        "() => { const s = getComputedStyle(document.activeElement);"
        " return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.outlineOffset]; }"
    )
    estilo, ancho, color, desplazamiento = contorno
    assert estilo not in ("none", ""), contorno
    # Sin animación de por medio: se mide justo después de la tecla.
    assert float(ancho.rstrip("px")) >= 2, contorno
    assert float(desplazamiento.rstrip("px")) >= 2, contorno
    assert color == "rgb(1, 118, 211)", contorno  # --border-focus del tema claro


def test_teclado_escape_cierra_y_devuelve_el_foco(modal_abierto):
    modal_abierto.keyboard.press("Escape")
    modal_abierto.wait_for_selector("[role=dialog]", state="detached")
    assert _activo(modal_abierto) == "disparador", (
        "cerrar y dejar el foco en body es perder el sitio en la página"
    )


def test_teclado_escape_solo_cierra_el_modal_de_arriba(modal_abierto):
    modal_abierto.click("#anidar")
    modal_abierto.wait_for_selector("#campo-interior")
    _esperar_foco_en_el_modal_de_arriba(modal_abierto)
    assert modal_abierto.eval_on_selector_all("[role=dialog]", "e => e.length") == 2
    modal_abierto.keyboard.press("Escape")
    modal_abierto.wait_for_function(
        "() => document.querySelectorAll('[role=dialog]').length === 1"
    )
    assert modal_abierto.eval_on_selector_all("[role=dialog]", "e => e.length") == 1


def test_teclado_el_scroll_del_fondo_se_restaura(modal_abierto):
    """Con dos anidados: React limpia el contenedor antes que el hijo."""
    modal_abierto.click("#anidar")
    modal_abierto.wait_for_selector("#campo-interior")
    _esperar_foco_en_el_modal_de_arriba(modal_abierto)
    assert modal_abierto.evaluate("() => document.body.style.overflow") == "hidden"
    modal_abierto.keyboard.press("Escape")   # cierra el interior
    modal_abierto.wait_for_function(
        "() => document.querySelectorAll('[role=dialog]').length === 1"
    )
    assert modal_abierto.evaluate("() => document.body.style.overflow") == "hidden", (
        "el fondo no debe desplazarse mientras quede un modal abierto"
    )
    modal_abierto.keyboard.press("Escape")   # cierra el exterior
    modal_abierto.wait_for_selector("[role=dialog]", state="detached")
    assert modal_abierto.evaluate("() => document.body.style.overflow") == ""


def test_teclado_un_modal_sin_controles_tampoco_deja_escapar_el_foco(pagina):
    pagina.goto("http://127.0.0.1:8907/index.html")
    pagina.click("#disparador-vacio")
    pagina.wait_for_selector("[role=dialog]")
    pagina.wait_for_function(
        "() => document.querySelector('.modal') === document.activeElement"
    )
    pagina.keyboard.press("Tab")
    assert pagina.eval_on_selector(".modal", "e => e.contains(document.activeElement)")


def test_teclado_el_velo_no_cierra_si_el_gesto_empieza_dentro(modal_abierto):
    """Seleccionar texto dentro y soltar fuera no debe descartar lo escrito."""
    modal_abierto.fill("#campo-1", "algo escrito")
    caja = modal_abierto.eval_on_selector(
        "#campo-1", "e => { const r = e.getBoundingClientRect(); return [r.x + 5, r.y + 5]; }"
    )
    modal_abierto.mouse.move(caja[0], caja[1])
    modal_abierto.mouse.down()
    modal_abierto.mouse.move(5, 5)          # se suelta sobre el velo
    modal_abierto.mouse.up()
    assert modal_abierto.eval_on_selector_all("[role=dialog]", "e => e.length") == 1
    assert modal_abierto.input_value("#campo-1") == "algo escrito"
