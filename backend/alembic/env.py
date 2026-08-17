"""Entorno de migraciones Alembic (SPEC-018 / T4.1).

Dos modos de ejecución, deliberadamente:

* **CLI** (`alembic upgrade head` desde `backend/`): crea su propio motor a partir
  de ``settings.DATABASE_URL``, la misma URL que usa la aplicación. No se
  configura en `alembic.ini` para que no haya dos fuentes de verdad de la conexión
  — ni una credencial versionada.
* **Programático** (``init_db``): recibe una conexión ya abierta en
  ``config.attributes["connection"]``. Es la receta oficial de Alembic para
  llamarlo desde código async: sin ella, ``asyncio.run`` dentro del bucle de
  eventos de la app reventaría.

``render_as_batch`` está activo porque SQLite no sabe hacer casi ningún
``ALTER TABLE``: sin modo batch, cualquier migración futura que altere una columna
funcionaría en Postgres y fallaría en el entorno de desarrollo.
"""
import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# `alembic` se invoca desde backend/, pero también desde la raíz del repo en CI.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app import models  # noqa: E402,F401  — registra todas las tablas en Base.metadata

config = context.config

# Solo configuramos logging en modo CLI: en modo programático la app ya instaló el
# suyo (SPEC-019/T5.1) y fileConfig lo desmontaría.
#
# `disable_existing_loggers=False` no es opcional: el valor por defecto de
# `fileConfig` es desactivar todos los loggers ya creados, así que una invocación de
# Alembic en el mismo proceso dejaría muda a la aplicación — incluido el logging
# estructurado de T5.1.
if config.config_file_name is not None and config.attributes.get("connection") is None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    """URL de la app, con precedencia a la que inyecte quien invoca (tests)."""
    return config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (``alembic upgrade head --sql``)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        # Comparar tipos solo donde el resultado es fiable. SQLite no tiene tipo
        # UUID: las columnas se emiten como NUMERIC y al reflejarlas vuelven así,
        # de modo que `compare_type` marcaría un cambio de tipo espurio en las 25
        # columnas UUID en cada autogenerate. En Postgres sí es útil.
        compare_type=connection.dialect.name != "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    # Conexión inyectada por init_db: usarla tal cual, sin abrir un motor nuevo
    # ni un bucle de eventos anidado.
    existing = config.attributes.get("connection")
    if existing is not None:
        do_run_migrations(existing)
        return
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
