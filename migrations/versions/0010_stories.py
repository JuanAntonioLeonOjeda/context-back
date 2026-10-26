"""Embeddings of articles and the stories grouped from them (phase story-contrast).

`article_embeddings` keeps one vector per article and encoder version. A grouping run is
immutable: `story_runs` records the threshold and the window it used, `stories` and
`story_articles` hold its result, and a new run writes new rows instead of changing old ones.

Revision ID: 0010
Revises: 0009
Created: 2026-10-27
"""

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE article_embeddings (
            article_id      bigint NOT NULL REFERENCES articles (id),
            encoder_name    text NOT NULL,      -- e.g. the sentence-transformers model name
            encoder_version text NOT NULL,      -- changing the encoder is a new version, a new row
            embedding       vector(768) NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (article_id, encoder_version),
            CONSTRAINT article_embeddings_encoder_not_blank
                CHECK (btrim(encoder_name) <> '' AND btrim(encoder_version) <> '')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE story_runs (
            id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            encoder_version text NOT NULL,
            threshold       real NOT NULL,      -- minimum cosine similarity to link two articles
            window_days     smallint NOT NULL,  -- maximum days between two linked articles
            created_at      timestamptz NOT NULL DEFAULT now(),

            CONSTRAINT story_runs_threshold_in_range CHECK (threshold > 0 AND threshold <= 1),
            CONSTRAINT story_runs_window_positive CHECK (window_days > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE stories (
            id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            run_id bigint NOT NULL REFERENCES story_runs (id),

            -- Lets story_articles repeat the run and keep one story per article in a run.
            CONSTRAINT stories_id_run_unique UNIQUE (id, run_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE story_articles (
            run_id     bigint NOT NULL,
            story_id   bigint NOT NULL,
            article_id bigint NOT NULL REFERENCES articles (id),
            similarity real NOT NULL,           -- cosine to the story's mean vector

            PRIMARY KEY (story_id, article_id),
            FOREIGN KEY (story_id, run_id) REFERENCES stories (id, run_id),
            -- An article belongs to at most one story in each run.
            CONSTRAINT story_articles_one_story_per_run UNIQUE (run_id, article_id),
            CONSTRAINT story_articles_similarity_in_range CHECK (similarity BETWEEN -1 AND 1)
        )
        """
    )
    # Serves "which stories does this article belong to" and the news reader's join.
    op.execute("CREATE INDEX story_articles_article_idx ON story_articles (article_id)")


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
