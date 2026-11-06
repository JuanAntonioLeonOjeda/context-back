from datos.stories.domain.grouping import group_stories, is_link
from datos.stories.domain.story import CandidatePair, GroupingSettings, Story

SETTINGS = GroupingSettings(threshold=0.8, window_days=3)


def article_ids(stories: list[Story]) -> list[int]:
    return sorted(member.article_id for story in stories for member in story.members)


def pair(
    a: int,
    b: int,
    *,
    outlets: tuple[str, str] = ("outlet-a", "outlet-b"),
    similarity: float = 0.9,
    days_apart: float = 0.5,
) -> CandidatePair:
    return CandidatePair(a, b, outlets[0], outlets[1], similarity, days_apart)


def test_two_outlets_covering_the_same_event_make_a_story() -> None:
    stories = group_stories([pair(1, 2, similarity=0.91)], SETTINGS)

    assert len(stories) == 1
    assert [(m.article_id, m.link_similarity) for m in stories[0].members] == [(1, 0.91), (2, 0.91)]


def test_two_articles_of_the_same_outlet_are_not_a_contrast() -> None:
    same_outlet = pair(1, 2, outlets=("outlet-a", "outlet-a"))

    assert not is_link(same_outlet, SETTINGS)
    assert group_stories([same_outlet], SETTINGS) == []


def test_similar_words_below_the_threshold_are_a_different_story() -> None:
    assert group_stories([pair(1, 2, similarity=0.79)], SETTINGS) == []


def test_the_threshold_itself_is_a_link() -> None:
    assert is_link(pair(1, 2, similarity=0.8), SETTINGS)


def test_the_window_edge_is_inside_and_the_next_moment_is_outside() -> None:
    assert is_link(pair(1, 2, days_apart=3.0), SETTINGS)
    assert not is_link(pair(1, 2, days_apart=3.01), SETTINGS)


def test_an_article_with_no_link_belongs_to_no_story() -> None:
    stories = group_stories([pair(1, 2), pair(3, 4, similarity=0.5)], SETTINGS)

    assert article_ids(stories) == [1, 2]


def test_separate_events_make_separate_stories_ordered_by_first_article() -> None:
    stories = group_stories([pair(7, 8), pair(1, 2)], SETTINGS)

    assert [[m.article_id for m in s.members] for s in stories] == [[1, 2], [7, 8]]


def test_a_third_outlet_joins_through_any_of_its_links() -> None:
    pairs = [pair(1, 2), pair(2, 3, outlets=("outlet-b", "outlet-c"), similarity=0.85)]

    stories = group_stories(pairs, SETTINGS)

    assert [[m.article_id for m in s.members] for s in stories] == [[1, 2, 3]]
    assert [m.link_similarity for m in stories[0].members] == [0.9, 0.9, 0.85]


def test_chaining_is_a_known_risk_a_and_c_join_through_b() -> None:
    # 1 and 3 are not linked directly; the story still holds the three (plan.md, "Non-obvious").
    pairs = [pair(1, 2), pair(2, 3, outlets=("outlet-b", "outlet-c"))]

    assert article_ids(group_stories(pairs, SETTINGS)) == [1, 2, 3]


def test_the_result_does_not_depend_on_the_order_of_the_pairs() -> None:
    pairs = [pair(5, 6), pair(2, 3, outlets=("outlet-b", "outlet-c")), pair(1, 2), pair(4, 5)]

    assert group_stories(pairs, SETTINGS) == group_stories(list(reversed(pairs)), SETTINGS)
