"""The indicator a sector is measured by, shown next to its news (phase context-voters).

Revision ID: 0014
Revises: 0013
Created: 2026-11-06
"""

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # No foreign key to `indicators`: that table is filled by `datos.indicators load`, which reads
    # the INE over the network, while the sectors are loaded on every start from the CSV
    # (docker/entrypoint.sh). A foreign key would make a fresh database refuse its sectors until the
    # INE answered. The governments loader checks the id against the indicators the project defines
    # instead (indicators/application/catalogue.py), and a sector with none stays NULL.
    op.execute(
        """
        ALTER TABLE sectors
            ADD COLUMN indicator_id text NULL,
            ADD CONSTRAINT sectors_indicator_id_slug CHECK (indicator_id ~ '^[a-z0-9_]+$')
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
