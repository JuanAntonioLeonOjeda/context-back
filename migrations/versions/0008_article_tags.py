"""Tags of an article, as the outlet publishes them (ADR-0019).

`tags` holds each tag once; `article_tags` says which articles carry it and where it came from.
Revision ID: 0008
Revises: 0007
Created: 2026-10-16
"""

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tags (
            id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            key   text NOT NULL,   -- the identity: lower case, single spaces
            label text NOT NULL,   -- as the first outlet wrote it

            CONSTRAINT tags_key_unique UNIQUE (key),
            CONSTRAINT tags_key_is_normalised
                CHECK (key = lower(btrim(regexp_replace(key, '\\s+', ' ', 'g')))),
            CONSTRAINT tags_key_not_blank CHECK (key <> ''),
            CONSTRAINT tags_label_short CHECK (btrim(label) <> '' AND char_length(label) <= 100)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE article_tags (
            article_id bigint NOT NULL REFERENCES articles (id),
            tag_id     bigint NOT NULL REFERENCES tags (id),
            source     text NOT NULL,   -- 'feed': published with it; 'body': read from its text

            PRIMARY KEY (article_id, tag_id, source),
            CONSTRAINT article_tags_source_known CHECK (source IN ('feed', 'body'))
        )
        """
    )
    # "Which articles carry this tag": the primary key already serves the other direction.
    op.execute("CREATE INDEX article_tags_tag_idx ON article_tags (tag_id)")


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
