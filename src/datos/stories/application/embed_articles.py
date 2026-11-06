"""Use case: embed the recent articles that have no vector for this encoder version yet.

Idempotent: an article is embedded once per encoder version, so running it again after a
collection touches only the new articles, and a new encoder version embeds everything again
alongside the old rows. The newest articles go first: an interrupted run leaves what the
portal shows most embedded.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import structlog

from datos.stories.domain.text import embedding_text

log = structlog.get_logger(__name__)

BATCH_SIZE = 64


@dataclass(frozen=True, slots=True)
class ArticleToEmbed:
    article_id: int
    headline: str
    lead: str | None


class TextEncoder(Protocol):
    name: str
    version: str  # changes whenever the vectors it gives would change

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in the same order."""
        ...


class EmbeddingRepository(Protocol):
    def missing(self, encoder_version: str, *, since: datetime, limit: int) -> list[ArticleToEmbed]:
        """Articles published since `since` with no vector of this version, newest first."""
        ...

    def add(
        self, encoder_name: str, encoder_version: str, vectors: Sequence[tuple[int, list[float]]]
    ) -> int:
        """Store the vectors append-only; return how many rows were new."""
        ...


def embed_new(encoder: TextEncoder, repository: EmbeddingRepository, *, since: datetime) -> int:
    """Embed every article since `since` that lacks a vector of this version; return how many."""
    stored = 0
    started = time.monotonic()
    while True:
        batch = repository.missing(encoder.version, since=since, limit=BATCH_SIZE)
        if not batch:
            break
        vectors = encoder.encode([embedding_text(a.headline, a.lead) for a in batch])
        stored += repository.add(
            encoder.name,
            encoder.version,
            [(a.article_id, vector) for a, vector in zip(batch, vectors, strict=True)],
        )
        log.info("articles_embedded", stored=stored, seconds=round(time.monotonic() - started))
    log.info("embedding_finished", encoder_version=encoder.version, stored=stored)
    return stored
