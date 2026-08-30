"""Audit log de acciones sensibles (SPEC-020 / T6.4 / AC4).

Registra **quién**, **qué**, **cuándo** y **desde dónde** para las acciones que
cambian permisos, publican contenido, destruyen datos o revelan un ataque en
curso. Es una bitácora de seguridad, no telemetría: cada fila debe poder
sostenerse en una revisión posterior.

Dos decisiones de diseño que conviene entender antes de tocar esta tabla:

**No hay clave ajena a `users`.** El actor se guarda como UUID suelto. Una FK con
``ON DELETE SET NULL`` borraría el rastro justo cuando más falta hace —al eliminar
la cuenta que hizo algo— y una con ``CASCADE`` borraría la fila entera. El UUID es
además pseudónimo: identifica sin arrastrar datos personales.

**El correo va enmascarado.** En los intentos de login fallidos el actor no está
autenticado y lo único que hay es el correo tecleado, que puede ni existir.
Guardarlo entero convertiría esta tabla en un listado de direcciones; se guarda
como ``a***@dominio.com``, igual que ya hacen los logs de auth, que basta para
correlacionar intentos contra una misma cuenta.
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, JSON, String, UUID as SA_UUID

from app.core.database import Base


class AuditAction:
    """Acciones auditadas. Cadenas estables: se consultan y se alertan por ellas."""

    ROLE_CHANGED = "role.changed"
    ARTICLE_PUBLISHED = "article.published"
    RAG_DOCUMENT_DELETED = "rag.document.deleted"
    LOGIN_FAILED = "auth.login_failed"
    ACCOUNT_LOCKED = "auth.account_locked"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        return (
            cls.ROLE_CHANGED,
            cls.ARTICLE_PUBLISHED,
            cls.RAG_DOCUMENT_DELETED,
            cls.LOGIN_FAILED,
            cls.ACCOUNT_LOCKED,
        )


class AuditLogModel(Base):
    """Una acción sensible, tal como ocurrió."""

    __tablename__ = "audit_log"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Quién. Sin FK a propósito (ver docstring del módulo).
    actor_id = Column(SA_UUID(as_uuid=True), nullable=True, index=True)
    actor_role = Column(String(32), nullable=True)
    actor_email_masked = Column(String(255), nullable=True)

    # Qué.
    action = Column(String(64), nullable=False, index=True)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(128), nullable=True, index=True)

    # Desde dónde, y con qué petición.
    ip = Column(String(64), nullable=True)
    # Correlaciona con el log estructurado de SPEC-019/T5.1: con este id se
    # recupera la traza completa de la petición que provocó la acción.
    request_id = Column(String(64), nullable=True, index=True)

    # Contexto mínimo y no sensible (p. ej. rol anterior y nuevo).
    detail = Column(JSON, default=dict, nullable=False)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    actor_id: UUID | None
    actor_role: str | None
    actor_email_masked: str | None
    action: str
    target_type: str | None
    target_id: str | None
    ip: str | None
    request_id: str | None
    detail: dict[str, Any]
