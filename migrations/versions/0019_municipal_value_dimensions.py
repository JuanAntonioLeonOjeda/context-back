"""Age and place of birth join education as dimensions of municipal values (voters-age-origin).

Revision ID: 0019
Revises: 0018
Created: 2026-11-16
"""

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # `dimension` is checked against the closed list the code knows (0017), so a new dimension is
    # a new migration. The constraint is dropped and created again with the longer list: the
    # rows already stored (education) satisfy it, and the append-only triggers guard rows, not
    # the table definition, so nothing else changes. Percentage columns need nothing: both new
    # dimensions are a share of a population, like education.
    op.execute(
        "ALTER TABLE municipal_value_loads DROP CONSTRAINT municipal_value_loads_dimension_known"
    )
    op.execute(
        """
        ALTER TABLE municipal_value_loads
            ADD CONSTRAINT municipal_value_loads_dimension_known
            CHECK (dimension IN ('education', 'age', 'born_abroad'))
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
