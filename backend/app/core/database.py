from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings

# Base para todos los modelos ORM
Base = declarative_base()

# SQLite does not support connection pooling parameters
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_engine_kwargs = (
    {"connect_args": {"check_same_thread": False}} if _is_sqlite
    else {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}
)

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
    autoflush=False,
    autocommit=False
)


async def get_session() -> AsyncSession:
    """Dependency para obtener la sesión de BD."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Crear todas las tablas y aplicar migraciones incrementales."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Incremental migrations: add new columns without dropping existing data
    # Each migration runs in its own transaction to prevent transaction abort
    migrations = [
        "ALTER TABLE agent_profiles ADD COLUMN scientific_format VARCHAR(32) NOT NULL DEFAULT 'apa'",
        "ALTER TABLE agent_profiles ADD COLUMN output_language VARCHAR(8) NOT NULL DEFAULT 'es'",
        "ALTER TABLE agent_profiles ADD COLUMN target_word_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE notifications ADD COLUMN article_id CHAR(32) REFERENCES articles(id) ON DELETE CASCADE",
        "ALTER TABLE articles ADD COLUMN project_id CHAR(32) REFERENCES projects(id) ON DELETE CASCADE",
        "ALTER TABLE saved_flows ADD COLUMN project_id CHAR(32) REFERENCES projects(id) ON DELETE CASCADE",
        "ALTER TABLE articles ADD COLUMN authors JSON",
        "ALTER TABLE articles ADD COLUMN abstract TEXT",
        "ALTER TABLE articles ADD COLUMN paper_html TEXT",
        # Postgres native enum: register the citation formats added to ScientificFormat.
        # (No-op on SQLite, where the enum is stored as VARCHAR — caught below.)
        "ALTER TYPE scientificformat ADD VALUE IF NOT EXISTS 'chicago'",
        "ALTER TYPE scientificformat ADD VALUE IF NOT EXISTS 'nature'",
        "ALTER TABLE users ADD COLUMN assigned_project_id CHAR(32) REFERENCES projects(id) ON DELETE SET NULL",
        """CREATE TABLE IF NOT EXISTS user_project_access (
            id CHAR(32) PRIMARY KEY,
            user_id CHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id CHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, project_id)
        )""",
    ]
    for sql in migrations:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(sql))
        except Exception as e:
            pass  # Column already exists or migration not applicable


async def close_db():
    """Cerrar el engine."""
    await engine.dispose()
