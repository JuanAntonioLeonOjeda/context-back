from datetime import UTC, datetime, timedelta

import pytest

from datos.stories.application.link_stories import NoStoriesError, link_stories
from datos.stories.domain.tree import StoryLink, StoryPair, StoryStart, TreeSettings

SETTINGS = TreeSettings(threshold=0.75, window_days=14)
DAY = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


class FakeLinks:
    def __init__(self, run_id: int | None, pairs: list[StoryPair]) -> None:
        self._run_id = run_id
        self._pairs = pairs
        self.runs: list[tuple[int, TreeSettings, list[StoryLink]]] = []

    def latest_story_run_id(self) -> int | None:
        return self._run_id

    def story_pairs(self, story_run_id: int, settings: TreeSettings) -> list[StoryPair]:
        return self._pairs

    def add_run(self, story_run_id: int, settings: TreeSettings, links: list[StoryLink]) -> int:
        self.runs.append((story_run_id, settings, links))
        return len(self.runs)


def pair(similarity: float) -> StoryPair:
    return StoryPair(
        StoryStart(1, DAY), StoryStart(2, DAY + timedelta(days=2)), similarity=similarity
    )


def test_the_run_stores_the_links_with_the_grouping_run_and_settings_it_used() -> None:
    fake = FakeLinks(7, [pair(0.8)])

    tree_run_id = link_stories(fake, fake, SETTINGS)

    assert tree_run_id == 1
    assert fake.runs == [(7, SETTINGS, [StoryLink(2, 1, 0.8)])]


def test_a_pair_below_the_threshold_is_dropped_even_if_the_reader_returned_it() -> None:
    fake = FakeLinks(7, [pair(0.6)])

    link_stories(fake, fake, SETTINGS)

    assert fake.runs[0][2] == []


def test_without_stories_there_is_nothing_to_link_and_nothing_is_stored() -> None:
    fake = FakeLinks(None, [])

    with pytest.raises(NoStoriesError):
        link_stories(fake, fake, SETTINGS)

    assert fake.runs == []
