"""Link each story to the earlier story it continues. Pure: no I/O, no clock, no vectors.

The similarities come from the database (pgvector compares the centroids of the stories); this
module only decides which pair is a link and which earlier story is the parent, so the rule can
be tested without a database.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TreeSettings:
    """What counts as a link. Provisional until pairs are labelled by hand (spec, open question)."""

    threshold: float  # minimum cosine similarity of the two story centroids
    window_days: int  # maximum days between the first articles of the two stories


@dataclass(frozen=True, slots=True)
class StoryStart:
    story_id: int
    started_at: datetime  # publication time of the story's first article


@dataclass(frozen=True, slots=True)
class StoryPair:
    """Two stories and the cosine similarity of their centroids; the order is not meaningful."""

    first: StoryStart
    second: StoryStart
    similarity: float


@dataclass(frozen=True, slots=True)
class StoryLink:
    story_id: int  # the later story
    parent_story_id: int  # the earlier one it continues
    similarity: float


def _order(story: StoryStart) -> tuple[datetime, int]:
    # The id breaks ties between equal times, so "earlier" is a strict order and never a cycle.
    return (story.started_at, story.story_id)


def choose_parents(pairs: Iterable[StoryPair], settings: TreeSettings) -> list[StoryLink]:
    """At most one link per story: to the most similar earlier story inside the window.

    Ties on similarity go to the earlier story, then to the lower id. The result is sorted by story
    id and does not depend on the order of `pairs`.
    """
    best: dict[int, tuple[float, StoryStart]] = {}
    later_of: dict[int, StoryStart] = {}
    for pair in pairs:
        earlier, later = sorted((pair.first, pair.second), key=_order)
        gap_days = (later.started_at - earlier.started_at).total_seconds() / 86400
        if pair.similarity < settings.threshold or gap_days > settings.window_days:
            continue
        later_of[later.story_id] = later
        current = best.get(later.story_id)
        if current is None or _beats(pair.similarity, earlier, current):
            best[later.story_id] = (pair.similarity, earlier)
    return [
        StoryLink(story_id, parent.story_id, similarity)
        for story_id, (similarity, parent) in sorted(best.items())
    ]


def _beats(similarity: float, candidate: StoryStart, current: tuple[float, StoryStart]) -> bool:
    current_similarity, current_parent = current
    if similarity != current_similarity:
        return similarity > current_similarity
    return _order(candidate) < _order(current_parent)


@dataclass(frozen=True, slots=True)
class TreeShape:
    root_story_id: int
    links: tuple[StoryLink, ...]  # every link of the tree, sorted by story id


def tree_shape(story_id: int, links: Iterable[StoryLink]) -> TreeShape | None:
    """The tree a story belongs to: climb to its root, then take every descendant.

    None when the story has no relations (it is neither a child nor a parent): a tree needs at
    least two stories. Links are a forest by construction (one parent each, parents strictly
    earlier), so the climb ends.
    """
    all_links = list(links)
    parent_of = {link.story_id: link for link in all_links}
    children: dict[int, list[StoryLink]] = {}
    for link in all_links:
        children.setdefault(link.parent_story_id, []).append(link)
    if story_id not in parent_of and story_id not in children:
        return None
    root = story_id
    while root in parent_of:
        root = parent_of[root].parent_story_id
    members: list[StoryLink] = []
    pending = [root]
    while pending:
        for link in children.get(pending.pop(), []):
            members.append(link)
            pending.append(link.story_id)
    return TreeShape(root, tuple(sorted(members, key=lambda link: link.story_id)))
