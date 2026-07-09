"""Deterministic paper-layout generator for the Publicador agent.

Turns an article's markdown body + title-block metadata into a self-contained,
printable HTML document (one template per scientific citation format). No LLM and
no external dependencies: a minimal markdown->HTML converter keeps the backend
dependency-free, and all CSS is inlined so the result can be rendered in an
iframe (``srcdoc``) and exported to PDF straight from the browser.
"""
import html
import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Per-format layout configuration
# Each scientific format maps to the visual conventions of its community.
# ---------------------------------------------------------------------------
_FORMAT_STYLE: Dict[str, Dict[str, Any]] = {
    "ieee": {
        "label": "IEEE",
        "columns": 2,
        "line_height": 1.25,
        "font": "'Times New Roman', Times, serif",
        "size": "9.5pt",
        "title_size": "20pt",
    },
    "apa": {
        "label": "APA 7th edition",
        "columns": 1,
        "line_height": 2.0,
        "font": "'Times New Roman', Times, serif",
        "size": "11pt",
        "title_size": "18pt",
    },
    "vancouver": {
        "label": "Vancouver",
        "columns": 1,
        "line_height": 1.5,
        "font": "'Times New Roman', Times, serif",
        "size": "11pt",
        "title_size": "18pt",
    },
    "chicago": {
        "label": "Chicago 17th edition",
        "columns": 1,
        "line_height": 1.6,
        "font": "Georgia, 'Times New Roman', serif",
        "size": "11pt",
        "title_size": "18pt",
    },
    "nature": {
        "label": "Nature",
        "columns": 1,
        "line_height": 1.5,
        "font": "Helvetica, Arial, sans-serif",
        "size": "10.5pt",
        "title_size": "19pt",
    },
}

_DEFAULT_FORMAT = "apa"


def _style_for(scientific_format: str) -> Dict[str, Any]:
    return _FORMAT_STYLE.get((scientific_format or "").lower(), _FORMAT_STYLE[_DEFAULT_FORMAT])


# ---------------------------------------------------------------------------
# Minimal markdown -> HTML conversion
# Supports the subset emitted by the Redactor/Formateador: headings, bold,
# italic, inline code, links, ordered/unordered lists and paragraphs.
# ---------------------------------------------------------------------------
def _inline(text: str) -> str:
    """Apply inline markdown formatting to already plain (un-escaped) text."""
    # Protect nothing fancy — escape first, then re-introduce safe tags.
    out = html.escape(text, quote=False)
    # links [text](url)  (escape already turned & into &amp;, urls are simple)
    out = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        out,
    )
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def markdown_to_html(md: str) -> str:
    """Convert a markdown string to an HTML fragment (block-level)."""
    if not md:
        return ""

    lines = md.replace("\r\n", "\n").split("\n")
    html_parts: List[str] = []
    paragraph: List[str] = []
    list_buffer: List[str] = []
    list_type: str | None = None  # "ul" | "ol"

    def flush_paragraph() -> None:
        if paragraph:
            html_parts.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_type
        if list_buffer:
            items = "".join(f"<li>{_inline(it)}</li>" for it in list_buffer)
            html_parts.append(f"<{list_type}>{items}</{list_type}>")
            list_buffer.clear()
            list_type = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            html_parts.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue

        ul = re.match(r"^[-*+]\s+(.*)$", stripped)
        ol = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if ul or ol:
            flush_paragraph()
            new_type = "ul" if ul else "ol"
            if list_type and list_type != new_type:
                flush_list()
            list_type = new_type
            list_buffer.append((ul or ol).group(1))
            continue

        # plain text → accumulate into a paragraph
        flush_list()
        paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Title block (authors + affiliations + abstract)
# ---------------------------------------------------------------------------
def _authors_block(authors: List[Dict[str, Any]]) -> str:
    if not authors:
        return ""
    cells = []
    for a in authors:
        name = html.escape((a.get("name") or "").strip())
        if not name:
            continue
        affiliation = html.escape((a.get("affiliation") or "").strip())
        email = (a.get("email") or "").strip()
        email_html = (
            f'<div class="author-email">{html.escape(email)}</div>' if email else ""
        )
        aff_html = (
            f'<div class="author-affil">{affiliation}</div>' if affiliation else ""
        )
        cells.append(
            f'<div class="author">'
            f'<div class="author-name">{name}</div>{aff_html}{email_html}'
            f"</div>"
        )
    if not cells:
        return ""
    return f'<div class="authors">{"".join(cells)}</div>'


# ---------------------------------------------------------------------------
# Per-format stylesheet
# ---------------------------------------------------------------------------
def _stylesheet(scientific_format: str) -> str:
    s = _style_for(scientific_format)
    columns = s["columns"]
    content_columns = (
        f"column-count: {columns}; column-gap: 28px; column-fill: balance;"
        if columns > 1
        else "max-width: 720px; margin: 0 auto;"
    )
    return f"""
    :root {{ color-scheme: light; }}
    @page {{ size: A4; margin: 18mm 16mm; }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: {s['font']};
      font-size: {s['size']};
      line-height: {s['line_height']};
      color: #111;
      background: #f3f4f6;
      margin: 0;
      padding: 24px;
    }}
    .sheet {{
      background: #fff;
      max-width: 820px;
      margin: 0 auto;
      padding: 40px 48px 56px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }}
    .paper-title {{
      font-size: {s['title_size']};
      font-weight: 700;
      text-align: center;
      line-height: 1.2;
      margin: 0 0 18px;
    }}
    .authors {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 8px 48px;
      margin-bottom: 24px;
    }}
    .author {{ text-align: center; font-size: 10pt; }}
    .author-name {{ font-weight: 600; font-size: 11pt; }}
    .author-affil {{ color: #333; white-space: pre-line; }}
    .author-email {{ color: #444; font-family: 'Courier New', monospace; font-size: 9pt; }}
    .abstract {{
      margin: 0 auto 22px;
      max-width: 680px;
      font-size: {('9pt' if columns > 1 else '10.5pt')};
    }}
    .abstract h2 {{
      font-size: 11pt;
      text-align: center;
      margin: 0 0 6px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .abstract p {{ text-align: justify; margin: 0; }}
    .paper-body {{ {content_columns} text-align: justify; hyphens: auto; }}
    .paper-body h1, .paper-body h2 {{
      font-size: 11.5pt; font-weight: 700; margin: 14px 0 6px;
      break-after: avoid;
    }}
    .paper-body h3, .paper-body h4 {{ font-size: 10.5pt; font-weight: 700; margin: 10px 0 4px; }}
    .paper-body p {{ margin: 0 0 8px; orphans: 2; widows: 2; }}
    .paper-body ul, .paper-body ol {{ margin: 0 0 8px 1.1em; padding: 0; }}
    .paper-body code {{ font-family: 'Courier New', monospace; font-size: 0.92em; }}
    .paper-body a {{ color: #1a4f8b; text-decoration: none; word-break: break-word; }}
    .paper-body h2:last-of-type ~ p {{ font-size: 0.95em; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .sheet {{ box-shadow: none; max-width: none; padding: 0; }}
    }}
    """


def build_paper_html(
    *,
    title: str,
    authors: List[Dict[str, Any]],
    abstract: str,
    body_markdown: str,
    scientific_format: str,
) -> str:
    """Assemble a complete, self-contained printable HTML document.

    The body markdown is expected to already carry the reformatted in-text
    citations and the deterministic references section produced by the
    Formateador; this function only lays it out.
    """
    fmt = (scientific_format or _DEFAULT_FORMAT).lower()
    style = _style_for(fmt)

    safe_title = html.escape((title or "Untitled").strip())
    authors_html = _authors_block(authors or [])
    abstract_html = ""
    if abstract and abstract.strip():
        abstract_html = (
            f'<section class="abstract"><h2>Abstract</h2>'
            f"<p>{_inline(abstract.strip())}</p></section>"
        )
    body_html = markdown_to_html(body_markdown)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{safe_title}</title>
<meta name="citation-format" content="{html.escape(style['label'])}" />
<style>{_stylesheet(fmt)}</style>
</head>
<body>
<main class="sheet" data-format="{html.escape(fmt)}">
  <h1 class="paper-title">{safe_title}</h1>
  {authors_html}
  {abstract_html}
  <div class="paper-body">
{body_html}
  </div>
</main>
</body>
</html>"""
