"""Bodies, the holders of their head post and their competences (phase org-chart).

Revision ID: 0016
Revises: 0015
Created: 2026-11-13
"""

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    _bodies()
    _holders()
    _competences()


def _bodies() -> None:
    # A body is a box of the chart: the head of an executive, a department (consejería, ministry),
    # a parliament, a court, or a generic local body. Curated by hand in `data/organization/`; the
    # database mirrors the CSV (the history is in the CSV and in git), so rows are replaced on load.
    op.execute(
        """
        CREATE TABLE bodies (
            id           text PRIMARY KEY,           -- 'es-gobierno', 'ccaa-13-sanidad'
            kind         text NOT NULL,
            level        text NOT NULL,
            territory_id text REFERENCES territories (id),
            name         text NOT NULL,              -- the official name
            parent_id    text REFERENCES bodies (id),
            dir3_id      text,                       -- the code of the body in DIR3, to cross-check
            source_url   text NOT NULL,

            CONSTRAINT bodies_id_is_slug CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
            CONSTRAINT bodies_kind_known CHECK (
                kind IN ('executive_head', 'department', 'parliament', 'judiciary', 'local')
            ),
            -- The same vocabulary as the competence table.
            CONSTRAINT bodies_level_known CHECK (level IN ('state', 'ccaa', 'local')),
            CONSTRAINT bodies_name_not_empty CHECK (btrim(name) <> ''),
            CONSTRAINT bodies_source_is_url CHECK (source_url ~ '^https?://'),
            CONSTRAINT bodies_dir3_id_format
                CHECK (dir3_id IS NULL OR dir3_id ~ '^[A-Z][0-9A-Z]{8}$'),
            CONSTRAINT bodies_dir3_id_unique UNIQUE (dir3_id),

            -- A generic local body has no territory; every other body has one.
            CONSTRAINT bodies_local_has_no_territory
                CHECK ((level = 'local') = (territory_id IS NULL)),
            -- A community's body belongs to a community (not to the State, not to a province).
            CONSTRAINT bodies_ccaa_belongs_to_a_community CHECK (
                level <> 'ccaa' OR (territory_id IS NOT NULL AND territory_id LIKE 'ccaa-%')
            ),
            -- A State body belongs to the State, except a court: a TSJ is a State body that sits
            -- in a community.
            CONSTRAINT bodies_state_belongs_to_the_state CHECK (
                level <> 'state'
                OR territory_id = 'es'
                OR (kind = 'judiciary' AND territory_id IS NOT NULL AND territory_id LIKE 'ccaa-%')
            ),
            -- The id starts with the territory, so two communities never share one.
            CONSTRAINT bodies_id_starts_with_its_territory CHECK (
                (territory_id IS NULL AND id LIKE 'local-%')
                OR (territory_id IS NOT NULL AND id LIKE territory_id || '-%')
            ),
            CONSTRAINT bodies_department_has_a_parent CHECK (
                kind <> 'department' OR parent_id IS NOT NULL
            ),
            CONSTRAINT bodies_parent_is_another_body CHECK (parent_id IS NULL OR parent_id <> id),

            -- Lets a holder repeat the kind of its body and have the database check it.
            CONSTRAINT bodies_id_kind_unique UNIQUE (id, kind)
        )
        """
    )
    op.execute("CREATE INDEX bodies_territory_id_idx ON bodies (territory_id)")
    op.execute("CREATE INDEX bodies_parent_id_idx ON bodies (parent_id)")


def _holders() -> None:
    # Who holds the head post of a body (the president, a consejero, a minister) and when. The
    # post is implicit: one row per period, with its title as written in the appointment.
    op.execute(
        """
        CREATE TABLE body_holders (
            id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            body_id     text NOT NULL,
            body_kind   text NOT NULL,              -- repeated from `bodies`: see the foreign key
            post_title  text NOT NULL,
            holder_name text NOT NULL,
            valid_from  date NOT NULL,
            valid_to    date,                       -- NULL: in force today
            source_url  text NOT NULL,

            -- Only the head of an executive and a department have a holder. A CHECK cannot look
            -- at another table, so the row repeats the body's kind and a composite foreign key
            -- makes the database refuse a kind that is not the body's.
            CONSTRAINT body_holders_body_fkey
                FOREIGN KEY (body_id, body_kind) REFERENCES bodies (id, kind),
            CONSTRAINT body_holders_kind_has_a_holder
                CHECK (body_kind IN ('executive_head', 'department')),
            CONSTRAINT body_holders_post_title_not_empty CHECK (btrim(post_title) <> ''),
            CONSTRAINT body_holders_holder_name_not_empty CHECK (btrim(holder_name) <> ''),
            -- Half-open [valid_from, valid_to), like the government terms.
            CONSTRAINT body_holders_period_not_empty
                CHECK (valid_to IS NULL OR valid_to > valid_from),
            CONSTRAINT body_holders_source_is_url CHECK (source_url ~ '^https?://'),
            -- One holder per body on any day. A period with no end is unbounded on the right, so it
            -- collides with any later one.
            CONSTRAINT body_holders_no_overlap EXCLUDE USING gist (
                body_id WITH =,
                daterange(valid_from, valid_to, '[)') WITH &&
            )
        )
        """
    )


def _competences() -> None:
    # What the law gives a body, in the project's own words, with the article and a link. It is a
    # statement about the body, never about a person or a party (ADR-0025). `competences` (sector x
    # level x function) is a different table: it says which level holds what, not what a body does.
    op.execute(
        """
        CREATE TABLE body_competences (
            id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            body_id     text NOT NULL REFERENCES bodies (id),
            summary     text NOT NULL,
            legal_basis text NOT NULL,
            source_url  text NOT NULL,

            CONSTRAINT body_competences_summary_not_empty CHECK (btrim(summary) <> ''),
            CONSTRAINT body_competences_legal_basis_not_empty CHECK (btrim(legal_basis) <> ''),
            CONSTRAINT body_competences_source_is_url CHECK (source_url ~ '^https?://')
        )
        """
    )
    op.execute("CREATE INDEX body_competences_body_id_idx ON body_competences (body_id)")
    # "A competence relates to at least one sector" spans several rows, which a constraint cannot
    # express; the loader checks it before writing.
    op.execute(
        """
        CREATE TABLE body_competence_sectors (
            competence_id bigint NOT NULL REFERENCES body_competences (id) ON DELETE CASCADE,
            sector_id     text NOT NULL REFERENCES sectors (id),

            PRIMARY KEY (competence_id, sector_id)
        )
        """
    )


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
