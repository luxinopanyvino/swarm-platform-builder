"""Agent profile ORM model and DTO (project-scoped)."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import Column, String, DateTime, Boolean, UUID as SA_UUID, ForeignKey, Text, Integer, JSON, Float

from app.core.database import Base


class AgentProfileModel(Base):
    """Agent profile scoped to a project."""
    __tablename__ = "agent_profiles"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    content = Column(Text, default="", nullable=False)
    model = Column(String(128), default="llama3.2:1b", nullable=False)
    temperature = Column(Float, default=0.7, nullable=False)
    rag_enabled = Column(Boolean, default=False, nullable=False)
    graph_rag_enabled = Column(Boolean, default=False, nullable=False)
    semantic_search_enabled = Column(Boolean, default=False, nullable=False)
    rag_collection = Column(String(255), default="rag_docs", nullable=False)
    rag_chunk_size = Column(Integer, default=500, nullable=False)
    rag_chunk_overlap = Column(Integer, default=50, nullable=False)
    rag_doc_ids = Column(JSON, default=list, nullable=False)
    tools_enabled = Column(Boolean, default=False, nullable=False)
    tools = Column(JSON, default=list, nullable=False)
    prompt_template = Column(Text, default="", nullable=False)
    scientific_format = Column(String(32), default="apa", nullable=False)
    output_language = Column(String(8), default="es", nullable=False)
    target_word_count = Column(Integer, default=0, nullable=False)
    is_builtin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AgentProfileResponse(BaseModel):
    """Agent profile response (project-scoped)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    slug: str
    name: str
    content: str
    model: str
    temperature: float
    rag_enabled: bool
    graph_rag_enabled: bool
    semantic_search_enabled: bool
    rag_collection: str
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_doc_ids: list
    tools_enabled: bool
    tools: list
    prompt_template: str
    scientific_format: str
    output_language: str
    target_word_count: int
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    @field_validator('rag_doc_ids', 'tools', mode='before')
    @classmethod
    def parse_rag_doc_ids(cls, v):
        """Ensure rag_doc_ids is always a list, even when stored as a JSON string."""
        if isinstance(v, str):
            import json as _json
            try:
                parsed = _json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return v if isinstance(v, list) else []
