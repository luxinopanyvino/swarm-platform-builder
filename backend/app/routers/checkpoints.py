"""Checkpoints router: flow auto-save states."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    FlowCheckpointModel, CreateCheckpointDTO, CheckpointResponse
)
from app.database import get_session
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/checkpoints", tags=["checkpoints"])


@router.post("", response_model=CheckpointResponse, status_code=201)
async def create_checkpoint(
    req: CreateCheckpointDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Save a new flow editor/execution checkpoint."""
    checkpoint = FlowCheckpointModel(
        author_id=UUID(token_data["user_id"]),
        article_id=req.article_id,
        state_json=req.state_json
    )
    session.add(checkpoint)
    await session.commit()
    await session.refresh(checkpoint)
    return CheckpointResponse.model_validate(checkpoint)


@router.get("/latest", response_model=CheckpointResponse)
async def get_latest_checkpoint(
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Retrieve the latest checkpoint saved by this user."""
    stmt = select(FlowCheckpointModel).where(
        FlowCheckpointModel.author_id == UUID(token_data["user_id"])
    ).order_by(FlowCheckpointModel.created_at.desc()).limit(1)
    
    result = await session.execute(stmt)
    checkpoint = result.scalars().first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="No checkpoints found")
    return CheckpointResponse.model_validate(checkpoint)
