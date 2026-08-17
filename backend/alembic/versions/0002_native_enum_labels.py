"""reparar etiquetas del enum nativo scientificformat en Postgres

Revision ID: 0002_enum_labels
Revises: 0001_baseline
Create Date: 2026-08-17 08:35:00.000000

`ScientificFormat` no declara ``values_callable``, así que SQLAlchemy almacena el
**nombre** del miembro: las etiquetas del enum nativo de Postgres son
``APA``, ``IEEE``, ``VANCOUVER``, ``CHICAGO``, ``NATURE``, ``NONE`` — en mayúscula.

Los ``ALTER`` ad-hoc que había en ``init_db`` añadían ``'chicago'`` y ``'nature'``
**en minúscula**, etiquetas que el ORM nunca usa; las que sí necesita no se
añadieron nunca. En una base Postgres anterior a Alembic, guardar un artículo con
esos formatos falla con ``invalid input value for enum scientificformat``. No se
veía porque aquellas sentencias corrían dentro de un ``try/except: pass``.

Esta revisión repara las bases existentes. Una base nueva ya nace correcta desde
``0001_baseline``, y ``ADD VALUE IF NOT EXISTS`` la deja intacta. En SQLite el
enum es un ``VARCHAR`` sin restricción (``create_constraint=False`` es el valor
por defecto en SQLAlchemy 2.x), así que no hay nada que reparar.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_enum_labels"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Etiquetas que deben existir en el tipo nativo. Congeladas a propósito: una
# migración es una foto del esquema, no una consulta a los modelos de hoy.
#
# `ACL` está aquí y no en `0001_baseline` porque llegó después (#281), cuando la
# base ya estaba escrita. Una base Postgres nueva la recibe en este paso; el
# resultado tras `upgrade head` es el mismo.
_SCIENTIFIC_FORMAT_LABELS = ("APA", "IEEE", "ACL", "VANCOUVER", "CHICAGO", "NATURE", "NONE")

# Minúsculas que dejaron los ALTER ad-hoc. Postgres no permite quitar etiquetas de
# un enum sin recrear el tipo, así que se quedan como residuo inerte; se dejan
# anotadas aquí para que quien lea el tipo en producción sepa de dónde salen.
_LEGACY_LOWERCASE_RESIDUE = ("chicago", "nature", "acl")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # Fuera de una transacción: Postgres no admite ADD VALUE en un bloque
    # transaccional junto con el uso posterior del valor.
    with op.get_context().autocommit_block():
        for label in _SCIENTIFIC_FORMAT_LABELS:
            op.execute(
                f"ALTER TYPE scientificformat ADD VALUE IF NOT EXISTS '{label}'"
            )


def downgrade() -> None:
    # Postgres no sabe quitar una etiqueta de un enum sin recrear el tipo y
    # reescribir todas las columnas que lo usan. Revertir esto haría más daño que
    # bien, y dejar etiquetas de más es inocuo.
    pass
