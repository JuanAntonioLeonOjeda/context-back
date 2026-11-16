"""Municipal values of a voter-profile dimension, loaded from a file (phase voters-dimensions).

Revision ID: 0017
Revises: 0016
Created: 2026-11-16
"""

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | None = None
depends_on: str | None = None

_APPEND_ONLY = ("municipal_value_loads", "municipal_values")


def upgrade() -> None:
    _loads()
    _values()
    _append_only()


def _loads() -> None:
    # One row per file loaded, like `elections`: the INE's table files are downloaded by hand
    # (the API refuses their volume, docs/sources-audit.md section 12), so the file's name and
    # hash stand in for the `downloads` row an automated source would have. `dimension` is
    # checked against the closed list the code knows; a new dimension is a new migration.
    op.execute(
        """
        CREATE TABLE municipal_value_loads (
            id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            dimension     text NOT NULL,
            source_url    text NOT NULL,            -- the page of the table at the INE
            source_file   text NOT NULL,            -- '66620.csv'
            source_sha256 text NOT NULL,
            loaded_at     timestamptz NOT NULL DEFAULT now(),

            CONSTRAINT municipal_value_loads_dimension_known CHECK (dimension IN ('education')),
            CONSTRAINT municipal_value_loads_sha256_hex CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT municipal_value_loads_one_file UNIQUE (dimension, source_sha256)
        )
        """
    )


def _values() -> None:
    # The value is the figure the profile bands by, already computed (education: % of the
    # population aged 15 or over with higher education). A revision is a new load, and the
    # current value is the one of the latest load, as with `municipal_income`.
    op.execute(
        """
        CREATE TABLE municipal_values (
            load_id           bigint NOT NULL REFERENCES municipal_value_loads (id),
            municipality_code text NOT NULL,
            province_id       text GENERATED ALWAYS AS ('prov-' || left(municipality_code, 2))
                              STORED NOT NULL REFERENCES territories (id),
            year              smallint NOT NULL,
            value             numeric(6, 3) NOT NULL,

            PRIMARY KEY (load_id, municipality_code, year),
            CONSTRAINT municipal_values_code_5_digits CHECK (municipality_code ~ '^[0-9]{5}$'),
            CONSTRAINT municipal_values_year_plausible CHECK (year BETWEEN 2015 AND 2100),
            CONSTRAINT municipal_values_percent CHECK (value BETWEEN 0 AND 100)
        )
        """
    )


def _append_only() -> None:
    # `voters_append_only()` was created by 0015; the same rule covers these two tables.
    for table in _APPEND_ONLY:
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_update_or_delete
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION voters_append_only()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
                BEFORE TRUNCATE ON {table}
                FOR EACH STATEMENT EXECUTE FUNCTION voters_append_only()
            """
        )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
