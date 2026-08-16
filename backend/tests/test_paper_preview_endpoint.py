"""Server-side paper preview endpoint (SPEC-022 / T11.3 / AC3).

The preview must be produced by the *same* layout function as the published
paper — that is the whole reason it lives on the server instead of being
re-implemented in the browser: preview == PDF.
"""
import pytest

from app.models import ArticleStatus, ScientificFormat, ThemeDTO, AuthorDTO
from app.modules.agents.adapters.paper_layout import build_paper_html
from app.routers.articles import PaperPreviewDTO, preview_article_paper


class _FakeArticle:
    def __init__(self, **kw):
        self.id = kw.get("id", "a1")
        self.title = kw.get("title", "Título guardado")
        self.body = kw.get("body", "## 1. Intro\n\nCuerpo guardado.")
        self.abstract = kw.get("abstract", "Abstract guardado.")
        self.authors = kw.get("authors", [{"name": "A. Autor"}])
        self.scientific_format = kw.get("scientific_format", ScientificFormat.APA)
        self.theme = kw.get("theme", {})
        self.project_id = None
        self.author_id = "u1"
        self.reviewer_id = None
        self.status = kw.get("status", ArticleStatus.DRAFT)


class _FakeSession:
    """Records whether anything was written — the preview must persist nothing."""
    def __init__(self, article):
        self._article = article
        self.committed = False
        self.added = []

    async def execute(self, _stmt):
        article = self._article

        class _R:
            def scalars(self_inner):
                class _S:
                    def first(self_s):
                        return article
                return _S()
        return _R()

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


ADMIN = {"role": "admin", "user_id": "someone-else"}


async def _preview(article, dto, token=ADMIN):
    session = _FakeSession(article)
    resp = await preview_article_paper(
        article_id=article.id, req=dto, token_data=token, session=session
    )
    return resp.body.decode(), session


# --------------------------------------------------------------------------- #
# AC3 — preview == PDF, from unsaved edits
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_preview_matches_build_paper_html_exactly():
    """Byte-identical to the published layout — same function, same inputs."""
    article = _FakeArticle()
    html, _ = await _preview(article, PaperPreviewDTO())

    expected = build_paper_html(
        title=article.title, authors=article.authors, abstract=article.abstract,
        body_markdown=article.body, scientific_format="apa", theme={},
    )
    assert html == expected


@pytest.mark.asyncio
async def test_preview_uses_unsaved_body():
    article = _FakeArticle()
    html, _ = await _preview(article, PaperPreviewDTO(body="## Nuevo\n\nTexto sin guardar."))

    assert "Texto sin guardar." in html
    assert "Cuerpo guardado." not in html


@pytest.mark.asyncio
async def test_preview_applies_an_unsaved_theme():
    article = _FakeArticle()
    html, _ = await _preview(article, PaperPreviewDTO(theme=ThemeDTO(columns=2, accent_color="violet")))

    assert "column-count: 2" in html   # apa is single-column by default
    assert "#6b4fe3" in html


@pytest.mark.asyncio
async def test_unsaved_theme_overrides_the_stored_one():
    article = _FakeArticle(theme={"accent_color": "green"})
    html, _ = await _preview(article, PaperPreviewDTO(theme=ThemeDTO(accent_color="red")))

    assert "#ba0517" in html      # request layer wins
    assert "#2e844a" not in html


@pytest.mark.asyncio
async def test_stored_theme_is_used_when_the_request_sends_none():
    article = _FakeArticle(theme={"accent_color": "teal"})
    html, _ = await _preview(article, PaperPreviewDTO())

    assert "#06a59a" in html


@pytest.mark.asyncio
async def test_fields_not_sent_fall_back_to_stored_values():
    article = _FakeArticle()
    html, _ = await _preview(article, PaperPreviewDTO(abstract="Abstract nuevo."))

    assert "Abstract nuevo." in html
    assert "Título guardado" in html          # untouched field preserved
    assert "Cuerpo guardado." in html


@pytest.mark.asyncio
async def test_preview_can_change_the_citation_format():
    article = _FakeArticle()
    html, _ = await _preview(article, PaperPreviewDTO(scientific_format=ScientificFormat.IEEE))

    assert 'data-format="ieee"' in html
    assert "column-count: 2" in html


@pytest.mark.asyncio
async def test_preview_accepts_unsaved_authors():
    article = _FakeArticle()
    html, _ = await _preview(article, PaperPreviewDTO(authors=[AuthorDTO(name="Nueva Autora")]))

    assert "Nueva Autora" in html
    assert "A. Autor" not in html


# --------------------------------------------------------------------------- #
# The preview must not persist anything
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_preview_persists_nothing():
    article = _FakeArticle()
    _, session = await _preview(
        article, PaperPreviewDTO(body="borrador efímero", theme=ThemeDTO(columns=2))
    )

    assert session.committed is False
    assert session.added == []
    assert article.body == "## 1. Intro\n\nCuerpo guardado."   # object untouched
    assert article.theme == {}


# --------------------------------------------------------------------------- #
# Visibility mirrors get_article_paper
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_preview_denied_for_unrelated_reader_on_a_draft():
    from fastapi import HTTPException

    article = _FakeArticle(status=ArticleStatus.DRAFT)
    with pytest.raises(HTTPException) as ei:
        await _preview(article, PaperPreviewDTO(), token={"role": "lector", "user_id": "nadie"})
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_preview_allowed_for_the_owner():
    article = _FakeArticle(status=ArticleStatus.DRAFT)
    html, _ = await _preview(article, PaperPreviewDTO(), token={"role": "lector", "user_id": "u1"})
    assert "Título guardado" in html


@pytest.mark.asyncio
async def test_missing_article_is_404():
    from fastapi import HTTPException

    session = _FakeSession(None)
    with pytest.raises(HTTPException) as ei:
        await preview_article_paper(
            article_id="nope", req=PaperPreviewDTO(), token_data=ADMIN, session=session
        )
    assert ei.value.status_code == 404
