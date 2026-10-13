"""Reference data (territories, parties, government terms, sectors, competences) and news
metadata (outlets, articles).

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

    op.execute(
        """
        CREATE TABLE parties (
            id         text PRIMARY KEY,                    -- stable slug used everywhere
            name       text NOT NULL,
            short_name text NOT NULL,
            colour_hex text NOT NULL,                       -- the only source of party colour

            CONSTRAINT parties_id_is_slug CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
            CONSTRAINT parties_colour_is_hex CHECK (colour_hex ~ '^#[0-9a-f]{6}$')
        )
        """
    )

    op.execute(
        """
        CREATE TABLE government_terms (
            id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            territory_id   text NOT NULL REFERENCES territories (id),
            president_name text NOT NULL,
            is_caretaker   boolean NOT NULL DEFAULT false,
            valid_from     date NOT NULL,
            valid_to       date,                            -- NULL: in force today
            source_url     text NOT NULL,

            -- Governments exist for the State and the communities, not for provinces.
            -- Relies on the territories id format: 'es' or 'ccaa-NN'.
            CONSTRAINT government_terms_territory_has_government
                CHECK (territory_id = 'es' OR territory_id LIKE 'ccaa-%'),

            -- Half-open [valid_from, valid_to): a term of zero days is a data error.
            CONSTRAINT government_terms_period_not_empty
                CHECK (valid_to IS NULL OR valid_to > valid_from),

            CONSTRAINT government_terms_source_is_url CHECK (source_url ~ '^https?://'),

            -- At most one government per territory on any day. daterange(a, NULL, '[)')
            -- is unbounded on the right, so two terms in force at once also collide.
            -- btree_gist provides the "=" operator on text inside a GiST index.
            CONSTRAINT government_terms_no_overlap EXCLUDE USING gist (
                territory_id WITH =,
                daterange(valid_from, valid_to, '[)') WITH &&
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE government_term_parties (
            term_id  bigint NOT NULL REFERENCES government_terms (id) ON DELETE CASCADE,
            party_id text NOT NULL REFERENCES parties (id),
            role     text NOT NULL,
            -- Each role has its own evidence: a vice-president's appointment for a coalition
            -- partner, the investiture vote for external support.
            source_url text NOT NULL,

            -- A party has one role per term: it governs or it supports from outside.
            PRIMARY KEY (term_id, party_id),
            CONSTRAINT government_term_parties_role_valid
                CHECK (role IN ('governing', 'external_support')),
            CONSTRAINT government_term_parties_source_is_url CHECK (source_url ~ '^https?://')
        )
        """
    )
    # "Every term has at least one governing party" spans several rows, which a CHECK
    # cannot express. It is enforced in the domain before loading (task 10).
    op.execute(
        "CREATE INDEX government_term_parties_party_id_idx ON government_term_parties (party_id)"
    )

    op.execute(
        """
        CREATE TABLE sectors (
            id   text PRIMARY KEY,                          -- 'education', 'health', 'housing'
            name text NOT NULL,

            -- Sectors are data (ADR-0007): adding one is an INSERT, not a migration.
            CONSTRAINT sectors_id_is_slug CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
        )
        """
    )

    op.execute(
        """
        CREATE TABLE competences (
            id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            sector_id   text NOT NULL REFERENCES sectors (id),
            activity    text NOT NULL,                      -- slug, e.g. 'teaching-staff'
            description text NOT NULL,
            level       text NOT NULL,
            function    text NOT NULL,
            legal_basis text NOT NULL,                      -- e.g. 'CE art. 149.1.30'
            source_url  text NOT NULL,

            CONSTRAINT competences_activity_is_slug
                CHECK (activity ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),

            -- Same vocabulary as territories; 'local' has no territories loaded yet.
            CONSTRAINT competences_level_valid CHECK (level IN ('state', 'ccaa', 'local')),

            -- A shared competence is one row per level, each saying what that level does,
            -- so attribution can pick the level that matches what the news describes.
            CONSTRAINT competences_function_valid
                CHECK (function IN ('basic_legislation', 'development_legislation', 'execution')),

            CONSTRAINT competences_source_is_url CHECK (source_url ~ '^https?://'),

            CONSTRAINT competences_one_row_per_level_and_function
                UNIQUE (sector_id, activity, level, function)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE outlets (
            id        text PRIMARY KEY,                     -- slug, e.g. 'outlet-a'
            name      text NOT NULL,
            home_url  text NOT NULL,
            scope     text NOT NULL,                        -- 'national' or 'regional'
            region_id text REFERENCES territories (id),     -- only for regional outlets

            CONSTRAINT outlets_id_is_slug CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
            CONSTRAINT outlets_home_url_is_url CHECK (home_url ~ '^https?://'),

            -- A regional outlet belongs to one community; a national one to none.
            -- IS NOT NULL is needed: "NULL LIKE ..." is NULL and a NULL CHECK passes.
            CONSTRAINT outlets_region_matches_scope
                CHECK (
                    (scope = 'national' AND region_id IS NULL)
                    OR (scope = 'regional' AND region_id IS NOT NULL AND region_id LIKE 'ccaa-%')
                )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE articles (
            id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            outlet_id    text NOT NULL REFERENCES outlets (id),
            url          text NOT NULL,
            published_at timestamptz NOT NULL,              -- as stated by the outlet
            fetched_at   timestamptz NOT NULL DEFAULT now(),
            headline     text NOT NULL,
            lead         text,                              -- some feeds have none

            CONSTRAINT articles_url_is_url CHECK (url ~ '^https?://'),
            CONSTRAINT articles_headline_not_blank CHECK (btrim(headline) <> ''),

            -- We keep metadata only, never bodies (project policies). A hard cap turns
            -- an accidental full-text insert into an error instead of a quiet copy.
            CONSTRAINT articles_lead_is_short CHECK (char_length(lead) <= 1000),

            -- Feeds are re-read; the same item must not create a second row. The
            -- collector normalises URLs (e.g. drops tracking parameters) before insert.
            CONSTRAINT articles_one_row_per_url UNIQUE (outlet_id, url)
        )
        """
    )
    op.execute("CREATE INDEX articles_published_at_idx ON articles (published_at)")


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
