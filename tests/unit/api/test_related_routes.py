"""`GET /articles/{id}/related`: the chain by day, its settings, and what is never returned."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from fastapi.testclient import TestClient

from datos.stories.domain.related import Candidate, NewsItem


class FakeRelated(Protocol):  # the `related_reader` fixture (conftest.FakeRelated)
    found: dict[int, list[Candidate]]


type Client = Callable[..., TestClient]


def _item(number: int, day: int, outlet: str = "el-mundo") -> NewsItem:
    return NewsItem(
        number,
        outlet,
        f"Titular {number}",
        datetime(2026, 11, day, 9, tzinfo=UTC),
        outlet.upper(),
        f"https://{outlet}.example/{number}",
    )


def test_the_chain_comes_by_day_with_each_similarity_and_the_settings(
    make_client: Client, related_reader: FakeRelated
) -> None:
    related_reader.found = {
        10: [Candidate(_item(11, 16), 0.8812, 0.88)],
        11: [Candidate(_item(12, 5, "abc"), 0.75, 0.70)],
    }

    body = make_client().get("/articles/10/related").json()

    assert body["article_id"] == 10
    assert body["settings"] == {
        "step_threshold": 0.7,
        "origin_threshold": 0.65,
        "window_days": 14,
        "max_days": 8,
    }
    assert [(d["day"], [i["article_id"] for i in d["items"]]) for d in body["days"]] == [
        ("2026-11-16", [10, 11]),
        ("2026-11-05", [12]),
    ]
    first, second = body["days"][0]["items"]
    assert first["similarity"] is None
    assert second["similarity"] == 0.881  # three decimals, as the trees
    assert set(second) == {
        "article_id",
        "outlet_id",
        "outlet_name",
        "headline",
        "url",
        "published_at",
        "similarity",
    }


def test_an_item_with_nothing_related_answers_itself_alone(make_client: Client) -> None:
    body = make_client().get("/articles/10/related").json()

    assert [[i["article_id"] for i in d["items"]] for d in body["days"]] == [[10]]


def test_an_unknown_article_is_a_404(make_client: Client) -> None:
    response = make_client().get("/articles/999/related")

    assert response.status_code == 404
    assert response.json() == {"detail": "no article 999"}


def test_the_contract_never_offers_the_lead_or_a_vector(make_client: Client) -> None:
    contract = make_client().get("/openapi.json").json()

    fields = contract["components"]["schemas"]["RelatedItemOut"]["properties"]
    assert not {"lead", "embedding", "vector", "party_id"} & set(fields)
