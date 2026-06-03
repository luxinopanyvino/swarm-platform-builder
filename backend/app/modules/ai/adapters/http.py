from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.shared.llm import call_llm, get_default_model

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class IngestRequest(BaseModel):
    source_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class AssistRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    model: str | None = None


def _vectorize_text(text: str, dim: int) -> list[float]:
    """
    Vectorizador deterministico simple para demo RAG.
    No usa embeddings externos y permite probar Qdrant end-to-end.
    """
    buckets = [0.0] * dim
    for i, char in enumerate(text.lower()):
        buckets[(ord(char) + i) % dim] += 1.0

    norm = sum(value * value for value in buckets) ** 0.5
    if norm == 0:
        return buckets
    return [value / norm for value in buckets]


def _chunk_text(text: str, chunk_size: int = 400) -> list[str]:
    clean = " ".join(text.split())
    return [clean[i : i + chunk_size] for i in range(0, len(clean), chunk_size)]


async def _ensure_collection(client: httpx.AsyncClient) -> None:
    collection = settings.QDRANT_COLLECTION
    response = await client.get(f"/collections/{collection}")
    if response.status_code == 200:
        return
    if response.status_code != 404:
        raise HTTPException(status_code=502, detail="No se pudo consultar Qdrant")

    create_response = await client.put(
        f"/collections/{collection}",
        json={
            "vectors": {
                "size": settings.RAG_VECTOR_SIZE,
                "distance": "Cosine",
            }
        },
    )
    if create_response.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="No se pudo crear la coleccion RAG")


async def _generate_with_ollama(model: str, query: str, contexts: list[str]) -> str:
    context_block = "\n".join(f"- {ctx}" for ctx in contexts) if contexts else "- (sin contexto recuperado)"
    prompt = (
        "Eres un asistente de redaccion cientifica. Usa el contexto RAG para responder de forma breve.\n\n"
        f"Pregunta:\n{query}\n\n"
        f"Contexto RAG:\n{context_block}\n\n"
        "Respuesta:"
    )

    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=45.0) as client:
            response = await client.post(
                "/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Ollama no pudo generar respuesta")
            return response.json().get("response", "").strip()
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Ollama no disponible")


@router.get("/models")
async def list_local_models():
    """Listar modelos locales disponibles en Ollama."""
    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=10.0) as client:
            response = await client.get("/api/tags")
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="No se pudo consultar modelos en Ollama")
            models = response.json().get("models", [])
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Ollama no disponible")

    names = [item.get("name") for item in models if item.get("name")]
    return {"models": names}


@router.post("/ingest")
async def ingest_source(req: IngestRequest):
    chunks = _chunk_text(req.text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Texto vacio para indexar")

    try:
        async with httpx.AsyncClient(base_url=settings.QDRANT_URL, timeout=10.0) as client:
            await _ensure_collection(client)
            points = []
            for index, chunk in enumerate(chunks):
                points.append(
                    {
                        "id": str(uuid4()),
                        "vector": _vectorize_text(chunk, settings.RAG_VECTOR_SIZE),
                        "payload": {
                            "source_id": req.source_id,
                            "chunk_index": index,
                            "text": chunk,
                        },
                    }
                )

            upsert_response = await client.put(
                f"/collections/{settings.QDRANT_COLLECTION}/points?wait=true",
                json={"points": points},
            )
            if upsert_response.status_code not in (200, 201):
                raise HTTPException(status_code=502, detail="No se pudo indexar en Qdrant")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Qdrant no disponible")

    return {
        "status": "indexed",
        "source_id": req.source_id,
        "chunks_indexed": len(chunks),
        "collection": settings.QDRANT_COLLECTION,
    }


@router.post("/assist")
async def assist(req: AssistRequest):
    try:
        async with httpx.AsyncClient(base_url=settings.QDRANT_URL, timeout=10.0) as client:
            await _ensure_collection(client)
            search_response = await client.post(
                f"/collections/{settings.QDRANT_COLLECTION}/points/search",
                json={
                    "vector": _vectorize_text(req.query, settings.RAG_VECTOR_SIZE),
                    "limit": req.top_k,
                    "with_payload": True,
                },
            )
            if search_response.status_code != 200:
                raise HTTPException(status_code=502, detail="No se pudo consultar Qdrant")
            result = search_response.json().get("result", [])
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Qdrant no disponible")

    contexts = [item.get("payload", {}).get("text", "") for item in result]
    fallback_answer = (
        "No encontre contexto relevante en Qdrant."
        if not contexts
        else "Contexto recuperado:\n\n- " + "\n- ".join(contexts)
    )
    selected_model = req.model or get_default_model()
    try:
        answer = await call_llm(
            f"You are a scientific writing assistant. Use the RAG context to answer briefly.\n\nQuestion:\n{req.query}\n\nRAG Context:\n" + ("\n".join(f"- {c}" for c in contexts) or "- (no context)") + "\n\nAnswer:",
            model=selected_model,
            timeout=45.0,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "query": req.query,
        "model": selected_model,
        "collection": settings.QDRANT_COLLECTION,
        "matches": len(contexts),
        "contexts": contexts,
        "fallback_answer": fallback_answer,
        "answer": answer,
    }
