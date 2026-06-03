"""Public magazine router — no authentication required.

Exposes published articles for the public-facing magazine slideshow.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArticleModel, ArticleStatus, ArticleResponse
from app.database import get_session

router = APIRouter(prefix="/api/v1/magazine", tags=["magazine"])


@router.get("", response_model=list[ArticleResponse])
async def public_magazine(
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """Return published articles for the public magazine. No auth required."""
    stmt = (
        select(ArticleModel)
        .where(ArticleModel.status == ArticleStatus.PUBLISHED)
        .order_by(ArticleModel.published_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [ArticleResponse.model_validate(a) for a in result.scalars().all()]
