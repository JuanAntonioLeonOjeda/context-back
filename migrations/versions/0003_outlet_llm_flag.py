"""Outlets: whether their text may be sent to an external LLM.

Revision ID: 0003
Revises: 0002
Created: 2026-10-13
"""

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE outlets
            -- Default false: a new outlet is processed only by rules and local models until
            -- someone checks its robots.txt (data/news/README.md, docs/sources-audit.md).
            ADD COLUMN external_llm_allowed boolean NOT NULL DEFAULT false
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
