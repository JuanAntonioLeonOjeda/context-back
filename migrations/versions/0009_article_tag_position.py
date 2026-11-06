"""The place of a tag among the tags of its article, as the feed listed them (ADR-0019).

A feed puts the main tags first, and the model reads only the first few (the text it reads is cut).
Links made before this revision have no place and come after the ones that do.

Revision ID: 0009
Revises: 0008
Created: 2026-10-16
"""

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE article_tags ADD COLUMN position smallint")
    op.execute(
        "ALTER TABLE article_tags"
        " ADD CONSTRAINT article_tags_position_not_negative CHECK (position >= 0)"
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
