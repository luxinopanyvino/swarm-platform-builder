"""Consulta del audit log (SPEC-020 / T6.4 / AC4).

AC4 pide que el registro sea **consultable**: una tabla que solo se escribe no
sirve para responder «quién cambió este rol» ni «desde dónde vinieron los intentos
fallidos». Este router es esa lectura, y es **solo para administradores**: el log
concentra quién hizo qué y desde qué IP, así que es justo el sitio que no debe
quedar expuesto a cualquier usuario autenticado.

Es de solo lectura por diseño. No hay endpoint para borrar ni editar entradas: la
purga es política de retención (T6.5) y debe ocurrir por un proceso deliberado, no
por una llamada de la API.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.audit_log import AuditLogModel, AuditLogResponse
from app.routers.auth import require_admin

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=dict)
async def list_audit_entries(
    action: str | None = Query(default=None, description="Filtra por acción exacta"),
    actor_id: UUID | None = Query(default=None),
    target_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    order: Literal["desc", "asc"] = Query(default="desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Lista entradas del audit log, de la más reciente a la más antigua.

    Paginado y acotado (`limit` máximo 200) porque esta tabla solo crece: una
    consulta sin límite sería un problema el día que de verdad haga falta usarla.
    """
    filters = []
    if action:
        filters.append(AuditLogModel.action == action)
    if actor_id:
        filters.append(AuditLogModel.actor_id == actor_id)
    if target_id:
        filters.append(AuditLogModel.target_id == target_id)
    if since:
        filters.append(AuditLogModel.created_at >= since)
    if until:
        filters.append(AuditLogModel.created_at <= until)

    total = await session.scalar(
        select(func.count()).select_from(AuditLogModel).where(*filters)
    )

    sort = AuditLogModel.created_at.desc() if order == "desc" else AuditLogModel.created_at.asc()
    result = await session.execute(
        select(AuditLogModel).where(*filters).order_by(sort).limit(limit).offset(offset)
    )

    return {
        "total": total or 0,
        "limit": limit,
        "offset": offset,
        "items": [AuditLogResponse.model_validate(row) for row in result.scalars().all()],
    }
