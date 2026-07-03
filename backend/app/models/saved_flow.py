"""Saved visual LangGraph pipeline ORM model and DTOs."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, DateTime, UUID as SA_UUID, ForeignKey, JSON

from app.core.database import Base


class SavedFlowModel(Base):
    """Saved visual LangGraph pipelines."""
    __tablename__ = "saved_flows"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    author_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nodes = Column(JSON, default=list, nullable=False)
    edges = Column(JSON, default=list, nullable=False)
    flow_sequence = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CreateSavedFlowDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    project_id: UUID | None = None
    nodes: list = Field(default=[])
    edges: list = Field(default=[])
    flow_sequence: list[str] = Field(..., min_length=1)


class UpdateSavedFlowDTO(BaseModel):
    name: str | None = None
    nodes: list | None = None
    edges: list | None = None
    flow_sequence: list[str] | None = None


class SavedFlowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None = None
    name: str
    author_id: UUID
    nodes: list
    edges: list
    flow_sequence: list[str]
    created_at: datetime
    updated_at: datetime
