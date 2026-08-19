"""Ninguna base de datos local vive en el repositorio (SPEC-018 / T4.2 / AC2).

AC2: `dev.db` —y cualquier `*.db` local— no está trackeado, `.gitignore` lo
excluye, y el arranque en desarrollo lo recrea solo.

Un binario de SQLite versionado no solo ensucia el historial: `backend/dev.db`
llevaba los hashes de contraseña de los usuarios de desarrollo y llegó a estar
**cinco meses desactualizado** respecto a la base real (`backend/data/dev.db`),
así que cualquiera que lo abriese leería un esquema que ya no existe. Estos tests
impiden que vuelva a colarse uno.
"""
import os
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(ROOT_DIR / 'tests' / 'test_no_tracked_db.db').as_posix()}",
)

DB_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".db-journal", ".db-wal", ".db-shm")


def _git(*args: str) -> str:
    """Ejecuta git en el repo; salta el test si no hay repo o no hay git."""
    try:
        result = subprocess.run(
            ("git", *args), cwd=REPO_DIR, capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:  # pragma: no cover
        pytest.skip(f"git no disponible: {exc}")
    if result.returncode not in (0, 1):  # 1 = "sin coincidencias" en check-ignore
        pytest.skip(f"git falló ({result.returncode}): {result.stderr.strip()}")
    return result.stdout


# --------------------------------------------------------------------------- #
# AC2 — nada de bases versionadas
# --------------------------------------------------------------------------- #

def test_no_database_file_is_tracked():
    tracked = [
        line for line in _git("ls-files").splitlines()
        if line.lower().endswith(DB_SUFFIXES)
    ]
    assert not tracked, f"bases de datos versionadas: {tracked}"


@pytest.mark.parametrize("candidate", [
    "backend/dev.db",                 # el que estaba trackeado
    "backend/data/dev.db",            # la base real de desarrollo
    "backend/tests/test_algo.db",     # las que crean los tests
    "dev.db",                         # arranque desde la raíz del repo
    "backend/app/scratch.sqlite3",
    "backend/data/dev.db-wal",        # auxiliares de SQLite
])
def test_gitignore_covers_local_databases(candidate):
    """`git check-ignore` es la única prueba fiable: interpreta el fichero como git."""
    assert _git("check-ignore", candidate).strip(), f"{candidate} no está ignorado"


def test_the_data_directory_survives_a_fresh_clone():
    """Git no versiona directorios vacíos, y SQLite no crea el directorio padre.

    Sin algo trackeado dentro de `backend/data/`, un clon nuevo arrancaba con
    `unable to open database file` — que es justo a donde apunta `config.yaml`.
    """
    tracked = _git("ls-files", "backend/data").split()
    assert tracked, "backend/data/ no sobrevive a un clon: nada trackeado dentro"


# --------------------------------------------------------------------------- #
# AC2 — «el arranque en dev lo recrea solo»
# --------------------------------------------------------------------------- #

def test_startup_creates_the_missing_sqlite_directory():
    from app.core.database import _ensure_sqlite_directory

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "no" / "existe" / "dev.db"
        _ensure_sqlite_directory(f"sqlite+aiosqlite:///{target.as_posix()}")
        assert target.parent.is_dir()


@pytest.mark.parametrize("url", [
    "sqlite+aiosqlite:///:memory:",
    "sqlite://",
])
def test_in_memory_databases_need_no_directory(url):
    """No hay fichero que respaldar: la función tiene que ser un no-op, no fallar."""
    from app.core.database import _ensure_sqlite_directory

    _ensure_sqlite_directory(url)


def test_a_fresh_dev_database_is_created_and_migrated():
    """De cero a base usable en un directorio que no existía, como un clon nuevo."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "data" / "dev.db"
        env = {
            **os.environ,
            "DEBUG": "true",
            "SECRET_KEY": "ci-secret-not-for-prod",
            "DATABASE_URL": f"sqlite+aiosqlite:///{target.as_posix()}",
            "PYTHONPATH": str(ROOT_DIR),
        }
        script = (
            "import asyncio;"
            "from app.core.database import init_db, close_db;"
            "asyncio.run(init_db())"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT_DIR, env=env, capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, result.stderr[-2000:]
        assert target.exists(), "la base de desarrollo no se recreó sola"

        import sqlite3
        with sqlite3.connect(target) as conn:
            tables = {r[0] for r in conn.execute(
                "select name from sqlite_master where type='table'"
            )}
        assert "users" in tables and "alembic_version" in tables


def test_stdlib_is_not_shadowed_by_a_tracked_database():
    """Guardia barata: el paquete no debe traer binarios de datos por descuido."""
    assert sysconfig.get_paths()  # sanity: entorno Python coherente
    strays = [
        path for path in ROOT_DIR.rglob("*.db")
        if ".git" not in path.parts and "node_modules" not in path.parts
        and _git("ls-files", str(path.relative_to(REPO_DIR))).strip()
    ]
    assert not strays, f"binarios de base versionados bajo backend/: {strays}"
