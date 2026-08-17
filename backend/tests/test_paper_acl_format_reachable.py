"""El preset ACL tiene que ser *alcanzable*, no solo existir (SPEC-022 / E11).

`paper_layout` traía la plantilla ACL desde T11.1 y el panel de diseño (T11.4) la
ofrecía en su desplegable, pero `ScientificFormat` no incluía el valor: la petición
de preview con `scientific_format="acl"` moría en la validación del DTO con un
`422` y el preset era inalcanzable desde la interfaz.

Los tests de T11.1 no lo cogieron porque llamaban a `build_paper_html("acl")`
directamente, saltándose la capa que rechazaba el valor. Estos casos cubren la
cadena completa: enum → DTO → maquetación → bibliografía.
"""
import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_acl_format.db").resolve()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}")

from app.models.enums import ScientificFormat  # noqa: E402
from app.modules.agents.adapters.formateador import (  # noqa: E402
    _FORMAT_INSTRUCTIONS,
    _FORMAT_LABELS,
    format_source_deterministic,
)
from app.modules.agents.adapters.paper_layout import _FORMAT_STYLE, build_paper_html  # noqa: E402

SOURCE = {
    "title": "Attention Is All You Need",
    "authors": "Vaswani, A. and Shazeer, N.",
    "journal": "Advances in Neural Information Processing Systems",
    "year": "2017",
    "url": "https://arxiv.org/abs/1706.03762",
}


# --------------------------------------------------------------------------- #
# El valor existe en toda la cadena
# --------------------------------------------------------------------------- #

def test_acl_is_a_valid_scientific_format():
    """La regresión concreta: el enum rechazaba 'acl' y el DTO devolvía 422."""
    assert ScientificFormat("acl") is ScientificFormat.ACL


def test_every_layout_preset_is_selectable():
    """Ningún preset de maquetación puede quedar sin valor de enum que lo alcance.

    Es la invariante que faltaba: si alguien añade un preset a `_FORMAT_STYLE` y
    olvida el enum, el preset nace inalcanzable y nadie se entera.
    """
    selectable = {f.value for f in ScientificFormat}
    assert set(_FORMAT_STYLE) <= selectable, (
        f"presets sin valor en ScientificFormat: {set(_FORMAT_STYLE) - selectable}"
    )


def test_every_layout_preset_has_formateador_guidance():
    """Y a la inversa: un formato maquetable sin instrucción de cita cita en vacío."""
    for fmt in _FORMAT_STYLE:
        assert fmt in _FORMAT_LABELS, f"{fmt} sin etiqueta en el formateador"
        assert fmt in _FORMAT_INSTRUCTIONS, f"{fmt} sin instrucción de cita"


def test_preview_dto_accepts_acl():
    from app.routers.articles import PaperPreviewDTO

    req = PaperPreviewDTO(scientific_format="acl")
    assert req.scientific_format is ScientificFormat.ACL


def test_preview_dto_still_rejects_unknown_formats():
    from app.routers.articles import PaperPreviewDTO

    with pytest.raises(ValidationError):
        PaperPreviewDTO(scientific_format="mla")


# --------------------------------------------------------------------------- #
# Bibliografía ACL: autor-año, coherente con su cita en texto
# --------------------------------------------------------------------------- #

def test_acl_bibliography_is_author_year_not_numbered():
    """ACL caía al `else` numerado: citas (Autor et al., Año) y refs `[1]`."""
    ref = format_source_deterministic(SOURCE, "acl", 1)

    assert not ref.startswith("[1]") and not ref.startswith("1.")
    assert ref.startswith("Vaswani, A. and Shazeer, N. 2017.")
    assert "Attention Is All You Need" in ref
    assert "In Advances in Neural Information Processing Systems." in ref
    assert "https://arxiv.org/abs/1706.03762" in ref


def test_acl_in_text_instruction_stays_author_year():
    """Si esta instrucción cambia a numerada, la rama de bibliografía debe seguirla."""
    assert "author-year" in _FORMAT_INSTRUCTIONS["acl"]


def test_acl_bibliography_omits_missing_fields():
    ref = format_source_deterministic({"title": "Un título suelto"}, "acl", 3)
    assert "N/A" not in ref and "None" not in ref
    assert "Un título suelto" in ref
    assert not ref.startswith("[3]")


@pytest.mark.parametrize("style", ["ieee", "vancouver", "nature"])
def test_numbered_styles_are_untouched(style):
    """La rama nueva no debe robarle casos a los estilos numerados."""
    ref = format_source_deterministic(SOURCE, style, 1)
    assert ref.startswith("[1]") or ref.startswith("1.")


# --------------------------------------------------------------------------- #
# La maqueta ACL sigue siendo la de conferencia
# --------------------------------------------------------------------------- #

def test_acl_paper_renders_two_columns():
    html = build_paper_html(
        title="Un artículo de conferencia",
        authors=[{"name": "A. Investigadora", "affiliation": "Universidad X"}],
        abstract="Resumen breve.",
        body_markdown="## Introducción\n\nTexto del cuerpo.\n",
        scientific_format="acl",
    )
    assert "column-count: 2" in html or "columns: 2" in html
    assert "Un artículo de conferencia" in html
