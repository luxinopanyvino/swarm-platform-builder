"""Los seeds de credenciales débiles viven tras un flag de dev (SPEC-015/T1.6/AC5).

AC5: con `DEBUG=false` no se siembran usuarios con credenciales débiles; el seed de
demo solo corre bajo flag de dev explícito.

Antes la condición era «la base de datos es SQLite», un proxy de «esto es local»
que no lo es: **cualquier despliegue sobre SQLite creaba `admin@admin` con
contraseña conocida**. Y no solo lo creaba — reimponía contraseña, rol y estado
activo en *cada arranque*, revirtiendo en silencio un cambio deliberado.

Los casos ejercitan las funciones de arranque de verdad, no el flag por separado:
lo que hay que garantizar es que **nadie siembre**, no que la condición exista.
"""
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_dev_seed.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from sqlalchemy import select  # noqa: E402

from app.core.config import Settings, _disable_dev_only_flags, settings  # noqa: E402
from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.core.security import hash_password, verify_password  # noqa: E402
from app.main import (  # noqa: E402
    dev_seed_enabled,
    ensure_dev_users,
    ensure_local_admin_user,
)
from app.models import UserModel, UserRole  # noqa: E402

CUENTAS_DEBILES = (
    "admin@admin",
    "redactor@example.com",
    "revisor@example.com",
    "publico@example.com",
)


@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def seed_on(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "ENABLE_DEV_SEED", True)


async def _usuarios() -> dict[str, UserModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserModel))
        return {u.email: u for u in result.scalars().all()}


# --------------------------------------------------------------------------- #
# AC5 — con DEBUG=false no se siembra nada
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_no_weak_accounts_are_seeded_by_default(db):
    """Por defecto —sin tocar nada— el arranque no crea ninguna cuenta."""
    await ensure_local_admin_user()
    await ensure_dev_users()
    assert await _usuarios() == {}


@pytest.mark.asyncio
async def test_the_flag_alone_is_not_enough_without_debug(db, monkeypatch):
    """La regresión que se quiere impedir: producción con el flag encendido."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ENABLE_DEV_SEED", False)  # lo que dejaría la config

    await ensure_local_admin_user()
    await ensure_dev_users()
    assert await _usuarios() == {}


def test_config_forces_the_flag_off_when_debug_is_false(monkeypatch):
    """Aunque config.yaml o el entorno lo activen: `DEBUG=false` manda.

    Es lo que convierte «acuérdate de apagarlo al desplegar» en algo que no hace
    falta recordar.
    """
    valores = {"DEBUG": False, "ENABLE_DEV_SEED": True}
    _disable_dev_only_flags(valores)
    assert valores["ENABLE_DEV_SEED"] is False


def test_the_flag_survives_when_debug_is_on():
    valores = {"DEBUG": True, "ENABLE_DEV_SEED": True}
    _disable_dev_only_flags(valores)
    assert valores["ENABLE_DEV_SEED"] is True


@pytest.mark.parametrize("debug,flag,esperado", [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, False),
])
def test_the_effective_value_needs_both(monkeypatch, debug, flag, esperado):
    monkeypatch.setenv("DEBUG", str(debug).lower())
    monkeypatch.setenv("ENABLE_DEV_SEED", str(flag).lower())
    monkeypatch.setenv("SECRET_KEY", "0" * 64)
    from app.core import config as config_module

    assert config_module._build_settings().ENABLE_DEV_SEED is esperado


def test_sqlite_is_no_longer_what_decides(monkeypatch):
    """El fallo de origen: SQLite se usaba como sinónimo de «esto es local»."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ENABLE_DEV_SEED", False)
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
    assert dev_seed_enabled() is False


# --------------------------------------------------------------------------- #
# AC5 — con el flag, la demo sigue funcionando
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_the_dev_accounts_are_created_with_the_flag(db, seed_on):
    await ensure_local_admin_user()
    await ensure_dev_users()

    usuarios = await _usuarios()
    for correo in CUENTAS_DEBILES:
        assert correo in usuarios, f"falta {correo}: el flujo local dejaría de funcionar"
    assert usuarios["admin@admin"].role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_the_documented_admin_password_still_works(db, seed_on):
    """El README promete admin@admin/admin123 bajo el flag; tiene que ser verdad."""
    await ensure_local_admin_user()
    admin = (await _usuarios())["admin@admin"]
    assert verify_password("admin123", admin.hashed_password)


@pytest.mark.asyncio
async def test_the_admin_password_can_be_overridden(db, seed_on, monkeypatch):
    monkeypatch.setenv("DEV_ADMIN_PASSWORD", "otra-contrasena-de-dev")
    await ensure_local_admin_user()
    admin = (await _usuarios())["admin@admin"]
    assert verify_password("otra-contrasena-de-dev", admin.hashed_password)
    assert not verify_password("admin123", admin.hashed_password)


# --------------------------------------------------------------------------- #
# El otro defecto: reimponer credenciales en cada arranque
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_an_existing_admin_password_is_never_overwritten(db, seed_on):
    """Reimponerla le quitaba al operador el control de su propia cuenta."""
    async with AsyncSessionLocal() as session:
        session.add(UserModel(
            email="admin@admin", hashed_password=hash_password("la-que-yo-elegi"),
            full_name="Admin", role=UserRole.ADMIN, is_active=True,
        ))
        await session.commit()

    await ensure_local_admin_user()

    admin = (await _usuarios())["admin@admin"]
    assert verify_password("la-que-yo-elegi", admin.hashed_password)
    assert not verify_password("admin123", admin.hashed_password)


@pytest.mark.asyncio
async def test_a_deactivated_account_is_not_reactivated(db, seed_on):
    """Desactivar una cuenta es una decisión; el arranque no puede deshacerla."""
    async with AsyncSessionLocal() as session:
        session.add(UserModel(
            email="redactor@example.com", hashed_password=hash_password("x" * 12),
            full_name="Redactor", role=UserRole.LECTOR, is_active=False,
        ))
        await session.commit()

    await ensure_dev_users()

    usuario = (await _usuarios())["redactor@example.com"]
    assert usuario.is_active is False
    assert usuario.role == UserRole.LECTOR, "se le devolvió el rol sembrado"


@pytest.mark.asyncio
async def test_seeding_twice_changes_nothing(db, seed_on):
    await ensure_local_admin_user()
    await ensure_dev_users()
    primero = {c: (u.hashed_password, u.role, u.is_active) for c, u in (await _usuarios()).items()}

    await ensure_local_admin_user()
    await ensure_dev_users()
    segundo = {c: (u.hashed_password, u.role, u.is_active) for c, u in (await _usuarios()).items()}

    assert primero == segundo


# --------------------------------------------------------------------------- #
# Coherencia con lo que se documenta y se despliega
# --------------------------------------------------------------------------- #

def test_the_flag_defaults_to_off_in_the_settings():
    assert Settings().ENABLE_DEV_SEED is False


def test_the_local_dev_script_enables_the_flag():
    """Si no, el flujo local documentado se rompería sin explicación."""
    script = (ROOT_DIR.parent / "dev-local.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "ENABLE_DEV_SEED=true" in script


def test_the_production_compose_never_enables_it():
    import yaml

    class T(yaml.SafeLoader):
        pass

    T.add_multi_constructor("!", lambda l, s, n: None)
    compose = yaml.load((ROOT_DIR.parent / "docker-compose.prod.yml").read_text(), Loader=T)
    entorno = compose["services"]["backend"].get("environment", {}) or {}
    assert str(entorno.get("ENABLE_DEV_SEED", "false")).lower() == "false"


@pytest.mark.parametrize("doc", ["README.md", "docs/guide/auth.md"])
def test_the_docs_say_the_accounts_need_the_flag(doc):
    """Prometer usuarios que ya no aparecen solos es peor que no documentarlos."""
    texto = (ROOT_DIR.parent / doc).read_text(encoding="utf-8")
    assert "ENABLE_DEV_SEED" in texto
