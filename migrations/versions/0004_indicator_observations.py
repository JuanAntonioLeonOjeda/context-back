"""Indicators: downloads, indicator definitions and append-only observations (ADR-0012).

Revision ID: 0004
Revises: 0003
Created: 2026-10-13
"""

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE downloads (
            id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source     text NOT NULL,
            url        text NOT NULL,
            fetched_at timestamptz NOT NULL DEFAULT now(),
            sha256     text NOT NULL,     -- of the response body: proves what we received

            CONSTRAINT downloads_source_known CHECK (source IN ('ine')),
            CONSTRAINT downloads_url_is_url CHECK (url ~ '^https?://'),
            CONSTRAINT downloads_sha256_hex CHECK (sha256 ~ '^[0-9a-f]{64}$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE indicators (
            id              text PRIMARY KEY,   -- 'unemployment_rate'
            name            text NOT NULL,      -- shown to users: the measure, no adjectives
            unit            text NOT NULL,      -- after applying scale_factor: 'persons', '%'
            scale_factor    numeric NOT NULL,   -- INE "Escala": 1000 for thousands
            periodicity     text NOT NULL,
            source_table_id text NOT NULL,      -- INE table, e.g. '14506'
            description     text NOT NULL,

            CONSTRAINT indicators_id_slug CHECK (id ~ '^[a-z0-9_]+$'),
            CONSTRAINT indicators_scale_positive CHECK (scale_factor > 0),
            CONSTRAINT indicators_periodicity_known
                CHECK (periodicity IN ('annual', 'quarterly'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observations (
            id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            indicator_id       text NOT NULL REFERENCES indicators (id),
            territory_id       text NOT NULL REFERENCES territories (id),
            period_year        integer NOT NULL,
            period_code        integer NOT NULL,  -- INE FK_Periodo: 28 year, 19-22 quarters
            period_start       date NOT NULL,
            value              numeric NOT NULL,  -- as published; a missing value is no row
            source_series_code text NOT NULL,     -- INE series, e.g. 'EPA452576'
            download_id        bigint NOT NULL REFERENCES downloads (id),

            CONSTRAINT observations_period_code_known
                CHECK (period_code IN (19, 20, 21, 22, 28)),
            -- The domain derives period_start (task 14); this guard keeps a wrong row out
            -- even if a future loader forgets the rule, as overlaps are checked twice.
            CONSTRAINT observations_period_start_matches CHECK (
                period_start = make_date(
                    period_year,
                    CASE period_code
                        WHEN 28 THEN 1 WHEN 19 THEN 1 WHEN 20 THEN 4
                        WHEN 21 THEN 7 WHEN 22 THEN 10
                    END,
                    1
                )
            ),
            -- One value per key and download; across downloads a key can have several
            -- rows (revisions). Not UNIQUE on value: A -> B -> A must be able to come back.
            CONSTRAINT observations_one_per_download
                UNIQUE (indicator_id, territory_id, period_start, download_id)
        )
        """
    )
    # Serves the "latest value per key" lookups of the loader and of the view.
    op.execute(
        """
        CREATE INDEX observations_latest_idx
            ON observations (indicator_id, territory_id, period_start, download_id DESC)
        """
    )
    # Append-only, enforced by the database and not only by the code (ADR-0012).
    op.execute(
        """
        CREATE FUNCTION observations_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'observations are append-only: % is not allowed', TG_OP;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER observations_no_update_or_delete
            BEFORE UPDATE OR DELETE ON observations
            FOR EACH ROW EXECUTE FUNCTION observations_append_only()
        """
    )
    op.execute(
        """
        CREATE TRIGGER observations_no_truncate
            BEFORE TRUNCATE ON observations
            FOR EACH STATEMENT EXECUTE FUNCTION observations_append_only()
        """
    )
    # The current value of each key is the row of its latest download.
    op.execute(
        """
        CREATE VIEW current_observations AS
            SELECT DISTINCT ON (indicator_id, territory_id, period_start) *
            FROM observations
            ORDER BY indicator_id, territory_id, period_start, download_id DESC
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
