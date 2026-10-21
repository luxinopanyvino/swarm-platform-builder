"""reparar columnas `theme` ausentes en bases anteriores a Alembic

Revision ID: 0005_repair_theme_columns
Revises: 0004_agent_run_steps

`projects.theme` y `articles.theme` (SPEC-022 / T11.2) llegaron justo antes de
adoptar Alembic, así que `0001_baseline` ya las incluye. Pero en las bases
anteriores a Alembic las añadía un ``ALTER`` ad-hoc dentro de un
``try/except: pass``: si fallaba, la base se quedaba sin ellas, `init_db` la
sellaba en `0001_baseline` y el arranque reventaba después con
``no such column: projects.theme`` al cargar el proyecto de sistema.

Esta revisión añade la columna solo donde falta. Una base nueva ya la tiene desde
`0001_baseline` y pasa por aquí sin cambios. El ``server_default`` es necesario
para añadir una columna ``NOT NULL`` a una tabla con filas; ``{}`` es lo mismo que
pone el ORM (`default=dict`): heredar todo el tema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_repair_theme_columns"
down_revision: Union[str, Sequence[str], None] = "0004_agent_run_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Congeladas a propósito: una migración es una foto, no una consulta a los modelos.
_TABLES_WITH_THEME = ("projects", "articles")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in _TABLES_WITH_THEME:
        columns = {c["name"] for c in inspector.get_columns(table)}
        if "theme" in columns:
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column("theme", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
            )


def downgrade() -> None:
    # Las columnas pertenecen a `0001_baseline`; quitarlas aquí dejaría una base
    # nueva en `0004` sin un esquema que esa revisión sí declara.
    pass
