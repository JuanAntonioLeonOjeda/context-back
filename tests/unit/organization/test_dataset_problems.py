"""Every reason not to load the organisation files, from a small dataset that is sound."""

from dataclasses import replace
from datetime import date

from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence
from datos.organization.domain.dataset import dataset_problems

SOURCE = "https://example.org/source"
TERRITORIES = {"es", "ccaa-05", "ccaa-13"}
SECTORS = {"health", "housing"}


def _body(
    id_: str,
    kind: BodyKind,
    level: BodyLevel,
    territory: str | None,
    parent: str | None = None,
    dir3: str | None = None,
) -> Body:
    return Body(id_, kind, level, territory, f"Name of {id_}", parent, dir3, SOURCE)


HEAD_ES = _body("es-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.STATE, "es")
HACIENDA = _body(
    "es-hacienda", BodyKind.DEPARTMENT, BodyLevel.STATE, "es", "es-gobierno", dir3="E05250001"
)
CORTES = _body("es-cortes", BodyKind.PARLIAMENT, BodyLevel.STATE, "es")
HEAD_13 = _body("ccaa-13-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.CCAA, "ccaa-13")
SANIDAD = _body(
    "ccaa-13-sanidad", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", "ccaa-13-gobierno"
)
TSJ = _body("ccaa-13-tsj", BodyKind.JUDICIARY, BodyLevel.STATE, "ccaa-13")
AYUNTAMIENTO = _body("local-ayuntamiento", BodyKind.LOCAL, BodyLevel.LOCAL, None)
CABILDO = _body("ccaa-05-cabildo", BodyKind.LOCAL, BodyLevel.LOCAL, "ccaa-05")
BODIES = [HEAD_ES, HACIENDA, CORTES, HEAD_13, SANIDAD, TSJ, AYUNTAMIENTO, CABILDO]


def _holder(body_id: str, name: str, valid_from: date, valid_to: date | None = None) -> Holder:
    return Holder(body_id, "Post", name, valid_from, valid_to, SOURCE)


START = date(2023, 6, 17)
HOLDERS = [_holder(b.id, f"Holder {b.id}", START) for b in (HEAD_ES, HACIENDA, HEAD_13, SANIDAD)]
COMPETENCES = [
    Competence("es-cortes", "Passes the State's laws", "CE art. 66", ("health",), SOURCE)
]


def _problems(
    bodies: list[Body] | None = None,
    holders: list[Holder] | None = None,
    competences: list[Competence] | None = None,
) -> list[str]:
    return dataset_problems(
        BODIES if bodies is None else bodies,
        HOLDERS if holders is None else holders,
        COMPETENCES if competences is None else competences,
        territory_ids=TERRITORIES,
        sector_ids=SECTORS,
    )


def _swap(old: Body, new: Body) -> list[Body]:
    """The sound bodies with `old` replaced by `new`."""
    return [new if b is old else b for b in BODIES]


def test_a_sound_dataset_has_no_problems() -> None:
    assert _problems() == []


# --- bodies --------------------------------------------------------------------------


def test_a_repeated_id_and_a_repeated_dir3_code_are_reported() -> None:
    twin = replace(CORTES, id="es-cortes", name="Another")
    shares_dir3 = replace(CORTES, id="es-senado", dir3_id="E05250001")

    assert _problems(bodies=[*BODIES, twin]) == ["body es-cortes: the id is repeated"]
    assert _problems(bodies=[*BODIES, shares_dir3]) == ["body es-senado: the DIR3 code is repeated"]


def test_an_unknown_territory_and_a_malformed_dir3_code_are_reported() -> None:
    assert _problems(
        bodies=_swap(CABILDO, replace(CABILDO, territory_id="ccaa-99", id="ccaa-99-cabildo"))
    ) == ["body ccaa-99-cabildo: unknown territory ccaa-99"]
    assert _problems(bodies=_swap(HACIENDA, replace(HACIENDA, dir3_id="e05"))) == [
        "body es-hacienda: the DIR3 code 'e05' is not one"
    ]


def test_the_level_the_territory_and_the_id_must_fit_one_another() -> None:
    cases = {
        "only a local body can have no territory": _swap(
            CORTES, replace(CORTES, territory_id=None, id="local-cortes")
        ),
        "a local body has no territory or belongs to a community": _swap(
            CABILDO, replace(CABILDO, territory_id="es", id="es-cabildo")
        ),
        "a body of a community belongs to a community": _swap(
            HEAD_13, replace(HEAD_13, territory_id="es", id="es-gobierno-ccaa")
        ),
        "a State body belongs to the State, except a court": _swap(
            CORTES, replace(CORTES, territory_id="ccaa-13", id="ccaa-13-cortes")
        ),
        "a body with a holder is not a local body": _swap(
            HEAD_13, replace(HEAD_13, level=BodyLevel.LOCAL)
        ),
        "the id must start with ccaa-13-": _swap(SANIDAD, replace(SANIDAD, id="sanidad")),
        "the id must start with local-": _swap(
            AYUNTAMIENTO, replace(AYUNTAMIENTO, id="ayuntamiento")
        ),
    }
    for expected, bodies in cases.items():
        assert any(expected in problem for problem in _problems(bodies=bodies)), expected


def test_a_court_may_sit_in_a_community_and_a_cabildo_belongs_to_its_own() -> None:
    # The sound dataset already has both: no problem.
    assert [b.id for b in BODIES if b.id in ("ccaa-13-tsj", "ccaa-05-cabildo")] == [
        "ccaa-13-tsj",
        "ccaa-05-cabildo",
    ]
    assert _problems() == []


def test_a_department_needs_an_executive_head_of_its_own_territory_as_parent() -> None:
    cases = {
        "a department needs a parent": _swap(SANIDAD, replace(SANIDAD, parent_id=None)),
        "it is its own parent": _swap(SANIDAD, replace(SANIDAD, parent_id="ccaa-13-sanidad")),
        "the parent ccaa-99-x does not exist": _swap(
            SANIDAD, replace(SANIDAD, parent_id="ccaa-99-x")
        ),
        "the parent es-cortes is not an executive head": _swap(
            SANIDAD, replace(SANIDAD, parent_id="es-cortes")
        ),
        "the parent es-gobierno belongs to another territory": _swap(
            SANIDAD, replace(SANIDAD, parent_id="es-gobierno")
        ),
    }
    for expected, bodies in cases.items():
        assert any(expected in problem for problem in _problems(bodies=bodies)), expected


def test_two_executive_heads_in_one_territory_are_reported_with_their_ids() -> None:
    second = _body("ccaa-13-otro", BodyKind.EXECUTIVE_HEAD, BodyLevel.CCAA, "ccaa-13")

    assert _problems(bodies=[*BODIES, second]) == [
        "territory ccaa-13: more than one executive head (ccaa-13-gobierno, ccaa-13-otro)"
    ]


# --- holders -------------------------------------------------------------------------


def test_a_holder_needs_a_body_that_exists_and_can_have_one() -> None:
    nobody = _holder("ccaa-13-nada", "A", START)
    on_parliament = _holder("es-cortes", "B", START)

    assert _problems(holders=[*HOLDERS, nobody]) == [
        "holder A of ccaa-13-nada from 2023-06-17: the body does not exist"
    ]
    assert _problems(holders=[*HOLDERS, on_parliament]) == [
        "holder B of es-cortes from 2023-06-17: a parliament has no holder"
    ]


def test_an_empty_period_is_reported() -> None:
    empty = _holder("ccaa-13-sanidad", "Z", date(2020, 1, 1), date(2020, 1, 1))

    assert "the period is empty" in "".join(_problems(holders=[*HOLDERS[:3], empty]))


def test_the_day_of_the_change_is_not_an_overlap_but_one_more_day_is() -> None:
    first = _holder("ccaa-13-sanidad", "First", date(2020, 1, 1), date(2023, 6, 17))
    ok = _holder("ccaa-13-sanidad", "Second", date(2023, 6, 17))
    late = _holder("ccaa-13-sanidad", "Second", date(2023, 6, 16))
    base = HOLDERS[:3]

    assert _problems(holders=[*base, first, ok]) == []
    assert _problems(holders=[*base, first, late]) == [
        "holders of ccaa-13-sanidad: First and Second overlap"
    ]


def test_a_period_without_an_end_overlaps_every_later_one() -> None:
    open_ended = _holder("ccaa-13-sanidad", "Open", date(2020, 1, 1))
    later = _holder("ccaa-13-sanidad", "Later", date(2030, 1, 1))

    assert _problems(holders=[*HOLDERS[:3], open_ended, later]) == [
        "holders of ccaa-13-sanidad: Open and Later overlap"
    ]


def test_a_long_period_is_compared_with_every_later_one_and_not_only_the_previous() -> None:
    long = _holder("ccaa-13-sanidad", "Long", date(2020, 1, 1), date(2030, 1, 1))
    short = _holder("ccaa-13-sanidad", "Short", date(2021, 1, 1), date(2022, 1, 1))
    after = _holder("ccaa-13-sanidad", "After", date(2023, 1, 1), date(2024, 1, 1))

    assert _problems(holders=[*HOLDERS[:3], long, short, after]) == [
        "holders of ccaa-13-sanidad: Long and Short overlap",
        "holders of ccaa-13-sanidad: Long and After overlap",
    ]


def test_a_vacant_stretch_between_two_holders_is_not_a_problem() -> None:
    first = _holder("ccaa-13-sanidad", "First", date(2020, 1, 1), date(2021, 1, 1))
    second = _holder("ccaa-13-sanidad", "Second", date(2022, 1, 1))

    assert _problems(holders=[*HOLDERS[:3], first, second]) == []


# --- competences ---------------------------------------------------------------------


def test_a_competence_needs_a_body_and_at_least_one_known_sector_listed_once() -> None:
    def competence(body_id: str, sectors: tuple[str, ...]) -> Competence:
        return Competence(body_id, "Passes laws", "Art. 1", sectors, SOURCE)

    cases = {
        "the body does not exist": competence("ccaa-13-nada", ("health",)),
        "it relates to no sector": competence("es-cortes", ()),
        "unknown sector nowhere": competence("es-cortes", ("nowhere",)),
        "sector health is repeated": competence("es-cortes", ("health", "health")),
    }
    for expected, bad in cases.items():
        assert any(expected in p for p in _problems(competences=[bad])), expected


def test_the_same_competence_of_a_body_listed_twice_is_reported_once_for_the_repeat() -> None:
    first = Competence("es-cortes", "Passes laws", "Art. 1", ("health",), SOURCE)
    same_text_other_body = replace(first, body_id="ccaa-13-tsj")
    other_text = replace(first, summary="Controls the government")

    assert _problems(competences=[first, same_text_other_body, other_text]) == []
    problems = _problems(competences=[first, first])
    assert [p for p in problems if "listed twice" in p] == [
        "competence of es-cortes ('Passes laws'): it is listed twice"
    ]


def test_every_problem_of_every_file_is_reported_at_once() -> None:
    problems = _problems(
        bodies=_swap(SANIDAD, replace(SANIDAD, parent_id=None)),
        holders=[*HOLDERS, _holder("es-cortes", "B", START)],
        competences=[Competence("es-cortes", "S", "A", (), SOURCE)],
    )

    assert len(problems) == 3
    assert problems[0].startswith("body ")
    assert problems[1].startswith("holder ")
    assert problems[2].startswith("competence ")
