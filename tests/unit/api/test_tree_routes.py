from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Protocol

import pytest
from fastapi.testclient import TestClient

from datos.stories.application.community_stories import StoryArticle, StoryRun
from datos.stories.application.story_tree import TreeRun
from datos.stories.domain.tree import StoryLink

Client = Callable[..., TestClient]


class FakeTrees(Protocol):  # the `trees_reader` fixture (conftest.FakeTrees)
    run: TreeRun | None
    link_rows: list[StoryLink]
    articles: Mapping[int, tuple[StoryArticle, ...]]


STORY_RUN = StoryRun(1, "encoder-v1", 0.88, 3, datetime(2026, 10, 26, 16, 56, tzinfo=UTC))
TREE_RUN = TreeRun(5, 0.75, 14, datetime(2026, 10, 27, 10, 35, tzinfo=UTC), STORY_RUN)


def article(outlet: str, day: int, number: int) -> StoryArticle:
    return StoryArticle(
        article_id=number,
        outlet_id=outlet,
        outlet_name=outlet.upper(),
        headline=f"Headline {number}",
        url=f"https://{outlet}.example/{number}",
        published_at=datetime(2026, 10, day, 9, 0, tzinfo=UTC),
    )


@pytest.fixture
def trees(trees_reader: FakeTrees) -> FakeTrees:
    trees_reader.run = TREE_RUN
    trees_reader.link_rows = [
        StoryLink(20, 10, 0.9),
        StoryLink(30, 10, 0.8),
        StoryLink(99, 98, 0.8),
    ]
    trees_reader.articles = {
        10: (article("a", 10, 1), article("b", 10, 2)),
        20: (article("a", 13, 3), article("b", 12, 4)),
        30: (article("a", 11, 5), article("b", 11, 6)),
    }
    return trees_reader


def test_the_tree_lists_nodes_oldest_first_each_pointing_at_the_story_it_continues(
    make_client: Client, trees: FakeTrees
) -> None:
    body = make_client().get("/stories/20/tree").json()

    assert body["root_story_id"] == 10
    assert [(n["story_id"], n["parent_story_id"]) for n in body["nodes"]] == [
        (10, None),
        (30, 10),
        (20, 10),
    ]
    assert [n["link_similarity"] for n in body["nodes"]] == [None, 0.8, 0.9]


def test_the_same_tree_comes_from_any_of_its_stories(make_client: Client, trees: FakeTrees) -> None:
    client = make_client()

    assert client.get("/stories/10/tree").json() == client.get("/stories/30/tree").json()


def test_the_response_says_how_links_and_stories_were_made(
    make_client: Client, trees: FakeTrees
) -> None:
    body = make_client().get("/stories/10/tree").json()

    assert body["linking"] == {
        "run_id": 5,
        "threshold": 0.75,
        "window_days": 14,
        "created_at": "2026-10-27T10:35:00Z",
    }
    assert body["grouping"]["threshold"] == 0.88
    assert body["grouping"]["encoder_version"] == "encoder-v1"


def test_a_node_has_headline_link_and_date_per_outlet_and_never_a_lead_or_a_party(
    make_client: Client, trees: FakeTrees
) -> None:
    body = make_client().get("/stories/10/tree").json()

    node = body["nodes"][0]
    assert set(node) == {"story_id", "parent_story_id", "link_similarity", "started_at", "articles"}
    assert set(node["articles"][0]) == {
        "outlet_id",
        "outlet_name",
        "headline",
        "url",
        "published_at",
    }
    assert [a["outlet_id"] for a in node["articles"]] == ["a", "b"]


def test_a_story_with_no_relations_answers_404(make_client: Client, trees: FakeTrees) -> None:
    response = make_client().get("/stories/777/tree")

    assert response.status_code == 404
    assert "no relations" in response.json()["detail"]


def test_before_any_linking_run_the_answer_is_404(make_client: Client) -> None:
    assert make_client().get("/stories/10/tree").status_code == 404
