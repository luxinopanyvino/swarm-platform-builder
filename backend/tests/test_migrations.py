"""Migraciones Alembic versionadas (SPEC-018 / T4.1 / AC1).

AC1: un cambio de esquema se aplica mediante una migración Alembic versionada,
`init_db` deja de ejecutar `ALTER TABLE` ad hoc, y **un despliegue limpio llega al
mismo esquema que uno migrado**.

Ese último punto es el que estos tests defienden de verdad: se construyen dos bases
—una migrada con `alembic upgrade head`, otra con `Base.metadata.create_all`— y se
comparan tabla por tabla. Es la prueba que pide el plan de la spec, y la que
detectaría que una migración se ha quedado atrás respecto a los modelos.
"""
import importlib.util
import logging
import os
import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_migrations.db").resolve()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402

from app import models  # noqa: E402,F401  — registra las tablas
from app.core import database as db_module  # noqa: E402
from app.core.database import Base, PRE_ALEMBIC_REVISION  # noqa: E402

ALEMBIC_INI = ROOT_DIR / "alembic.ini"
VERSIONS_DIR = ROOT_DIR / "alembic" / "versions"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _config(url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _sync_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _async_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _snapshot(url: str) -> dict:
    """Foto comparable del esquema.

    Se comparan nombres y nulabilidad de columnas, índices, restricciones únicas y
    **destino** de las claves ajenas — no sus nombres: la base creada por
    `create_all` deja las FK anónimas en SQLite, mientras que la migración nombra
    la que cierra el ciclo `users` ↔ `projects`. Los tipos tampoco: SQLite no tiene
    UUID y ambos caminos emiten el mismo `NUMERIC`, así que compararlos no aporta.
    """
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        snapshot = {}
        for table in sorted(inspector.get_table_names()):
            if table == "alembic_version":
                continue
            snapshot[table] = {
                "columns": sorted(
                    (c["name"], bool(c["nullable"])) for c in inspector.get_columns(table)
                ),
                "indexes": sorted(
                    (i["name"], tuple(i["column_names"]), bool(i["unique"]))
                    for i in inspector.get_indexes(table)
                ),
                "unique": sorted(
                    tuple(u["column_names"]) for u in inspector.get_unique_constraints(table)
                ),
                "foreign_keys": sorted(
                    (
                        tuple(fk["constrained_columns"]),
                        fk["referred_table"],
                        tuple(fk["referred_columns"]),
                    )
                    for fk in inspector.get_foreign_keys(table)
                ),
            }
        return snapshot
    finally:
        engine.dispose()


@pytest.fixture
def migrated_db(tmp_path):
    """Base construida aplicando todas las migraciones."""
    path = tmp_path / "migrated.db"
    command.upgrade(_config(_async_url(path)), "head")
    return path


@pytest.fixture
def created_db(tmp_path):
    """Base construida como lo haría un `create_all` desde los modelos."""
    path = tmp_path / "created.db"
    engine = create_engine(_sync_url(path))
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    return path


# --------------------------------------------------------------------------- #
# AC1 — el despliegue limpio y el migrado llegan al mismo esquema
# --------------------------------------------------------------------------- #

def test_migrated_schema_equals_create_all_schema(migrated_db, created_db):
    assert _snapshot(_sync_url(migrated_db)) == _snapshot(_sync_url(created_db))


def test_migrated_database_has_every_model_table(migrated_db):
    engine = create_engine(_sync_url(migrated_db))
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert set(Base.metadata.tables) <= tables


def test_alembic_check_reports_no_pending_changes(migrated_db):
    """`alembic check` compara los modelos con la base migrada: debe estar al día.

    Es el guardarraíl contra el olvido de siempre — cambiar un modelo y no generar
    la migración.
    """
    command.check(_config(_async_url(migrated_db)))


# --------------------------------------------------------------------------- #
# AC1 — `init_db` ya no toca el esquema a mano
# --------------------------------------------------------------------------- #

def test_init_db_has_no_adhoc_ddl():
    """AC1 al pie de la letra: ni `ALTER TABLE`, ni `CREATE TABLE`, ni `create_all`.

    Se analiza el AST y no el texto: los comentarios desaparecen y los docstrings se
    excluyen a mano, porque la documentación de este módulo *habla* de los ALTER que
    había — mencionarlos para explicar por qué ya no están no puede hacer fallar el
    test, pero ejecutarlos sí.
    """
    import ast

    tree = ast.parse(Path(db_module.__file__).read_text(encoding="utf-8"))
    docstrings = {
        ast.get_docstring(node, clean=False)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }

    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in docstrings:
                continue
            upper = node.value.upper()
            if "ALTER TABLE" in upper or "ALTER TYPE" in upper or "CREATE TABLE" in upper:
                offenders.append(node.value[:60])
        if isinstance(node, ast.Attribute) and node.attr == "create_all":
            offenders.append("create_all")

    assert not offenders, f"DDL ad hoc en app/core/database.py: {offenders}"


@pytest.mark.asyncio
async def test_init_db_creates_the_schema_from_scratch(tmp_path, monkeypatch):
    path = tmp_path / "fresh.db"
    engine = create_engine(_sync_url(path))  # crea el fichero vacío
    engine.dispose()

    await _run_init_db(monkeypatch, path)

    with sqlite3.connect(path) as conn:
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert set(Base.metadata.tables) <= tables
    assert _current_revision(path) == _head_revision()


@pytest.mark.asyncio
async def test_init_db_is_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "twice.db"
    await _run_init_db(monkeypatch, path)
    first = _snapshot(_sync_url(path))
    await _run_init_db(monkeypatch, path)
    assert _snapshot(_sync_url(path)) == first
    assert _current_revision(path) == _head_revision()


# --------------------------------------------------------------------------- #
# Bases anteriores a Alembic: sellar, no reejecutar
# --------------------------------------------------------------------------- #

@pytest.fixture
def pre_alembic_db(tmp_path):
    """Base como las anteriores a Alembic: esquema del corte y sin `alembic_version`.

    Se genera aplicando `0001_baseline` y borrando después el sello, en vez de con
    `create_all`. Es lo que de verdad había en producción —el esquema congelado en el
    momento de adoptar Alembic— mientras que `create_all` refleja los modelos de
    **hoy**, que ya incluyen tablas creadas por migraciones posteriores; con
    `create_all` el test se rompería al añadir cualquier migración, y por un motivo
    falso.

    Es una fixture síncrona a propósito: `command.upgrade` abre su propio bucle de
    eventos con `asyncio.run`, que reventaría dentro de un test `async`.
    """
    path = tmp_path / "legacy.db"
    command.upgrade(_config(_async_url(path)), PRE_ALEMBIC_REVISION)
    with sqlite3.connect(path) as conn:
        conn.execute("drop table alembic_version")
    return path


@pytest.mark.asyncio
async def test_pre_alembic_database_is_stamped_and_keeps_its_data(pre_alembic_db, monkeypatch):
    """Aplicar la base a una BD que ya tiene las tablas fallaría; hay que sellarla."""
    path = pre_alembic_db
    engine = create_engine(_sync_url(path))
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "insert into users (id, email, hashed_password, full_name, role,"
                " is_active, created_at, updated_at)"
                " values ('abc', 'a@b.c', 'x', 'A', 'admin', 1, '2026-01-01', '2026-01-01')"
            )
    finally:
        engine.dispose()

    await _run_init_db(monkeypatch, path)

    assert _current_revision(path) == _head_revision()
    with sqlite3.connect(path) as conn:
        assert conn.execute("select count(*) from users").fetchone()[0] == 1


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def database_logs():
    """Registros de `app.core.database`, capturados en el propio logger.

    Se evita `caplog`: su handler no recibe estos registros de forma fiable en los
    tests async de este módulo, y la propia emisión sí ocurre (se ve con
    `--log-cli-level`). Un handler explícito no depende de esa fontanería.
    """
    handler = _CapturingHandler()
    logger = logging.getLogger("app.core.database")
    logger.addHandler(handler)
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate


@pytest.mark.asyncio
async def test_stamp_warns_when_the_legacy_schema_is_incomplete(pre_alembic_db, monkeypatch, database_logs):
    """Los ALTER ad-hoc corrían en `try/except: pass`: una base pudo quedar coja.

    Sellarla en silencio congelaría esa divergencia, así que se avisa de lo que
    falta en lugar de fingir que todo está en orden.
    """
    path = pre_alembic_db
    engine = create_engine(_sync_url(path))
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("drop table notifications")
    finally:
        engine.dispose()

    await _run_init_db(monkeypatch, path)

    warnings = [r for r in database_logs if r.levelno >= logging.WARNING]
    assert warnings, "se selló una base incompleta sin avisar"
    assert "notifications" in warnings[0].getMessage()
    assert "notifications" in warnings[0].missing
    assert warnings[0].event == "alembic_stamp_divergence"


# --------------------------------------------------------------------------- #
# Integridad del árbol de revisiones
# --------------------------------------------------------------------------- #

def test_there_is_exactly_one_head():
    """Dos cabezas significan que dos ramas añadieron migraciones en paralelo."""
    heads = ScriptDirectory.from_config(_config("sqlite://")).get_heads()
    assert len(heads) == 1, f"revisiones divergentes: {heads}"


def test_baseline_is_the_revision_used_for_stamping():
    script = ScriptDirectory.from_config(_config("sqlite://"))
    bases = script.get_bases()
    assert bases == [PRE_ALEMBIC_REVISION]


def test_downgrade_to_base_leaves_no_model_tables(migrated_db):
    """Si el downgrade no está bien, la migración no es reversible ni comprobable."""
    command.downgrade(_config(_async_url(migrated_db)), "base")
    with sqlite3.connect(migrated_db) as conn:
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert not (set(Base.metadata.tables) & tables)


# --------------------------------------------------------------------------- #
# Etiquetas del enum nativo (el fallo que el try/except ocultaba)
# --------------------------------------------------------------------------- #

def _enum_labels_migration():
    spec = importlib.util.spec_from_file_location(
        "_mig_0002", VERSIONS_DIR / "0002_native_enum_labels.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_enum_labels_cover_the_model_labels():
    """La invariante que faltaba.

    `ScientificFormat` no usa `values_callable`, así que Postgres guarda el
    **nombre** del miembro (`CHICAGO`), no su valor. Los ALTER ad-hoc añadían
    `'chicago'` en minúscula: una etiqueta que el ORM nunca usa, mientras la que
    necesitaba no existía. Si alguien añade un miembro al enum sin migración, esto
    falla en lugar de estallar al guardar en producción.
    """
    from app.models.article import ArticleModel

    model_labels = set(ArticleModel.__table__.c.scientific_format.type.enums)
    migration_labels = set(_enum_labels_migration()._SCIENTIFIC_FORMAT_LABELS)
    assert model_labels <= migration_labels, (
        f"etiquetas del ORM sin migración que las registre: {model_labels - migration_labels}"
    )


def test_native_enum_labels_are_uppercase_member_names():
    """Pin del porqué: son nombres de miembro, no valores."""
    labels = _enum_labels_migration()._SCIENTIFIC_FORMAT_LABELS
    assert all(label == label.upper() for label in labels)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def _head_revision() -> str:
    return ScriptDirectory.from_config(_config("sqlite://")).get_current_head()


def _current_revision(path: Path) -> str | None:
    with sqlite3.connect(path) as conn:
        rows = conn.execute("select version_num from alembic_version").fetchall()
    return rows[0][0] if rows else None


async def _run_init_db(monkeypatch, path: Path) -> None:
    """Ejecuta `init_db` contra una base concreta, con su propio motor."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(_async_url(path), future=True)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "_is_sqlite", True)
    try:
        await db_module.init_db()
    finally:
        await engine.dispose()
