"""The organisation chart of a territory, assembled from a small dataset worked out by hand."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from datos.organization.application.organization_chart import (
    OrganizationChart,
    general_chart,
    organization_chart,
)
from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Box, Competence
from datos.organization.domain.chart import ChartStatus

SOURCE = "https://example.org/source"
DAY = date(2026, 11, 13)


def _body(
    id_: str,
    kind: BodyKind,
    level: BodyLevel,
    territory: str | None,
    parent: str | None = None,
) -> Body:
    return Body(id_, kind, level, territory, f"Name of {id_}", parent, None, SOURCE)


def _holder(body_id: str) -> Holder:
    return Holder(body_id, "Post", f"Holder of {body_id}", date(2023, 6, 17), None, SOURCE)


def _competence(body_id: str, summary: str) -> Competence:
    return Competence(body_id, summary, "Art. 1", ("health",), SOURCE)


BODIES = [
    _body("es-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.STATE, "es"),
    _body("es-hacienda", BodyKind.DEPARTMENT, BodyLevel.STATE, "es", "es-gobierno"),
    _body("es-cortes", BodyKind.PARLIAMENT, BodyLevel.STATE, "es"),
    _body("es-supremo", BodyKind.JUDICIARY, BodyLevel.STATE, "es"),
    _body("ccaa-13-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.CCAA, "ccaa-13"),
    _body("ccaa-13-sanidad", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", "ccaa-13-gobierno"),
    _body("ccaa-13-asamblea", BodyKind.PARLIAMENT, BodyLevel.CCAA, "ccaa-13"),
    _body("ccaa-13-tsj", BodyKind.JUDICIARY, BodyLevel.STATE, "ccaa-13"),
    _body("ccaa-05-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.CCAA, "ccaa-05"),
    _body("ccaa-05-cabildo", BodyKind.LOCAL, BodyLevel.LOCAL, "ccaa-05"),
    _body("local-ayuntamiento", BodyKind.LOCAL, BodyLevel.LOCAL, None),
]
HOLDERS = [
    _holder(i) for i in ("es-gobierno", "es-hacienda", "ccaa-13-gobierno", "ccaa-13-sanidad")
]
COMPETENCES = [
    _competence("es-hacienda", "Taxes"),
    _competence("es-cortes", "Laws of the State"),
    _competence("ccaa-13-sanidad", "Health"),
    _competence("ccaa-13-sanidad", "Public health"),
    _competence("ccaa-13-asamblea", "Laws of the community"),
    _competence("ccaa-13-tsj", "Highest court of the community"),
    _competence("local-ayuntamiento", "Urbanism"),
    _competence("ccaa-05-cabildo", "Island government"),
]


class _Reader:
    def bodies(self) -> list[Body]:
        return list(BODIES)

    def holders(self) -> list[Holder]:
        return list(HOLDERS)

    def competences(self) -> list[Competence]:
        return list(COMPETENCES)

    def sector_names(self) -> dict[str, str]:
        return {"health": "Sanidad"}


def _chart(territory_id: str, day: date = DAY) -> OrganizationChart:
    return organization_chart(_Reader(), territory_id, day)


def _ids(boxes: Sequence[Box]) -> list[str]:
    return [box.body.id for box in boxes]


def test_a_community_chart_has_its_executive_with_the_competences_of_each_body() -> None:
    chart = _chart("ccaa-13")

    assert chart.executive.status is ChartStatus.COMPLETE
    assert chart.executive.head is not None
    assert chart.executive.head.body.id == "ccaa-13-gobierno"
    assert [s.summary for s in chart.executive_competences["ccaa-13-sanidad"]] == [
        "Health",
        "Public health",
    ]
    assert chart.executive_competences["ccaa-13-gobierno"] == ()
    assert chart.sector_names == {"health": "Sanidad"}
    assert chart.day == DAY


def test_a_community_chart_has_its_own_parliament_and_the_court_that_sits_in_it() -> None:
    chart = _chart("ccaa-13")

    assert _ids(chart.parliaments) == ["ccaa-13-asamblea"]
    assert _ids(chart.judiciary) == ["ccaa-13-tsj"]
    assert [c.summary for c in chart.parliaments[0].competences] == ["Laws of the community"]


def test_the_general_chart_is_the_states_with_the_generic_local_bodies_only() -> None:
    chart = _chart("es")

    assert chart.executive.status is ChartStatus.COMPLETE
    assert _ids(chart.parliaments) == ["es-cortes"]
    assert _ids(chart.judiciary) == ["es-supremo"]
    assert _ids(chart.local) == ["local-ayuntamiento"]


def test_a_community_has_the_generic_local_bodies_and_those_that_exist_only_in_it() -> None:
    assert _ids(_chart("ccaa-05").local) == ["ccaa-05-cabildo", "local-ayuntamiento"]
    assert _ids(_chart("ccaa-13").local) == ["local-ayuntamiento"]


def test_a_community_without_a_complete_executive_is_no_data_and_carries_no_competences() -> None:
    chart = _chart("ccaa-05")  # a head with no department and no holder

    assert chart.executive.status is ChartStatus.NO_DATA
    assert chart.executive.head is None
    assert chart.executive_competences == {}


def test_a_territory_with_no_bodies_has_an_empty_chart_but_the_generic_local_bodies() -> None:
    chart = _chart("ccaa-99")

    assert chart.executive.status is ChartStatus.NO_DATA
    assert (chart.parliaments, chart.judiciary) == ((), ())
    assert _ids(chart.local) == ["local-ayuntamiento"]


def test_the_day_decides_who_is_in_force() -> None:
    before_everyone = _chart("ccaa-13", date(2020, 1, 1))

    assert before_everyone.executive.status is ChartStatus.NO_DATA


class _CountingReader(_Reader):
    def __init__(self) -> None:
        self.reads = {"bodies": 0, "holders": 0}

    def bodies(self) -> list[Body]:
        self.reads["bodies"] += 1
        return super().bodies()

    def holders(self) -> list[Holder]:
        self.reads["holders"] += 1
        return super().holders()


def test_the_general_chart_and_the_status_of_each_executive_come_from_one_read() -> None:
    reader = _CountingReader()

    chart, statuses = general_chart(reader, ["ccaa-13", "ccaa-05", "ccaa-99"], DAY)

    assert chart.territory_id == "es"
    assert chart.executive.status is ChartStatus.COMPLETE
    assert statuses == {
        "ccaa-13": ChartStatus.COMPLETE,
        "ccaa-05": ChartStatus.NO_DATA,
        "ccaa-99": ChartStatus.NO_DATA,
    }
    assert reader.reads == {"bodies": 1, "holders": 1}


class _WithBodies(_Reader):
    def __init__(self, extra: list[Body]) -> None:
        self._extra = extra

    def bodies(self) -> list[Body]:
        return [*BODIES, *self._extra]


def test_a_department_that_no_longer_exists_does_not_hold_the_executive_back() -> None:
    old = replace(
        _body("ccaa-13-vieja", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", "ccaa-13-gobierno"),
        valid_to=date(2026, 1, 1),  # merged: it has no holder in the files any more
    )
    reader = _WithBodies([old])

    before = organization_chart(reader, "ccaa-13", date(2025, 12, 31))
    after = organization_chart(reader, "ccaa-13", date(2026, 1, 1))

    assert before.executive.status is ChartStatus.NO_DATA  # still a department without a holder
    assert after.executive.status is ChartStatus.COMPLETE
    assert [p.body.id for p in after.executive.departments] == ["ccaa-13-sanidad"]


def test_a_department_that_does_not_exist_yet_is_not_part_of_the_chart() -> None:
    new = replace(
        _body("ccaa-13-nueva", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", "ccaa-13-gobierno"),
        valid_from=date(2027, 1, 1),
    )

    chart = organization_chart(_WithBodies([new]), "ccaa-13", DAY)

    assert [p.body.id for p in chart.executive.departments] == ["ccaa-13-sanidad"]
    assert chart.executive.status is ChartStatus.COMPLETE


def test_the_status_of_a_community_ignores_a_body_that_is_closed() -> None:
    old = replace(
        _body("ccaa-13-vieja", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", "ccaa-13-gobierno"),
        valid_to=date(2026, 1, 1),
    )

    _, statuses = general_chart(_WithBodies([old]), ["ccaa-13"], DAY)

    assert statuses == {"ccaa-13": ChartStatus.COMPLETE}
