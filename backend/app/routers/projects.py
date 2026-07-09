"""Projects router: create, list, and manage workspace projects."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import (
    ProjectModel,
    ProjectCreateDTO,
    ProjectResponse,
    ProjectUseCaseType,
    UserModel,
    UserRole,
    UserProjectAccessModel,
)
from sqlalchemy import and_
from app.core.security import verify_token
from app.shared.agents_seed import seed_agents_for_project
from fastapi import Header

# Import seeding lazily to avoid circular import
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


async def _get_current_user(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    """Resolve Bearer token to a UserModel."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("user_id")
    result = await session.execute(select(UserModel).where(UserModel.id == UUID(user_id)))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(_get_current_user),
):
    """Return projects visible to the current user.

    - admin    → all projects
    - redactor → only alejandria_magazine projects (system + own)
    - lector   → only alejandria_magazine projects (system + own)
    - others   → system projects + own projects
    """
    if current_user.role == UserRole.ADMIN:
        stmt = select(ProjectModel).order_by(ProjectModel.is_system.desc(), ProjectModel.created_at)
    elif current_user.role == UserRole.LECTOR:
        # Lectors only see the single project assigned to them by an admin
        if not current_user.assigned_project_id:
            return []
        stmt = select(ProjectModel).where(ProjectModel.id == current_user.assigned_project_id)
    else:
        # Own projects + system projects + projects explicitly granted by admin
        granted_stmt = select(UserProjectAccessModel.project_id).where(
            UserProjectAccessModel.user_id == current_user.id
        )
        granted_result = await session.execute(granted_stmt)
        granted_ids = list(granted_result.scalars().all())

        stmt = select(ProjectModel).where(
            or_(
                ProjectModel.is_system == True,  # noqa: E712
                ProjectModel.owner_id == current_user.id,
                ProjectModel.id.in_(granted_ids),
            )
        ).order_by(ProjectModel.is_system.desc(), ProjectModel.created_at)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateDTO,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(_get_current_user),
):
    """Create a new project for the current user."""
    project = ProjectModel(
        name=body.name,
        description=body.description,
        use_case_type=body.use_case_type,
        owner_id=current_user.id,
        is_system=False,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    # Seed template agents based on use case type
    await seed_agents_for_project(project.id, body.use_case_type)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(_get_current_user),
):
    """Get a project by ID (must be system or owned by user)."""
    result = await session.execute(
        select(ProjectModel).where(ProjectModel.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.is_system and project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        if current_user.role == UserRole.LECTOR and current_user.assigned_project_id == project.id:
            pass  # lector's assigned project — allow
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(_get_current_user),
):
    """Delete a user-owned project (system projects cannot be deleted)."""
    result = await session.execute(
        select(ProjectModel).where(ProjectModel.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.is_system:
        raise HTTPException(status_code=403, detail="System projects cannot be deleted")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    await session.delete(project)
    await session.commit()


# ── Admin: user project access management ──────────────────────────────────────

def _require_admin(current_user: UserModel = Depends(_get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return current_user


@router.get("/access/{user_id}", response_model=list[ProjectResponse])
async def list_user_project_access(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _admin: UserModel = Depends(_require_admin),
):
    """List all projects a user has been granted access to (admin only)."""
    stmt = (
        select(ProjectModel)
        .join(UserProjectAccessModel, UserProjectAccessModel.project_id == ProjectModel.id)
        .where(UserProjectAccessModel.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/access/{user_id}/{project_id}", status_code=201, response_model=ProjectResponse)
async def grant_project_access(
    user_id: UUID,
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    _admin: UserModel = Depends(_require_admin),
):
    """Grant a user access to a project (admin only)."""
    # Verify user exists
    user_result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    if not user_result.scalars().first():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verify project exists
    proj_result = await session.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = proj_result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Idempotent: skip if already granted
    existing = await session.execute(
        select(UserProjectAccessModel).where(
            UserProjectAccessModel.user_id == user_id,
            UserProjectAccessModel.project_id == project_id,
        )
    )
    if not existing.scalars().first():
        session.add(UserProjectAccessModel(user_id=user_id, project_id=project_id))
        await session.commit()

    return project


@router.delete("/access/{user_id}/{project_id}", status_code=204)
async def revoke_project_access(
    user_id: UUID,
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    _admin: UserModel = Depends(_require_admin),
):
    """Revoke a user's access to a project (admin only)."""
    result = await session.execute(
        select(UserProjectAccessModel).where(
            UserProjectAccessModel.user_id == user_id,
            UserProjectAccessModel.project_id == project_id,
        )
    )
    access = result.scalars().first()
    if access:
        await session.delete(access)
        await session.commit()
