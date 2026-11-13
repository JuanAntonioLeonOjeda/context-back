"""The executive chart of a territory, complete or nothing, with cases worked out by hand."""

from datetime import date

from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.chart import ChartStatus, ExecutiveChart, executive_chart

SOURCE = "https://example.org/source"
DAY = date(2026, 11, 13)
SINCE = date(2023, 6, 17)


def _body(territory: str, slug: str, kind: BodyKind, name: str) -> Body:
    return Body(f"{territory}-{slug}", kind, BodyLevel.CCAA, territory, name, None, None, SOURCE)


def _holder(
    body: Body, name: str, valid_from: date = SINCE, valid_to: date | None = None
) -> Holder:
    return Holder(body.id, "Consejero", name, valid_from, valid_to, SOURCE)


def _government(territory: str = "ccaa-13") -> tuple[list[Body], list[Holder]]:
    """A head and three departments, each with a holder; the names sort differently with and
    without regard to case: educación, Sanidad, Vivienda."""
    head = _body(territory, "gobierno", BodyKind.EXECUTIVE_HEAD, "Presidencia")
    departments = [
        _body(territory, "vivienda", BodyKind.DEPARTMENT, "Vivienda"),
        _body(territory, "sanidad", BodyKind.DEPARTMENT, "Sanidad"),
        _body(territory, "educacion", BodyKind.DEPARTMENT, "educación"),
    ]
    bodies = [head, *departments]
    return bodies, [_holder(b, f"Holder of {b.id}") for b in bodies]


def test_a_government_with_a_holder_everywhere_is_complete() -> None:
    bodies, holders = _government()

    chart = executive_chart(bodies, holders, "ccaa-13", DAY)

    assert chart.status is ChartStatus.COMPLETE
    assert chart.head is not None
    assert chart.head.body.id == "ccaa-13-gobierno"
    assert chart.head.holder.holder_name == "Holder of ccaa-13-gobierno"


def test_the_departments_come_by_name_without_regard_to_case_and_never_by_input_order() -> None:
    bodies, holders = _government()

    chart = executive_chart(bodies, holders, "ccaa-13", DAY)
    reversed_chart = executive_chart(bodies[::-1], holders[::-1], "ccaa-13", DAY)

    names = [post.body.name for post in chart.departments]
    assert names == ["educación", "Sanidad", "Vivienda"]
    assert reversed_chart == chart


def test_two_departments_with_the_same_name_keep_a_fixed_order_by_id() -> None:
    bodies, holders = _government()
    twin = _body("ccaa-13", "aaa-sanidad", BodyKind.DEPARTMENT, "Sanidad")
    bodies.append(twin)
    holders.append(_holder(twin, "Twin"))

    chart = executive_chart(bodies, holders, "ccaa-13", DAY)

    assert [post.body.id for post in chart.departments][1:3] == [
        "ccaa-13-aaa-sanidad",
        "ccaa-13-sanidad",
    ]


def test_one_department_without_a_holder_leaves_nothing_of_the_government() -> None:
    bodies, holders = _government()
    without = [h for h in holders if h.body_id != "ccaa-13-sanidad"]

    chart = executive_chart(bodies, without, "ccaa-13", DAY)

    assert (chart.status, chart.head, chart.departments) == (ChartStatus.NO_DATA, None, ())


def test_a_head_without_a_holder_is_no_data_even_if_every_department_has_one() -> None:
    bodies, holders = _government()
    without = [h for h in holders if h.body_id != "ccaa-13-gobierno"]

    assert executive_chart(bodies, without, "ccaa-13", DAY).status is ChartStatus.NO_DATA


def test_a_holder_not_yet_in_force_or_already_gone_does_not_count() -> None:
    bodies, holders = _government()
    sanidad = next(b for b in bodies if b.id == "ccaa-13-sanidad")
    others = [h for h in holders if h.body_id != sanidad.id]

    future = [*others, _holder(sanidad, "Future", valid_from=date(2026, 11, 14))]
    gone = [*others, _holder(sanidad, "Gone", valid_to=DAY)]  # its last day was the day before

    assert executive_chart(bodies, future, "ccaa-13", DAY).status is ChartStatus.NO_DATA
    assert executive_chart(bodies, gone, "ccaa-13", DAY).status is ChartStatus.NO_DATA
    assert executive_chart(bodies, future, "ccaa-13", date(2026, 11, 14)).status is (
        ChartStatus.COMPLETE
    )


def test_a_head_alone_is_not_a_government() -> None:
    bodies, holders = _government()
    only_head = [b for b in bodies if b.kind is BodyKind.EXECUTIVE_HEAD]

    assert executive_chart(only_head, holders, "ccaa-13", DAY).status is ChartStatus.NO_DATA


def test_two_heads_in_one_territory_cannot_be_drawn() -> None:
    bodies, holders = _government()
    second = _body("ccaa-13", "otro-gobierno", BodyKind.EXECUTIVE_HEAD, "Another")
    bodies.append(second)
    holders.append(_holder(second, "Another"))

    assert executive_chart(bodies, holders, "ccaa-13", DAY).status is ChartStatus.NO_DATA


def test_a_territory_with_no_bodies_is_no_data_and_another_territory_does_not_fill_in() -> None:
    bodies, holders = _government("ccaa-14")

    assert executive_chart([], [], "ccaa-13", DAY).status is ChartStatus.NO_DATA
    assert executive_chart(bodies, holders, "ccaa-13", DAY).status is ChartStatus.NO_DATA
    assert executive_chart(bodies, holders, "ccaa-14", DAY).status is ChartStatus.COMPLETE


def test_the_same_data_for_two_territories_gives_the_same_shape() -> None:
    bodies_a, holders_a = _government("ccaa-13")
    bodies_b, holders_b = _government("ccaa-14")

    chart_a = executive_chart(bodies_a + bodies_b, holders_a + holders_b, "ccaa-13", DAY)
    chart_b = executive_chart(bodies_a + bodies_b, holders_a + holders_b, "ccaa-14", DAY)

    def shape(chart: ExecutiveChart) -> list[str]:
        assert chart.head is not None
        return [p.body.id.split("-", 2)[2] for p in (chart.head, *chart.departments)]

    assert chart_a.status is chart_b.status is ChartStatus.COMPLETE
    assert shape(chart_a) == shape(chart_b)
