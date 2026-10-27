"""`GET /stories/{id}/tree`: the tree of related stories a story belongs to. Headline, link and date
only: never the lead (sources audit, section 7), a vector or a party (ADR-0018).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.stories.application.community_stories import StoryRun
from datos.stories.application.story_tree import StoryTreeReader, TreeNode, TreeRun, story_tree
from datos.stories.interface.routes import ArticleOut, GroupingOut

DESCRIPTION = """
The tree of related stories the story belongs to, from the latest linking run: each story points
at the earlier story it continues (`parent_story_id`, null for the root). A link only says
"related and later": it does not say why.

**Order:** nodes by the publication time of their first article, oldest first, ties by story id;
inside a node, articles by outlet id, then publication time. The order never depends on an
outlet's size, audience or line.

`linking` says how the links were made and `grouping` how the stories were; both thresholds are
provisional until pairs are labelled by hand. 404 when the story has no relations.
"""


class LinkingOut(BaseModel):
    run_id: int
    threshold: float
    window_days: int
    created_at: datetime


class TreeNodeOut(BaseModel):
    story_id: int
    parent_story_id: int | None
    link_similarity: float | None
    started_at: datetime
    articles: list[ArticleOut]


class StoryTreeOut(BaseModel):
    root_story_id: int
    linking: LinkingOut
    grouping: GroupingOut
    nodes: list[TreeNodeOut]


def build_tree_router(*, trees: Provider[StoryTreeReader]) -> APIRouter:
    router = APIRouter(tags=["stories"])

    @router.get("/stories/{story_id}/tree", response_model=StoryTreeOut, description=DESCRIPTION)
    def tree(story_id: int, reader: Annotated[StoryTreeReader, Depends(trees)]) -> StoryTreeOut:
        found = story_tree(story_id, reader)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"story {story_id} has no relations")
        return StoryTreeOut(
            root_story_id=found.root_story_id,
            linking=_linking(found.run),
            grouping=_grouping(found.run.story_run),
            nodes=[_node(node) for node in found.nodes],
        )

    return router


def _linking(run: TreeRun) -> LinkingOut:
    return LinkingOut(
        run_id=run.tree_run_id,
        threshold=run.threshold,
        window_days=run.window_days,
        created_at=run.created_at,
    )


def _grouping(run: StoryRun) -> GroupingOut:
    return GroupingOut(
        run_id=run.run_id,
        encoder_version=run.encoder_version,
        threshold=run.threshold,
        window_days=run.window_days,
        created_at=run.created_at,
    )


def _node(node: TreeNode) -> TreeNodeOut:
    return TreeNodeOut(
        story_id=node.story_id,
        parent_story_id=node.parent_story_id,
        link_similarity=node.link_similarity,
        started_at=node.started_at,
        articles=[
            ArticleOut(
                outlet_id=a.outlet_id,
                outlet_name=a.outlet_name,
                headline=a.headline,
                url=a.url,
                published_at=a.published_at,
            )
            for a in node.articles
        ],
    )
