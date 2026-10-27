"""Use case: link each story of the latest grouping run to the earlier story it continues.

A tree run is immutable (migration 0011): running it again writes a new run with its own threshold
and window, and the reader uses the latest.
"""

from typing import Protocol

import structlog

from datos.stories.domain.tree import StoryLink, StoryPair, TreeSettings, choose_parents

log = structlog.get_logger(__name__)


class StoryPairReader(Protocol):
    def latest_story_run_id(self) -> int | None:
        """The most recent grouping run, or None when stories were never grouped."""
        ...

    def story_pairs(self, story_run_id: int, settings: TreeSettings) -> list[StoryPair]:
        """Pairs of stories of the run whose first articles are at most `settings.window_days` apart
        and whose centroids have a cosine similarity of at least the threshold."""
        ...


class TreeWriter(Protocol):
    def add_run(self, story_run_id: int, settings: TreeSettings, links: list[StoryLink]) -> int:
        """Store a tree run with its links whole or not at all; return the run id."""
        ...


class NoStoriesError(Exception):
    """There is nothing to link: the grouping job has not run."""


def link_stories(reader: StoryPairReader, writer: TreeWriter, settings: TreeSettings) -> int:
    """Link the stories of the latest grouping run; return the id of the stored tree run."""
    story_run_id = reader.latest_story_run_id()
    if story_run_id is None:
        raise NoStoriesError("no stories: run `python -m datos.stories group`")
    pairs = reader.story_pairs(story_run_id, settings)
    links = choose_parents(pairs, settings)
    run_id = writer.add_run(story_run_id, settings, links)
    log.info(
        "stories_linked",
        tree_run_id=run_id,
        story_run_id=story_run_id,
        threshold=settings.threshold,
        window_days=settings.window_days,
        pairs=len(pairs),
        links=len(links),
    )
    return run_id
