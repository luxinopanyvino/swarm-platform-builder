"""Enumerations shared across ORM models and DTOs."""
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system.

    - ADMIN:    full platform access; can manage users and assign roles.
    - REDACTOR: can create and edit articles, run pipelines.
    - LECTOR:   read-only access to published articles inside the platform.
    - PUBLICO:  unauthenticated / public access to the magazine slideshow only.
    """
    ADMIN    = "admin"
    REDACTOR = "redactor"
    LECTOR   = "lector"
    PUBLICO  = "publico"


class ArticleStatus(str, Enum):
    """Article lifecycle states."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ProjectUseCaseType(str, Enum):
    """Project use case types."""
    ALEJANDRIA_MAGAZINE = "alejandria_magazine"
    DESARROLLO = "desarrollo"
    MARKETING = "marketing"
    TIQUETING = "tiqueting"
    DISENO = "diseno"
    CUSTOM = "custom"


class ScientificFormat(str, Enum):
    """Supported scientific formats (must stay in sync with the formateador adapter)."""
    APA = "apa"
    IEEE = "ieee"
    ACL = "acl"
    VANCOUVER = "vancouver"
    CHICAGO = "chicago"
    NATURE = "nature"
    NONE = "none"
