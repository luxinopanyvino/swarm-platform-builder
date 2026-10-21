"""UX-002 — el estado vacío del lienzo queda centrado y no tapa la barra de acciones.

El contenedor era `position:absolute; inset:0` sin layout propio: el `EmptyState`
fluía desde arriba y se montaba sobre la barra de acciones flotante.
"""
import re
from pathlib import Path

FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"
PAGINA = (FRONT / "platform" / "pages" / "FlowDesignerPage.jsx").read_text(encoding="utf-8")
CSS = (FRONT / "index.css").read_text(encoding="utf-8")


def _regla(selector: str) -> str:
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\}", CSS, re.S)
    assert m, f"no encuentro {selector} en index.css"
    return m.group(1)


def test_el_contenedor_usa_la_clase_y_no_estilos_en_linea():
    assert '<div className="flow-empty">' in PAGINA


def test_el_contenedor_centra_y_deja_libre_la_barra_y_el_lienzo():
    regla = _regla(".flow-empty")
    assert "align-items: center" in regla and "justify-content: center" in regla
    assert "pointer-events: none" in regla  # no bloquea la interacción con el lienzo
    assert "padding: calc(" in regla        # reserva el hueco de la barra de acciones
