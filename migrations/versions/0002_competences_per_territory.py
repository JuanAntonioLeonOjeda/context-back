"""Competences: per-territory rows and full legislation as a function.

Revision ID: 0002
Revises: 0001
Created: 2026-10-13
"""

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE competences
            -- NULL: the row applies to every community. A value: the row applies to that
            -- community only and replaces the general rows of the same sector and activity
            -- (Ceuta and Melilla do not manage education or health care).
            ADD COLUMN territory_id text REFERENCES territories (id),
            ADD CONSTRAINT competences_territory_is_community
                CHECK (territory_id IS NULL OR territory_id LIKE 'ccaa-%'),

            -- 'legislation' is full legislation, not the development of state bases
            -- (e.g. regional housing, CE art. 148.1.3ª).
            DROP CONSTRAINT competences_function_valid,
            ADD CONSTRAINT competences_function_valid
                CHECK (function IN (
                    'legislation', 'basic_legislation', 'development_legislation', 'execution'
                )),

            -- NULLS NOT DISTINCT: two general rows (territory_id NULL) with the same key are
            -- duplicates; by default PostgreSQL would treat the NULLs as different.
            DROP CONSTRAINT competences_one_row_per_level_and_function,
            ADD CONSTRAINT competences_one_row_per_level_and_function
                UNIQUE NULLS NOT DISTINCT (sector_id, activity, level, function, territory_id)
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
