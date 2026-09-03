"""Resolución y autorización del proyecto de una petición (SPEC-013 / T8.5 / AC6).

El contexto llega por la cabecera `X-Project-Id` (la envía el cliente desde el
proyecto activo) o, cuando el endpoint ya lo recibe, por parámetro explícito.

Por qué una **dependencia** y no un parámetro por endpoint: el aislamiento que
pide AC6 solo vale si no se puede olvidar. Un parámetro más en la firma se olvida
en el siguiente endpoint que alguien añada; una dependencia que además comprueba
el acceso, no. Y el mismo control de acceso que hace `projects.py` vive aquí en
una sola función en lugar de repetido por endpoint.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import ProjectModel, UserModel, UserProjectAccessModel, UserRole
from app.platform.project_context import ProjectContext
from app.routers.auth import get_current_user

CABECERA_PROYECTO = "X-Project-Id"


async def user_can_access(session: AsyncSession, user: UserModel, project: ProjectModel) -> bool:
    """Mismas reglas que `GET /projects/{id}`, en un solo sitio."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.LECTOR:
        return user.assigned_project_id == project.id
    if project.is_system or project.owner_id == user.id:
        return True
    concedido = await session.execute(
        select(UserProjectAccessModel.id).where(
            UserProjectAccessModel.user_id == user.id,
            UserProjectAccessModel.project_id == project.id,
        )
    )
    return concedido.scalars().first() is not None


async def load_project_context(
    session: AsyncSession, user: UserModel, project_id: UUID
) -> ProjectContext:
    """Carga el proyecto comprobando que quien pregunta puede verlo.

    El 404 para un proyecto ajeno es deliberado: un 403 confirmaría que ese
    identificador existe.
    """
    resultado = await session.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    proyecto = resultado.scalars().first()
    if proyecto is None or not await user_can_access(session, user, proyecto):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return ProjectContext(
        project_id=proyecto.id, name=proyecto.name, is_system=proyecto.is_system
    )


async def usuario_actual(session: AsyncSession, token_data) -> UserModel:
    resultado = await session.execute(
        select(UserModel).where(UserModel.id == UUID(token_data["user_id"]))
    )
    usuario = resultado.scalars().first()
    if usuario is None or not usuario.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return usuario


async def get_project_context(
    x_project_id: Optional[str] = Header(default=None, alias=CABECERA_PROYECTO),
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectContext:
    """Contexto del proyecto activo. Obligatorio: sin él no hay dónde aislar."""
    if not x_project_id:
        raise HTTPException(
            status_code=400,
            detail=f"Falta la cabecera {CABECERA_PROYECTO}: toda operación sobre "
                   "documentos pertenece a un proyecto",
        )
    try:
        project_id = UUID(x_project_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"{CABECERA_PROYECTO} no es un UUID")

    usuario = await usuario_actual(session, token_data)
    return await load_project_context(session, usuario, project_id)


async def get_optional_project_context(
    x_project_id: Optional[str] = Header(default=None, alias=CABECERA_PROYECTO),
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Optional[ProjectContext]:
    """Igual, pero tolera su ausencia: para lecturas que sin proyecto no listan nada.

    Un identificador **inválido o ajeno** sigue siendo un error: tolerar la
    ausencia no es tolerar que alguien apunte a un proyecto que no es suyo.
    """
    if not x_project_id:
        return None
    return await get_project_context(x_project_id, token_data, session)
