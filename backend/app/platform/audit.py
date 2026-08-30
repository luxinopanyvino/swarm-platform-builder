"""Registro de acciones sensibles (SPEC-020 / T6.4 / AC4).

Un audit log solo vale si es fiable, así que este helper toma dos decisiones
explícitas sobre cuándo se escribe y qué pasa si falla.

**Dentro de la transacción del llamante, por defecto.** `record_audit` hace
`session.add` y **no** hace commit: la fila viaja en la misma transacción que el
cambio que describe. De ahí salen las dos propiedades que se quieren — no queda
registrada una acción que acabó revertida, ni se pierde el registro de una acción
que sí se aplicó.

**Salvo cuando no hay transacción que aprovechar.** Un intento de login fallido
termina lanzando un `401`: no hay commit posterior al que engancharse, así que ese
camino usa `commit=True`. Y ahí el fallo del propio registro **no** puede convertir
un `401` en un `500`, así que se captura y se deja en el log de errores. La
asimetría es deliberada: en el camino transaccional un fallo debe propagarse
(rompería la atomicidad), en el otro no.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import request_id_ctx
from app.models.audit_log import AuditAction, AuditLogModel

logger = logging.getLogger(__name__)

__all__ = ["AuditAction", "record_audit", "mask_email", "client_ip"]


def mask_email(email: str | None) -> str | None:
    """`ana@ejemplo.com` → `a***@ejemplo.com`.

    Suficiente para correlacionar intentos contra una misma cuenta sin guardar la
    dirección. En los login fallidos el correo puede ni siquiera existir: guardarlo
    entero convertiría la tabla en un listado de direcciones tecleadas.
    """
    if not email:
        return None
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    head = local[0] if local else ""
    return f"{head}***@{domain}"


def client_ip(request) -> str | None:
    """IP del cliente, con el primer salto de `X-Forwarded-For` si viene por proxy."""
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client and request.client.host:
        return request.client.host
    return None


def _as_uuid(value: Any) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def build_entry(
    *,
    action: str,
    actor: Mapping[str, Any] | None = None,
    actor_id: Any = None,
    actor_role: str | None = None,
    email: str | None = None,
    target_type: str | None = None,
    target_id: Any = None,
    request=None,
    detail: dict[str, Any] | None = None,
) -> AuditLogModel:
    """Construye la fila sin tocar la sesión (útil para probarla aislada)."""
    if actor:
        actor_id = actor_id if actor_id is not None else actor.get("user_id")
        actor_role = actor_role or actor.get("role")
        email = email or actor.get("email")

    return AuditLogModel(
        actor_id=_as_uuid(actor_id),
        actor_role=str(actor_role) if actor_role else None,
        actor_email_masked=mask_email(email),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        ip=client_ip(request),
        # Correlación con el log estructurado de T5.1: con este id se recupera la
        # traza completa de la petición que provocó la acción.
        request_id=(request_id_ctx.get() or None) if request_id_ctx.get() != "-" else None,
        detail=detail or {},
    )


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    commit: bool = False,
    **fields: Any,
) -> AuditLogModel | None:
    """Registra una acción sensible.

    Por defecto se suma a la transacción abierta del llamante (ver docstring del
    módulo). Con ``commit=True`` se persiste por su cuenta, para los caminos que
    terminan lanzando una excepción y nunca llegan a un commit.
    """
    entry = build_entry(action=action, **fields)
    session.add(entry)

    if not commit:
        return entry

    try:
        await session.commit()
    except Exception:
        # Camino de excepción (p. ej. login fallido): auditar no puede convertir un
        # 401 en un 500. Se deja constancia en el log de errores y se sigue.
        logger.error(
            "No se pudo registrar la acción auditada %s", action,
            exc_info=True,
            extra={"event": "audit_write_failed", "audit_action": action},
        )
        await session.rollback()
        return None
    return entry
