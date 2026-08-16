"""Upload validation by real content (SPEC-016 / T2.3 / AC2).

An extension allowlist only checks the *claimed* type; these tests pin down that
the bytes themselves are checked, so a renamed payload is rejected before it is
parsed, indexed or served back.
"""
import pytest
from fastapi import HTTPException

from app.platform.uploads import sniff_type, validate_upload

DOCS = {".txt", ".md", ".pdf"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

PDF = b"%PDF-1.7\n1 0 obj\n<< >>\nendobj\n"
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 20
GIF = b"GIF89a" + b"\x00" * 20
WEBP = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + b"\x00" * 20
TEXT = "Un documento de texto plano.\nCon acentos: ñ á é.\n".encode("utf-8")


# --------------------------------------------------------------------------- #
# Sniffing
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw,expected", [
    (PDF, "pdf"), (PNG, "png"), (JPEG, "jpeg"), (GIF, "gif"), (WEBP, "webp"), (TEXT, "text"),
])
def test_sniff_recognises_known_types(raw, expected):
    assert sniff_type(raw) == expected


@pytest.mark.parametrize("raw", [
    b"",                                  # empty
    b"\x00\x01\x02\x03binary junk",       # NUL → binary of unknown kind
    b"\x7fELF\x02\x01\x01\x00",           # ELF executable
])
def test_sniff_rejects_unknown_or_binary(raw):
    assert sniff_type(raw) is None


@pytest.mark.parametrize("markup", [
    b"<!DOCTYPE html><html><body>hi</body></html>",
    b"<html><script>alert(1)</script></html>",
    b"  <svg onload=alert(1)></svg>",
    b"<?xml version='1.0'?><root/>",
])
def test_markup_is_not_accepted_as_text(markup):
    """Markup uploaded as .txt/.md is the stored-XSS vector; never call it text."""
    assert sniff_type(markup) is None


# --------------------------------------------------------------------------- #
# AC2 — content must match the declared extension
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("filename,raw", [
    ("doc.pdf", PDF), ("notas.txt", TEXT), ("readme.md", TEXT),
])
def test_valid_documents_pass(filename, raw):
    assert validate_upload(filename, raw, DOCS)


@pytest.mark.parametrize("filename,raw", [
    ("imagen.png", PNG), ("foto.jpg", JPEG), ("foto.jpeg", JPEG),
    ("anim.gif", GIF), ("moderna.webp", WEBP),
])
def test_valid_images_pass(filename, raw):
    assert validate_upload(filename, raw, IMAGES)


@pytest.mark.parametrize("filename,raw", [
    ("fake.pdf", TEXT),          # text claiming to be a PDF
    ("fake.pdf", PNG),           # image claiming to be a PDF
    ("fake.txt", PDF),           # PDF renamed to .txt
    ("fake.md", PNG),            # image renamed to .md
])
def test_mismatched_content_is_rejected_with_400(filename, raw):
    with pytest.raises(HTTPException) as ei:
        validate_upload(filename, raw, DOCS)
    assert ei.value.status_code == 400


@pytest.mark.parametrize("filename,raw", [
    ("evil.png", b"<html><script>alert(1)</script></html>"),
    ("evil.png", PDF),
    ("evil.jpg", PNG),           # right family, wrong format
    ("evil.webp", GIF),
])
def test_mismatched_images_are_rejected_with_400(filename, raw):
    with pytest.raises(HTTPException) as ei:
        validate_upload(filename, raw, IMAGES)
    assert ei.value.status_code == 400


def test_disallowed_extension_is_415_not_400():
    """'You may not upload this kind' is a different answer from 'this is a lie'."""
    with pytest.raises(HTTPException) as ei:
        validate_upload("script.exe", PDF, DOCS)
    assert ei.value.status_code == 415


def test_image_extension_rejected_when_only_documents_are_allowed():
    with pytest.raises(HTTPException) as ei:
        validate_upload("foto.png", PNG, DOCS)
    assert ei.value.status_code == 415


def test_missing_filename_is_rejected():
    with pytest.raises(HTTPException):
        validate_upload("", PDF, DOCS)


def test_empty_file_is_rejected():
    with pytest.raises(HTTPException) as ei:
        validate_upload("vacio.txt", b"", DOCS)
    assert ei.value.status_code == 400


def test_extension_matching_is_case_insensitive():
    assert validate_upload("DOC.PDF", PDF, DOCS) == "pdf"
