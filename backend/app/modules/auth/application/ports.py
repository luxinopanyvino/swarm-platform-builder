from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from app.modules.auth.domain.entities import User


class IUserRepository(ABC):
    """Puerto de salida: Repositorio de usuarios."""
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """Crear un usuario."""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email."""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Obtener usuario por ID."""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Actualizar un usuario."""
        pass
