"""Simplified models: DTOs and SQLAlchemy ORM schemas in one file."""
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import Column, String, DateTime, Boolean, UUID as SA_UUID, ForeignKey, Text, Enum as SA_Enum, Integer, JSON, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


# ============ Enums ============


class UserRole(str, Enum):
    """User roles in the system.

    - ADMIN:    full platform access; can manage users and assign roles.
    - REDACTOR: can create and edit articles, run pipelines.
    - LECTOR:   read-only access to published articles inside the platform.
    - PUBLICO:  unauthenticated / public access to the magazine slideshow only.
    """
    ADMIN    = "admin"
    REDACTOR = "redactor"
    LECTOR   = "lector"
    PUBLICO  = "publico"


class ArticleStatus(str, Enum):
    """Article lifecycle states."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ProjectUseCaseType(str, Enum):
    """Project use case types."""
    ALEJANDRIA_MAGAZINE = "alejandria_magazine"
    DESARROLLO = "desarrollo"
    MARKETING = "marketing"
    TIQUETING = "tiqueting"
    DISENO = "diseno"
    CUSTOM = "custom"


class ScientificFormat(str, Enum):
    """Supported scientific formats."""
    APA = "apa"
    IEEE = "ieee"
    VANCOUVER = "vancouver"
    NONE = "none"


# ============ SQLAlchemy ORM Models ============


class UserModel(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SA_Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.REDACTOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    assigned_project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ArticleModel(Base):
    """Article model."""
    __tablename__ = "articles"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(512), nullable=False)
    body = Column(Text, default="", nullable=False)
    status = Column(SA_Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False, index=True)
    scientific_format = Column(SA_Enum(ScientificFormat), default=ScientificFormat.NONE)
    author_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    cover_url = Column(String(1024))
    rejection_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime)

    author = relationship("UserModel", foreign_keys=[author_id], lazy="select")


class AgentRunModel(Base):
    """Agent execution run tracking model."""
    __tablename__ = "agent_runs"

    run_id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_name = Column(String(64), nullable=False)
    article_id = Column(SA_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="SET NULL"), index=True)
    author_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status = Column(String(16), default="running", nullable=False, index=True)
    input_payload = Column(JSON, default=dict, nullable=False)
    output_payload = Column(JSON)
    tokens_used = Column(Integer, default=0, nullable=False)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime)


class ProjectModel(Base):
    """Workspace project model."""
    __tablename__ = "projects"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="", nullable=False)
    use_case_type = Column(SA_Enum(ProjectUseCaseType), nullable=False, default=ProjectUseCaseType.CUSTOM)
    owner_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


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


class UserProjectAccessModel(Base):
    """Many-to-many: which projects a user has been granted access to by an admin."""
    __tablename__ = "user_project_access"
    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_user_project"),)

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============ Pydantic DTOs ============


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


class CreateArticleDTO(BaseModel):
    """Create article request."""
    title: str = Field(..., min_length=1, max_length=512)
    body: str = Field(default="")
    project_id: UUID | None = None


class UpdateArticleDTO(BaseModel):
    """Update article request."""
    title: str | None = None
    body: str | None = None
    scientific_format: ScientificFormat | None = None


class ArticleResponse(BaseModel):
    """Article response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None = None
    title: str
    body: str
    status: ArticleStatus
    scientific_format: ScientificFormat
    author_id: UUID
    author_name: str | None = None
    reviewer_id: UUID | None
    cover_url: str | None
    rejection_comment: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class ArticleListResponse(BaseModel):
    """List articles response."""
    items: list[ArticleResponse]
    total: int
    page: int
    size: int
    pages: int


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


# ============ AI DTOs ============


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


# ============ Agent Run DTOs ============

class AgentRunRequest(BaseModel):
    """Request for running the agent pipeline."""
    flow_sequence: list[str] = Field(..., min_length=1)
    agent_settings: dict[str, dict] = Field(default={})
    keywords: list[str] = Field(default=[])
    context_description: str = Field(default="")
    article_outline: str = Field(default="")


class AgentRunDetailResponse(BaseModel):
    """Detailed response of a single agent run step."""
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    agent_name: str
    article_id: UUID | None
    author_id: UUID | None
    status: str
    input_payload: dict | None = None
    output_payload: dict | None = None
    tokens_used: int
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class AgentRunListResponse(BaseModel):
    """Response containing a list of agent runs."""
    runs: list[AgentRunDetailResponse]


# ============ Saved Flow Models & DTOs ============

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


# ============ Flow Checkpoint Models & DTOs ============

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


# ============ Notification Models & DTOs ============

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

