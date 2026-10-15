"""Whether a sector is in use: the taxonomy has 12 topics, three of them live (ADR-0007).

Revision ID: 0007
Revises: 0006
Created: 2026-10-15
"""

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # The sectors that exist today are the three of launch and all are in use, so the default is
    # true: nothing is rewritten by hand and a sector inserted without the column stays active.
    # A planned sector is the exception and says so (is_active = false), never the other way round.
    op.execute("ALTER TABLE sectors ADD COLUMN is_active boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
