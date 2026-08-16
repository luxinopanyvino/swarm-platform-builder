"""ACL conference preset for the paper layout (SPEC-022 / T11.1 / AC1).

The layout is deterministic HTML+CSS (no LLM, no browser), so every assertion
here is made on structural and CSS markers of the generated document.
"""
import re

import pytest

from app.modules.agents.adapters.paper_layout import build_paper_html

BODY = """## 1. Introducción

Primer párrafo de la introducción.

### 1.1 Motivación

Detalle de la motivación.

## 2. Método

Descripción del método.

## Referencias

[1] P. Lewis et al., "Retrieval-Augmented Generation", NeurIPS, 2020.

[2] S. Yao et al., "ReAct", ICLR, 2023.
"""

AUTHORS = [{"name": "L. San Martín", "affiliation": "CCHIA", "email": "a@b.cl"}]


def paper(fmt: str = "acl") -> str:
    return build_paper_html(
        title="Orquestación multi-agente",
        authors=AUTHORS,
        abstract="Resumen del artículo.",
        body_markdown=BODY,
        scientific_format=fmt,
    )


# --------------------------------------------------------------------------- #
# AC1 — two columns, serif, justified, numbered sections, hanging references
# --------------------------------------------------------------------------- #

def test_acl_is_two_columns():
    html = paper()
    assert "column-count: 2" in html
    assert 'data-format="acl"' in html


def test_acl_uses_serif_and_justified_text():
    html = paper()
    assert "'Times New Roman', Times, serif" in html
    assert "text-align: justify" in html


def test_acl_numbers_sections_with_css_counters():
    html = paper()
    # Counter is initialised, incremented and rendered — no hard-coded numbers.
    assert "counter-reset: section" in html
    assert "counter-increment: section" in html
    assert 'content: counter(section)' in html
    # Subsections render as "N.M".
    assert 'content: counter(section) "." counter(subsection)' in html


def test_acl_tags_headings_for_numbering():
    html = paper()
    assert '<h2 class="section-heading">Introducción</h2>' in html
    assert '<h3 class="subsection-heading">Motivación</h3>' in html


def test_acl_strips_manual_numbering_to_avoid_duplication():
    """The body already says "## 1. Introducción"; the counter supplies the number."""
    html = paper()
    assert ">1. Introducción<" not in html
    assert ">1.1 Motivación<" not in html


def test_acl_references_section_is_not_numbered():
    html = paper()
    assert '<h2 class="references-heading">Referencias</h2>' in html
    assert ".paper-body h2.references-heading::before { content: none; }" in html


def test_acl_references_have_hanging_indent():
    html = paper()
    block = re.search(
        r"\.paper-body h2\.references-heading ~ p \{(.*?)\}", paper(), re.DOTALL
    )
    assert block, "missing hanging-indent rule for the reference list"
    rule = block.group(1)
    assert "text-indent: -1.2em" in rule   # first line flush left
    assert "padding-left: 1.2em" in rule   # continuation lines indented
    assert "text-indent: -1.2em" in html


@pytest.mark.parametrize("label", ["Referencias", "References", "Bibliografía"])
def test_reference_heading_labels_are_recognised(label):
    html = build_paper_html(
        title="T", authors=[], abstract="", body_markdown=f"## {label}\n\n[1] X.",
        scientific_format="acl",
    )
    assert 'class="references-heading"' in html


# --------------------------------------------------------------------------- #
# Regression — other formats keep their previous output
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("fmt", ["apa", "ieee", "vancouver", "chicago", "nature"])
def test_other_formats_are_not_decorated_or_numbered(fmt):
    html = paper(fmt)
    assert "counter-increment: section" not in html
    assert "section-heading" not in html
    assert "references-heading" not in html
    # Manual numbering is preserved for formats that do not auto-number.
    assert "1. Introducción" in html


def test_ieee_remains_two_columns_and_apa_single():
    assert "column-count: 2" in paper("ieee")
    assert "column-count" not in paper("apa")


def test_unknown_format_still_falls_back_to_default():
    html = paper("does-not-exist")
    assert 'data-format="does-not-exist"' in html
    assert "counter-increment: section" not in html  # default (apa) is not numbered


def test_layout_is_deterministic():
    assert paper() == paper()
