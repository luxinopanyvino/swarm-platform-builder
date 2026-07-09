"""Document metadata extraction for RAG ingestion.

Best-effort extraction of a document's title and authors so the Investigador can
build real bibliographic citations instead of generic placeholders. Owned by the
research/sources pipeline (Investigador). Never raises — returns empty strings on
failure and the caller falls back to the cleaned filename.
"""
import io
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# Lines that signal we've passed the title block and should stop scanning.
_STOP_MARKERS = ("abstract", "resumen", "introduction", "introducción", "keywords", "palabras clave")

# Heuristic: a plausible author line (names, initials, commas, "and"/"y").
_AUTHOR_HINT = re.compile(r"^[A-ZÁÉÍÓÚÑ][\w.\-]+(?:\s+[A-ZÁÉÍÓÚÑ][\w.\-]+)*(?:\s*(?:,|and|y|&)\s*[A-ZÁÉÍÓÚÑ][\w.\-]+.*)?$")
_EMAIL = re.compile(r"[\w.\-]+@[\w.\-]+")


_JUNK_TITLES = {"untitled", "microsoft word", "pdf", "document", "title", "paper"}


def _clean_value(v: str) -> str:
    """Collapse whitespace/newlines that PDF metadata fields often contain."""
    return re.sub(r"\s+", " ", (v or "").strip())


def _pdf_metadata(raw_bytes: bytes) -> Dict[str, str]:
    """Read the embedded /Title and /Author fields from a PDF, if present."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw_bytes))
        meta = reader.metadata or {}
        title = _clean_value(meta.get("/Title"))
        author = _clean_value(meta.get("/Author"))
        # Reject junk titles (generator names, single words, "untitled", etc.).
        if title and (title.lower() in _JUNK_TITLES or len(title.split()) < 2):
            title = ""
        return {"title": title, "authors": author}
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("PDF metadata read failed: %s", exc)
        return {"title": "", "authors": ""}


def _pdf_first_page_text(raw_bytes: bytes) -> str:
    """Extract just the first page's text — the cleanest source for the title block."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw_bytes))
        if reader.pages:
            return reader.pages[0].extract_text() or ""
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("PDF first-page extract failed: %s", exc)
    return ""


def _looks_like_title(line: str) -> bool:
    if not line:
        return False
    low = line.lower()
    # Reject arXiv headers, DOIs, dates and other non-title boilerplate.
    if low.startswith("arxiv") or "arxiv:" in low or low.startswith("doi"):
        return False
    if re.match(r"^\d{3,}\.\d{3,}", line):  # bare arXiv id like 2604.25850
        return False
    words = line.split()
    if not (2 <= len(words) <= 25) or len(line) > 200 or _EMAIL.search(line):
        return False
    # A real title is mostly letters/spaces, not numbers or symbols.
    alpha = sum(c.isalpha() or c.isspace() for c in line)
    return alpha >= len(line) * 0.6


def _from_text(text: str) -> Dict[str, str]:
    """Infer title/authors from the first lines of the document body.

    Academic papers begin with: Title, then Authors, then affiliations, then the
    abstract. We take the first substantial line as the title and the following
    name-like line(s) as authors, stopping at the abstract.
    """
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]  # drop blank lines

    title = ""
    authors = ""
    for i, line in enumerate(lines[:15]):
        low = line.lower()
        if any(m in low for m in _STOP_MARKERS):
            break
        if not title and _looks_like_title(line):
            title = line
            # Look ahead for an author line within the next few lines.
            for cand in lines[i + 1:i + 5]:
                cl = cand.lower()
                if any(m in cl for m in _STOP_MARKERS):
                    break
                if _AUTHOR_HINT.match(cand) and not _looks_like_title(cand) or (
                    _AUTHOR_HINT.match(cand) and ("," in cand or " and " in cl or " y " in cl)
                ):
                    authors = cand
                    break
            break
    return {"title": title, "authors": authors}


def extract_doc_metadata(filename: str, raw_bytes: bytes, text: str) -> Dict[str, str]:
    """Return {'title', 'authors'} for a document, best-effort.

    Priority: embedded PDF metadata (most reliable) → first-page text heuristic
    → empty (caller falls back to the cleaned filename). Runs at ingestion, so
    the title/authors are stored alongside the vectors.
    """
    is_pdf = (filename or "").lower().endswith(".pdf")
    title = ""
    authors = ""

    if is_pdf and raw_bytes:
        pdf = _pdf_metadata(raw_bytes)
        title = pdf.get("title", "")
        authors = pdf.get("authors", "")

    if not title or not authors:
        # Prefer the PDF's first page (cleaner) over the full concatenated text.
        source_text = ""
        if is_pdf and raw_bytes:
            source_text = _pdf_first_page_text(raw_bytes)
        source_text = source_text or text
        guessed = _from_text(source_text)
        title = title or guessed.get("title", "")
        authors = authors or guessed.get("authors", "")

    # Reject obviously bad titles (e.g. just the filename or a single token).
    if title and len(title.split()) < 2:
        title = ""

    return {"title": _clean_value(title), "authors": _clean_value(authors)}
