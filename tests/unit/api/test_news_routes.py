from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from datos.governments.domain.competence import Competence, CompetenceFunction, CompetenceLevel
from datos.news.application.community_news import ClassifiedArticle

Client = Callable[..., TestClient]
STATE, CCAA = CompetenceLevel.STATE, CompetenceLevel.CCAA
SPAIN = ZoneInfo("Europe/Madrid")


class RecordsQuery(Protocol):  # the `news_reader` fixture (conftest.FakeNews)
    last_query: dict[str, object]


HEALTH = [
    Competence(
        "health",
        "primary_care",
        "Primary care",
        CCAA,
        CompetenceFunction.EXECUTION,
        None,
        "Statute art. 141",
        "https://www.boe.es/ccaa",
    ),
    Competence(
        "health",
        "primary_care",
        "Primary care",
        STATE,
        CompetenceFunction.BASIC_LEGISLATION,
        None,
        "CE art. 149.1.16",
        "https://www.boe.es/ce",
    ),
]


def article(
    *,
    published_at: datetime = datetime(2026, 10, 12, 9, 0, tzinfo=UTC),
    levels: frozenset[CompetenceLevel] = frozenset({CCAA}),
    outlet_id: str = "outlet-a",
) -> ClassifiedArticle:
    return ClassifiedArticle(
        article_id=1,
        outlet_id=outlet_id,
        outlet_name="Outlet A",
        headline="El Gobierno de Canarias amplía la atención primaria",
        url="https://outlet-a.example/1",
        published_at=published_at,
        levels=levels,
        model_id="rules",
        model_version="216d8cbc0b67",
    )


def test_an_item_has_headline_link_date_classifier_and_never_the_lead(make_client: Client) -> None:
    body = (
        make_client(articles=[article()], competences=HEALTH)
        .get("/communities/ccaa-05/news?sector=health")
        .json()
    )

    [item] = body["items"]
    assert set(item) == {
        "outlet_id",
        "outlet_name",
        "headline",
        "url",
        "published_at",
        "classified_by",
        "attribution",
    }
    assert item["classified_by"] == {"model_id": "rules", "model_version": "216d8cbc0b67"}
    assert (body["territory_id"], body["sector_id"]) == ("ccaa-05", "health")


def test_a_named_regional_government_gives_its_governing_parties_with_the_basis(
    make_client: Client,
) -> None:
    body = (
        make_client(articles=[article()], competences=HEALTH)
        .get("/communities/ccaa-05/news?sector=health")
        .json()
    )

    [entry] = body["items"][0]["attribution"]
    assert entry["confidence"] == "high"
    assert (entry["level"], entry["territory_id"]) == ("ccaa", "ccaa-05")
    assert entry["party_ids"] == ["coalicion-canaria", "pp"]  # never ASG, external support
    assert [c["legal_basis"] for c in entry["competences"]] == ["Statute art. 141"]
    assert entry["reason"] is None


def test_an_article_that_names_no_government_is_not_determined_with_its_reason(
    make_client: Client,
) -> None:
    body = (
        make_client(articles=[article(levels=frozenset())], competences=HEALTH)
        .get("/communities/ccaa-05/news?sector=health")
        .json()
    )

    [entry] = body["items"][0]["attribution"]
    assert (entry["confidence"], entry["reason"]) == ("not_determined", "no_level_named")
    assert entry["party_ids"] == []


def test_the_government_is_the_one_in_force_on_the_publication_day_in_spain(
    make_client: Client,
) -> None:
    # 00:30 in Spain on the day the new Canarian government starts is still the 13th in UTC.
    published = datetime(2023, 7, 14, 0, 30, tzinfo=SPAIN)
    body = (
        make_client(
            articles=[article(published_at=published)], competences=HEALTH, today=date(2023, 7, 20)
        )
        .get("/communities/ccaa-05/news?sector=health")
        .json()
    )

    [entry] = body["items"][0]["attribution"]
    assert entry["party_ids"] == ["coalicion-canaria", "pp"]
    assert entry["is_caretaker"] is False


def test_the_reader_is_asked_for_30_days_in_spain_5_per_outlet_and_the_active_classifier(
    make_client: Client, news_reader: RecordsQuery
) -> None:
    body = (
        make_client(today=date(2026, 10, 14)).get("/communities/ccaa-05/news?sector=housing").json()
    )

    assert body["since"] == "2026-09-15"
    assert body["items"] == []
    assert news_reader.last_query == {
        "territory_id": "ccaa-05",
        "sector_id": "housing",
        "since": datetime(2026, 9, 15, tzinfo=SPAIN),
        "model_id": "rules",
        "per_outlet": 5,
    }


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
