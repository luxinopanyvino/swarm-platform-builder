"""Per-project asset store for paper figures (SPEC-022 / T11.5).

Images live in a **project-scoped** directory, separate from the RAG store:
Qdrant holds embeddings, not binaries, and keeping figures out of it preserves
the per-project isolation of E8 (a project can only ever reach its own assets).

Assets are referenced from the article body as ``![alt](asset:<id>)`` and are
inlined as ``data:`` URIs when the paper is laid out, so the generated HTML stays
**self-contained** — which is what lets it render inside a locked-down
``sandbox=""`` iframe and print to PDF with no further requests.
"""
import base64
import re
import uuid
from pathlib import Path
from typing import Optional

# Canonical type → (extension, mime). Mirrors what uploads.sniff_type detects.
_IMAGE_TYPES = {
    "png": (".png", "image/png"),
    "jpeg": (".jpg", "image/jpeg"),
    "gif": (".gif", "image/gif"),
    "webp": (".webp", "image/webp"),
}

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Figures are embedded as data URIs, so a large file inflates every render of
# the paper. 5 MB is generous for a figure and keeps the document manageable.
MAX_IMAGE_BYTES = 5 * 1024 * 1024

_ASSET_REF_RE = re.compile(r"^asset:([0-9a-f]{32})$", re.IGNORECASE)
_ID_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


def _assets_root() -> Path:
    """Base directory of the store, next to the RAG local fallback."""
    for candidate in (Path("app/.assets"), Path("../app/.assets")):
        if candidate.parent.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    fallback = Path("app/.assets")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _project_dir(project_id: str) -> Path:
    """Directory for a project's assets.

    ``project_id`` is constrained to hex so it can never escape the store via
    ``..`` or an absolute path.
    """
    safe = re.sub(r"[^0-9a-fA-F]", "", str(project_id or ""))[:32]
    if not safe:
        safe = "__none__"
    directory = _assets_root() / safe
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_image(project_id: str, raw: bytes, detected_type: str) -> str:
    """Persist an already-validated image and return its asset id."""
    ext, _mime = _IMAGE_TYPES[detected_type]
    asset_id = uuid.uuid4().hex
    (_project_dir(project_id) / f"{asset_id}{ext}").write_bytes(raw)
    return asset_id


def load_image(project_id: str, asset_id: str) -> Optional[tuple]:
    """Return ``(bytes, mime)`` for an asset of this project, or ``None``."""
    if not _ID_RE.match(str(asset_id or "")):
        return None
    directory = _project_dir(project_id)
    for ext, mime in _IMAGE_TYPES.values():
        path = directory / f"{asset_id}{ext}"
        if path.exists():
            return path.read_bytes(), mime
    return None


def parse_asset_ref(ref: str) -> Optional[str]:
    """Extract the asset id from an ``asset:<id>`` reference."""
    match = _ASSET_REF_RE.match((ref or "").strip())
    return match.group(1).lower() if match else None


def make_project_resolver(project_id: str):
    """Build the ``asset:<id>`` → data-URI resolver used by the paper layout.

    Scoped to one project on purpose: an article can only ever inline figures
    belonging to its own project, even if the body references another id.
    """
    def resolve(ref: str) -> Optional[str]:
        asset_id = parse_asset_ref(ref)
        if not asset_id:
            return None
        found = load_image(project_id, asset_id)
        if not found:
            return None
        raw, mime = found
        return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    return resolve
