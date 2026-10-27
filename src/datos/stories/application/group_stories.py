"""Use case: group the recent articles into stories and store the run.

A run is immutable (migration 0010): running it again writes a new run with its own threshold and
window, and the reader uses the latest.
"""

from datetime import datetime
from typing import Protocol

import structlog

from datos.stories.domain.grouping import group_stories
from datos.stories.domain.story import CandidatePair, GroupingSettings, Story

log = structlog.get_logger(__name__)


class CandidatePairReader(Protocol):
    def latest_encoder_version(self) -> str | None:
        """The encoder version of the most recent embedding, or None with no embeddings."""
        ...

    def candidate_pairs(
        self, encoder_version: str, *, since: datetime, settings: GroupingSettings
    ) -> list[CandidatePair]:
        """Pairs of articles of different outlets published since `since`, at most
        `settings.window_days` apart and with a cosine similarity of at least the threshold."""
        ...


class StoryWriter(Protocol):
    def add_run(
        self, encoder_version: str, settings: GroupingSettings, stories: list[Story]
    ) -> int:
        """Store a run with its stories whole or not at all; return the run id."""
        ...


class NoEmbeddingsError(Exception):
    """There is nothing to group: the embeddings job has not run."""


def group_recent(
    reader: CandidatePairReader,
    writer: StoryWriter,
    settings: GroupingSettings,
    *,
    since: datetime,
) -> int:
    """Group the articles since `since` with the latest encoder version; return the run id."""
    encoder_version = reader.latest_encoder_version()
    if encoder_version is None:
        raise NoEmbeddingsError("no article has a vector: run `python -m datos.stories embed`")
    pairs = reader.candidate_pairs(encoder_version, since=since, settings=settings)
    stories = group_stories(pairs, settings)
    run_id = writer.add_run(encoder_version, settings, stories)
    log.info(
        "stories_grouped",
        run_id=run_id,
        encoder_version=encoder_version,
        threshold=settings.threshold,
        window_days=settings.window_days,
        pairs=len(pairs),
        stories=len(stories),
        articles=sum(len(story.members) for story in stories),
    )
    return run_id
