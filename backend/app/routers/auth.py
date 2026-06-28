"""Auth router: register, login, manage users."""
import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import account_lockout, login_ip_limiter, register_ip_limiter
from app.core.security import hash_password, verify_password, create_access_token, verify_token
from app.models import UserModel, UserRegisterDTO, UserLoginDTO, TokenResponse, UserResponse, UserRole, ProjectModel
from app.database import get_session

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    """Best-effort client IP for throttling (first X-Forwarded-For hop)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _mask_email(email: str) -> str:
    """Mask the local part of an email so logs carry no raw PII."""
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    head = local[0] if local else ""
    return f"{head}***@{domain}"


def _enforce_ip_rate_limit(limiter, client_ip: str, action: str) -> None:
    """Raise HTTP 429 when the per-IP sliding window is saturated."""
    retry_after = limiter.check_and_record(
        client_ip,
        settings.AUTH_RATELIMIT_MAX_ATTEMPTS,
        settings.AUTH_RATELIMIT_WINDOW_SECONDS,
    )
    if retry_after is not None:
        retry = int(retry_after) + 1
        logger.warning("auth.rate_limit_exceeded action=%s ip=%s", action, client_ip)
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Inténtalo de nuevo más tarde.",
            headers={"Retry-After": str(retry)},
        )


class AssignRoleDTO(BaseModel):
    role: UserRole


# Roles allowed for self-registration. Minimal privilege by design: signup must
# never grant content-creation, pipeline-execution or RAG/scraper access.
_MINIMAL_SIGNUP_ROLES: dict[str, UserRole] = {
    UserRole.LECTOR.value: UserRole.LECTOR,
    UserRole.PUBLICO.value: UserRole.PUBLICO,
}


def resolve_default_signup_role() -> UserRole:
    """Resolve the configured default signup role, fail-safe to LECTOR.

    Only minimal-privilege roles (``lector``/``publico``) are honoured; any other
    or unset value falls back to ``LECTOR`` so a misconfiguration can never grant
    elevated privileges on registration.
    """
    raw = (settings.DEFAULT_SIGNUP_ROLE or "").strip().lower()
    return _MINIMAL_SIGNUP_ROLES.get(raw, UserRole.LECTOR)


@router.post("/register", response_model=TokenResponse)
async def register(
    req: UserRegisterDTO,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Register a new user."""
    # Throttle account creation per source IP (anti-abuse / mass signup).
    _enforce_ip_rate_limit(register_ip_limiter, _client_ip(request), "register")

    # Check email exists
    stmt = select(UserModel).where(UserModel.email == req.email)
    existing = await session.execute(stmt)
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user with the minimal-privilege default role (never REDACTOR/ADMIN).
    user = UserModel(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=resolve_default_signup_role(),
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
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Login user.

    Brute-force protections:
    * per-IP sliding-window rate limit (429 when exceeded);
    * per-account lockout after consecutive failed attempts (423 while locked).
    """
    client_ip = _client_ip(request)
    account_key = req.email.strip().lower()

    # 1) Rate-limit the source IP before doing any work.
    _enforce_ip_rate_limit(login_ip_limiter, client_ip, "login")

    # 2) Reject early if the targeted account is currently locked.
    remaining = account_lockout.locked_for(account_key)
    if remaining is not None:
        logger.warning(
            "auth.login_blocked_locked account=%s ip=%s", _mask_email(account_key), client_ip
        )
        raise HTTPException(
            status_code=423,
            detail="Cuenta bloqueada temporalmente por demasiados intentos fallidos.",
            headers={"Retry-After": str(int(remaining) + 1)},
        )

    stmt = select(UserModel).where(UserModel.email == req.email)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(req.password, user.hashed_password):
        locked = account_lockout.record_failure(
            account_key,
            settings.AUTH_LOCKOUT_MAX_FAILED,
            settings.AUTH_LOCKOUT_SECONDS,
        )
        if locked:
            logger.warning(
                "auth.account_locked account=%s ip=%s", _mask_email(account_key), client_ip
            )
        else:
            logger.info(
                "auth.login_failed account=%s ip=%s", _mask_email(account_key), client_ip
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Successful login clears the failure counter for this account.
    account_lockout.reset(account_key)

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


def require_redactor(token_data=Depends(get_current_user)):
    """Dependency for resource-creating/executing endpoints.

    Only REDACTOR or ADMIN may run pipelines, ingest RAG documents or invoke the
    scraper. Minimal-privilege roles (LECTOR/PUBLICO) get a 403.
    """
    if token_data.get("role") not in (UserRole.ADMIN, UserRole.REDACTOR):
        raise HTTPException(status_code=403, detail="Se requiere rol de redactor o administrador")
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

