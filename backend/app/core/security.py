from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hashear una contraseña."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

# Alias de compatibilidad para routers
hash_password = get_password_hash


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar una contraseña contra su hash."""
    pwd_bytes = plain_password.encode('utf-8')
    try:
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


import uuid


def create_access_token(user_id_or_data: str | dict, email: Optional[str] = None, role: Optional[str] = None) -> str:
    """Crear un token de acceso JWT."""
    if isinstance(user_id_or_data, dict):
        user_id = user_id_or_data.get("user_id")
        user_email = user_id_or_data.get("email")
        user_role = user_id_or_data.get("role") or "author"
    else:
        user_id = user_id_or_data
        user_email = email
        user_role = role or "author"

    to_encode = {
        "user_id": user_id,
        "email": user_email,
        "role": user_role,
        "type": "access",
        "jti": str(uuid.uuid4())
    }
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, email: str) -> str:
    """Crear un token de refresco JWT."""
    to_encode = {
        "user_id": user_id,
        "email": email,
        "type": "refresh"
    }
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verificar y decodificar un token JWT. Solo acepta tokens de tipo 'access'."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Reject refresh tokens being used as access tokens
        if payload.get("type") != "access":
            return None
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role") or "author"
        
        if user_id is None or email is None:
            return None
        
        return {"user_id": user_id, "email": email, "role": role}
    except JWTError:
        return None
