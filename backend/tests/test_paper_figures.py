"""Figures in the paper layout (SPEC-022 / T11.5 / AC5).

Images are referenced as ``![alt](asset:<id>)`` and inlined as data URIs when the
paper is laid out, so the document stays self-contained: it renders inside the
locked-down ``sandbox=""`` iframe and prints to PDF with no further requests.
"""
import base64

import pytest

from app.platform import assets
from app.modules.agents.adapters.paper_layout import build_paper_html, markdown_to_html

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
GIF = b"GIF89a" + b"\x00" * 20


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the asset store at a temp dir so tests never touch the real one."""
    monkeypatch.setattr(assets, "_assets_root", lambda: tmp_path)
    return tmp_path


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #

def test_saved_image_round_trips(store):
    asset_id = assets.save_image("proj1", PNG, "png")
    raw, mime = assets.load_image("proj1", asset_id)
    assert raw == PNG
    assert mime == "image/png"


def test_assets_are_isolated_per_project(store):
    """E8 isolation: a project can never reach another project's figures."""
    asset_id = assets.save_image("proj1", PNG, "png")
    assert assets.load_image("proj2", asset_id) is None


def test_unknown_asset_returns_none(store):
    assert assets.load_image("proj1", "0" * 32) is None


@pytest.mark.parametrize("evil", ["../../etc/passwd", "..", "/absolute", "' OR 1=1"])
def test_traversal_in_ids_and_projects_is_neutralised(store, evil):
    assert assets.load_image(evil, evil) is None
    assert assets.parse_asset_ref(f"asset:{evil}") is None


def test_parse_asset_ref():
    valid = "a" * 32
    assert assets.parse_asset_ref(f"asset:{valid}") == valid
    assert assets.parse_asset_ref("asset:not-hex") is None
    assert assets.parse_asset_ref("https://example.com/x.png") is None


# --------------------------------------------------------------------------- #
# AC5 — the figure appears in the generated layout
# --------------------------------------------------------------------------- #

def test_asset_reference_is_inlined_as_a_data_uri(store):
    asset_id = assets.save_image("proj1", PNG, "png")
    resolver = assets.make_project_resolver("proj1")

    html = markdown_to_html(f"![Figura 1](asset:{asset_id})", resolver)

    assert "<figure" in html and "<img" in html
    assert f"data:image/png;base64,{base64.b64encode(PNG).decode()}" in html
    assert "<figcaption>Figura 1</figcaption>" in html


def test_figure_appears_in_the_full_paper(store):
    asset_id = assets.save_image("proj1", GIF, "gif")
    html = build_paper_html(
        title="T", authors=[], abstract="",
        body_markdown=f"## Resultados\n\n![Gráfico](asset:{asset_id})",
        scientific_format="ieee",
        asset_resolver=assets.make_project_resolver("proj1"),
    )
    assert "data:image/gif;base64" in html
    assert ".paper-figure" in html          # the figure styling is present


def test_figure_from_another_project_is_dropped(store):
    asset_id = assets.save_image("proj1", PNG, "png")
    resolver = assets.make_project_resolver("proj2")

    html = markdown_to_html(f"![Ajena](asset:{asset_id})", resolver)

    assert "<img" not in html


def test_missing_asset_is_dropped_without_breaking_the_paragraph(store):
    resolver = assets.make_project_resolver("proj1")
    html = markdown_to_html(f"Antes ![X](asset:{'b' * 32}) después", resolver)

    assert "<img" not in html
    assert "Antes" in html and "después" in html


# --------------------------------------------------------------------------- #
# Only safe sources may be embedded
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ref", [
    "javascript:alert(1)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "http://insecure.example/x.png",       # plain http
    "file:///etc/passwd",
    "vbscript:msgbox(1)",
])
def test_unsafe_image_sources_are_dropped(ref):
    html = markdown_to_html(f"![x]({ref})")
    assert "<img" not in html
    assert "javascript:" not in html and "text/html" not in html


@pytest.mark.parametrize("ref", [
    "data:image/png;base64,AAAA",
    "https://example.org/figura.png",
])
def test_safe_image_sources_are_kept(ref):
    html = markdown_to_html(f"![x]({ref})")
    assert "<img" in html


def test_alt_text_is_escaped():
    html = markdown_to_html('![<script>alert(1)</script>](data:image/png;base64,AAAA)')
    assert "<script>" not in html


def test_links_still_work_next_to_images():
    """The image rule runs first; a plain link must not be eaten by it."""
    html = markdown_to_html("[texto](https://example.org) y ![f](data:image/png;base64,AA)")
    assert '<a href="https://example.org">texto</a>' in html
    assert "<img" in html


def test_body_without_images_is_unchanged(store):
    plain = "## Sección\n\nTexto normal con [enlace](https://x.org)."
    assert markdown_to_html(plain) == markdown_to_html(plain, assets.make_project_resolver("p"))
