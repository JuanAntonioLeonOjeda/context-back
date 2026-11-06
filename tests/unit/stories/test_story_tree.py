from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from datos.stories.application.community_stories import StoryArticle, StoryRun
from datos.stories.application.story_tree import TreeRun, story_tree
from datos.stories.domain.tree import StoryLink

STORY_RUN = StoryRun(1, "v1", 0.88, 3, datetime(2026, 10, 26, tzinfo=UTC))
TREE_RUN = TreeRun(5, 0.75, 14, datetime(2026, 10, 27, tzinfo=UTC), STORY_RUN)


def article(day: int) -> StoryArticle:
    return StoryArticle(
        day, "a", "A", "H", "https://a.example/1", datetime(2026, 10, day, tzinfo=UTC)
    )


class FakeReader:
    def __init__(self, run: TreeRun | None, links: list[StoryLink]) -> None:
        self._run = run
        self._links = links
        self.asked: list[int] = []

    def latest_tree_run(self) -> TreeRun | None:
        return self._run

    def links(self, tree_run_id: int) -> list[StoryLink]:
        return self._links

    def story_articles(
        self, story_run_id: int, story_ids: Sequence[int]
    ) -> Mapping[int, tuple[StoryArticle, ...]]:
        self.asked = list(story_ids)
        return {i: (article(10 + i),) for i in story_ids}


def test_only_the_stories_of_the_tree_are_read() -> None:
    reader = FakeReader(
        TREE_RUN, [StoryLink(2, 1, 0.8), StoryLink(3, 2, 0.8), StoryLink(9, 8, 0.8)]
    )

    tree = story_tree(3, reader)

    assert tree is not None
    assert sorted(reader.asked) == [1, 2, 3]
    assert [n.story_id for n in tree.nodes] == [1, 2, 3]
    assert tree.nodes[0].parent_story_id is None


def test_a_node_starts_when_its_first_article_was_published() -> None:
    tree = story_tree(1, FakeReader(TREE_RUN, [StoryLink(2, 1, 0.8)]))

    assert tree is not None
    assert tree.nodes[1].started_at == datetime(2026, 10, 12, tzinfo=UTC)


def test_no_run_or_no_relations_is_no_tree() -> None:
    assert story_tree(1, FakeReader(None, [])) is None
    assert story_tree(1, FakeReader(TREE_RUN, [StoryLink(9, 8, 0.8)])) is None
