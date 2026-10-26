from datetime import UTC, datetime

import pytest

from datos.stories.application.group_stories import NoEmbeddingsError, group_recent
from datos.stories.domain.story import CandidatePair, GroupingSettings, Story

SINCE = datetime(2026, 9, 1, tzinfo=UTC)
SETTINGS = GroupingSettings(threshold=0.88, window_days=3)


class FakeStories:
    def __init__(self, version: str | None, pairs: list[CandidatePair]) -> None:
        self._version = version
        self._pairs = pairs
        self.runs: list[tuple[str, GroupingSettings, list[Story]]] = []

    def latest_encoder_version(self) -> str | None:
        return self._version

    def candidate_pairs(
        self, encoder_version: str, *, since: datetime, settings: GroupingSettings
    ) -> list[CandidatePair]:
        return self._pairs

    def add_run(
        self, encoder_version: str, settings: GroupingSettings, stories: list[Story]
    ) -> int:
        self.runs.append((encoder_version, settings, stories))
        return len(self.runs)


def test_the_run_stores_the_stories_with_the_version_and_settings_it_used() -> None:
    fake = FakeStories("v1", [CandidatePair(1, 2, "a", "b", 0.95, 0.2)])

    run_id = group_recent(fake, fake, SETTINGS, since=SINCE)

    assert run_id == 1
    version, settings, stories = fake.runs[0]
    assert (version, settings) == ("v1", SETTINGS)
    assert [m.article_id for m in stories[0].members] == [1, 2]


def test_a_pair_below_the_threshold_is_dropped_even_if_the_reader_returned_it() -> None:
    fake = FakeStories("v1", [CandidatePair(1, 2, "a", "b", 0.80, 0.2)])

    group_recent(fake, fake, SETTINGS, since=SINCE)

    assert fake.runs[0][2] == []


def test_without_embeddings_there_is_nothing_to_group_and_nothing_is_stored() -> None:
    fake = FakeStories(None, [])

    with pytest.raises(NoEmbeddingsError):
        group_recent(fake, fake, SETTINGS, since=SINCE)

    assert fake.runs == []
