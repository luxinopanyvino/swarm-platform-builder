from uuid import uuid4, UUID
from app.modules.articles.domain.entities import Article, ArticleStatus
from app.modules.articles.application.ports import IArticleRepository


class CreateArticleUseCase:
    """Caso de uso: Crear un nuevo artículo."""
    
    def __init__(self, article_repository: IArticleRepository):
        self.article_repository = article_repository
    
    async def execute(self, title: str, body: str, author_id: UUID) -> Article:
        """Crear un artículo."""
        article = Article(
            id=uuid4(),
            title=title,
            body=body,
            author_id=author_id,
            status=ArticleStatus.DRAFT
        )
        return await self.article_repository.create(article)


class GetArticleUseCase:
    """Caso de uso: Obtener un artículo."""
    
    def __init__(self, article_repository: IArticleRepository):
        self.article_repository = article_repository
    
    async def execute(self, article_id: UUID) -> Article:
        """Obtener un artículo por ID."""
        article = await self.article_repository.get_by_id(article_id)
        if not article:
            raise ValueError("Artículo no encontrado")
        return article


class UpdateArticleUseCase:
    """Caso de uso: Actualizar un artículo."""
    
    def __init__(self, article_repository: IArticleRepository):
        self.article_repository = article_repository
    
    async def execute(
        self,
        article_id: UUID,
        author_id: UUID,
        title: str = None,
        body: str = None,
        scientific_format: str = None
    ) -> Article:
        """Actualizar un artículo."""
        article = await self.article_repository.get_by_id(article_id)
        if not article:
            raise ValueError("Artículo no encontrado")
        
        # Verificar que sea propietario
        if article.author_id != author_id:
            raise ValueError("No tienes permiso para editar este artículo")
        
        # Actualizar
        article.update(title, body, scientific_format)
        return await self.article_repository.update(article)


class SubmitForReviewUseCase:
    """Caso de uso: Enviar a revisión."""
    
    def __init__(self, article_repository: IArticleRepository):
        self.article_repository = article_repository
    
    async def execute(self, article_id: UUID, author_id: UUID) -> Article:
        """Enviar artículo a revisión."""
        article = await self.article_repository.get_by_id(article_id)
        if not article:
            raise ValueError("Artículo no encontrado")
        
        if article.author_id != author_id:
            raise ValueError("No tienes permiso para editar este artículo")
        
        article.submit_for_review()
        return await self.article_repository.update(article)


class ApproveArticleUseCase:
    """Caso de uso: Aprobar artículo."""
    
    def __init__(self, article_repository: IArticleRepository):
        self.article_repository = article_repository
    
    async def execute(self, article_id: UUID, reviewer_id: UUID) -> Article:
        """Aprobar un artículo."""
        article = await self.article_repository.get_by_id(article_id)
        if not article:
            raise ValueError("Artículo no encontrado")
        
        article.approve(reviewer_id)
        article.publish()  # Publicar automáticamente
        return await self.article_repository.update(article)


class RejectArticleUseCase:
    """Caso de uso: Rechazar artículo."""
    
    def __init__(self, article_repository: IArticleRepository):
        self.article_repository = article_repository
    
    async def execute(self, article_id: UUID, reviewer_id: UUID, comment: str) -> Article:
        """Rechazar un artículo."""
        article = await self.article_repository.get_by_id(article_id)
        if not article:
            raise ValueError("Artículo no encontrado")
        
        article.reject(reviewer_id, comment)
        return await self.article_repository.update(article)
