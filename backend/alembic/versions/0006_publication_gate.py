"""compuerta de publicación: informe, aprobación humana y estado requires_human_review

SPEC-032 / T20.6 / AC6, ADR-0011.

* `publication_gate_reports`: una fila por evaluación de la compuerta, ligada al
  texto evaluado por su huella. `article_id` es `CASCADE` (sin artículo no hay qué
  describir) y `run_id` `SET NULL` (purgar la ejecución no se lleva el informe).
* `articles.responsible_author_id`, `approved_by`, `approved_at`,
  `approved_text_sha256`: el autor humano responsable y la aprobación explícita.
  Nulos en los artículos existentes — los ya publicados no se tocan.
* `articlestatus` gana `REQUIRES_HUMAN_REVIEW`. En Postgres es una etiqueta de un
  enum nativo; en SQLite es un VARCHAR sin restricción y no hay nada que añadir.

Revision ID: 0006_publication_gate
Revises: 0005_repair_theme_columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_publication_gate"
down_revision: Union[str, Sequence[str], None] = "0005_repair_theme_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # Fuera de una transacción: Postgres no admite ADD VALUE junto con el uso
        # posterior del valor en el mismo bloque transaccional.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE articlestatus ADD VALUE IF NOT EXISTS 'REQUIRES_HUMAN_REVIEW'")

    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("responsible_author_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("approved_by", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("approved_text_sha256", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_articles_responsible_author_id_users", "users",
            ["responsible_author_id"], ["id"], ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_articles_approved_by_users", "users", ["approved_by"], ["id"], ondelete="SET NULL",
        )

    op.create_table(
        "publication_gate_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("publication_gate_reports") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_publication_gate_reports_article_id"), ["article_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_publication_gate_reports_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            "ix_publication_gate_reports_article_created", ["article_id", "created_at"], unique=False
        )


def downgrade() -> None:
    op.drop_table("publication_gate_reports")
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_constraint("fk_articles_approved_by_users", type_="foreignkey")
        batch_op.drop_constraint("fk_articles_responsible_author_id_users", type_="foreignkey")
        batch_op.drop_column("approved_text_sha256")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approved_by")
        batch_op.drop_column("responsible_author_id")
    # Postgres no sabe quitar una etiqueta de un enum sin recrear el tipo; dejarla es inocuo.
