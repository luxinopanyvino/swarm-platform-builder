"""Shared pytest fixtures for the backend test-suite."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the backend package is importable when pytest is invoked from repo root.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ── Los tests nunca tocan la base de desarrollo ─────────────────────────────
#
# Cada test fija su `DATABASE_URL` al importarse, pero `settings` y el `engine` se
# construyen **una vez**, con lo que haya en el entorno al primer import de
# `app.core.config`. Si el primer fichero en importarse no lo fija —un test que no
# usa la base—, gana `config.yaml`, que apunta a `./data/dev.db`, y el siguiente
# fixture con `Base.metadata.drop_all` vacía la base de desarrollo real. Pasó al
# correr un subconjunto de tests: se perdieron usuarios, artículos y flujos, y
# `alembic_version` sobrevivió marcando `head`, así que el backend no volvía a
# crear las tablas y no arrancaba.
#
# Dos capas: un valor por defecto seguro antes de importar nada de `app`, y una
# guarda que aborta la sesión si la base efectiva es la de desarrollo (p. ej. un
# `DATABASE_URL` exportado en la shell, que `setdefault` respeta).
_BASE_DE_TESTS = Path(tempfile.gettempdir()) / f"swarm-backend-tests-{os.getpid()}.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_BASE_DE_TESTS.as_posix()}")

# Donde vive la base de desarrollo (`config.yaml`, `dev-local.cmd`).
DIRECTORIO_DE_DESARROLLO = ROOT_DIR / "data"

from app.core.rate_limit import reset_auth_throttling  # noqa: E402


def motivo_para_rechazar_url(url: str, cwd: Path) -> str | None:
    """Por qué `url` no es una base aceptable para los tests, o `None` si lo es."""
    if not url.startswith("sqlite"):
        return "no es SQLite: los tests borran tablas y solo deben correr sobre una base desechable"
    ruta = url.split(":///", 1)[1] if ":///" in url else ""
    if not ruta or ruta == ":memory:":
        return None
    fichero = Path(ruta)
    if not fichero.is_absolute():
        fichero = cwd / fichero
    try:
        fichero.resolve().relative_to(DIRECTORIO_DE_DESARROLLO.resolve())
    except ValueError:
        return None
    return f"apunta a la base de desarrollo ({fichero.resolve()})"


def pytest_collection_finish(session):
    """Con todos los tests importados, `settings` ya dice qué base se va a usar."""
    config = sys.modules.get("app.core.config")
    url = config.settings.DATABASE_URL if config else os.environ.get("DATABASE_URL", "")
    motivo = motivo_para_rechazar_url(url, Path.cwd())
    if motivo:
        pytest.exit(
            f"Tests abortados: DATABASE_URL {motivo}. Los fixtures hacen drop_all y la "
            "vaciarían. Quita DATABASE_URL del entorno o apúntalo a un fichero temporal.",
            returncode=2,
        )


def pytest_sessionfinish(session, exitstatus):
    """Borra la base temporal por defecto; en Windows puede seguir abierta y se deja."""
    try:
        _BASE_DE_TESTS.unlink(missing_ok=True)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _reset_auth_throttling():
    """Keep auth rate-limit / lockout state isolated between tests.

    The throttling stores are process-wide singletons; without this reset, hits
    from one test would leak into the next and make the suite order-dependent.
    """
    reset_auth_throttling()
    yield
    reset_auth_throttling()
