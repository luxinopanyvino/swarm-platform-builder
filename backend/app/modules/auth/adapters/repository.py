from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import Optional

from app.modules.auth.domain.entities import User, UserRole
from app.modules.auth.application.ports import IUserRepository
from app.modules.auth.adapters.persistence import UserORM


class UserRepositoryImpl(IUserRepository):
    """Implementación del repositorio de usuarios."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user: User) -> User:
        """Crear un usuario en la BD."""
        orm_user = UserORM(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            role=user.role.value,
            is_active=user.is_active
        )
        self.session.add(orm_user)
        await self.session.commit()
        await self.session.refresh(orm_user)
        return self._to_domain(orm_user)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email."""
        result = await self.session.execute(
            select(UserORM).where(UserORM.email == email)
        )
        orm_user = result.scalars().first()
        return self._to_domain(orm_user) if orm_user else None
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Obtener usuario por ID."""
        result = await self.session.execute(
            select(UserORM).where(UserORM.id == user_id)
        )
        orm_user = result.scalars().first()
        return self._to_domain(orm_user) if orm_user else None
    
    async def update(self, user: User) -> User:
        """Actualizar un usuario."""
        result = await self.session.execute(
            select(UserORM).where(UserORM.id == user.id)
        )
        orm_user = result.scalars().first()
        
        if not orm_user:
            raise ValueError("Usuario no encontrado")
        
        orm_user.email = user.email
        orm_user.full_name = user.full_name
        orm_user.hashed_password = user.hashed_password
        orm_user.role = user.role.value
        orm_user.is_active = user.is_active
        
        await self.session.commit()
        await self.session.refresh(orm_user)
        return self._to_domain(orm_user)
    
    def _to_domain(self, orm_user: UserORM) -> User:
        """Convertir ORM a dominio."""
        if not orm_user:
            return None
        return User(
            id=orm_user.id,
            email=orm_user.email,
            full_name=orm_user.full_name,
            hashed_password=orm_user.hashed_password,
            role=UserRole(orm_user.role),
            is_active=orm_user.is_active,
            created_at=orm_user.created_at,
            updated_at=orm_user.updated_at
        )
