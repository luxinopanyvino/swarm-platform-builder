"""Flow checkpoint ORM model and DTOs."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, UUID as SA_UUID, ForeignKey, JSON

from app.core.database import Base


class FlowCheckpointModel(Base):
    """Checkpoints for active or draft agent states."""
    __tablename__ = "flow_checkpoints"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(SA_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="SET NULL"), nullable=True, index=True)
    state_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CreateCheckpointDTO(BaseModel):
    article_id: UUID | None = None
    state_json: dict


class CheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    article_id: UUID | None
    state_json: dict
    created_at: datetime
