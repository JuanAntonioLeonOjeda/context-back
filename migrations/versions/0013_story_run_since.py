"""The start of the window a grouping run looked at (review of story-contrast).

A run records its threshold and its window between articles, but not how far back it read: two
runs with the same settings could have grouped different articles. Runs already stored keep NULL:
the date was not recorded then and is not guessed.

Revision ID: 0013
Revises: 0012
Created: 2026-10-27
"""

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE story_runs ADD COLUMN since timestamptz"
        "  -- only the articles published from here on were grouped; NULL when not recorded"
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
