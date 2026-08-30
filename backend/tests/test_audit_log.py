"""Audit log de acciones sensibles (SPEC-020 / T6.4 / AC4).

AC4: una acción sensible —cambio de rol, publicación, borrado de documentos RAG,
login fallido o bloqueo— queda registrada en un audit log **consultable**, con
quién, qué, cuándo y desde dónde, y **sin PII innecesaria**.

Los casos van de extremo a extremo (petición HTTP → fila en la tabla) porque lo que
se quiere garantizar no es que el helper funcione, sino que los routers lo llamen:
un audit log del que se olvida un endpoint es peor que no tenerlo, porque genera
confianza infundada.
"""
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_audit.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import ArticleModel, ArticleStatus, UserModel, UserRole  # noqa: E402
from app.models.audit_log import AuditAction, AuditLogModel  # noqa: E402
from app.platform.audit import build_entry, mask_email  # noqa: E402


@pytest_asyncio.fixture
async def db():
    """Esquema limpio para cada test.

    Fixture async explícita (`pytest_asyncio.fixture`) y no autouse: los casos que
    solo ejercitan el enmascarado y la construcción de la entrada son síncronos y no
    tocan la base, así que no tienen por qué pagar el ciclo de creación.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _make_user(email: str, role: UserRole, password: str = "Contrasena-1234") -> UserModel:
    async with AsyncSessionLocal() as session:
        user = UserModel(
            email=email,
            hashed_password=hash_password(password),
            full_name=email.split("@")[0],
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _token(client: AsyncClient, email: str, password: str = "Contrasena-1234") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _entries(action: str | None = None) -> list[AuditLogModel]:
    async with AsyncSessionLocal() as session:
        stmt = select(AuditLogModel)
        if action:
            stmt = stmt.where(AuditLogModel.action == action)
        result = await session.execute(stmt.order_by(AuditLogModel.created_at))
        return list(result.scalars().all())


# --------------------------------------------------------------------------- #
# Enmascarado y construcción de la entrada
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw,expected", [
    ("ana@ejemplo.com", "a***@ejemplo.com"),
    ("x@d.io", "x***@d.io"),
    ("@sinlocal.com", "***@sinlocal.com"),
    ("sindominio", "***"),
    (None, None),
])
def test_email_masking(raw, expected):
    assert mask_email(raw) == expected


def test_entry_takes_actor_fields_from_the_token_payload():
    actor = {"user_id": str(uuid4()), "role": "admin", "email": "jefa@ejemplo.com"}
    entry = build_entry(action=AuditAction.ROLE_CHANGED, actor=actor, target_type="user")

    assert str(entry.actor_id) == actor["user_id"]
    assert entry.actor_role == "admin"
    assert entry.actor_email_masked == "j***@ejemplo.com"


def test_entry_never_stores_a_raw_email():
    entry = build_entry(action=AuditAction.LOGIN_FAILED, email="victima@ejemplo.com")
    assert entry.actor_email_masked == "v***@ejemplo.com"
    assert "victima" not in (entry.actor_email_masked or "")


def test_entry_survives_a_malformed_actor_id():
    """Un id ilegible no puede tumbar la acción que se está auditando."""
    entry = build_entry(action=AuditAction.ROLE_CHANGED, actor_id="no-es-un-uuid")
    assert entry.actor_id is None


# --------------------------------------------------------------------------- #
# AC4 — cada acción sensible deja rastro
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_role_change_is_audited(db, client):
    admin = await _make_user("admin-audit@ejemplo.com", UserRole.ADMIN)
    victim = await _make_user("otro@ejemplo.com", UserRole.LECTOR)

    async with client as ac:
        token = await _token(ac, admin.email)
        response = await ac.put(
            f"/api/v1/auth/users/{victim.id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {token}", "X-Request-ID": "corr-rol"},
        )
    assert response.status_code == 200, response.text

    entries = await _entries(AuditAction.ROLE_CHANGED)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.actor_id == admin.id           # quién
    assert entry.target_id == str(victim.id)    # sobre quién
    assert entry.detail == {"from": "lector", "to": "admin"}
    assert entry.request_id == "corr-rol"       # correlación con los logs de T5.1
    assert entry.created_at is not None         # cuándo


@pytest.mark.asyncio
async def test_publishing_an_article_is_audited(db, client):
    author = await _make_user("redactora@ejemplo.com", UserRole.REDACTOR)
    async with AsyncSessionLocal() as session:
        article = ArticleModel(
            title="Un artículo", body="cuerpo", status=ArticleStatus.DRAFT, author_id=author.id
        )
        session.add(article)
        await session.commit()
        await session.refresh(article)

    async with client as ac:
        token = await _token(ac, author.email)
        response = await ac.post(
            f"/api/v1/articles/{article.id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200, response.text

    entries = await _entries(AuditAction.ARTICLE_PUBLISHED)
    assert len(entries) == 1
    assert entries[0].target_id == str(article.id)
    assert entries[0].actor_id == author.id


@pytest.mark.asyncio
async def test_a_failed_login_is_audited_even_though_it_ends_in_401(db, client):
    """El camino de excepción no llega a un commit del llamante: se persiste aparte."""
    await _make_user("existe@ejemplo.com", UserRole.LECTOR)

    async with client as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "existe@ejemplo.com", "password": "incorrecta"},
        )
    assert response.status_code == 401

    entries = await _entries(AuditAction.LOGIN_FAILED)
    assert len(entries) == 1
    assert entries[0].actor_id is None                       # no hay actor autenticado
    assert entries[0].actor_email_masked == "e***@ejemplo.com"
    assert entries[0].detail["user_exists"] is True


@pytest.mark.asyncio
async def test_the_audit_trail_never_stores_the_attempted_password(db, client):
    async with client as ac:
        await ac.post(
            "/api/v1/auth/login",
            json={"email": "quien@ejemplo.com", "password": "SUPERSECRETA-NO-GUARDAR"},
        )

    for entry in await _entries():
        volcado = f"{entry.detail} {entry.actor_email_masked} {entry.target_id}"
        assert "SUPERSECRETA" not in volcado


@pytest.mark.asyncio
async def test_repeated_failures_end_in_an_account_locked_entry(db, client):
    from app.core.config import settings

    await _make_user("bloqueable@ejemplo.com", UserRole.LECTOR)
    async with client as ac:
        for _ in range(settings.AUTH_LOCKOUT_MAX_FAILED):
            await ac.post(
                "/api/v1/auth/login",
                json={"email": "bloqueable@ejemplo.com", "password": "mala"},
            )

    assert len(await _entries(AuditAction.ACCOUNT_LOCKED)) == 1


# --------------------------------------------------------------------------- #
# AC4 — y es consultable, pero no por cualquiera
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_the_audit_endpoint_requires_an_admin(db, client):
    await _make_user("curiosa@ejemplo.com", UserRole.LECTOR)
    async with client as ac:
        token = await _token(ac, "curiosa@ejemplo.com")
        response = await ac.get("/api/v1/audit", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_the_audit_endpoint_rejects_anonymous_callers(db, client):
    async with client as ac:
        response = await ac.get("/api/v1/audit")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_an_admin_can_query_and_filter_the_trail(db, client):
    admin = await _make_user("jefa@ejemplo.com", UserRole.ADMIN)
    victim = await _make_user("cambiante@ejemplo.com", UserRole.LECTOR)

    async with client as ac:
        token = await _token(ac, admin.email)
        headers = {"Authorization": f"Bearer {token}"}
        await ac.put(
            f"/api/v1/auth/users/{victim.id}/role", json={"role": "redactor"}, headers=headers
        )
        await ac.post("/api/v1/auth/login", json={"email": victim.email, "password": "mala"})

        todo = await ac.get("/api/v1/audit", headers=headers)
        filtrado = await ac.get(
            "/api/v1/audit", params={"action": AuditAction.ROLE_CHANGED}, headers=headers
        )

    assert todo.status_code == 200
    assert todo.json()["total"] >= 2
    assert filtrado.json()["total"] == 1
    assert filtrado.json()["items"][0]["action"] == AuditAction.ROLE_CHANGED


@pytest.mark.asyncio
async def test_the_query_is_paginated_and_capped(db, client):
    admin = await _make_user("paginadora@ejemplo.com", UserRole.ADMIN)
    async with client as ac:
        token = await _token(ac, admin.email)
        headers = {"Authorization": f"Bearer {token}"}
        for _ in range(3):
            await ac.post("/api/v1/auth/login", json={"email": "x@y.z", "password": "mala"})

        pagina = await ac.get("/api/v1/audit", params={"limit": 2}, headers=headers)
        excesivo = await ac.get("/api/v1/audit", params={"limit": 5000}, headers=headers)

    assert len(pagina.json()["items"]) == 2
    assert pagina.json()["total"] >= 3
    assert excesivo.status_code == 422, "el límite superior no se está aplicando"


@pytest.mark.asyncio
async def test_the_trail_is_read_only_over_http(db, client):
    """No hay borrado por API: purgar es política de retención (T6.5), no una llamada."""
    admin = await _make_user("solo-lectura@ejemplo.com", UserRole.ADMIN)
    async with client as ac:
        token = await _token(ac, admin.email)
        headers = {"Authorization": f"Bearer {token}"}
        borrado = await ac.delete("/api/v1/audit", headers=headers)
        alta = await ac.post("/api/v1/audit", json={}, headers=headers)

    assert borrado.status_code == 405
    assert alta.status_code == 405


@pytest.mark.asyncio
async def test_deleting_a_rag_document_is_audited(db, client, monkeypatch):
    """Sin Qdrant: se sustituye el borrado remoto, que no es lo que se prueba aquí.

    Lo que importa es que el endpoint deje rastro, porque el borrado **no es
    reversible** desde la aplicación: si nadie registra quién lo hizo, el documento
    simplemente desaparece.
    """
    import app.routers.agents as agents_router

    async def _fake_delete(*args, **kwargs):
        return True

    monkeypatch.setattr(agents_router, "delete_document", _fake_delete)

    admin = await _make_user("borradora@ejemplo.com", UserRole.ADMIN)
    async with client as ac:
        token = await _token(ac, admin.email)
        response = await ac.delete(
            "/api/v1/agents/investigador/rag/documents/doc-42",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200, response.text

    entries = await _entries(AuditAction.RAG_DOCUMENT_DELETED)
    assert len(entries) == 1
    assert entries[0].target_id == "doc-42"
    assert entries[0].actor_id == admin.id
    assert entries[0].detail["agent"] == "investigador"


@pytest.mark.asyncio
async def test_a_failed_rag_deletion_leaves_no_audit_entry(db, client, monkeypatch):
    """Nada que auditar si nada se borró: el registro describe hechos, no intentos."""
    import app.routers.agents as agents_router

    async def _fake_delete(*args, **kwargs):
        return False

    monkeypatch.setattr(agents_router, "delete_document", _fake_delete)

    admin = await _make_user("fallida@ejemplo.com", UserRole.ADMIN)
    async with client as ac:
        token = await _token(ac, admin.email)
        response = await ac.delete(
            "/api/v1/agents/investigador/rag/documents/doc-99",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 500
    assert await _entries(AuditAction.RAG_DOCUMENT_DELETED) == []
