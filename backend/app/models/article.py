"""Article ORM model and related DTOs."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, String, DateTime, UUID as SA_UUID, ForeignKey, Text, Enum as SA_Enum, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import ArticleStatus, ScientificFormat


class ArticleModel(Base):
    """Article model."""
    __tablename__ = "articles"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(512), nullable=False)
    body = Column(Text, default="", nullable=False)
    status = Column(SA_Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False, index=True)
    scientific_format = Column(SA_Enum(ScientificFormat), default=ScientificFormat.NONE)
    # Paper-layout metadata (title block + abstract). authors is a list of
    # {"name": str, "affiliation": str, "email": str} dicts.
    authors = Column(JSON, default=list, nullable=False)
    abstract = Column(Text, default="", nullable=False)
    # Self-contained printable HTML produced by the Publicador (paper layout).
    paper_html = Column(Text, default="", nullable=False)
    # Per-article paper theme: {"font", "accent_color", "columns"}. Values come
    # from the allowlists in paper_layout; it overrides the format preset and the
    # project theme (SPEC-022/T11.2). Empty dict = inherit everything.
    theme = Column(JSON, default=dict, nullable=False)
    author_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    cover_url = Column(String(1024))
    rejection_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime)

    author = relationship("UserModel", foreign_keys=[author_id], lazy="select")


class CreateArticleDTO(BaseModel):
    """Create article request."""
    title: str = Field(..., min_length=1, max_length=512)
    body: str = Field(default="")
    project_id: UUID | None = None


class AuthorDTO(BaseModel):
    """A single author entry for the paper title block."""
    name: str = Field(..., min_length=1, max_length=255)
    affiliation: str = Field(default="", max_length=512)
    email: str = Field(default="", max_length=255)


class ThemeDTO(BaseModel):
    """User-chosen paper theme. Values are validated against the allowlists in
    paper_layout (unknown ones are dropped there), so this stays permissive and
    the layout module remains the single source of truth for what is allowed."""
    font: str | None = None
    accent_color: str | None = None
    columns: int | None = None


class UpdateArticleDTO(BaseModel):
    """Update article request."""
    title: str | None = None
    body: str | None = None
    scientific_format: ScientificFormat | None = None
    authors: list[AuthorDTO] | None = None
    abstract: str | None = None
    theme: ThemeDTO | None = None


class ArticleResponse(BaseModel):
    """Article response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None = None
    title: str
    body: str
    status: ArticleStatus
    scientific_format: ScientificFormat
    authors: list = []
    abstract: str | None = None
    theme: dict = {}
    author_id: UUID
    author_name: str | None = None
    reviewer_id: UUID | None
    cover_url: str | None
    rejection_comment: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    @field_validator('authors', mode='before')
    @classmethod
    def _coerce_authors(cls, v):
        """Legacy rows store NULL for authors; coerce to an empty list."""
        return v if isinstance(v, list) else []

    @field_validator('theme', mode='before')
    @classmethod
    def _coerce_theme(cls, v):
        """Rows created before the theme column store NULL; coerce to {}."""
        return v if isinstance(v, dict) else {}


class ArticleListResponse(BaseModel):
    """List articles response."""
    items: list[ArticleResponse]
    total: int
    page: int
    size: int
    pages: int
