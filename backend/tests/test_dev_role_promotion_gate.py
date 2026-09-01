"""El atajo de promoción de rol no sobrevive a producción (SPEC-015 / T1.5 / AC4).

AC4: *Given* `ENABLE_DEV_ROLE_PROMOTION` ausente **o un `config.yaml` que lo
activa**, *When* `DEBUG=false`, *Then* el valor efectivo es `False` y
`dev/promote-reviewer` responde `403`.

La mitad que faltaba era la del `config.yaml`. Ser fail-safe *cuando el flag falta*
—lo único que había— no cubre el caso peligroso: un `config.yaml` con el flag a
`true` **viaja en el repositorio** y se despliega tal cual, así que el riesgo no es
olvidarse de ponerlo, sino olvidarse de quitarlo.

El endpoint deja que un usuario se cambie el rol a sí mismo; en producción eso es
una escalada de privilegios.
"""
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_dev_promotion.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from app.core import config as config_module  # noqa: E402
from app.core.config import _DEV_ONLY_FLAGS, settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


async def _reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def _register(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": "Anon"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _rebuild(monkeypatch, *, debug: bool, yaml_config: dict | None = None, env=None):
    """Reconstruye los settings como en un arranque real."""
    monkeypatch.setenv("SECRET_KEY", "0" * 64)
    monkeypatch.setenv("DEBUG", str(debug).lower())
    monkeypatch.delenv("ENABLE_DEV_ROLE_PROMOTION", raising=False)
    for clave, valor in (env or {}).items():
        monkeypatch.setenv(clave, valor)
    monkeypatch.setattr(config_module, "_read_yaml_config", lambda: yaml_config or {})
    return config_module._build_settings()


# --------------------------------------------------------------------------- #
# AC4 — el valor efectivo
# --------------------------------------------------------------------------- #

def test_a_config_yaml_cannot_enable_it_in_production(monkeypatch):
    """El hueco que faltaba: un config.yaml versionado con el flag a true."""
    rebuilt = _rebuild(
        monkeypatch, debug=False,
        yaml_config={"access_control": {"enable_dev_role_promotion": True}},
    )
    assert rebuilt.ENABLE_DEV_ROLE_PROMOTION is False


def test_an_environment_variable_cannot_enable_it_either(monkeypatch):
    rebuilt = _rebuild(monkeypatch, debug=False, env={"ENABLE_DEV_ROLE_PROMOTION": "true"})
    assert rebuilt.ENABLE_DEV_ROLE_PROMOTION is False


def test_it_stays_false_when_absent(monkeypatch):
    """La otra mitad de AC4, que ya se cumplía; queda fijada junto a la nueva."""
    assert _rebuild(monkeypatch, debug=False).ENABLE_DEV_ROLE_PROMOTION is False
    assert _rebuild(monkeypatch, debug=True).ENABLE_DEV_ROLE_PROMOTION is False


def test_development_can_still_turn_it_on(monkeypatch):
    """El gate no puede convertirse en «siempre apagado»: dev-local.cmd lo usa."""
    rebuilt = _rebuild(
        monkeypatch, debug=True,
        yaml_config={"access_control": {"enable_dev_role_promotion": True}},
    )
    assert rebuilt.ENABLE_DEV_ROLE_PROMOTION is True


@pytest.mark.parametrize("debug,configurado,esperado", [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, False),
])
def test_the_effective_value_needs_both(monkeypatch, debug, configurado, esperado):
    rebuilt = _rebuild(
        monkeypatch, debug=debug,
        yaml_config={"access_control": {"enable_dev_role_promotion": configurado}},
    )
    assert rebuilt.ENABLE_DEV_ROLE_PROMOTION is esperado


def test_the_flag_is_registered_as_dev_only():
    """Si alguien lo saca de la tupla, este test lo dice antes que un incidente."""
    assert "ENABLE_DEV_ROLE_PROMOTION" in _DEV_ONLY_FLAGS


# --------------------------------------------------------------------------- #
# AC4 — y el endpoint responde 403
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_the_endpoint_is_forbidden_in_production(monkeypatch):
    """Aunque la configuración lo pidiera: con DEBUG=false, 403."""
    await _reset_database()
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ENABLE_DEV_ROLE_PROMOTION", False)  # lo que deja la config
    try:
        async with _client() as client:
            token = await _register(client, "escalada@example.com")
            resp = await client.post(
                "/api/v1/auth/dev/promote-reviewer",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403, resp.text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_the_endpoint_does_not_change_the_role_when_forbidden(monkeypatch):
    """403 tiene que significar «no pasó nada», no «no te lo cuento»."""
    await _reset_database()
    monkeypatch.setattr(settings, "ENABLE_DEV_ROLE_PROMOTION", False)
    try:
        async with _client() as client:
            token = await _register(client, "sinefecto@example.com")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post("/api/v1/auth/dev/promote-reviewer", headers=headers)

            me = await client.get("/api/v1/auth/me", headers=headers)
            assert me.json()["role"] == "lector", "el rol cambió pese al 403"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_the_endpoint_still_works_in_development(monkeypatch):
    """Prueba de que el gate cierra por el motivo correcto y no está roto sin más."""
    await _reset_database()
    monkeypatch.setattr(settings, "ENABLE_DEV_ROLE_PROMOTION", True)
    try:
        async with _client() as client:
            token = await _register(client, "dev@example.com")
            resp = await client.post(
                "/api/v1/auth/dev/promote-reviewer",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, resp.text
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------- #
# Coherencia con lo que se despliega
# --------------------------------------------------------------------------- #

def test_the_shipped_config_files_keep_it_off():
    """Aunque ya no bastaría para activarlo, versionarlo a `true` sería una señal
    equivocada para quien lea el fichero."""
    import yaml

    for ruta in ("config.yaml", "backend/config.yaml"):
        datos = yaml.safe_load((ROOT_DIR.parent / ruta).read_text(encoding="utf-8"))
        acceso = datos.get("access_control", {})
        assert acceso.get("enable_dev_role_promotion") is False, ruta


def test_the_production_compose_keeps_it_off():
    import yaml

    class T(yaml.SafeLoader):
        pass

    T.add_multi_constructor("!", lambda l, s, n: None)
    for ruta in ("docker-compose.yml", "docker-compose.prod.yml"):
        compose = yaml.load((ROOT_DIR.parent / ruta).read_text(encoding="utf-8"), Loader=T)
        entorno = compose["services"]["backend"].get("environment", {}) or {}
        assert str(entorno.get("ENABLE_DEV_ROLE_PROMOTION", "false")).lower() == "false", ruta
