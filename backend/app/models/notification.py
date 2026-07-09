"""In-app notification ORM model and DTO."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, DateTime, Boolean, UUID as SA_UUID, ForeignKey, Text

from app.core.database import Base


class NotificationModel(Base):
    """In-app notifications (e.g. for @mentions)."""
    __tablename__ = "notifications"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(SA_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    article_id: UUID | None
    title: str
    message: str
    read: bool
    created_at: datetime
