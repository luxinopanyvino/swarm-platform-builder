"""Notifications router: manage user notifications."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    NotificationModel, NotificationResponse
)
from app.core.database import get_session
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List all notifications for the current user."""
    stmt = select(NotificationModel).where(
        NotificationModel.user_id == UUID(token_data["user_id"])
    ).order_by(NotificationModel.created_at.desc())
    
    result = await session.execute(stmt)
    notifications = result.scalars().all()
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark a notification as read."""
    stmt = select(NotificationModel).where(
        NotificationModel.id == notification_id,
        NotificationModel.user_id == UUID(token_data["user_id"])
    )
    result = await session.execute(stmt)
    notification = result.scalars().first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.read = True
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return NotificationResponse.model_validate(notification)
