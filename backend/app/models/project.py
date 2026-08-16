"""Project and per-user project access ORM models and DTOs."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, DateTime, Boolean, UUID as SA_UUID, ForeignKey, Text, Enum as SA_Enum, UniqueConstraint, JSON

from app.core.database import Base
from app.models.enums import ProjectUseCaseType


class ProjectModel(Base):
    """Workspace project model."""
    __tablename__ = "projects"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="", nullable=False)
    use_case_type = Column(SA_Enum(ProjectUseCaseType), nullable=False, default=ProjectUseCaseType.CUSTOM)
    owner_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_system = Column(Boolean, default=False, nullable=False)
    # Default paper theme for the project's articles; each article may override
    # it (cascade: format preset -> project theme -> article theme).
    theme = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserProjectAccessModel(Base):
    """Many-to-many: which projects a user has been granted access to by an admin."""
    __tablename__ = "user_project_access"
    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_user_project"),)

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProjectCreateDTO(BaseModel):
    """Create project request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    use_case_type: ProjectUseCaseType = ProjectUseCaseType.CUSTOM


class ProjectResponse(BaseModel):
    """Project response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    use_case_type: ProjectUseCaseType
    owner_id: UUID | None
    is_system: bool
    created_at: datetime
    updated_at: datetime
