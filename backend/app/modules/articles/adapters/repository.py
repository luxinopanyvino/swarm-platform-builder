from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from uuid import UUID
from typing import Optional, List

from app.modules.articles.domain.entities import Article, ArticleStatus
from app.modules.articles.application.ports import IArticleRepository
from app.modules.articles.adapters.persistence import ArticleORM


class ArticleRepositoryImpl(IArticleRepository):
    """Implementación del repositorio de artículos."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, article: Article) -> Article:
        """Crear un artículo."""
        orm_article = ArticleORM(
            id=article.id,
            title=article.title,
            body=article.body,
            status=article.status.value,
            scientific_format=article.scientific_format,
            author_id=article.author_id,
            reviewer_id=article.reviewer_id,
            cover_url=article.cover_url,
            rejection_comment=article.rejection_comment
        )
        self.session.add(orm_article)
        await self.session.commit()
        await self.session.refresh(orm_article)
        return self._to_domain(orm_article)
    
    async def get_by_id(self, article_id: UUID) -> Optional[Article]:
        """Obtener artículo por ID."""
        result = await self.session.execute(
            select(ArticleORM).where(ArticleORM.id == article_id)
        )
        orm_article = result.scalars().first()
        return self._to_domain(orm_article) if orm_article else None
    
    async def get_by_author(self, author_id: UUID, skip: int = 0, limit: int = 10) -> List[Article]:
        """Obtener artículos por autor."""
        result = await self.session.execute(
            select(ArticleORM)
            .where(ArticleORM.author_id == author_id)
            .order_by(desc(ArticleORM.created_at))
            .offset(skip)
            .limit(limit)
        )
        orm_articles = result.scalars().all()
        return [self._to_domain(art) for art in orm_articles]
    
    async def get_by_status(self, status: str, skip: int = 0, limit: int = 10) -> List[Article]:
        """Obtener artículos por estado."""
        result = await self.session.execute(
            select(ArticleORM)
            .where(ArticleORM.status == status)
            .order_by(desc(ArticleORM.created_at))
            .offset(skip)
            .limit(limit)
        )
        orm_articles = result.scalars().all()
        return [self._to_domain(art) for art in orm_articles]
    
    async def update(self, article: Article) -> Article:
        """Actualizar un artículo."""
        result = await self.session.execute(
            select(ArticleORM).where(ArticleORM.id == article.id)
        )
        orm_article = result.scalars().first()
        
        if not orm_article:
            raise ValueError("Artículo no encontrado")
        
        orm_article.title = article.title
        orm_article.body = article.body
        orm_article.status = article.status.value
        orm_article.scientific_format = article.scientific_format
        orm_article.reviewer_id = article.reviewer_id
        orm_article.rejection_comment = article.rejection_comment
        orm_article.published_at = article.published_at
        
        await self.session.commit()
        await self.session.refresh(orm_article)
        return self._to_domain(orm_article)
    
    async def delete(self, article_id: UUID) -> bool:
        """Eliminar un artículo."""
        result = await self.session.execute(
            select(ArticleORM).where(ArticleORM.id == article_id)
        )
        orm_article = result.scalars().first()
        
        if not orm_article:
            return False
        
        await self.session.delete(orm_article)
        await self.session.commit()
        return True
    
    def _to_domain(self, orm_article: ArticleORM) -> Article:
        """Convertir ORM a dominio."""
        if not orm_article:
            return None
        return Article(
            id=orm_article.id,
            title=orm_article.title,
            body=orm_article.body,
            author_id=orm_article.author_id,
            status=ArticleStatus(orm_article.status),
            scientific_format=orm_article.scientific_format,
            reviewer_id=orm_article.reviewer_id,
            cover_url=orm_article.cover_url,
            rejection_comment=orm_article.rejection_comment,
            created_at=orm_article.created_at,
            updated_at=orm_article.updated_at,
            published_at=orm_article.published_at
        )
