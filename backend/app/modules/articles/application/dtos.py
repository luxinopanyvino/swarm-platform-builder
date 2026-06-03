from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.modules.articles.domain.entities import ArticleStatus


class CreateArticleDTO(BaseModel):
    """DTO para crear artículo."""
    title: str
    body: str = ""


class UpdateArticleDTO(BaseModel):
    """DTO para actualizar artículo."""
    title: str = None
    body: str = None
    scientific_format: str = None


class ArticleResponse(BaseModel):
    """DTO para respuesta de artículo."""
    id: UUID
    title: str
    body: str
    status: ArticleStatus
    scientific_format: str
    author_id: UUID
    reviewer_id: UUID = None
    cover_url: str = None
    rejection_comment: str = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime = None
    
    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """DTO para lista de artículos."""
    items: list[ArticleResponse]
    total: int
    page: int
    size: int
    pages: int
