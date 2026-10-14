"""Classifications of articles: append-only, one row per article and classifier version (ADR-0015).

Revision ID: 0005
Revises: 0004
Created: 2026-10-14
"""

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE classifications (
            id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            article_id    bigint NOT NULL REFERENCES articles (id),
            model_id      text NOT NULL,        -- 'rules', later the own model
            model_version text NOT NULL,        -- rules: a hash of data/classification/
            communities   text[] NOT NULL,      -- territory ids, 'ccaa-NN'
            sectors       text[] NOT NULL,      -- sector ids
            levels        text[] NOT NULL,      -- 'state', 'ccaa', 'local'
            evidence      jsonb NOT NULL,       -- the terms that produced each label
            created_at    timestamptz NOT NULL DEFAULT now(),

            CONSTRAINT classifications_model_not_blank
                CHECK (btrim(model_id) <> '' AND btrim(model_version) <> ''),
            CONSTRAINT classifications_levels_valid
                CHECK (levels <@ ARRAY['state', 'ccaa', 'local']),
            CONSTRAINT classifications_communities_valid
                CHECK (communities <@ ARRAY[
                    'ccaa-01','ccaa-02','ccaa-03','ccaa-04','ccaa-05','ccaa-06','ccaa-07',
                    'ccaa-08','ccaa-09','ccaa-10','ccaa-11','ccaa-12','ccaa-13','ccaa-14',
                    'ccaa-15','ccaa-16','ccaa-17','ccaa-18','ccaa-19'
                ]),
            -- An article is classified once per classifier version: re-running adds nothing.
            CONSTRAINT classifications_one_per_version
                UNIQUE (article_id, model_id, model_version)
        )
        """
    )
    # Serves "which articles has this classifier version not seen yet" and the news queries.
    op.execute(
        """
        CREATE INDEX classifications_model_idx
            ON classifications (model_id, model_version, article_id)
        """
    )
    op.execute(
        "CREATE INDEX classifications_communities_idx ON classifications USING gin (communities)"
    )
    # Append-only, enforced by the database as for observations (ADR-0012).
    op.execute(
        """
        CREATE FUNCTION classifications_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'classifications are append-only: % is not allowed', TG_OP;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER classifications_no_update_or_delete
            BEFORE UPDATE OR DELETE ON classifications
            FOR EACH ROW EXECUTE FUNCTION classifications_append_only()
        """
    )
    op.execute(
        """
        CREATE TRIGGER classifications_no_truncate
            BEFORE TRUNCATE ON classifications
            FOR EACH STATEMENT EXECUTE FUNCTION classifications_append_only()
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
