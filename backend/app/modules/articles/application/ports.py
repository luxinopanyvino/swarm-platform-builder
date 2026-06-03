from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List
from app.modules.articles.domain.entities import Article


class IArticleRepository(ABC):
    """Puerto de salida: Repositorio de artículos."""
    
    @abstractmethod
    async def create(self, article: Article) -> Article:
        """Crear un artículo."""
        pass
    
    @abstractmethod
    async def get_by_id(self, article_id: UUID) -> Optional[Article]:
        """Obtener artículo por ID."""
        pass
    
    @abstractmethod
    async def get_by_author(self, author_id: UUID, skip: int = 0, limit: int = 10) -> List[Article]:
        """Obtener artículos por autor."""
        pass
    
    @abstractmethod
    async def get_by_status(self, status: str, skip: int = 0, limit: int = 10) -> List[Article]:
        """Obtener artículos por estado."""
        pass
    
    @abstractmethod
    async def update(self, article: Article) -> Article:
        """Actualizar un artículo."""
        pass
    
    @abstractmethod
    async def delete(self, article_id: UUID) -> bool:
        """Eliminar un artículo."""
        pass
