from collections.abc import Callable

from fastapi.testclient import TestClient

Client = Callable[..., TestClient]


def test_the_card_lists_every_indicator_with_its_source(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-05/indicators").json()

    assert [i["indicator_id"] for i in body] == ["poverty_or_exclusion_rate", "unemployment_rate"]
    rate = body[1]
    assert rate["latest"] == {
        "period_start": "2026-04-01",
        "year": 2026,
        "quarter": 2,
        "value": 11.6,
    }
    assert [p["value"] for p in rate["series"]] == [12.1, 11.6]
    assert rate["source"] == {
        "publisher": "INE",
        "table_id": "14506",
        "table_url": "https://www.ine.es/jaxiT3/Tabla.htm?t=14506",
        "series_code": "EPA452496",
        "fetched_at": "2026-10-13T15:48:00Z",
    }


def test_an_indicator_without_data_has_null_not_zero(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-13/indicators").json()

    assert all(i["latest"] is None and i["series"] == [] for i in body)


def test_an_unknown_community_answers_404(make_client: Client) -> None:
    response = make_client().get("/communities/es/indicators")

    assert response.status_code == 404
