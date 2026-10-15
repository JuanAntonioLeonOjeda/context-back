"""Scores of a model's classifications: how sure it is of each label it gives (ADR-0016).

Revision ID: 0006
Revises: 0005
Created: 2026-10-15
"""

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ADD COLUMN with a constant default neither rewrites the table nor fires a row trigger, so the
    # append-only trigger of 0005 is untouched. The existing rows are the rules' and the rules give
    # no scores: '[]' is the truth for them, not a placeholder.
    op.execute("ALTER TABLE classifications ADD COLUMN scores jsonb NOT NULL DEFAULT '[]'::jsonb")
    op.execute(
        """
        ALTER TABLE classifications
            ADD CONSTRAINT classifications_scores_is_array CHECK (jsonb_typeof(scores) = 'array')
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
