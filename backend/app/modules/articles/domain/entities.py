from enum import Enum
from uuid import UUID
from datetime import datetime


class ArticleStatus(str, Enum):
    """Estados del artículo."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class Article:
    """Entidad de Artículo (dominio)."""
    
    def __init__(
        self,
        id: UUID,
        title: str,
        body: str,
        author_id: UUID,
        status: ArticleStatus = ArticleStatus.DRAFT,
        scientific_format: str = "none",
        reviewer_id: UUID = None,
        cover_url: str = None,
        rejection_comment: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        published_at: datetime = None
    ):
        self.id = id
        self.title = title
        self.body = body
        self.author_id = author_id
        self.status = status
        self.scientific_format = scientific_format
        self.reviewer_id = reviewer_id
        self.cover_url = cover_url
        self.rejection_comment = rejection_comment
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.published_at = published_at
    
    def submit_for_review(self):
        """Enviar a revisión."""
        if self.status != ArticleStatus.DRAFT:
            raise ValueError("Solo borradores pueden enviarse a revisión")
        self.status = ArticleStatus.IN_REVIEW
        self.updated_at = datetime.utcnow()
    
    def approve(self, reviewer_id: UUID):
        """Aprobar artículo."""
        if self.status != ArticleStatus.IN_REVIEW:
            raise ValueError("Solo artículos en revisión pueden aprobarse")
        self.status = ArticleStatus.APPROVED
        self.reviewer_id = reviewer_id
        self.updated_at = datetime.utcnow()
    
    def publish(self):
        """Publicar artículo."""
        if self.status != ArticleStatus.APPROVED:
            raise ValueError("Solo artículos aprobados pueden publicarse")
        self.status = ArticleStatus.PUBLISHED
        self.published_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def reject(self, reviewer_id: UUID, comment: str):
        """Rechazar artículo."""
        if self.status != ArticleStatus.IN_REVIEW:
            raise ValueError("Solo artículos en revisión pueden rechazarse")
        self.status = ArticleStatus.REJECTED
        self.reviewer_id = reviewer_id
        self.rejection_comment = comment
        self.updated_at = datetime.utcnow()
    
    def update(self, title: str = None, body: str = None, scientific_format: str = None):
        """Actualizar artículo."""
        if self.status != ArticleStatus.DRAFT:
            raise ValueError("Solo borradores pueden editarse")
        
        if title:
            self.title = title
        if body is not None:
            self.body = body
        if scientific_format:
            self.scientific_format = scientific_format
        
        self.updated_at = datetime.utcnow()
