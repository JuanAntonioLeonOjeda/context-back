"""A vector index for the related news: the nearest earlier items of a step (related-news).

Revision ID: 0020
Revises: 0019
Created: 2026-11-25
"""

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # HNSW on the cosine distance, the one `<=>` computes and the related news orders by. Measured
    # on 38,000 articles (2026-11-25): a step's candidates in 8 ms instead of 38 (median), none of
    # the 188 candidates of 30 random articles missed; 151 MB, built in 17 s. It is approximate:
    # the query keeps reading the index past the window filter with pgvector's iterative scans
    # (pg_related_reader.py). Not CONCURRENTLY: Alembic runs inside a transaction, and the only
    # writer (the worker) can wait the seconds the build takes.
    op.execute(
        "CREATE INDEX article_embeddings_embedding_hnsw_idx"
        " ON article_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX article_embeddings_embedding_hnsw_idx")
