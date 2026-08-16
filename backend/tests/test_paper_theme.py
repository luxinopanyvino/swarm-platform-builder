"""Editable paper theme (SPEC-022 / T11.2 / AC2).

The user never writes CSS: they pick values from allowlists which override the
format preset. Anything unknown must fall back to the preset without breaking
the layout — that is what makes a stale or hostile stored theme harmless.
"""
import pytest

from app.modules.agents.adapters.paper_layout import (
    build_paper_html,
    resolve_theme,
    sanitize_theme,
)

BODY = "## 1. Introducción\n\nTexto del artículo.\n\n## Referencias\n\n[1] X."


def paper(theme=None, fmt="apa"):
    return build_paper_html(
        title="T", authors=[], abstract="A",
        body_markdown=BODY, scientific_format=fmt, theme=theme,
    )


# --------------------------------------------------------------------------- #
# Overriding the preset
# --------------------------------------------------------------------------- #

def test_theme_font_overrides_the_preset():
    # apa's preset font is Times; the theme switches it to a sans family.
    assert "Helvetica, Arial, sans-serif" in paper({"font": "helvetica"})
    assert "Helvetica, Arial, sans-serif" not in paper()


def test_theme_columns_override_the_preset():
    # apa is single-column by default.
    assert "column-count" not in paper()
    assert "column-count: 2" in paper({"columns": 2})


def test_theme_can_also_reduce_columns():
    # ieee is two-column by default; the theme brings it down to one.
    assert "column-count: 2" in paper(fmt="ieee")
    assert "column-count" not in paper({"columns": 1}, fmt="ieee")


def test_theme_accent_colours_headings_and_links():
    html = paper({"accent_color": "violet"})
    assert "#6b4fe3" in html


def test_default_accent_is_the_neutral_ink_token():
    assert "#0b1b33" in paper()


# --------------------------------------------------------------------------- #
# Invalid values fall back instead of breaking (AC2)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bad", [
    {"font": "comic-sans"},                 # not in the curated allowlist
    {"accent_color": "#ff0000"},            # raw hex, not a design token
    {"accent_color": "hotpink"},
    {"columns": 5},
    {"columns": 0},
    {"columns": True},                      # bool must not pass as int 1
    {"font": None, "accent_color": None},
    {"font": 123},
])
def test_invalid_values_are_dropped(bad):
    assert sanitize_theme(bad) == {}
    # …and the rendered paper is identical to the un-themed one.
    assert paper(bad) == paper()


@pytest.mark.parametrize("junk", [None, "", [], "font=helvetica", 42])
def test_non_dict_themes_are_ignored(junk):
    assert sanitize_theme(junk) == {}
    assert paper(junk) == paper()


def test_partial_theme_keeps_preset_for_the_rest():
    """Only the supplied key changes; the others stay on the preset."""
    html = paper({"font": "georgia"})
    assert "Georgia, 'Times New Roman', serif" in html
    assert "column-count" not in html          # apa stays single-column


def test_css_injection_attempt_is_dropped():
    hostile = {"font": "x; } body { display:none } .a{", "accent_color": "red;}*{color:red"}
    assert sanitize_theme(hostile) == {}
    assert "display:none" not in paper(hostile)


# --------------------------------------------------------------------------- #
# Cascade: project theme → article theme (AC2)
# --------------------------------------------------------------------------- #

def test_article_theme_overrides_project_theme():
    project = {"font": "georgia", "accent_color": "blue"}
    article = {"accent_color": "green"}

    resolved = resolve_theme(project, article)

    assert resolved["font"] == "georgia"        # inherited from the project
    assert resolved["accent_color"] == "green"  # article wins


def test_cascade_ignores_an_invalid_layer_without_losing_the_valid_one():
    resolved = resolve_theme({"font": "georgia"}, {"font": "comic-sans"})
    assert resolved == {"font": "georgia"}


def test_empty_cascade_is_empty():
    assert resolve_theme(None, {}) == {}


def test_theme_is_deterministic():
    t = {"font": "verdana", "accent_color": "teal", "columns": 2}
    assert paper(t) == paper(t)
