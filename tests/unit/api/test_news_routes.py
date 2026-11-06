from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from datos.news.application.community_news import ClassifiedArticle

Client = Callable[..., TestClient]
SPAIN = ZoneInfo("Europe/Madrid")


class RecordsQuery(Protocol):  # the `news_reader` fixture (conftest.FakeNews)
    last_query: dict[str, object]


def article(
    *,
    published_at: datetime = datetime(2026, 10, 12, 9, 0, tzinfo=UTC),
    outlet_id: str = "outlet-a",
) -> ClassifiedArticle:
    return ClassifiedArticle(
        article_id=1,
        outlet_id=outlet_id,
        outlet_name="Outlet A",
        headline="El Gobierno de Canarias amplía la atención primaria",
        url="https://outlet-a.example/1",
        published_at=published_at,
        model_id="rules",
        model_version="216d8cbc0b67",
    )


def test_an_item_has_headline_link_date_classifier_and_never_a_party_or_the_lead(
    make_client: Client,
) -> None:
    body = make_client(articles=[article()]).get("/communities/ccaa-05/news?sector=health").json()

    [item] = body["items"]
    assert set(item) == {
        "outlet_id",
        "outlet_name",
        "headline",
        "url",
        "published_at",
        "classified_by",
        "tree_story_id",
    }  # no party, no lead (ADR-0018, sources audit)
    assert item["classified_by"] == {"model_id": "rules", "model_version": "216d8cbc0b67"}
    assert (body["territory_id"], body["sector_id"]) == ("ccaa-05", "health")


def test_without_dates_the_reader_is_asked_for_the_last_3_days_in_spain(
    make_client: Client, news_reader: RecordsQuery
) -> None:
    body = (
        make_client(today=date(2026, 10, 14)).get("/communities/ccaa-05/news?sector=housing").json()
    )

    assert (body["since"], body["until"]) == ("2026-10-08", "2026-10-14")
    assert body["items"] == []
    assert news_reader.last_query == {
        "territory_id": "ccaa-05",
        "sector_id": "housing",
        "since": datetime(2026, 10, 8, tzinfo=SPAIN),
        "until": datetime(2026, 10, 15, tzinfo=SPAIN),  # the end of the last day, excluded
        "model_id": "rules",
        "per_outlet_per_day": 5,
    }


def test_a_range_of_dates_is_passed_to_the_reader_with_both_days_included(
    make_client: Client, news_reader: RecordsQuery
) -> None:
    body = (
        make_client(today=date(2026, 10, 14))
        .get("/communities/ccaa-05/news?sector=health&date_from=2026-10-01&date_to=2026-10-03")
        .json()
    )

    assert (body["since"], body["until"]) == ("2026-10-01", "2026-10-03")
    assert news_reader.last_query["since"] == datetime(2026, 10, 1, tzinfo=SPAIN)
    assert news_reader.last_query["until"] == datetime(2026, 10, 4, tzinfo=SPAIN)


def test_only_the_first_day_means_until_today_and_only_the_last_means_a_week_back(
    make_client: Client,
) -> None:
    client = make_client(today=date(2026, 10, 14))

    only_from = client.get("/communities/ccaa-05/news?sector=health&date_from=2026-10-10").json()
    only_to = client.get("/communities/ccaa-05/news?sector=health&date_to=2026-10-05").json()

    assert (only_from["since"], only_from["until"]) == ("2026-10-10", "2026-10-14")
    assert (only_to["since"], only_to["until"]) == ("2026-09-29", "2026-10-05")


def test_a_backwards_or_too_long_range_or_a_bad_date_answers_422(make_client: Client) -> None:
    client = make_client(today=date(2026, 10, 14))
    base = "/communities/ccaa-05/news?sector=health"

    assert client.get(f"{base}&date_from=2026-10-05&date_to=2026-10-01").status_code == 422
    assert client.get(f"{base}&date_from=2026-09-01&date_to=2026-10-14").status_code == 422
    assert (
        client.get(f"{base}&date_from=2026-09-14&date_to=2026-10-14").status_code == 200
    )  # 31 days
    assert client.get(f"{base}&date_from=ayer").status_code == 422


def test_an_unknown_community_or_the_state_answers_404(make_client: Client) -> None:
    client = make_client()

    for territory_id in ("ccaa-99", "es"):
        response = client.get(f"/communities/{territory_id}/news?sector=health")
        assert response.status_code == 404
        assert "unknown community" in response.json()["detail"]


def test_an_unknown_or_missing_sector_answers_422(make_client: Client) -> None:
    client = make_client()

    assert client.get("/communities/ccaa-05/news?sector=transport").status_code == 422
    assert client.get("/communities/ccaa-05/news").status_code == 422


def test_the_description_points_to_the_governments_endpoint_by_its_path(
    make_client: Client,
) -> None:
    operation = (
        make_client()
        .get("/openapi.json")
        .json()["paths"]["/communities/{territory_id}/news"]["get"]
    )

    assert "`/communities/{territory_id}/governments`" in operation["description"]
    assert "built-in" not in operation["description"]


def test_an_item_says_which_story_has_the_tree_it_belongs_to_or_null(make_client: Client) -> None:
    with_tree = ClassifiedArticle(
        article_id=2,
        outlet_id="outlet-b",
        outlet_name="Outlet B",
        headline="Headline",
        url="https://outlet-b.example/2",
        published_at=datetime(2026, 10, 12, 9, 0, tzinfo=UTC),
        model_id="rules",
        model_version="216d8cbc0b67",
        tree_story_id=42,
    )

    body = (
        make_client(articles=[with_tree, article()]).get("/communities/ccaa-05/news?sector=health")
    ).json()

    assert [item["tree_story_id"] for item in body["items"]] == [42, None]


def test_trees_ask_the_reader_for_the_community_sector_and_classifier_and_name_the_tree(
    make_client: Client, news_reader: RecordsQuery
) -> None:
    tree_item = replace(article(), tree_story_id=37)

    response = make_client(articles=[tree_item]).get("/communities/ccaa-05/trees?sector=health")

    assert response.status_code == 200
    body = response.json()
    assert (body["territory_id"], body["sector_id"]) == ("ccaa-05", "health")
    assert [i["tree_story_id"] for i in body["items"]] == [37]
    assert set(body["items"][0]) >= {"headline", "url", "published_at", "outlet_name"}
    assert news_reader.last_query == {
        "territory_id": "ccaa-05",
        "sector_id": "health",
        "model_id": "rules",
    }


def test_trees_of_an_unknown_community_or_sector_are_refused(make_client: Client) -> None:
    client = make_client()

    assert client.get("/communities/ccaa-99/trees?sector=health").status_code == 404
    assert client.get("/communities/ccaa-05/trees?sector=nope").status_code == 422
