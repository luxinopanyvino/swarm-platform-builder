"""Agents router: run and monitor agent orchestrations, manage agent prompts."""
import asyncio
import json
import re
import uuid
import yaml
from uuid import UUID
from pathlib import Path
from typing import Dict, Any

# Slugs that are always protected and cannot be deleted
_PROTECTED_SLUGS: frozenset[str] = frozenset({
    'investigador', 'redactor', 'revisor', 'formateador', 'publicador', 'orquestador',
    'arquitecto', 'backend-dev', 'frontend-dev', 'qa-tester', 'devops', 'code-reviewer',
    'estratega', 'copywriter', 'social-media', 'seo-specialist', 'analista',
    'clasificador', 'agente-soporte', 'escalador', 'resolutor', 'qa-calidad',
    'art-director', 'ui-designer', 'ux-researcher', 'revisor-visual', 'motion-designer',
})

import httpx

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArticleModel, AgentRunModel, AgentRunRequest,
    AgentRunListResponse, AgentRunDetailResponse,
    AgentProfileModel, AgentProfileResponse,
)
from app.database import get_session
from app.routers.auth import get_current_user
from app.core.security import verify_token
from app.modules.agents.application.use_cases import Orchestrator, active_streams, active_tasks, publish_event
from app.modules.agents.adapters.rag import (
    extract_text, chunk_text, ensure_collection, upsert_chunks,
    list_documents, delete_document, get_rag_backend,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def get_claude_agents_dir() -> Path:
    # Agent profile .agent.md files live in backend/app/agents/
    paths = [
        Path("app/agents"),
        Path("../app/agents"),
    ]
    for p in paths:
        if p.exists() and p.is_dir():
            return p
    return Path("app/agents")


def get_agent_profile_id(filepath: Path) -> str:
    filename = filepath.name
    if filename.endswith(".agent.md"):
        return filename[:-len(".agent.md")]
    return filepath.stem


def read_agent_profile(filepath: Path) -> dict[str, Any]:
    profile_id = get_agent_profile_id(filepath)
    with open(filepath, "r", encoding="utf-8") as file:
        raw = file.read()

    frontmatter: dict[str, Any] = {}
    content = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except Exception:
                frontmatter = {}
            content = parts[2]

    return {
        "id": profile_id,
        "name": profile_id.replace("-", " ").title(),
        "frontmatter": frontmatter,
        "content": content.lstrip(),
    }


def resolve_agent_rag_settings(agent_name: str, settings: Any, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    collection = settings.QDRANT_COLLECTION
    chunk_size = 500
    chunk_overlap = 50

    agents_dir = get_claude_agents_dir()
    profile_path = agents_dir / f"{agent_name}.agent.md"
    if profile_path.exists():
        profile = read_agent_profile(profile_path)
        frontmatter = profile["frontmatter"]
        collection = frontmatter.get("rag_collection", collection)
        chunk_size = int(frontmatter.get("rag_chunk_size", chunk_size) or chunk_size)
        chunk_overlap = int(frontmatter.get("rag_chunk_overlap", chunk_overlap) or chunk_overlap)

    if overrides:
        if overrides.get("rag_collection"):
            collection = str(overrides["rag_collection"]).strip()
        if overrides.get("rag_chunk_size") is not None:
            chunk_size = int(overrides["rag_chunk_size"])
        if overrides.get("rag_chunk_overlap") is not None:
            chunk_overlap = int(overrides["rag_chunk_overlap"])

    chunk_size = max(100, min(chunk_size, 4000))
    chunk_overlap = max(0, min(chunk_overlap, max(chunk_size - 1, 0)))

    return {
        "collection": collection,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }


@router.get("/definitions")
async def get_agent_definitions(token_data=Depends(get_current_user)):
    """Get static descriptions of standard system agents."""
    return {
        "investigador": { "id": "investigador", "name": "Investigador", "description": "Busca contexto en Qdrant RAG y APIs científicas." },
        "redactor": { "id": "redactor", "name": "Redactor", "description": "Genera borrador académico en Markdown usando Ollama." },
        "revisor": { "id": "revisor", "name": "Revisor", "description": "Evalúa el borrador con un score 0-100 y genera feedback." },
        "formateador": { "id": "formateador", "name": "Formateador", "description": "Reformatea citas en APA, IEEE o Vancouver." },
        "publicador": { "id": "publicador", "name": "Publicador", "description": "Guarda el artículo final en DB y lo marca como PUBLISHED." }
    }


@router.get("/claude-defs", response_model=list[AgentProfileResponse])
async def get_claude_agent_definitions(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    token_data=Depends(get_current_user),
):
    """Return all agent profiles for a given project."""
    result = await session.execute(
        select(AgentProfileModel)
        .where(AgentProfileModel.project_id == project_id)
        .order_by(AgentProfileModel.is_builtin.desc(), AgentProfileModel.created_at)
    )
    return result.scalars().all()


@router.get("/rag/collections")
async def get_rag_collections_overview(token_data=Depends(get_current_user)):
    """Return all RAG documents stored in the local filesystem store (no Qdrant required)."""
    from app.modules.agents.adapters.rag import _local_rag_root, _load_local_document

    rag_root = _local_rag_root()
    collections: dict[str, dict[str, Any]] = {}

    for collection_dir in sorted(rag_root.iterdir()):
        if not collection_dir.is_dir():
            continue
        collection_name = collection_dir.name

        for doc_path in sorted(collection_dir.glob("*.json")):
            data = _load_local_document(doc_path)
            if not data:
                continue
            agent_name = data.get("agent_name", "unknown")
            doc_entry = {
                "doc_id": data.get("doc_id", doc_path.stem),
                "filename": data.get("filename", doc_path.stem),
                "agent_name": agent_name,
                "chunks": len(data.get("chunks", [])),
            }

            bucket = collections.setdefault(collection_name, {
                "name": collection_name,
                "agents": {},
                "total_documents": 0,
                "total_chunks": 0,
            })
            agent_bucket = bucket["agents"].setdefault(agent_name, {
                "id": agent_name,
                "name": agent_name.replace("-", " ").title(),
                "rag_enabled": True,
                "documents": [],
            })
            agent_bucket["documents"].append(doc_entry)
            bucket["total_documents"] += 1
            bucket["total_chunks"] += doc_entry["chunks"]

    # Convert agents dict to list for each collection
    result = []
    for col in collections.values():
        col["agents"] = list(col["agents"].values())
        result.append(col)

    return {
        "collections": sorted(result, key=lambda item: item["name"]),
        "storage_backend": "local",
    }


@router.get("/rag/library")
async def get_rag_library(token_data=Depends(get_current_user)):
    """Return all documents stored in Qdrant (or local fallback) across all collections."""
    from app.core.config import settings
    from app.modules.agents.adapters.rag import list_library_documents

    docs = await list_library_documents(settings.QDRANT_URL, settings.QDRANT_API_KEY)

    # Group by collection
    collections: dict[str, dict[str, Any]] = {}
    for doc in docs:
        col_name = doc["collection"]
        bucket = collections.setdefault(col_name, {
            "name": col_name,
            "documents": [],
            "total_chunks": 0,
        })
        bucket["documents"].append({
            "doc_id": doc["doc_id"],
            "filename": doc["filename"],
            "agent_name": doc.get("agent_name", ""),
            "chunks": doc["chunks"],
        })
        bucket["total_chunks"] += doc["chunks"]

    result = sorted(collections.values(), key=lambda c: c["name"])
    backend = await get_rag_backend(settings.QDRANT_URL, settings.QDRANT_API_KEY)
    return {"collections": result, "storage_backend": backend}


@router.post("/rag/library/upload")
async def upload_to_rag_library(
    file: UploadFile = File(...),
    collection: str | None = Form(None),
    chunk_size: int | None = Form(None),
    chunk_overlap: int | None = Form(None),
    token_data=Depends(get_current_user),
):
    """Upload a document to the global RAG library (not tied to any agent)."""
    from app.core.config import settings

    allowed = {".txt", ".md", ".pdf"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=415, detail=f"Tipo de archivo no soportado '{ext}'. Use: {', '.join(allowed)}")

    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx. 10 MB)")

    text = extract_text(file.filename, raw)
    if not text.strip():
        raise HTTPException(status_code=422, detail="No se pudo extraer texto del archivo")

    col = (collection or settings.QDRANT_COLLECTION).strip() or settings.QDRANT_COLLECTION
    c_size = max(100, min(int(chunk_size or settings.RAG_CHUNK_SIZE if hasattr(settings, "RAG_CHUNK_SIZE") else 500), 4000))
    c_overlap = max(0, min(int(chunk_overlap or 50), 499))

    doc_id = str(uuid.uuid4())
    chunks = chunk_text(text, chunk_size=c_size, overlap=c_overlap)

    await ensure_collection(settings.QDRANT_URL, col, settings.RAG_VECTOR_SIZE, settings.QDRANT_API_KEY)
    count = await upsert_chunks(
        qdrant_url=settings.QDRANT_URL,
        collection=col,
        doc_id=doc_id,
        agent_name="__library__",
        filename=file.filename,
        chunks=chunks,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        embedding_model=settings.OLLAMA_EMBED_MODEL,
        vector_size=settings.RAG_VECTOR_SIZE,
        api_key=settings.QDRANT_API_KEY,
    )

    if count <= 0:
        raise HTTPException(status_code=502, detail="No se pudo indexar el documento")

    return {
        "status": "indexed",
        "doc_id": doc_id,
        "filename": file.filename,
        "collection": col,
        "chunks": count,
    }


@router.delete("/rag/library/{collection}/{doc_id}")
async def delete_from_rag_library(
    collection: str,
    doc_id: str,
    token_data=Depends(get_current_user),
):
    """Delete a document from the global RAG library."""
    from app.core.config import settings
    import re as _re

    # Sanitize path parameters to prevent traversal / injection
    if not _re.match(r"^[a-zA-Z0-9_\-]+$", collection):
        raise HTTPException(status_code=422, detail="Invalid collection name")
    if not _re.match(r"^[a-zA-Z0-9_\-]+$", doc_id):
        raise HTTPException(status_code=422, detail="Invalid doc_id")

    ok = await delete_document(settings.QDRANT_URL, collection, doc_id, settings.QDRANT_API_KEY)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo eliminar el documento")
    return {"status": "deleted", "doc_id": doc_id}


@router.get("/tools")
async def list_available_tools(_token=Depends(get_current_user)):
    """Return the catalog of available tools for agent tool calling."""
    from app.modules.agents.adapters.tools import TOOL_CATALOG
    return {"tools": TOOL_CATALOG}


@router.put("/claude-defs/{agent_id}", response_model=AgentProfileResponse)
async def update_claude_agent_definition(
    agent_id: UUID,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    token_data=Depends(get_current_user),
):
    """Update an agent profile by its UUID."""
    result = await session.execute(
        select(AgentProfileModel).where(AgentProfileModel.id == agent_id)
    )
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    content = payload.get("content", "")

    # Detect JSON params vs markdown content
    is_json = False
    params = {}
    try:
        if content.strip().startswith("{") and content.strip().endswith("}"):
            params = json.loads(content)
            is_json = True
    except Exception:
        pass

    if is_json:
        for key in ("model", "temperature", "rag_enabled", "rag_collection",
                    "rag_chunk_size", "rag_chunk_overlap", "rag_doc_ids",
                    "graph_rag_enabled", "semantic_search_enabled",
                    "tools_enabled", "tools", "prompt_template",
                    "scientific_format", "output_language", "target_word_count"):
            if key in params:
                setattr(agent, key, params[key])
    else:
        agent.content = content

    await session.commit()
    await session.refresh(agent)
    return agent


@router.post("/claude-defs", response_model=AgentProfileResponse, status_code=201)
async def create_claude_agent_definition(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    token_data=Depends(get_current_user),
):
    """Create a new custom agent profile in the given project."""
    project_id_raw = payload.get("project_id")
    if not project_id_raw:
        raise HTTPException(status_code=422, detail="project_id is required")
    try:
        project_id = UUID(str(project_id_raw))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id")

    slug = payload.get("name", "").strip().lower()
    if not slug or not re.match(r"^[a-z0-9_-]+$", slug):
        raise HTTPException(status_code=422, detail="name must be lowercase alphanumeric/hyphens/underscores")

    # Check duplicate slug within project
    existing = await session.execute(
        select(AgentProfileModel).where(
            AgentProfileModel.project_id == project_id,
            AgentProfileModel.slug == slug,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail=f"Agent '{slug}' already exists in this project")

    description = payload.get("description", f"Agente personalizado: {slug}")
    body = f"# {slug.capitalize()}\n\n## Rol\n{description}\n\n## Dominio\nDefinido por el usuario.\n\n## Salida esperada\nDefinida por el usuario.\n"

    agent = AgentProfileModel(
        project_id=project_id,
        slug=slug,
        name=slug.replace("-", " ").title(),
        content=body,
        model=payload.get("model", "llama3.2:1b"),
        temperature=float(payload.get("temperature", 0.7)),
        rag_enabled=bool(payload.get("rag_enabled", False)),
        rag_collection=payload.get("rag_collection", "rag_docs"),
        rag_chunk_size=max(100, min(int(payload.get("rag_chunk_size", 500)), 4000)),
        rag_chunk_overlap=max(0, min(int(payload.get("rag_chunk_overlap", 50)), 499)),
        prompt_template=payload.get("prompt_template", ""),
        is_builtin=False,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.delete("/claude-defs/{agent_id}", status_code=204)
async def delete_claude_agent_definition(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    token_data=Depends(get_current_user),
):
    """Delete a custom agent profile. Built-in agents cannot be deleted."""
    result = await session.execute(
        select(AgentProfileModel).where(AgentProfileModel.id == agent_id)
    )
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.slug in _PROTECTED_SLUGS:
        raise HTTPException(status_code=403, detail="Built-in agents cannot be deleted")
    await session.delete(agent)
    await session.commit()


@router.get("/models")
async def get_available_models(token_data=Depends(get_current_user)):
    """List models available for the configured LLM provider."""
    from app.core.config import settings
    if settings.LLM_PROVIDER.lower() == "openai":
        if settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                client_kwargs: dict = {"api_key": settings.OPENAI_API_KEY}
                if settings.OPENAI_BASE_URL:
                    client_kwargs["base_url"] = settings.OPENAI_BASE_URL
                client = AsyncOpenAI(**client_kwargs)
                resp = await client.models.list()
                await client.close()
                names = sorted(m.id for m in resp.data)
                return {"provider": "openai", "models": names}
            except Exception:
                pass
        return {
            "provider": "openai",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        }

    # Ollama
    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=5.0) as client:
            resp = await client.get("/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"provider": "ollama", "models": models or ["llama3.2:1b"]}
    except Exception:
        pass
    return {"provider": "ollama", "models": ["llama3.2:1b", "llama3.1", "mistral", "gemma2", "phi3"]}


@router.post("/{agent_name}/rag/upload")
async def upload_rag_document(
    agent_name: str,
    file: UploadFile = File(...),
    rag_collection: str | None = Form(None),
    rag_chunk_size: int | None = Form(None),
    rag_chunk_overlap: int | None = Form(None),
    token_data=Depends(get_current_user),
):
    """Upload a file, chunk it, embed via Ollama and store in Qdrant for an agent."""
    from app.core.config import settings

    allowed = {".txt", ".md", ".pdf"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported file type '{ext}'. Use: {', '.join(allowed)}")

    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:  # 10 MB guard
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    text = extract_text(file.filename, raw)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    doc_id = str(uuid.uuid4())

    rag_settings = resolve_agent_rag_settings(agent_name, settings, {
        "rag_collection": rag_collection,
        "rag_chunk_size": rag_chunk_size,
        "rag_chunk_overlap": rag_chunk_overlap,
    })
    chunks = chunk_text(text, chunk_size=rag_settings["chunk_size"], overlap=rag_settings["chunk_overlap"])
    collection = rag_settings["collection"]

    await ensure_collection(settings.QDRANT_URL, collection, settings.RAG_VECTOR_SIZE, settings.QDRANT_API_KEY)

    count = await upsert_chunks(
        qdrant_url=settings.QDRANT_URL,
        collection=collection,
        doc_id=doc_id,
        agent_name=agent_name,
        filename=file.filename,
        chunks=chunks,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        embedding_model=settings.OLLAMA_EMBED_MODEL,
        vector_size=settings.RAG_VECTOR_SIZE,
        api_key=settings.QDRANT_API_KEY,
    )

    if count <= 0:
        raise HTTPException(status_code=502, detail="No se pudo indexar el documento en Qdrant")

    return {
        "status": "indexed",
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": count,
        "collection": collection,
        "chunk_size": rag_settings["chunk_size"],
        "chunk_overlap": rag_settings["chunk_overlap"],
    }


@router.get("/{agent_name}/rag/documents")
async def list_rag_documents(agent_name: str, token_data=Depends(get_current_user)):
    """List all RAG documents indexed for an agent."""
    from app.core.config import settings

    rag_settings = resolve_agent_rag_settings(agent_name, settings)
    collection = rag_settings["collection"]
    backend = await get_rag_backend(settings.QDRANT_URL, settings.QDRANT_API_KEY)

    docs = await list_documents(settings.QDRANT_URL, collection, agent_name, settings.QDRANT_API_KEY)
    return {
        "documents": docs,
        "collection": collection,
        "chunk_size": rag_settings["chunk_size"],
        "chunk_overlap": rag_settings["chunk_overlap"],
        "storage_backend": backend,
    }


@router.delete("/{agent_name}/rag/documents/{doc_id}")
async def delete_rag_document(agent_name: str, doc_id: str, token_data=Depends(get_current_user)):
    """Remove all Qdrant points belonging to a RAG document."""
    from app.core.config import settings

    rag_settings = resolve_agent_rag_settings(agent_name, settings)
    collection = rag_settings["collection"]

    ok = await delete_document(settings.QDRANT_URL, collection, doc_id, settings.QDRANT_API_KEY)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete document from the configured RAG store")
    return {"status": "deleted", "doc_id": doc_id}


@router.post("/{article_id}/run")
async def run_agent_pipeline(
    article_id: UUID,
    req: AgentRunRequest,
    background_tasks: BackgroundTasks,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Run the multi-agent pipeline on a specific article in the background.
    Compiles and executes LangGraph nodes in the requested flow sequence.
    """
    # Verify article exists and belongs to the authenticated author
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    res = await session.execute(stmt)
    article = res.scalars().first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this article")
        
    # Use provided keywords if given; otherwise extract from title as fallback
    title = article.title
    if req.keywords:
        keywords = req.keywords
    else:
        keywords = [w.strip(".,;:?!") for w in title.lower().split() if len(w) > 4]
        if not keywords:
            keywords = ["scientific", "research"]

    # Prepend context description to the initial research data if provided
    if req.context_description:
        # Inject into agent_settings so investigador can use it
        req.agent_settings.setdefault("investigador", {})
        existing = req.agent_settings["investigador"].get("context_hint", "")
        if not existing:
            req.agent_settings["investigador"]["context_hint"] = req.context_description

    # Load stored agent profiles and merge into agent_settings as fallback.
    # This ensures persisted values (e.g. target_word_count, output_language)
    # are used even when the frontend doesn't forward them explicitly.
    agent_slugs = list(req.flow_sequence)
    profiles_stmt = select(AgentProfileModel).where(AgentProfileModel.slug.in_(agent_slugs))
    profiles_res = await session.execute(profiles_stmt)
    for profile in profiles_res.scalars().all():
        slug = profile.slug
        req.agent_settings.setdefault(slug, {})
        s = req.agent_settings[slug]
        if "model" not in s and profile.model:
            s["model"] = profile.model
        if "temperature" not in s and profile.temperature is not None:
            s["temperature"] = profile.temperature
        if "output_language" not in s and profile.output_language:
            s["output_language"] = profile.output_language
        if "scientific_format" not in s and profile.scientific_format:
            s["scientific_format"] = profile.scientific_format
        if "target_word_count" not in s and profile.target_word_count:
            s["target_word_count"] = profile.target_word_count
        if "prompt_template" not in s and profile.prompt_template:
            s["prompt_template"] = profile.prompt_template
        if "rag_collection" not in s and profile.rag_collection:
            s["rag_collection"] = profile.rag_collection
        if "rag_doc_ids" not in s and profile.rag_doc_ids:
            s["rag_doc_ids"] = profile.rag_doc_ids
        if "graph_rag_enabled" not in s and profile.graph_rag_enabled is not None:
            s["graph_rag_enabled"] = profile.graph_rag_enabled
        if "semantic_search_enabled" not in s and profile.semantic_search_enabled is not None:
            s["semantic_search_enabled"] = profile.semantic_search_enabled
        if "tools_enabled" not in s and profile.tools_enabled:
            s["tools_enabled"] = profile.tools_enabled
        if "tools" not in s and profile.tools:
            s["tools"] = profile.tools
        
    scientific_format = article.scientific_format.value if article.scientific_format else "apa"
    
    # Run Orchestrator flow as a background task to allow SSE to immediately stream
    background_tasks.add_task(
        Orchestrator.run,
        article_id=article_id,
        author_id=article.author_id,
        title=title,
        keywords=keywords,
        scientific_format=scientific_format,
        flow_sequence=req.flow_sequence,
        agent_settings=req.agent_settings,
        context_description=req.context_description,
        # Pass existing body so re-runs (e.g. only revisor+formateador) start with
        # the already-generated content instead of an empty draft.
        initial_draft_text=article.body or "",
        article_outline=req.article_outline,
    )
    
    return {"status": "accepted", "message": "Agent execution pipeline started"}


@router.delete("/{article_id}/run", status_code=200)
async def cancel_pipeline_run(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cancel an in-progress pipeline run. The article remains in DRAFT."""
    # Verify ownership
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    res = await session.execute(stmt)
    article = res.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if str(article.author_id) != token_data["user_id"] and token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    task = active_tasks.get(article_id)
    if task is None or task.done():
        raise HTTPException(status_code=409, detail="No active pipeline for this article")

    task.cancel()
    return {"status": "cancelled", "article_id": str(article_id)}



@router.get("/{article_id}/runs", response_model=AgentRunListResponse)
async def get_article_agent_runs(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieve history logs of agent executions for a specific article.
    """
    # Verify ownership of the article
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    res = await session.execute(stmt)
    article = res.scalars().first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if str(article.author_id) != token_data["user_id"] and token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this article")
        
    # Query agent execution history
    stmt_runs = select(AgentRunModel).where(AgentRunModel.article_id == article_id).order_by(AgentRunModel.started_at.desc())
    res_runs = await session.execute(stmt_runs)
    runs = res_runs.scalars().all()
    
    return AgentRunListResponse(
        runs=[AgentRunDetailResponse.model_validate(r) for r in runs]
    )


@router.get("/{article_id}/stream")
async def stream_agent_runs(
    article_id: UUID,
    token: str | None = None,
    session: AsyncSession = Depends(get_session)
):
    """SSE endpoint for real-time monitoring of active agent runs."""
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    # Verify ownership of the article
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    res = await session.execute(stmt)
    article = res.scalars().first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    q = asyncio.Queue()
    if article_id not in active_streams:
        active_streams[article_id] = []
    active_streams[article_id].append(q)

    async def event_generator():
        try:
            while True:
                # Wait for an event from active_streams
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
        except asyncio.CancelledError:
            # client disconnected — re-raise so the generator is properly cancelled
            raise
        finally:
            if article_id in active_streams:
                if q in active_streams[article_id]:
                    active_streams[article_id].remove(q)
                if not active_streams[article_id]:
                    del active_streams[article_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")
