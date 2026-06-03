"""RAG utilities: text extraction, chunking, embedding and Qdrant persistence."""
import asyncio
import hashlib
import io
import json
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


def _local_rag_root() -> Path:
    for candidate in (Path("app/.rag_local"), Path("../app/.rag_local")):
        if candidate.parent.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    root = Path("app/.rag_local")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _local_collection_dir(collection: str) -> Path:
    # Sanitize: strip path separators, dots sequences, and control chars
    safe_name = collection.replace("/", "_").replace("\\", "_").strip()
    # Reject path traversal attempts (e.g. "..", "...", "../x")
    if not safe_name or safe_name in (".", "..") or ".." in safe_name.split("_"):
        safe_name = "rag_docs"
    # Only allow alphanumeric, hyphens, underscores
    import re as _re
    safe_name = _re.sub(r"[^a-zA-Z0-9_\-]", "_", safe_name) or "rag_docs"
    directory = _local_rag_root() / safe_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _local_document_path(collection: str, doc_id: str) -> Path:
    return _local_collection_dir(collection) / f"{doc_id}.json"


def _load_local_document(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        logger.warning(f"Could not read local RAG document '{path}': {error}")
        return None


async def is_qdrant_available(qdrant_url: str, api_key: Optional[str] = None) -> bool:
    """Return whether the configured Qdrant instance is reachable."""
    headers = {"api-key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=5.0, headers=headers) as client:
            response = await client.get("/collections")
            return response.status_code == 200
    except Exception:
        return False


async def get_rag_backend(qdrant_url: str, api_key: Optional[str] = None) -> str:
    return "qdrant" if await is_qdrant_available(qdrant_url, api_key) else "local"

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(filename: str, raw_bytes: bytes) -> str:
    """Return plain text from a .txt, .md, or .pdf file."""
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning(f"PDF extraction failed for {filename}: {e}")
            return ""
    # txt / md and anything else
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks of approximately chunk_size characters."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # If para itself is bigger than chunk_size, split by words
            if len(para) > chunk_size:
                words = para.split()
                buf = ""
                for word in words:
                    if len(buf) + len(word) + 1 <= chunk_size:
                        buf = (buf + " " + word).strip()
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = word
                if buf:
                    current = buf
                else:
                    current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    # Apply overlap: prepend last `overlap` chars of previous chunk to each chunk
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            overlapped.append((tail + " " + chunks[i]).strip())
        return overlapped

    return chunks


# ---------------------------------------------------------------------------
# Embeddings — provider-aware (Ollama or OpenAI-compatible)
# ---------------------------------------------------------------------------

async def get_embedding(text: str, ollama_base_url: str, model: str) -> Optional[List[float]]:
    """
    Request an embedding vector from the configured provider.

    When ``settings.LLM_PROVIDER == "openai"`` the OpenAI Embeddings API is
    used (``settings.OPENAI_EMBED_MODEL``); otherwise falls back to Ollama.
    The ``ollama_base_url`` and ``model`` parameters are kept for backwards
    compatibility and are used only when provider is "ollama".
    """
    from app.core.config import settings  # lazy to avoid circular imports

    if settings.LLM_PROVIDER.lower() == "openai":
        return await _get_embedding_openai(text)
    return await _get_embedding_ollama(text, ollama_base_url, model)


async def _get_embedding_ollama(text: str, ollama_base_url: str, model: str) -> Optional[List[float]]:
    """Embed via Ollama /api/embeddings."""
    try:
        async with httpx.AsyncClient(base_url=ollama_base_url, timeout=60.0) as client:
            resp = await client.post("/api/embeddings", json={"model": model, "prompt": text})
            if resp.status_code == 200:
                return resp.json().get("embedding")
    except Exception as e:
        logger.warning("Ollama embedding failed: %s", e)
    return None


async def _get_embedding_openai(text: str) -> Optional[List[float]]:
    """Embed via OpenAI Embeddings API (or any OpenAI-compatible endpoint)."""
    from app.core.config import settings
    try:
        import openai  # optional dependency — only needed when provider=openai
        client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )
        response = await client.embeddings.create(
            input=text,
            model=settings.OPENAI_EMBED_MODEL,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning("OpenAI embedding failed: %s", e)
    return None


def _fallback_vector(text: str, size: int) -> List[float]:
    """Deterministic pseudo-vector based on text hash. Used when Ollama is unavailable."""
    h = hashlib.sha256(text.encode()).digest()
    floats = []
    for i in range(size):
        byte_val = h[i % len(h)]
        floats.append((byte_val - 128) / 128.0)
    return floats


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------

async def ensure_collection(
    qdrant_url: str,
    collection: str,
    vector_size: int,
    api_key: Optional[str] = None,
) -> None:
    """Create the Qdrant collection if it does not already exist."""
    if not await is_qdrant_available(qdrant_url, api_key):
        _local_collection_dir(collection)
        return

    headers = {"api-key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=10.0, headers=headers) as client:
            check = await client.get(f"/collections/{collection}")
            if check.status_code == 404:
                payload = {
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine",
                    }
                }
                await client.put(f"/collections/{collection}", json=payload)
                logger.info(f"Created Qdrant collection '{collection}' with size={vector_size}")
    except Exception as e:
        logger.warning(f"Could not ensure Qdrant collection '{collection}': {e}")


async def upsert_chunks(
    qdrant_url: str,
    collection: str,
    doc_id: str,
    agent_name: str,
    filename: str,
    chunks: List[str],
    ollama_base_url: str,
    embedding_model: str,
    vector_size: int,
    api_key: Optional[str] = None,
) -> int:
    """Embed and upsert chunks into Qdrant. Returns count of inserted points."""
    if not await is_qdrant_available(qdrant_url, api_key):
        payload = {
            "doc_id": doc_id,
            "agent_name": agent_name,
            "filename": filename,
            "chunks": [
                {
                    "chunk_index": index,
                    "text": chunk,
                }
                for index, chunk in enumerate(chunks)
            ],
        }
        _local_document_path(collection, doc_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return len(chunks)

    headers = {"api-key": api_key} if api_key else {}
    points = []

    # Embed all chunks in parallel (batches of 20 to avoid overloading Ollama)
    _EMBED_BATCH = 20

    async def _embed_one(idx: int, text: str):
        vec = await get_embedding(text, ollama_base_url, embedding_model)
        if vec is None or len(vec) != vector_size:
            vec = _fallback_vector(text, vector_size)
        else:
            vec = vec[:vector_size]
        return idx, vec

    vectors: list = [None] * len(chunks)
    for batch_start in range(0, len(chunks), _EMBED_BATCH):
        batch = chunks[batch_start: batch_start + _EMBED_BATCH]
        results = await asyncio.gather(
            *[_embed_one(batch_start + j, chunk) for j, chunk in enumerate(batch)]
        )
        for idx, vec in results:
            vectors[idx] = vec

    for i, chunk in enumerate(chunks):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}:{i}"))
        points.append({
            "id": point_id,
            "vector": vectors[i],
            "payload": {
                "doc_id": doc_id,
                "agent_name": agent_name,
                "filename": filename,
                "chunk_index": i,
                "text": chunk,
            },
        })

    if not points:
        return 0

    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=30.0, headers=headers) as client:
            resp = await client.put(
                f"/collections/{collection}/points?wait=true",
                json={"points": points},
            )
            if resp.status_code not in (200, 206):
                logger.error(f"Qdrant upsert failed: {resp.status_code} {resp.text}")
                return 0
    except Exception as e:
        logger.exception("Qdrant upsert error")
        return 0

    return len(points)


async def list_documents(
    qdrant_url: str,
    collection: str,
    agent_name: str,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return unique documents (by doc_id) stored for a given agent."""
    if not await is_qdrant_available(qdrant_url, api_key):
        docs = []
        for path in _local_collection_dir(collection).glob("*.json"):
            data = _load_local_document(path)
            if not data or data.get("agent_name") != agent_name:
                continue
            docs.append({
                "doc_id": data.get("doc_id", path.stem),
                "filename": data.get("filename", "unknown"),
                "agent_name": agent_name,
                "chunks": len(data.get("chunks", [])),
            })
        return sorted(docs, key=lambda item: item["filename"].lower())

    headers = {"api-key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=10.0, headers=headers) as client:
            # Check collection exists first
            check = await client.get(f"/collections/{collection}")
            if check.status_code != 200:
                return []

            payload = {
                "filter": {
                    "must": [{"key": "agent_name", "match": {"value": agent_name}}]
                },
                "limit": 500,
                "with_payload": True,
                "with_vector": False,
            }
            resp = await client.post(f"/collections/{collection}/points/scroll", json=payload)
            if resp.status_code != 200:
                return []

            points = resp.json().get("result", {}).get("points", [])
            seen: Dict[str, Dict] = {}
            for p in points:
                pl = p.get("payload", {})
                doc_id = pl.get("doc_id")
                if doc_id and doc_id not in seen:
                    seen[doc_id] = {
                        "doc_id": doc_id,
                        "filename": pl.get("filename", "unknown"),
                        "agent_name": agent_name,
                        "chunks": 0,
                    }
                if doc_id:
                    seen[doc_id]["chunks"] += 1

            return list(seen.values())
    except Exception as e:
        logger.warning(f"list_documents error: {e}")
        return []


async def delete_document(
    qdrant_url: str,
    collection: str,
    doc_id: str,
    api_key: Optional[str] = None,
) -> bool:
    """Delete all Qdrant points belonging to a doc_id."""
    if not await is_qdrant_available(qdrant_url, api_key):
        path = _local_document_path(collection, doc_id)
        if path.exists():
            path.unlink()
            return True
        return False

    headers = {"api-key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=10.0, headers=headers) as client:
            payload = {
                "filter": {
                    "must": [{"key": "doc_id", "match": {"value": doc_id}}]
                }
            }
            resp = await client.post(f"/collections/{collection}/points/delete?wait=true", json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"delete_document error: {e}")
        return False


async def list_library_documents(
    qdrant_url: str,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return all collections and their unique documents (no agent filter).

    Each entry: {collection, doc_id, filename, agent_name, chunks}
    """
    if not await is_qdrant_available(qdrant_url, api_key):
        results: List[Dict[str, Any]] = []
        root = _local_rag_root()
        if not root.exists():
            return results
        for collection_dir in sorted(root.iterdir()):
            if not collection_dir.is_dir():
                continue
            for doc_path in sorted(collection_dir.glob("*.json")):
                data = _load_local_document(doc_path)
                if not data:
                    continue
                results.append({
                    "collection": collection_dir.name,
                    "doc_id": data.get("doc_id", doc_path.stem),
                    "filename": data.get("filename", doc_path.stem),
                    "agent_name": data.get("agent_name", ""),
                    "chunks": len(data.get("chunks", [])),
                })
        return results

    headers = {"api-key": api_key} if api_key else {}
    results: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=10.0, headers=headers) as client:
            col_resp = await client.get("/collections")
            if col_resp.status_code != 200:
                return results
            collection_names = [c["name"] for c in col_resp.json().get("result", {}).get("collections", [])]

            for collection_name in collection_names:
                offset = None
                seen: Dict[str, Dict] = {}
                while True:
                    body: Dict[str, Any] = {
                        "limit": 250,
                        "with_payload": True,
                        "with_vector": False,
                    }
                    if offset is not None:
                        body["offset"] = offset
                    scroll_resp = await client.post(
                        f"/collections/{collection_name}/points/scroll", json=body
                    )
                    if scroll_resp.status_code != 200:
                        break
                    scroll_result = scroll_resp.json().get("result", {})
                    points = scroll_result.get("points", [])
                    next_offset = scroll_result.get("next_page_offset")
                    for p in points:
                        pl = p.get("payload", {})
                        doc_id = pl.get("doc_id")
                        if not doc_id:
                            continue
                        if doc_id not in seen:
                            seen[doc_id] = {
                                "collection": collection_name,
                                "doc_id": doc_id,
                                "filename": pl.get("filename", "unknown"),
                                "agent_name": pl.get("agent_name", ""),
                                "chunks": 0,
                            }
                        seen[doc_id]["chunks"] += 1
                    if not next_offset or not points:
                        break
                    offset = next_offset
                results.extend(seen.values())
    except Exception as error:
        logger.warning(f"list_library_documents error: {error}")
    return results


async def fetch_agent_context(
    qdrant_url: str,
    collection: str,
    agent_name: str,
    limit: int = 5,
    api_key: Optional[str] = None,
) -> str:
    """Return a compact text block with chunks for an agent from Qdrant or local fallback.
    Simple scroll by agent_name — no semantic ranking. Use semantic_search_context for
    keyword-based relevance ranking."""
    if not await is_qdrant_available(qdrant_url, api_key):
        texts: List[str] = []
        for path in sorted(_local_collection_dir(collection).glob("*.json")):
            data = _load_local_document(path)
            if not data or data.get("agent_name") != agent_name:
                continue
            for chunk in data.get("chunks", []):
                text = chunk.get("text", "")
                if text:
                    texts.append(text)
                if len(texts) >= limit:
                    return "\n\n---\n\n".join(texts)
        return "\n\n---\n\n".join(texts)

    headers = {"api-key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=5.0, headers=headers) as client:
            check = await client.get(f"/collections/{collection}")
            if check.status_code != 200:
                return ""

            payload = {
                "filter": {
                    "must": [{"key": "agent_name", "match": {"value": agent_name}}]
                },
                "limit": limit,
                "with_payload": True,
                "with_vector": False,
            }
            resp = await client.post(f"/collections/{collection}/points/scroll", json=payload)
            if resp.status_code != 200:
                return ""

            points = resp.json().get("result", {}).get("points", [])
            chunks = [p.get("payload", {}).get("text", "") for p in points if p.get("payload", {}).get("text")]
            return "\n\n---\n\n".join(chunks)
    except Exception as error:
        logger.warning(f"RAG fetch failed for agent '{agent_name}': {error}")
        return ""


async def semantic_search_context(
    query: str,
    qdrant_url: str,
    collection: str,
    agent_name: str,
    ollama_base_url: str,
    embedding_model: str,
    limit: int = 5,
    score_threshold: float = 0.0,
    api_key: Optional[str] = None,
    doc_ids: Optional[list] = None,
) -> str:
    """Semantic search: embed the query and retrieve the most relevant chunks from
    Qdrant filtered by agent_name (and optionally by doc_ids). Falls back to
    fetch_agent_context when Qdrant is unavailable or embedding fails."""
    if not await is_qdrant_available(qdrant_url, api_key):
        return await fetch_agent_context(qdrant_url, collection, agent_name, limit, api_key)

    # Embed the query
    query_vector = await get_embedding(query, ollama_base_url, embedding_model)
    if query_vector is None:
        logger.warning("semantic_search_context: embedding failed, falling back to scroll")
        return await fetch_agent_context(qdrant_url, collection, agent_name, limit, api_key)

    headers = {"api-key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(base_url=qdrant_url, timeout=10.0, headers=headers) as client:
            check = await client.get(f"/collections/{collection}")
            if check.status_code != 200:
                return ""

            payload: Dict[str, Any] = {
                "vector": query_vector,
                "filter": {
                    "must": [{"key": "agent_name", "match": {"value": agent_name}}]
                },
                "limit": limit,
                "with_payload": True,
                "with_vector": False,
            }
            # Narrow search to specific documents when the user selected individual files
            if doc_ids:
                payload["filter"]["must"].append(
                    {"key": "doc_id", "match": {"any": doc_ids}}
                )
            if score_threshold > 0.0:
                payload["score_threshold"] = score_threshold

            resp = await client.post(f"/collections/{collection}/points/search", json=payload)
            if resp.status_code != 200:
                logger.warning(f"Qdrant search returned {resp.status_code}: {resp.text[:200]}")
                return await fetch_agent_context(qdrant_url, collection, agent_name, limit, api_key)

            results = resp.json().get("result", [])
            chunks = [
                r.get("payload", {}).get("text", "")
                for r in results
                if r.get("payload", {}).get("text")
            ]
            logger.info(f"semantic_search_context: {len(chunks)} chunks returned for query '{query[:60]}'")
            return "\n\n---\n\n".join(chunks)
    except Exception as error:
        logger.warning(f"Semantic RAG search failed for agent '{agent_name}': {error}")
        return await fetch_agent_context(qdrant_url, collection, agent_name, limit, api_key)
