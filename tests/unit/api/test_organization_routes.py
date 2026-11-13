"""GET /organization and GET /communities/{id}/organization on the small dataset of conftest.

The State and Madrid have a complete executive; Canarias has a head with nobody in it, a cabildo of
its own and no department.
"""

from collections.abc import Callable
from datetime import date

from fastapi.testclient import TestClient

type Client = Callable[..., TestClient]


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def test_a_community_with_a_complete_executive_gives_its_head_and_departments_by_name(
    make_client: Client,
) -> None:
    body = make_client().get("/communities/ccaa-13/organization").json()

    assert (body["territory_id"], body["as_of"]) == ("ccaa-13", "2026-10-13")
    executive = body["executive"]
    assert executive["status"] == "complete"
    assert executive["head"]["holder"]["name"] == "Isabel Díaz Ayuso"
    assert executive["head"]["holder"]["since"] == "2023-06-17"
    # Case-insensitive, never by input order or importance: "educación" before "Sanidad".
    assert [d["name"] for d in executive["departments"]] == [
        "consejería de educación",
        "Consejería de Sanidad",
    ]
    assert [d["holder"]["name"] for d in executive["departments"]] == [
        "María Mercedes Zarzalejo Carbajo",
        "Fátima Matute Teresa",
    ]


def test_each_body_carries_its_competences_with_the_names_of_their_sectors(
    make_client: Client,
) -> None:
    executive = make_client().get("/communities/ccaa-13/organization").json()["executive"]

    sanidad = executive["departments"][1]
    [competence] = sanidad["competences"]
    assert competence["summary"] == "Salud y asistencia sanitaria."
    assert competence["legal_basis"] == "Decreto 245/2023, art. 1"
    # A sector the taxonomy has no name for keeps its id as its name.
    assert competence["sectors"] == [
        {"id": "health", "name": "Sanidad"},
        {"id": "unknown", "name": "unknown"},
    ]
    assert executive["head"]["competences"] == []
    assert executive["departments"][0]["competences"] == []


def test_a_community_has_its_parliament_and_the_court_that_sits_in_it(make_client: Client) -> None:
    body = make_client().get("/communities/ccaa-13/organization").json()

    assert [b["name"] for b in body["parliaments"]] == ["Asamblea de Madrid"]
    assert [(b["name"], b["level"]) for b in body["judiciary"]] == [
        ("Tribunal Superior de Justicia de Madrid", "state")
    ]
    assert body["parliaments"][0]["holder"] is None
    assert body["parliaments"][0]["competences"][0]["sectors"] == [
        {"id": "taxes", "name": "Impuestos"}
    ]


def test_the_local_bodies_are_the_generic_ones_and_those_of_the_community_only(
    make_client: Client,
) -> None:
    client = make_client()

    madrid = client.get("/communities/ccaa-13/organization").json()
    canarias = client.get("/communities/ccaa-05/organization").json()

    assert [b["name"] for b in madrid["local"]] == ["Ayuntamiento"]
    assert [b["name"] for b in canarias["local"]] == ["Ayuntamiento", "Cabildo insular"]


def test_an_executive_that_cannot_be_drawn_gives_no_head_and_no_departments(
    make_client: Client,
) -> None:
    executive = make_client().get("/communities/ccaa-05/organization").json()["executive"]

    assert executive == {"status": "no_data", "head": None, "departments": []}


def test_the_day_of_the_clock_decides_who_is_in_force(make_client: Client) -> None:
    client = make_client(today=date(2020, 1, 1))

    body = client.get("/communities/ccaa-13/organization").json()

    assert (body["as_of"], body["executive"]["status"]) == ("2020-01-01", "no_data")


def test_unknown_communities_and_the_state_are_not_communities(make_client: Client) -> None:
    client = make_client()

    assert client.get("/communities/ccaa-99/organization").status_code == 404
    assert client.get("/communities/es/organization").status_code == 404
    assert client.get("/communities/es/organization").json() == {"detail": "unknown community es"}


def test_the_contract_declares_the_404_of_a_community(make_client: Client) -> None:
    contract = make_client().get("/openapi.json").json()

    responses = contract["paths"]["/communities/{territory_id}/organization"]["get"]["responses"]
    assert responses["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/NotFoundOut"
    }
    assert "/organization" in contract["paths"]


def test_the_general_chart_is_the_states_with_the_generic_local_bodies_and_the_communities(
    make_client: Client,
) -> None:
    body = make_client().get("/organization").json()

    assert body["territory_id"] == "es"
    assert body["executive"]["status"] == "complete"
    assert body["executive"]["head"]["holder"]["name"] == "Pedro Sánchez Pérez-Castejón"
    assert [d["name"] for d in body["executive"]["departments"]] == ["Ministerio de Hacienda"]
    assert body["executive"]["departments"][0]["dir3_id"] == "E05250001"
    assert body["executive"]["head"]["dir3_id"] is None
    assert [b["name"] for b in body["parliaments"]] == ["Cortes Generales"]
    assert [b["name"] for b in body["judiciary"]] == ["Tribunal Supremo"]
    assert [b["name"] for b in body["local"]] == ["Ayuntamiento"]  # no cabildo: it is Canarias'


def test_the_general_chart_lists_the_communities_by_name_with_whether_they_can_be_drawn(
    make_client: Client,
) -> None:
    body = make_client().get("/organization").json()

    assert body["communities"] == [
        {"territory_id": "ccaa-05", "name": "Canarias", "executive_status": "no_data"},
        {"territory_id": "ccaa-13", "name": "Comunidad de Madrid", "executive_status": "complete"},
    ]


def test_no_party_is_given_for_anyone_anywhere(make_client: Client) -> None:
    client = make_client()

    keys = _keys(client.get("/organization").json()) | _keys(
        client.get("/communities/ccaa-13/organization").json()
    )

    assert not keys & {"party", "parties", "party_id", "party_ids", "partido", "partidos"}
