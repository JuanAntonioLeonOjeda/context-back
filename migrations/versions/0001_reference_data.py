"""Reference data: territories, parties, governments and competences.

Revision ID: 0001
Revises:
Created: 2026-10-13
"""

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # btree_gist lets an exclusion constraint mix "=" on text with "&&" on date ranges.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.execute(
        """
        CREATE TABLE territories (
            id        text PRIMARY KEY,                     -- 'es', 'ccaa-01', 'prov-28'
            ine_code  text,                                 -- NULL only for the State
            name      text NOT NULL,
            level     text NOT NULL,
            parent_id text REFERENCES territories (id)
            -- TODO(author) 1: CHECK that level is 'state', 'ccaa', 'autonomous_city' or 'province'.
            -- TODO(author) 2: CHECK that the State has no ine_code and every other level has one.
            -- TODO(author) 3: UNIQUE so that no two territories share the same level and INE code.
            -- Optional 4: CHECK that the id prefix matches the level (hint: LIKE or a regex ~).
        )
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
