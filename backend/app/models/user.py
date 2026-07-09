"""User ORM model and authentication DTOs."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, DateTime, Boolean, UUID as SA_UUID, ForeignKey, Enum as SA_Enum

from app.core.database import Base
from app.models.enums import UserRole


class UserModel(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SA_Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.LECTOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    assigned_project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserRegisterDTO(BaseModel):
    """Register request."""
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLoginDTO(BaseModel):
    """Login request."""
    email: str = Field(..., min_length=3, max_length=255)
    password: str


class UserResponse(BaseModel):
    """User response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    assigned_project_id: UUID | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
