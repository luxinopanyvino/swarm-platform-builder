from enum import Enum
from uuid import UUID
from datetime import datetime


class UserRole(str, Enum):
    """Roles de usuario."""
    ADMIN    = "admin"
    REDACTOR = "redactor"
    LECTOR   = "lector"
    PUBLICO  = "publico"


class User:
    """Entidad de Usuario (dominio)."""
    
    def __init__(
        self,
        id: UUID,
        email: str,
        full_name: str,
        hashed_password: str,
        role: UserRole = UserRole.REDACTOR,
        is_active: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def update_password(self, new_hashed_password: str):
        """Actualizar contraseña."""
        self.hashed_password = new_hashed_password
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Desactivar usuario."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
