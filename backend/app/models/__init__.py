"""Domain models package: ORM schemas and Pydantic DTOs.

Historically these lived in a single ``app/models.py`` monolith. They are now
split by domain into submodules, but the public surface is preserved: every
name that used to be importable as ``from app.models import X`` still is.

Importing this package imports every submodule that defines an ORM model, so
they all register on ``Base.metadata`` (required by ``create_all`` in tests and
``init_db``).
"""
from app.core.database import Base

from app.models.enums import (
    ArticleStatus,
    ProjectUseCaseType,
    ScientificFormat,
    UserRole,
)
from app.models.user import (
    TokenResponse,
    UserLoginDTO,
    UserModel,
    UserRegisterDTO,
    UserResponse,
)
from app.models.article import (
    ArticleListResponse,
    ArticleModel,
    ArticleResponse,
    AuthorDTO,
    ThemeDTO,
    CreateArticleDTO,
    UpdateArticleDTO,
)
from app.models.audit_log import (
    AuditAction,
    AuditLogModel,
    AuditLogResponse,
)
from app.models.project import (
    ProjectCreateDTO,
    ProjectModel,
    ProjectResponse,
    UserProjectAccessModel,
)
from app.models.agent_profile import (
    AgentProfileModel,
    AgentProfileResponse,
)
from app.models.agent_run import (
    AgentRunDetailResponse,
    AgentRunListResponse,
    AgentRunModel,
    AgentRunRequest,
)
from app.models.saved_flow import (
    CreateSavedFlowDTO,
    SavedFlowModel,
    SavedFlowResponse,
    UpdateSavedFlowDTO,
)
from app.models.checkpoint import (
    CheckpointResponse,
    CreateCheckpointDTO,
    FlowCheckpointModel,
)
from app.models.notification import (
    NotificationModel,
    NotificationResponse,
)
from app.models.ai import (
    AIAssistRequest,
    AIAssistResponse,
    AIFormatRequest,
    AIFormatResponse,
    AIIngestRequest,
)

__all__ = [
    "Base",
    # Audit log (SPEC-020/T6.4)
    "AuditAction",
    "AuditLogModel",
    "AuditLogResponse",
    # Enums
    "UserRole",
    "ArticleStatus",
    "ProjectUseCaseType",
    "ScientificFormat",
    # User
    "UserModel",
    "UserRegisterDTO",
    "UserLoginDTO",
    "UserResponse",
    "TokenResponse",
    # Article
    "ArticleModel",
    "CreateArticleDTO",
    "AuthorDTO",
    "ThemeDTO",
    "UpdateArticleDTO",
    "ArticleResponse",
    "ArticleListResponse",
    # Project
    "ProjectModel",
    "UserProjectAccessModel",
    "ProjectCreateDTO",
    "ProjectResponse",
    # Agent profile
    "AgentProfileModel",
    "AgentProfileResponse",
    # Agent run
    "AgentRunModel",
    "AgentRunRequest",
    "AgentRunDetailResponse",
    "AgentRunListResponse",
    # Saved flow
    "SavedFlowModel",
    "CreateSavedFlowDTO",
    "UpdateSavedFlowDTO",
    "SavedFlowResponse",
    # Checkpoint
    "FlowCheckpointModel",
    "CreateCheckpointDTO",
    "CheckpointResponse",
    # Notification
    "NotificationModel",
    "NotificationResponse",
    # AI
    "AIAssistRequest",
    "AIAssistResponse",
    "AIIngestRequest",
    "AIFormatRequest",
    "AIFormatResponse",
]
