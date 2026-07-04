from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_session
from app.modules.articles.application.dtos import (
    CreateArticleDTO,
    UpdateArticleDTO,
    ArticleResponse,
    ArticleListResponse
)
from app.modules.articles.application.use_cases import (
    CreateArticleUseCase,
    GetArticleUseCase,
    UpdateArticleUseCase,
    SubmitForReviewUseCase,
    ApproveArticleUseCase,
    RejectArticleUseCase
)
from app.modules.articles.adapters.repository import ArticleRepositoryImpl
from app.core.security import verify_token

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Dependency para obtener el usuario actual."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    token = authorization.replace("Bearer ", "")
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return token_data


@router.get("", response_model=ArticleListResponse)
async def list_my_articles(
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Listar artículos del usuario autenticado."""
    repo = ArticleRepositoryImpl(session)
    items = await repo.get_by_author(UUID(token_data.user_id), skip=0, limit=100)
    return {
        "items": [ArticleResponse.model_validate(article) for article in items],
        "total": len(items),
        "page": 1,
        "size": len(items),
        "pages": 1
    }


@router.post("", response_model=ArticleResponse, status_code=201)
async def create_article(
    req: CreateArticleDTO,
    token_data = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Crear un nuevo artículo."""
    try:
        repo = ArticleRepositoryImpl(session)
        use_case = CreateArticleUseCase(repo)
        article = await use_case.execute(req.title, req.body, UUID(token_data.user_id))
        return ArticleResponse.from_orm(article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Obtener un artículo."""
    try:
        repo = ArticleRepositoryImpl(session)
        use_case = GetArticleUseCase(repo)
        article = await use_case.execute(article_id)
        return ArticleResponse.from_orm(article)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: UUID,
    req: UpdateArticleDTO,
    token_data = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Actualizar un artículo."""
    try:
        repo = ArticleRepositoryImpl(session)
        use_case = UpdateArticleUseCase(repo)
        article = await use_case.execute(
            article_id,
            UUID(token_data.user_id),
            req.title,
            req.body,
            req.scientific_format
        )
        return ArticleResponse.from_orm(article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{article_id}/submit", response_model=ArticleResponse)
async def submit_for_review(
    article_id: UUID,
    token_data = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Enviar artículo a revisión."""
    try:
        repo = ArticleRepositoryImpl(session)
        use_case = SubmitForReviewUseCase(repo)
        article = await use_case.execute(article_id, UUID(token_data.user_id))
        return ArticleResponse.from_orm(article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{article_id}/approve", response_model=ArticleResponse)
async def approve_article(
    article_id: UUID,
    token_data = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Aprobar un artículo."""
    try:
        if token_data.role not in ["reviewer", "admin"]:
            raise HTTPException(status_code=403, detail="No tienes permiso")
        
        repo = ArticleRepositoryImpl(session)
        use_case = ApproveArticleUseCase(repo)
        article = await use_case.execute(article_id, UUID(token_data.user_id))
        return ArticleResponse.from_orm(article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{article_id}/reject", response_model=ArticleResponse)
async def reject_article(
    article_id: UUID,
    body: dict,
    token_data = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Rechazar un artículo."""
    try:
        if token_data.role not in ["reviewer", "admin"]:
            raise HTTPException(status_code=403, detail="No tienes permiso")
        
        comment = body.get("comment", "")
        repo = ArticleRepositoryImpl(session)
        use_case = RejectArticleUseCase(repo)
        article = await use_case.execute(article_id, UUID(token_data.user_id), comment)
        return ArticleResponse.from_orm(article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
