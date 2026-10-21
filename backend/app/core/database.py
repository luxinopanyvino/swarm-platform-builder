import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base para todos los modelos ORM
Base = declarative_base()

# SQLite does not support connection pooling parameters
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_engine_kwargs = (
    {"connect_args": {"check_same_thread": False}} if _is_sqlite
    else {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}
)


def _ensure_sqlite_directory(url: str) -> None:
    """Crear el directorio del fichero SQLite si no existe (SPEC-018 / T4.2 / AC2).

    SQLite **no** crea el directorio padre: abrir `./data/dev.db` en un clon recién
    hecho falla con `unable to open database file`. Como los `.db` no se versionan,
    el directorio puede no existir, así que el arranque lo prepara y «la base de
    desarrollo se recrea sola» vale para cualquier ruta configurada, no solo para
    la que lleva un `.gitkeep`.
    """
    database = make_url(url).database
    if not database or database == ":memory:":
        return  # base en memoria: no hay fichero que respaldar
    parent = Path(database).expanduser().parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


if _is_sqlite:
    _ensure_sqlite_directory(settings.DATABASE_URL)

# Motor async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    **_engine_kwargs,
)

# Factory para sesiones
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"

# Revisión que describe el esquema tal como lo dejaban `create_all` + los ALTER
# incrementales que vivían aquí. Las bases anteriores a Alembic se sellan en ella.
PRE_ALEMBIC_REVISION = "0001_baseline"

# Clave arbitraria y estable para el advisory lock de Postgres. Solo tiene que ser
# la misma en todos los workers.
_MIGRATION_LOCK_KEY = 728341168


async def get_session() -> AsyncSession:
    """Dependency para obtener la sesión de BD."""
    async with AsyncSessionLocal() as session:
        yield session


def _alembic_config(connection) -> Config:
    """Config de Alembic que reutiliza una conexión ya abierta.

    Es la receta oficial para invocar Alembic desde código async: `env.py` detecta
    `attributes["connection"]` y la usa en lugar de abrir su propio motor, que
    intentaría un `asyncio.run` dentro del bucle de eventos de la aplicación.
    """
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["connection"] = connection
    return config


def _missing_schema_objects(inspector) -> list[str]:
    """Tablas y columnas de los modelos que no existen en la base real."""
    tables = set(inspector.get_table_names())
    missing: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        if table_name not in tables:
            missing.append(table_name)
            continue
        live_columns = {c["name"] for c in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in live_columns:
                missing.append(f"{table_name}.{column.name}")
    return sorted(missing)


def _stamp_if_pre_alembic(connection) -> None:
    """Sella una base preexistente en la revisión base, en vez de reejecutarla.

    Una base creada antes de adoptar Alembic ya tiene las tablas pero no
    `alembic_version`: aplicarle `0001_baseline` fallaría con «table already
    exists». Aquí se detecta ese caso y se marca como ya migrada.

    Además compara el esquema real con los modelos y **avisa** de lo que falte. Los
    ALTER ad-hoc corrían dentro de un `try/except: pass`, así que una base puede
    haber quedado incompleta en silencio; sellarla sin más congelaría esa
    divergencia sin que nadie se enterase.
    """
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "alembic_version" in tables:
        return  # ya gestionada por Alembic
    if not tables:
        return  # base nueva: el upgrade la crea desde cero

    missing = _missing_schema_objects(inspector)

    if missing:
        logger.warning(
            "Base de datos preexistente con esquema incompleto; se sella en %s pero "
            "faltan objetos que los ALTER ad-hoc no aplicaron: %s",
            PRE_ALEMBIC_REVISION,
            ", ".join(missing),
            extra={"event": "alembic_stamp_divergence", "missing": missing},
        )
    else:
        logger.info(
            "Base de datos preexistente sellada en %s (esquema conforme a los modelos)",
            PRE_ALEMBIC_REVISION,
            extra={"event": "alembic_stamp"},
        )

    command.stamp(_alembic_config(connection), PRE_ALEMBIC_REVISION, purge=True)


def _upgrade_to_head(connection) -> None:
    _stamp_if_pre_alembic(connection)

    context = MigrationContext.configure(connection)
    current = context.get_current_revision()
    head = ScriptDirectory.from_config(_alembic_config(connection)).get_current_head()
    if current != head:
        logger.info(
            "Aplicando migraciones: %s -> %s", current or "base", head,
            extra={"event": "alembic_upgrade", "from_revision": current, "to_revision": head},
        )
        command.upgrade(_alembic_config(connection), "head")

    _assert_schema_matches_models(connection, head)


def _assert_schema_matches_models(connection, head: str) -> None:
    """Abortar el arranque si, ya en `head`, faltan tablas o columnas de los modelos.

    Una base sellada con huecos que ninguna migración repara llega a `head` igual de
    coja, y el fallo aparece después como un `no such column` en la primera consulta
    que toque el hueco, lejos de su causa. Mejor parar aquí y decir qué falta.
    """
    missing = _missing_schema_objects(inspect(connection))
    if missing:
        raise RuntimeError(
            f"El esquema de la base de datos está en la revisión {head} pero no "
            f"coincide con los modelos; faltan: {', '.join(missing)}. Añade una "
            "migración que los cree o, en desarrollo, borra la base para recrearla."
        )


async def init_db() -> None:
    """Llevar el esquema a la última migración (SPEC-018 / T4.1 / AC1).

    Única vía al esquema: ya no hay `create_all` ni `ALTER TABLE` ad hoc, así que un
    despliegue limpio y uno migrado llegan al mismo sitio por construcción.

    En Postgres se toma un *advisory lock* antes de migrar: con varios workers,
    todos ejecutan este arranque y sin el lock competirían por el mismo DDL. El
    segundo en entrar encuentra la revisión ya aplicada y no hace nada.
    """
    async with engine.begin() as conn:
        if not _is_sqlite:
            await conn.execute(text("SELECT pg_advisory_xact_lock(:key)"),
                               {"key": _MIGRATION_LOCK_KEY})
        await conn.run_sync(_upgrade_to_head)


async def close_db():
    """Cerrar el engine."""
    await engine.dispose()
