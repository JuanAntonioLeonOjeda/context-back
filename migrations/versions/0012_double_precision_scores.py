"""Thresholds and similarities of stories as double precision (review of story-contrast).

`real` kept 24 bits, so a threshold of 0.88 came back from the API as 0.8799999952316284. Both
earlier migrations are already applied, so this one changes the columns instead of editing them.
Thresholds are the author's round numbers: they are rounded back to four decimals. Similarities
keep the value they had.

Revision ID: 0012
Revises: 0011
Created: 2026-10-27
"""

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE story_runs
            ALTER COLUMN threshold TYPE double precision
            USING round(threshold::numeric, 4)::double precision
        """
    )
    op.execute(
        """
        ALTER TABLE story_tree_runs
            ALTER COLUMN threshold TYPE double precision
            USING round(threshold::numeric, 4)::double precision
        """
    )
    op.execute("ALTER TABLE story_articles ALTER COLUMN similarity TYPE double precision")
    op.execute("ALTER TABLE story_links ALTER COLUMN similarity TYPE double precision")


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
