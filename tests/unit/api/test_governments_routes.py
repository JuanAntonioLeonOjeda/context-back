from collections.abc import Callable
from datetime import date

from fastapi.testclient import TestClient

Client = Callable[..., TestClient]


def test_lists_the_communities_in_ine_order_without_the_state(make_client: Client) -> None:
    response = make_client().get("/territories")

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == ["ccaa-05", "ccaa-13"]


def test_the_government_today_comes_from_the_clock(make_client: Client) -> None:
    body = make_client(today=date(2026, 10, 13)).get("/communities/ccaa-05/governments").json()

    assert body["date"] == "2026-10-13"
    assert body["term"]["valid_from"] == "2023-07-14"
    assert body["term"]["is_caretaker"] is False


def test_parties_come_alphabetically_with_their_role_and_source(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-05/governments").json()

    assert [(p["party_id"], p["role"]) for p in body["term"]["parties"]] == [
        ("asg", "external_support"),
        ("coalicion-canaria", "governing"),
        ("pp", "governing"),
    ]
    assert all(p["source_url"].startswith("https://") for p in body["term"]["parties"])
    assert body["term"]["parties"][1]["short_name"] == "CC"


def test_a_past_date_gives_the_caretaker_term_in_force_then(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-05/governments?date=2023-07-13").json()

    assert body["term"]["is_caretaker"] is True
    assert [p["party_id"] for p in body["term"]["parties"]] == ["coalicion-canaria"]


def test_the_day_a_new_term_starts_belongs_to_the_new_term(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-05/governments?date=2023-07-14").json()

    assert body["term"]["valid_from"] == "2023-07-14"


def test_a_date_before_the_dataset_answers_404_with_the_reason(make_client: Client) -> None:
    response = make_client().get("/communities/ccaa-13/governments?date=2019-01-01")

    assert response.status_code == 404
    assert "no government of ccaa-13" in response.json()["detail"]


def test_an_unknown_community_or_the_state_answers_404(make_client: Client) -> None:
    client = make_client()

    for territory_id in ("ccaa-99", "es"):
        response = client.get(f"/communities/{territory_id}/governments")
        assert response.status_code == 404
        assert "unknown community" in response.json()["detail"]


def test_an_invalid_date_answers_422(make_client: Client) -> None:
    response = make_client().get("/communities/ccaa-05/governments?date=13-10-2026")

    assert response.status_code == 422


def test_parties_lists_the_party_table(make_client: Client) -> None:
    body = make_client().get("/parties").json()

    assert [p["id"] for p in body] == ["asg", "coalicion-canaria", "pp"]
    assert set(body[0]) == {"id", "name", "short_name", "colour_hex"}


def test_the_map_lists_every_community_with_its_governing_parties_only(
    make_client: Client,
) -> None:
    body = make_client().get("/map/governments").json()

    assert body["date"] == "2026-10-13"
    assert body["communities"] == [
        {
            "territory_id": "ccaa-05",
            "governing_party_ids": ["coalicion-canaria", "pp"],
            "is_caretaker": False,
            "has_data": True,
        },
        {
            "territory_id": "ccaa-13",
            "governing_party_ids": ["pp"],
            "is_caretaker": False,
            "has_data": True,
        },
    ]


def test_the_map_on_a_date_without_data_keeps_the_community_marked(make_client: Client) -> None:
    body = make_client().get("/map/governments?date=2023-06-01").json()

    madrid = next(c for c in body["communities"] if c["territory_id"] == "ccaa-13")
    canarias = next(c for c in body["communities"] if c["territory_id"] == "ccaa-05")
    assert madrid == {
        "territory_id": "ccaa-13",
        "governing_party_ids": [],
        "is_caretaker": False,
        "has_data": False,
    }
    assert canarias["is_caretaker"] is True
