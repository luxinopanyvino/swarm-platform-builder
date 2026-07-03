"""DTOs for AI assistance, ingest and formatting endpoints."""
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ScientificFormat


class AIAssistRequest(BaseModel):
    """Request for AI assistance."""
    article_id: UUID
    user_prompt: str = Field(..., min_length=1, max_length=1000)
    selected_text: str | None = None
    article_context: str | None = None


class AIAssistResponse(BaseModel):
    """Response from AI assistance."""
    run_id: UUID
    suggestion: str
    sources: list[dict] = []
    tokens_used: int = 0
    status: str  # "completed" | "fallback" | "failed"


class AIIngestRequest(BaseModel):
    """Request for AI ingest (RAG)."""
    article_id: UUID
    source_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class AIFormatRequest(BaseModel):
    """Request for scientific formatting."""
    article_id: UUID
    text: str
    format: ScientificFormat


class AIFormatResponse(BaseModel):
    """Response from formatting."""
    run_id: UUID
    formatted_text: str
    status: str  # "completed" | "failed"
