"""A file of the INE can be loaded for more than one year (phase voters-dimensions).

Revision ID: 0018
Revises: 0017
Created: 2026-11-16
"""

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # The INE's table files hold several years (education: 2021 to 2024) and a load stores the
    # values of the year it was asked for, so the same file is loaded once per year, and again
    # when a revised value comes back to an earlier file. `UNIQUE (dimension, source_sha256)` of
    # 0017 refused both. Nothing needs it: a value that did not change is never stored again and a
    # load with no new value is never recorded. The hash stays indexed to find a file's loads.
    op.execute("ALTER TABLE municipal_value_loads DROP CONSTRAINT municipal_value_loads_one_file")
    op.execute(
        "CREATE INDEX municipal_value_loads_file ON municipal_value_loads"
        " (dimension, source_sha256)"
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
