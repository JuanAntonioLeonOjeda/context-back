"""GET /communities/{id}/voters with two municipalities whose numbers are worked out by hand.

38038: census 200, income 14,000, valid 200 (PP 120, CC 80). 35016: census 300, income 15,000,
valid 200 (blank 10, PP 100, CC 60, LISTA X 30). In income order the census midpoints are 100 and
350 of 500: bands floor(5·100/500) = 1 and floor(5·350/500) = 3.
"""

from collections.abc import Callable
from decimal import Decimal

from fastapi.testclient import TestClient

from datos.voters.application.community_voters import CandidatureCount, MunicipalRow

type Client = Callable[..., TestClient]


def test_names_the_election_and_the_dimension_with_their_sources(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-05/voters").json()

    assert body["election"]["id"] == "congreso-2023-07"
    assert body["election"]["source_url"].startswith("https://infoelectoral.interior.gob.es/")
    dimension = body["dimension"]
    assert (dimension["id"], dimension["unit"], dimension["year"]) == (
        "income",
        "eur_per_person",
        2023,
    )
    # The statistic's page, which a reader can open; not the request the loader made.
    assert dimension["source_url"].startswith("https://www.ine.es/dyngs/INEbase/")
    assert "wstempus" not in dimension["source_url"]
    assert body["municipalities"] == 2
    assert body["no_profile_reason"] is None


def test_groups_are_ordered_by_label_with_a_candidature_by_its_acronym_and_others_last(
    make_client: Client,
) -> None:
    groups = make_client().get("/communities/ccaa-05/voters").json()["profile"]["groups"]

    assert [(g["id"], g["kind"], g["label"]) for g in groups] == [
        ("coalicion-canaria", "party", "CC"),
        ("lista:LISTA X", "candidature", "LISTA X"),
        ("pp", "party", "PP"),
        ("otras", "others", None),
    ]


def test_each_municipality_lands_in_its_band_with_hand_computed_shares(
    make_client: Client,
) -> None:
    bands = make_client().get("/communities/ccaa-05/voters").json()["profile"]["bands"]

    assert [b["municipalities"] for b in bands] == [0, 1, 0, 1, 0]
    low, high = bands[1], bands[3]
    assert (low["census_percent"], low["value_min"], low["valid_votes"]) == (
        40.0,
        14000.0,
        200,
    )
    assert [s["percent"] for s in low["shares"]] == [40.0, 0.0, 60.0, 0.0]
    assert (high["census_percent"], high["blank_percent"]) == (60.0, 5.0)
    assert [(s["group_id"], s["percent"]) for s in high["shares"]] == [
        ("coalicion-canaria", 30.0),
        ("lista:LISTA X", 15.0),
        ("pp", 50.0),
        ("otras", 0.0),
    ]


def test_an_empty_band_has_zeros_and_no_value_range(make_client: Client) -> None:
    empty = make_client().get("/communities/ccaa-05/voters").json()["profile"]["bands"][0]

    assert (empty["census"], empty["census_percent"], empty["value_min"]) == (0, 0.0, None)
    assert all(s["percent"] == 0.0 for s in empty["shares"])


def test_the_size_of_a_municipality_groups_by_electors_at_fixed_limits(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-05/voters?by=size").json()

    # No INE download behind it: the size is the census of the election's own files.
    assert body["dimension"] == {
        "id": "size",
        "unit": "electors",
        "source_url": None,
        "year": None,
        "fetched_at": None,
    }
    bands = body["profile"]["bands"]
    # Four bands (limits 1,500, 8,000 and 40,000 electors); both municipalities, of 200 and 300
    # electors, are in the first one, whatever their income.
    assert [b["municipalities"] for b in bands] == [2, 0, 0, 0]
    first = bands[0]
    assert (first["census"], first["census_percent"], first["value_min"], first["value_max"]) == (
        500,
        100.0,
        200.0,
        300.0,
    )
    # Valid votes 400 (blank 10): CC 140, LISTA X 30, PP 220.
    assert first["blank_percent"] == 2.5
    assert [(s["group_id"], s["percent"]) for s in first["shares"]] == [
        ("coalicion-canaria", 35.0),
        ("lista:LISTA X", 7.5),
        ("pp", 55.0),
        ("otras", 0.0),
    ]
    assert bands[2]["value_min"] is None


def test_an_unknown_dimension_is_a_422_that_names_the_allowed_ones(make_client: Client) -> None:
    response = make_client().get("/communities/ccaa-05/voters?by=age")

    assert response.status_code == 422
    assert "'income', 'size' or 'education'" in response.json()["detail"][0]["msg"]


def test_the_contract_lists_the_dimensions_and_defaults_to_income(make_client: Client) -> None:
    contract = make_client().get("/openapi.json").json()

    parameters = contract["paths"]["/communities/{territory_id}/voters"]["get"]["parameters"]
    by = next(p for p in parameters if p["name"] == "by")
    assert by["schema"]["default"] == "income"
    assert contract["components"]["schemas"]["DimensionId"]["enum"] == [
        "income",
        "size",
        "education",
    ]


def test_a_community_without_results_has_no_profile_and_says_why(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-13/voters").json()

    assert body["profile"] is None
    assert body["no_profile_reason"] == "no_results"


def test_a_community_of_one_municipality_has_no_profile_and_says_why(
    make_client: Client,
) -> None:
    ceuta_like = [
        MunicipalRow("35016", 300, 0, Decimal("15000"), (CandidatureCount("000005", "PP", 300),))
    ]

    body = make_client(voter_rows=ceuta_like).get("/communities/ccaa-05/voters").json()

    assert (body["profile"], body["no_profile_reason"]) == (None, "too_few_municipalities")


def test_unknown_community_or_election_is_404(make_client: Client) -> None:
    client = make_client()

    assert client.get("/communities/ccaa-99/voters").status_code == 404
    missing = client.get("/communities/ccaa-05/voters?election=congreso-2019-11")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "no election congreso-2019-11"}


def test_the_contract_declares_the_404_and_its_body(make_client: Client) -> None:
    contract = make_client().get("/openapi.json").json()

    not_found = contract["paths"]["/communities/{territory_id}/voters"]["get"]["responses"]["404"]
    schema = not_found["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/NotFoundOut"}
    assert set(contract["components"]["schemas"]["NotFoundOut"]["properties"]) == {"detail"}


def test_says_from_which_share_a_group_is_shown_with_or_without_a_profile(
    make_client: Client,
) -> None:
    client = make_client()

    assert client.get("/communities/ccaa-05/voters").json()["shown_from_percent"] == 3
    assert client.get("/communities/ccaa-13/voters").json()["shown_from_percent"] == 3


def test_groups_follow_the_label_a_reader_sees_not_their_ids(make_client: Client) -> None:
    # By id: "coalicion-canaria" < "lista:ZETA" < "pp". By label: "CC" < "PP" < "ZETA".
    rows = [
        MunicipalRow(
            "35016",
            300,
            0,
            Decimal("15000"),
            (
                CandidatureCount("000005", "PP", 100),
                CandidatureCount("000031", "CCa", 100),
                CandidatureCount("000098", "ZETA", 100),
            ),
        ),
        MunicipalRow("38038", 200, 0, Decimal("14000"), (CandidatureCount("000005", "PP", 200),)),
    ]

    groups = make_client(voter_rows=rows).get("/communities/ccaa-05/voters").json()["profile"]
    assert [g["label"] for g in groups["groups"]] == ["CC", "PP", "ZETA", None]
