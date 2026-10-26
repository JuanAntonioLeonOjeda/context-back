"""Group articles into stories from candidate pairs. Pure: no I/O, no clock, no vectors.

The pairs come from the database (pgvector computes the similarities); this module only decides
which pairs are links and which links make a story, so the rule can be tested without a database.
"""

from collections.abc import Iterable

from datos.stories.domain.story import CandidatePair, GroupingSettings, Story, StoryMember


def is_link(pair: CandidatePair, settings: GroupingSettings) -> bool:
    """Two articles of different outlets, similar enough and published close enough in time."""
    return (
        pair.outlet_a_id != pair.outlet_b_id
        and pair.similarity >= settings.threshold
        and pair.days_apart <= settings.window_days
    )


def group_stories(pairs: Iterable[CandidatePair], settings: GroupingSettings) -> list[Story]:
    """The connected components of the accepted links, ordered by their first article id.

    Known risk (plan.md): if A~B and B~C are links but A and C are not alike, the three end up
    together. The result is deterministic: it does not depend on the order of `pairs`.
    """
    links = sorted(
        (pair for pair in pairs if is_link(pair, settings)),
        key=lambda pair: (pair.article_a_id, pair.article_b_id),
    )
    parent: dict[int, int] = {}
    for link in links:
        _union(parent, link.article_a_id, link.article_b_id)

    strongest: dict[int, float] = {}
    for link in links:
        for article_id in (link.article_a_id, link.article_b_id):
            strongest[article_id] = max(strongest.get(article_id, 0.0), link.similarity)

    members_by_root: dict[int, list[StoryMember]] = {}
    for article_id in sorted(parent):
        member = StoryMember(article_id, strongest[article_id])
        members_by_root.setdefault(_find(parent, article_id), []).append(member)
    return sorted(
        (Story(tuple(members)) for members in members_by_root.values()),
        key=lambda story: story.members[0].article_id,
    )


def _find(parent: dict[int, int], article_id: int) -> int:
    parent.setdefault(article_id, article_id)
    while parent[article_id] != article_id:
        parent[article_id] = parent[parent[article_id]]  # path halving keeps the trees flat
        article_id = parent[article_id]
    return article_id


def _union(parent: dict[int, int], first: int, second: int) -> None:
    first_root, second_root = _find(parent, first), _find(parent, second)
    if first_root != second_root:
        # The smaller id becomes the root, so the outcome does not depend on the order.
        parent[max(first_root, second_root)] = min(first_root, second_root)
