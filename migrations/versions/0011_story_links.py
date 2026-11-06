"""Links between stories: each story points at the earlier story it continues (phase history-trace).

A tree run is immutable and refers to the grouping run whose stories it links, with the threshold
and the window it used. `story_links` has one row per child, so a story has at most one parent.

Revision ID: 0011
Revises: 0010
Created: 2026-10-27
"""

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE story_tree_runs (
            id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            story_run_id bigint NOT NULL REFERENCES story_runs (id),
            threshold    real NOT NULL,         -- minimum cosine of two story centroids
            window_days  smallint NOT NULL,     -- maximum days between the first articles
            created_at   timestamptz NOT NULL DEFAULT now(),

            -- Lets story_links repeat the grouping run and keep its stories in that run.
            CONSTRAINT story_tree_runs_id_story_run_unique UNIQUE (id, story_run_id),
            CONSTRAINT story_tree_runs_threshold_in_range CHECK (threshold > 0 AND threshold <= 1),
            CONSTRAINT story_tree_runs_window_positive CHECK (window_days > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE story_links (
            tree_run_id     bigint NOT NULL,
            story_run_id    bigint NOT NULL,
            story_id        bigint NOT NULL,    -- the later story
            parent_story_id bigint NOT NULL,    -- the earlier one it continues
            similarity      real NOT NULL,      -- cosine of the two centroids

            -- One parent per story: the result is a forest, never a graph.
            PRIMARY KEY (tree_run_id, story_id),
            FOREIGN KEY (tree_run_id, story_run_id)
                REFERENCES story_tree_runs (id, story_run_id),
            -- Both stories belong to the grouping run the tree run was made on.
            FOREIGN KEY (story_id, story_run_id) REFERENCES stories (id, run_id),
            FOREIGN KEY (parent_story_id, story_run_id) REFERENCES stories (id, run_id),
            CONSTRAINT story_links_not_self CHECK (story_id <> parent_story_id),
            CONSTRAINT story_links_similarity_in_range CHECK (similarity BETWEEN -1 AND 1)
        )
        """
    )
    # Serves "the children of this story" when a tree is walked downwards.
    op.execute("CREATE INDEX story_links_parent_idx ON story_links (tree_run_id, parent_story_id)")


def downgrade() -> None:
    # Forward-only migrations (ADR-0010): fix mistakes with a new revision.
    raise NotImplementedError("Downgrades are not supported.")
