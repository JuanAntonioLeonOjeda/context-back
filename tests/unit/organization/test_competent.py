"""Which bodies a news item names, from its classification and the charts (ADR-0027)."""

from datetime import date

from datos.organization.domain.body import Body, BodyKind, BodyLevel
from datos.organization.domain.boxes import Competence
from datos.organization.domain.competent import NewsTopic, competent_bodies, levels_for

DAY = date(2026, 11, 20)
TABLE = {
    "health": frozenset({BodyLevel.STATE, BodyLevel.CCAA}),
    "housing": frozenset({BodyLevel.STATE, BodyLevel.CCAA, BodyLevel.LOCAL}),
}


def _body(
    body_id: str,
    level: BodyLevel,
    territory: str | None,
    kind: BodyKind = BodyKind.DEPARTMENT,
    **period: date,
) -> Body:
    return Body(body_id, kind, level, territory, body_id.title(), None, None, "https://x", **period)


BODIES = [
    _body("es-sanidad", BodyLevel.STATE, "es"),
    _body("es-vivienda", BodyLevel.STATE, "es"),
    _body("ccaa-05-sanidad", BodyLevel.CCAA, "ccaa-05"),
    _body("ccaa-13-sanidad", BodyLevel.CCAA, "ccaa-13"),
    _body("ccaa-05-obras-publicas", BodyLevel.CCAA, "ccaa-05"),
    _body("local-ayuntamiento", BodyLevel.LOCAL, None, BodyKind.LOCAL),
    _body("ccaa-05-parlamento", BodyLevel.CCAA, "ccaa-05", BodyKind.PARLIAMENT),
]
COMPETENCES = [
    Competence(body.id, "", "", (sector,), "https://x")
    for body, sector in [
        (BODIES[0], "health"),
        (BODIES[1], "housing"),
        (BODIES[2], "health"),
        (BODIES[3], "health"),
        (BODIES[4], "housing"),
        (BODIES[5], "housing"),
        (BODIES[6], "health"),  # a parliament legislates on health, but does not manage it
    ]
]


def _topic(
    sectors: set[str], communities: set[str], levels: set[BodyLevel] | None = None
) -> NewsTopic:
    return NewsTopic(frozenset(communities), frozenset(sectors), frozenset(levels or ()), DAY)


def _ids(topic: NewsTopic, bodies: list[Body] = BODIES) -> list[tuple[str, str, bool]]:
    return [
        (c.body.id, c.sector_id, c.shared)
        for c in competent_bodies(topic, bodies, COMPETENCES, TABLE)
    ]


def test_a_news_item_with_its_level_names_the_body_of_that_level_and_its_community() -> None:
    topic = _topic({"health"}, {"ccaa-05"}, {BodyLevel.CCAA})

    assert _ids(topic) == [("ccaa-05-sanidad", "health", False)]


def test_with_no_level_it_names_the_levels_of_the_competence_table_and_says_they_are_shared() -> (
    None
):
    topic = _topic({"health"}, {"ccaa-05"})

    assert _ids(topic) == [("es-sanidad", "health", True), ("ccaa-05-sanidad", "health", True)]


def test_a_community_body_is_named_only_for_a_news_item_of_its_community() -> None:
    assert ("ccaa-13-sanidad", "health", True) not in _ids(_topic({"health"}, {"ccaa-05"}))
    # A news item of no community reaches only the State's body.
    assert _ids(_topic({"health"}, set())) == [("es-sanidad", "health", True)]


def test_a_news_item_of_two_communities_names_both_bodies() -> None:
    ids = _ids(_topic({"health"}, {"ccaa-05", "ccaa-13"}, {BodyLevel.CCAA}))

    assert ids == [("ccaa-05-sanidad", "health", False), ("ccaa-13-sanidad", "health", False)]


def test_the_generic_local_body_is_named_at_the_local_level() -> None:
    ids = _ids(_topic({"housing"}, {"ccaa-05"}))

    assert ids == [
        ("es-vivienda", "housing", True),
        ("ccaa-05-obras-publicas", "housing", True),
        ("local-ayuntamiento", "housing", True),
    ]


def test_only_a_department_or_a_local_body_is_named_never_a_parliament() -> None:
    ids = _ids(_topic({"health"}, {"ccaa-05"}, {BodyLevel.CCAA}))

    assert all(body_id != "ccaa-05-parlamento" for body_id, _, _ in ids)


def test_a_body_not_in_force_on_the_publication_day_is_not_named() -> None:
    gone = _body("ccaa-05-sanidad", BodyLevel.CCAA, "ccaa-05", valid_to=DAY)  # ended that day
    later = _body("ccaa-05-sanidad", BodyLevel.CCAA, "ccaa-05", valid_from=date(2026, 11, 21))
    topic = _topic({"health"}, {"ccaa-05"}, {BodyLevel.CCAA})

    assert _ids(topic, [gone]) == []
    assert _ids(topic, [later]) == []


def test_each_sector_of_the_news_item_names_its_own_bodies_in_sector_order() -> None:
    ids = _ids(_topic({"housing", "health"}, {"ccaa-05"}, {BodyLevel.CCAA}))

    assert ids == [
        ("ccaa-05-sanidad", "health", False),
        ("ccaa-05-obras-publicas", "housing", False),
    ]


def test_no_sector_or_a_sector_the_table_does_not_know_names_nothing() -> None:
    assert _ids(_topic(set(), {"ccaa-05"})) == []
    assert _ids(_topic({"justice"}, {"ccaa-05"})) == []


def test_the_levels_are_the_news_items_own_when_it_has_them() -> None:
    topic = _topic({"health"}, {"ccaa-05"}, {BodyLevel.STATE})

    assert levels_for("health", topic, TABLE) == (frozenset({BodyLevel.STATE}), False)
