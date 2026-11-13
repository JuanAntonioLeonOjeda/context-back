"""The boxes with no holder and the competences of a body, with cases worked out by hand."""

import pytest

from datos.organization.domain.body import Body, BodyKind, BodyLevel
from datos.organization.domain.boxes import Competence, boxes, competences_of

SOURCE = "https://example.org/source"


def _body(
    id_: str, kind: BodyKind, name: str, territory: str | None, level: BodyLevel = BodyLevel.CCAA
) -> Body:
    return Body(id_, kind, level, territory, name, None, None, SOURCE)


def _competence(body_id: str, summary: str) -> Competence:
    return Competence(body_id, summary, "Article 1", ("health",), SOURCE)


PARLIAMENT_13 = _body("ccaa-13-parlamento", BodyKind.PARLIAMENT, "Asamblea", "ccaa-13")
PARLIAMENT_14 = _body("ccaa-14-parlamento", BodyKind.PARLIAMENT, "Parlamento", "ccaa-14")
STATE_COURT = _body(
    "es-tribunal", BodyKind.JUDICIARY, "Tribunal Supremo", "es", level=BodyLevel.STATE
)
TSJ_13 = _body(
    "ccaa-13-tsj", BodyKind.JUDICIARY, "Tribunal Superior", "ccaa-13", level=BodyLevel.STATE
)
CABILDO = _body("local-cabildo", BodyKind.LOCAL, "cabildo insular", None, level=BodyLevel.LOCAL)
AYUNTAMIENTO = _body(
    "local-ayuntamiento", BodyKind.LOCAL, "Ayuntamiento", None, level=BodyLevel.LOCAL
)
DIPUTACION = _body(
    "local-diputacion", BodyKind.LOCAL, "Diputación provincial", None, level=BodyLevel.LOCAL
)
CABILDO_05 = _body("ccaa-05-cabildo", BodyKind.LOCAL, "Cabildo", "ccaa-05", level=BodyLevel.LOCAL)
ALL = [
    PARLIAMENT_14,
    PARLIAMENT_13,
    STATE_COURT,
    TSJ_13,
    CABILDO,
    DIPUTACION,
    AYUNTAMIENTO,
    CABILDO_05,
]


def test_the_parliament_of_a_territory_is_its_own_and_no_other() -> None:
    result = boxes(ALL, [], kind=BodyKind.PARLIAMENT, territory_id="ccaa-13")

    assert [box.body.id for box in result] == ["ccaa-13-parlamento"]
    assert boxes(ALL, [], kind=BodyKind.PARLIAMENT, territory_id="ccaa-99") == ()


def test_a_court_in_a_community_is_not_the_states_and_the_other_way_round() -> None:
    in_community = boxes(ALL, [], kind=BodyKind.JUDICIARY, territory_id="ccaa-13")
    of_the_state = boxes(ALL, [], kind=BodyKind.JUDICIARY, territory_id="es")

    assert [box.body.id for box in in_community] == ["ccaa-13-tsj"]
    assert [box.body.id for box in of_the_state] == ["es-tribunal"]


def test_the_generic_local_bodies_belong_to_no_territory_and_come_by_name_without_case() -> None:
    result = boxes(ALL, [], kind=BodyKind.LOCAL, territory_id=None)

    # "cabildo insular" before "Diputación provincial": a plain sort puts every uppercase first.
    assert [box.body.name for box in result] == [
        "Ayuntamiento",
        "cabildo insular",
        "Diputación provincial",
    ]


def test_a_community_has_the_generic_local_bodies_and_those_that_exist_only_in_it() -> None:
    in_canarias = boxes(ALL, [], kind=BodyKind.LOCAL, territory_id="ccaa-05")
    in_madrid = boxes(ALL, [], kind=BodyKind.LOCAL, territory_id="ccaa-13")

    assert [box.body.id for box in in_canarias] == [
        "local-ayuntamiento",
        "ccaa-05-cabildo",
        "local-cabildo",
        "local-diputacion",
    ]
    assert [box.body.id for box in in_madrid] == [
        "local-ayuntamiento",
        "local-cabildo",
        "local-diputacion",
    ]


def test_two_boxes_with_the_same_name_keep_a_fixed_order_by_id() -> None:
    twin = _body("ccaa-13-aaa", BodyKind.PARLIAMENT, "Asamblea", "ccaa-13")

    result = boxes([PARLIAMENT_13, twin], [], kind=BodyKind.PARLIAMENT, territory_id="ccaa-13")

    assert [box.body.id for box in result] == ["ccaa-13-aaa", "ccaa-13-parlamento"]


def test_a_box_carries_the_competences_of_its_body_in_the_order_given() -> None:
    first = _competence("ccaa-13-parlamento", "Passes the community's laws")
    other = _competence("ccaa-14-parlamento", "Another body's competence")
    second = _competence("ccaa-13-parlamento", "Approves the budget")

    [box] = boxes(ALL, [first, other, second], kind=BodyKind.PARLIAMENT, territory_id="ccaa-13")

    assert box.competences == (first, second)
    assert competences_of([first, other, second], "ccaa-14-parlamento") == (other,)


def test_a_body_without_competences_is_still_a_box() -> None:
    [box] = boxes([PARLIAMENT_13], [], kind=BodyKind.PARLIAMENT, territory_id="ccaa-13")

    assert box.competences == ()


@pytest.mark.parametrize("kind", [BodyKind.EXECUTIVE_HEAD, BodyKind.DEPARTMENT])
def test_the_bodies_with_a_holder_come_from_the_executive_chart_not_from_here(
    kind: BodyKind,
) -> None:
    with pytest.raises(ValueError, match="executive_chart"):
        boxes(ALL, [], kind=kind, territory_id="ccaa-13")
