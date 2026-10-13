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
            parent_id text REFERENCES territories (id),

            -- 1. Only the three known levels (Ceuta and Melilla are communities, 'ccaa').
            --    Adding a level later is a new migration that drops and recreates this
            --    constraint (cheaper than altering an ENUM).
            CONSTRAINT territories_level_valid
                CHECK (level IN ('state', 'ccaa', 'province')),

            -- 2. The State has no INE code; every other level has a two-digit one.
            --    "ine_code ~ '^[0-9]{2}$'" is a regex match, so '1' or 'AB' are rejected.
            --    IS NOT NULL is explicit on purpose: a CHECK that evaluates to NULL
            --    counts as satisfied, and "NULL ~ regex" is NULL, so without it a
            --    community with no code would be accepted.
            CONSTRAINT territories_ine_code_by_level
                CHECK (
                    (level = 'state' AND ine_code IS NULL)
                    OR (level <> 'state' AND ine_code IS NOT NULL AND ine_code ~ '^[0-9]{2}$')
                ),

            -- 3. The id prefix must match the level, so 'prov-28' can never be stored as a
            --    community. '^...$' anchors the pattern to the whole value.
            CONSTRAINT territories_id_matches_level
                CHECK (
                    (level = 'state' AND id = 'es')
                    OR (level = 'ccaa' AND id ~ '^ccaa-[0-9]{2}$')
                    OR (level = 'province' AND id ~ '^prov-[0-9]{2}$')
                ),

            -- 4. The id already encodes the INE code, so the two cannot disagree.
            --    There is no UNIQUE (level, ine_code): checks 3 and 4 fix the id from
            --    (level, code), so the primary key already rejects a duplicate.
            CONSTRAINT territories_id_ends_with_ine_code
                CHECK (ine_code IS NULL OR id LIKE '%-' || ine_code)
        )
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
