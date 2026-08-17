"""Link sanitising in the paper layout (SPEC-016 / T2.2 / AC1).

The layout is rendered in an iframe and printed, so a hostile ``href`` in the
article body is a stored-XSS vector for every reader of the published paper.
Only schemes a paper legitimately uses survive.
"""
import pytest

from app.modules.agents.adapters.paper_layout import markdown_to_html


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "JavaScript:alert(1)",                 # scheme is case-insensitive
    "  javascript:alert(1)",               # leading whitespace is ignored by browsers
    "java\tscript:alert(1)",               # …and so are embedded control chars
    "data:text/html;base64,PHNjcmlwdD4=",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
])
def test_dangerous_schemes_are_dropped(url):
    """No anchor is emitted, so nothing is clickable and no scheme is live.

    Some of these (padded with whitespace) do not even match the link syntax and
    survive as literal markdown text — which is equally safe, and fails closed:
    the words are visible, no ``href`` exists.
    """
    html = markdown_to_html(f"Ver [aquí]({url}) el detalle.")

    assert "<a" not in html
    assert "href" not in html.lower()


def test_rejected_link_keeps_its_text():
    """The reader must still see the words, just not a live anchor."""
    html = markdown_to_html("Ver [el informe](javascript:alert(1)) completo.")

    assert "el informe" in html
    assert "<a" not in html


@pytest.mark.parametrize("url", [
    "https://example.org/paper.pdf",
    "http://example.org/x",
    "mailto:autor@example.org",
    "#seccion-3",
    "figuras/grafico.png",
])
def test_legitimate_links_survive(url):
    html = markdown_to_html(f"[texto]({url})")
    assert f'href="{url}"' in html


def test_quotes_in_url_cannot_break_out_of_the_attribute():
    html = markdown_to_html('[x](https://e.org/a"onmouseover=alert(1))')

    assert "onmouseover=alert(1)" not in html.replace("&quot;", '"').split('href="')[1].split('"')[0]
    assert "&quot;" in html or '"' not in html.split("href=")[1][1:].split('"')[0]


def test_doi_links_still_work():
    """The Formateador emits DOI links; they must not be collateral damage."""
    html = markdown_to_html("[1] Autor. https://doi.org/10.1000/xyz")
    assert "doi.org" in html


def test_reference_list_with_links_is_unaffected():
    body = "## Referencias\n\n[1] P. Lewis. RAG. https://doi.org/10.5555/1\n"
    html = markdown_to_html(body)
    assert "10.5555/1" in html
