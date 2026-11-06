from datetime import UTC, datetime, timedelta

from datos.stories.domain.tree import (
    StoryLink,
    StoryPair,
    StoryStart,
    TreeSettings,
    choose_parents,
    tree_shape,
)

SETTINGS = TreeSettings(threshold=0.75, window_days=14)
DAY = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def story(story_id: int, days: float = 0.0) -> StoryStart:
    return StoryStart(story_id, DAY + timedelta(days=days))


def pair(first: StoryStart, second: StoryStart, similarity: float = 0.8) -> StoryPair:
    return StoryPair(first, second, similarity)


def test_a_story_continues_the_earlier_one_it_is_similar_to() -> None:
    earlier, later = story(1, 0), story(2, 3)

    assert choose_parents([pair(earlier, later, 0.8)], SETTINGS) == [StoryLink(2, 1, 0.8)]


def test_the_direction_is_chronological_whatever_the_order_of_the_pair() -> None:
    earlier, later = story(1, 0), story(2, 3)

    assert choose_parents([pair(later, earlier)], SETTINGS) == choose_parents(
        [pair(earlier, later)], SETTINGS
    )


def test_a_story_has_only_one_parent_the_most_similar_earlier_one() -> None:
    a, b, child = story(1, 0), story(2, 1), story(3, 5)

    links = choose_parents([pair(a, child, 0.78), pair(b, child, 0.9)], SETTINGS)

    assert links == [StoryLink(3, 2, 0.9)]


def test_the_earlier_story_has_no_parent_of_its_own_when_nothing_precedes_it() -> None:
    links = choose_parents([pair(story(1, 0), story(2, 3))], SETTINGS)

    assert [link.story_id for link in links] == [2]


def test_a_chain_links_each_story_to_the_previous_one() -> None:
    a, b, c = story(1, 0), story(2, 3), story(3, 6)

    links = choose_parents([pair(a, b), pair(b, c)], SETTINGS)

    assert [(link.story_id, link.parent_story_id) for link in links] == [(2, 1), (3, 2)]


def test_below_the_threshold_is_no_link_and_the_threshold_itself_is() -> None:
    a, b = story(1, 0), story(2, 3)

    assert choose_parents([pair(a, b, 0.7499)], SETTINGS) == []
    assert choose_parents([pair(a, b, 0.75)], SETTINGS) == [StoryLink(2, 1, 0.75)]


def test_the_window_edge_is_inside_and_after_it_is_outside() -> None:
    assert len(choose_parents([pair(story(1, 0), story(2, 14))], SETTINGS)) == 1
    assert choose_parents([pair(story(1, 0), story(2, 14.01))], SETTINGS) == []


def test_equal_similarity_goes_to_the_earlier_story_then_to_the_lower_id() -> None:
    older, newer, child = story(1, 0), story(2, 2), story(3, 5)
    same_time_low, same_time_high = story(4, 2), story(5, 2)

    assert choose_parents([pair(newer, child), pair(older, child)], SETTINGS) == [
        StoryLink(3, 1, 0.8)
    ]
    assert choose_parents(
        [pair(same_time_high, story(6, 5)), pair(same_time_low, story(6, 5))], SETTINGS
    ) == [StoryLink(6, 4, 0.8)]


def test_two_stories_at_the_same_instant_can_never_be_each_others_parent() -> None:
    a, b = story(1, 2), story(2, 2)

    links = choose_parents([pair(a, b)], SETTINGS)

    assert links == [StoryLink(2, 1, 0.8)]  # the lower id is "earlier": one direction only


def test_the_result_does_not_depend_on_the_order_of_the_pairs() -> None:
    a, b, c, d = story(1, 0), story(2, 3), story(3, 6), story(4, 7)
    pairs = [pair(a, b), pair(b, c, 0.9), pair(a, c, 0.8), pair(c, d, 0.77)]

    assert choose_parents(pairs, SETTINGS) == choose_parents(list(reversed(pairs)), SETTINGS)


def test_the_tree_of_a_story_is_found_from_any_of_its_members() -> None:
    links = [StoryLink(2, 1, 0.8), StoryLink(3, 2, 0.8), StoryLink(4, 1, 0.8), StoryLink(9, 8, 0.8)]

    for member in (1, 2, 3, 4):
        shape = tree_shape(member, links)
        assert shape is not None
        assert shape.root_story_id == 1
        assert [link.story_id for link in shape.links] == [2, 3, 4]


def test_a_story_with_no_relations_has_no_tree() -> None:
    assert tree_shape(5, [StoryLink(2, 1, 0.8)]) is None
    assert tree_shape(5, []) is None


def test_another_tree_of_the_same_run_is_left_out() -> None:
    shape = tree_shape(8, [StoryLink(2, 1, 0.8), StoryLink(9, 8, 0.8)])

    assert shape is not None
    assert (shape.root_story_id, [link.story_id for link in shape.links]) == (8, [9])
