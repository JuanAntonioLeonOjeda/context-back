"""Election results by municipality and income by municipality (phase context-voters).

Revision ID: 0015
Revises: 0014
Created: 2026-11-06
"""

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | None = None
depends_on: str | None = None

_APPEND_ONLY = (
    "elections",
    "election_candidatures",
    "municipal_results",
    "municipal_candidature_votes",
    "municipal_income",
)


def upgrade() -> None:
    _elections()
    _results()
    _income()
    _append_only()


def _elections() -> None:
    # One row per election loaded. The file is downloaded by hand (Infoelectoral answers a bot
    # challenge, docs/sources-audit.md section 10), so its name and hash stand in for the
    # `downloads` row an automated source would have.
    op.execute(
        """
        CREATE TABLE elections (
            id            text PRIMARY KEY,          -- 'congreso-2023-07'
            kind          text NOT NULL,
            held_on       date NOT NULL,
            source_file   text NOT NULL,             -- '02202307_MUNI.zip'
            source_sha256 text NOT NULL,
            loaded_at     timestamptz NOT NULL DEFAULT now(),

            CONSTRAINT elections_id_slug CHECK (id ~ '^[a-z]+-[0-9]{4}-[0-9]{2}$'),
            CONSTRAINT elections_kind_known CHECK (kind IN ('congreso')),
            CONSTRAINT elections_sha256_hex CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT elections_one_file UNIQUE (source_sha256)
        )
        """
    )
    # A candidature as the file names it (file 03). `national_head_code` is the candidature its
    # votes add up to nationally (PSC and PSdeG-PSOE to PSOE); a head points at itself. The
    # foreign key is deferred so a candidature can be inserted before its head in one transaction.
    op.execute(
        """
        CREATE TABLE election_candidatures (
            election_id        text NOT NULL REFERENCES elections (id),
            code               text NOT NULL,
            acronym            text NOT NULL,
            name               text NOT NULL,
            national_head_code text NOT NULL,

            PRIMARY KEY (election_id, code),
            CONSTRAINT election_candidatures_code_6_digits CHECK (code ~ '^[0-9]{6}$'),
            CONSTRAINT election_candidatures_head_6_digits
                CHECK (national_head_code ~ '^[0-9]{6}$'),
            CONSTRAINT election_candidatures_head_exists
                FOREIGN KEY (election_id, national_head_code)
                REFERENCES election_candidatures (election_id, code)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )


def _results() -> None:
    # Municipalities are not in `territories` (only the State, communities and provinces are), so
    # the province is derived from the INE code and checked against it: a code whose province does
    # not exist cannot be stored, and the community comes from the province's parent.
    op.execute(
        """
        CREATE TABLE municipal_results (
            election_id        text NOT NULL REFERENCES elections (id),
            municipality_code  text NOT NULL,        -- INE: province (2) + municipality (3)
            municipality_name  text NOT NULL,
            province_id        text GENERATED ALWAYS AS ('prov-' || left(municipality_code, 2))
                               STORED NOT NULL REFERENCES territories (id),
            census             integer NOT NULL,     -- INE census (file 05)
            blank_votes        integer NOT NULL,
            null_votes         integer NOT NULL,
            candidature_votes  integer NOT NULL,     -- valid votes = blank + candidature

            PRIMARY KEY (election_id, municipality_code),
            CONSTRAINT municipal_results_code_5_digits CHECK (municipality_code ~ '^[0-9]{5}$'),
            CONSTRAINT municipal_results_counts_not_negative CHECK (
                census >= 0 AND blank_votes >= 0 AND null_votes >= 0 AND candidature_votes >= 0
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE municipal_candidature_votes (
            election_id       text NOT NULL,
            municipality_code text NOT NULL,
            candidature_code  text NOT NULL,
            votes             integer NOT NULL,

            PRIMARY KEY (election_id, municipality_code, candidature_code),
            CONSTRAINT municipal_candidature_votes_result
                FOREIGN KEY (election_id, municipality_code)
                REFERENCES municipal_results (election_id, municipality_code),
            CONSTRAINT municipal_candidature_votes_candidature
                FOREIGN KEY (election_id, candidature_code)
                REFERENCES election_candidatures (election_id, code),
            CONSTRAINT municipal_candidature_votes_not_negative CHECK (votes >= 0)
        )
        """
    )


def _income() -> None:
    # Like `observations` (ADR-0012): what the INE published, with the download it came from; a
    # revision is a new row and the current value is the one of the latest download.
    op.execute(
        """
        CREATE TABLE municipal_income (
            id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            municipality_code text NOT NULL,
            province_id       text GENERATED ALWAYS AS ('prov-' || left(municipality_code, 2))
                              STORED NOT NULL REFERENCES territories (id),
            year              smallint NOT NULL,
            euros_per_person  numeric(10, 2) NOT NULL,  -- ADRH, mean net income per person
            series_code       text NOT NULL,            -- the INE series of the municipality
            download_id       bigint NOT NULL REFERENCES downloads (id),

            CONSTRAINT municipal_income_code_5_digits CHECK (municipality_code ~ '^[0-9]{5}$'),
            CONSTRAINT municipal_income_year_plausible CHECK (year BETWEEN 2015 AND 2100),
            CONSTRAINT municipal_income_positive CHECK (euros_per_person > 0),
            CONSTRAINT municipal_income_one_per_download
                UNIQUE (municipality_code, year, download_id)
        )
        """
    )


def _append_only() -> None:
    # Official results do not change once published, and income follows the observations' rule:
    # nothing is updated or deleted, enforced by the database and not only by the code.
    op.execute(
        """
        CREATE FUNCTION voters_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: % is not allowed', TG_TABLE_NAME, TG_OP;
        END;
        $$
        """
    )
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
