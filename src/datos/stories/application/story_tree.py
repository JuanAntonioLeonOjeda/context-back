"""Use case: the tree of related stories a story belongs to, in the latest tree run.

A node is a story of the grouping run the tree run was made on, with its articles; a link says
"this story continues that earlier one". Nothing here ranks stories or outlets (ADR-0018), and no
party is attached.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from datos.stories.application.community_stories import StoryArticle, StoryRun
from datos.stories.domain.tree import StoryLink, tree_shape


@dataclass(frozen=True, slots=True)
class TreeRun:
    """How the links were made: the linking run and the grouping run it was made on."""

    tree_run_id: int
    threshold: float
    window_days: int
    created_at: datetime
    story_run: StoryRun


@dataclass(frozen=True, slots=True)
class TreeNode:
    story_id: int
    parent_story_id: int | None  # None for the root
    link_similarity: float | None  # None for the root
    started_at: datetime  # publication time of the first article of the story
    articles: tuple[StoryArticle, ...]  # by outlet id, then publication time, then article id


@dataclass(frozen=True, slots=True)
class StoryTree:
    root_story_id: int
    run: TreeRun
    nodes: tuple[TreeNode, ...]  # oldest first, ties by story id


class StoryTreeReader(Protocol):
    def latest_tree_run(self) -> TreeRun | None: ...

    def links(self, tree_run_id: int) -> list[StoryLink]: ...

    def story_articles(
        self, story_run_id: int, story_ids: Sequence[int]
    ) -> Mapping[int, tuple[StoryArticle, ...]]:
        """The articles of each story of the grouping run, ordered as a node shows them."""
        ...


def story_tree(story_id: int, reader: StoryTreeReader) -> StoryTree | None:
    """The tree of the story, or None when there is no tree run or the story has no relations."""
    run = reader.latest_tree_run()
    if run is None:
        return None
    links = reader.links(run.tree_run_id)
    shape = tree_shape(story_id, links)
    if shape is None:
        return None
    link_of = {link.story_id: link for link in shape.links}
    story_ids = [shape.root_story_id, *link_of]
    articles = reader.story_articles(run.story_run.run_id, story_ids)
    nodes = [
        TreeNode(
            story_id=member,
            parent_story_id=link.parent_story_id if (link := link_of.get(member)) else None,
            link_similarity=link.similarity if link else None,
            started_at=min(article.published_at for article in articles[member]),
            articles=articles[member],
        )
        for member in story_ids
    ]
    nodes.sort(key=lambda node: (node.started_at, node.story_id))
    return StoryTree(shape.root_story_id, run, tuple(nodes))
