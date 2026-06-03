from pydantic import BaseModel, EmailStr
from uuid import UUID
from app.modules.auth.domain.entities import UserRole


class RegisterDTO(BaseModel):
    """DTO para registro."""
    email: EmailStr
    password: str
    full_name: str


class LoginDTO(BaseModel):
    """DTO para login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """DTO para respuesta de token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """DTO para respuesta de usuario."""
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    
    class Config:
        from_attributes = True
