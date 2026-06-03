from uuid import uuid4
from app.modules.auth.domain.entities import User, UserRole
from app.modules.auth.application.ports import IUserRepository
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token


class RegisterUseCase:
    """Caso de uso: Registrar un nuevo usuario."""
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository
    
    async def execute(self, email: str, password: str, full_name: str) -> User:
        """Registrar un usuario."""
        # Verificar que no exista
        existing = await self.user_repository.get_by_email(email)
        if existing:
            raise ValueError(f"El usuario con email {email} ya existe")
        
        # Crear usuario
        hashed_password = get_password_hash(password)
        user = User(
            id=uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=UserRole.REDACTOR
        )
        
        # Persistir
        return await self.user_repository.create(user)


class LoginUseCase:
    """Caso de uso: Login de usuario."""
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository
    
    async def execute(self, email: str, password: str) -> dict:
        """Autenticar un usuario y retornar tokens."""
        # Obtener usuario
        user = await self.user_repository.get_by_email(email)
        if not user:
            raise ValueError("Email o contraseña inválida")
        
        # Verificar contraseña
        if not verify_password(password, user.hashed_password):
            raise ValueError("Email o contraseña inválida")
        
        # Generar tokens
        access_token = create_access_token(str(user.id), user.email, user.role.value)
        refresh_token = create_refresh_token(str(user.id), user.email)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


class GetUserUseCase:
    """Caso de uso: Obtener información del usuario."""
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository
    
    async def execute(self, user_id: str) -> User:
        """Obtener un usuario por ID."""
        from uuid import UUID
        user = await self.user_repository.get_by_id(UUID(user_id))
        if not user:
            raise ValueError("Usuario no encontrado")
        return user
