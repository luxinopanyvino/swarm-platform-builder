"""Auth router: register, login, manage users."""
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, verify_token
from app.models import UserModel, UserRegisterDTO, UserLoginDTO, TokenResponse, UserResponse, UserRole, ProjectModel
from app.database import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class AssignRoleDTO(BaseModel):
    role: UserRole


@router.post("/register", response_model=TokenResponse)
async def register(
    req: UserRegisterDTO,
    session: AsyncSession = Depends(get_session)
):
    """Register a new user."""
    # Check email exists
    stmt = select(UserModel).where(UserModel.email == req.email)
    existing = await session.execute(stmt)
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = UserModel(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    # Generate token
    access_token = create_access_token({"user_id": str(user.id), "email": user.email, "role": user.role.value})
    
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: UserLoginDTO,
    session: AsyncSession = Depends(get_session)
):
    """Login user."""
    stmt = select(UserModel).where(UserModel.email == req.email)
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"user_id": str(user.id), "email": user.email, "role": user.role.value})
    
    return TokenResponse(access_token=access_token)


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Dependency to extract and validate user token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.replace("Bearer ", "")
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token_data


@router.get("/me", response_model=UserResponse)
async def get_me(
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current authenticated user info."""
    stmt = select(UserModel).where(UserModel.id == UUID(token_data["user_id"]))
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.model_validate(user)


@router.post("/dev/promote-reviewer", response_model=UserResponse)
async def promote_to_reviewer(
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Promote user to reviewer (dev only)."""
    if not settings.ENABLE_DEV_ROLE_PROMOTION:
        raise HTTPException(status_code=403, detail="Role promotion disabled")
    
    stmt = select(UserModel).where(UserModel.id == UUID(token_data["user_id"]))
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = UserRole.LECTOR
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return UserResponse.model_validate(user)


# ─── Admin: user management ───────────────────────────────────────────────────

def require_admin(token_data=Depends(get_current_user)):
    """Dependency that rejects non-admin callers."""
    if token_data.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return token_data


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    token_data=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all platform users (admin only)."""
    result = await session.execute(select(UserModel).order_by(UserModel.created_at))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def assign_role(
    user_id: UUID,
    req: AssignRoleDTO,
    token_data=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Assign a role to a user (admin only). Admin cannot demote themselves."""
    if str(user_id) == token_data["user_id"]:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")

    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.role = req.role
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


class AssignProjectDTO(BaseModel):
    project_id: UUID | None = None


@router.put("/users/{user_id}/project", response_model=UserResponse)
async def assign_project(
    user_id: UUID,
    req: AssignProjectDTO,
    token_data=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Assign (or remove) a project to a user (admin only).

    Set project_id to null to remove the assignment.
    """
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if req.project_id is not None:
        proj_result = await session.execute(select(ProjectModel).where(ProjectModel.id == req.project_id))
        if not proj_result.scalars().first():
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    user.assigned_project_id = req.project_id
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)

