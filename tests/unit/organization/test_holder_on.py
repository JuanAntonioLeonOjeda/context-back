"""Who holds the head post of a body on a given day, with cases worked out by hand."""

from datetime import date

from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder, holder_on

SOURCE = "https://example.org/source"
CHANGE = date(2026, 3, 1)


def _holder(body_id: str, name: str, valid_from: date, valid_to: date | None) -> Holder:
    return Holder(body_id, "Consejero", name, valid_from, valid_to, SOURCE)


FIRST = _holder("ccaa-13-sanidad", "First", date(2023, 6, 17), CHANGE)
SECOND = _holder("ccaa-13-sanidad", "Second", CHANGE, None)
HOLDERS = [FIRST, SECOND]


def test_the_day_of_the_change_belongs_to_the_new_holder() -> None:
    assert holder_on(HOLDERS, "ccaa-13-sanidad", date(2026, 2, 28)) == FIRST
    assert holder_on(HOLDERS, "ccaa-13-sanidad", CHANGE) == SECOND


def test_the_first_day_of_a_period_is_covered_and_the_day_before_is_not() -> None:
    assert holder_on(HOLDERS, "ccaa-13-sanidad", date(2023, 6, 17)) == FIRST
    assert holder_on(HOLDERS, "ccaa-13-sanidad", date(2023, 6, 16)) is None


def test_a_holder_without_an_end_covers_every_later_day() -> None:
    assert holder_on(HOLDERS, "ccaa-13-sanidad", date(2040, 1, 1)) == SECOND


def test_a_closed_period_covers_nothing_after_it() -> None:
    assert holder_on([FIRST], "ccaa-13-sanidad", CHANGE) is None
    assert holder_on([FIRST], "ccaa-13-sanidad", date(2030, 1, 1)) is None


def test_the_holder_of_another_body_never_answers() -> None:
    other = _holder("ccaa-13-educacion", "Other", date(2023, 6, 17), None)

    assert holder_on([other], "ccaa-13-sanidad", date(2025, 1, 1)) is None
    assert holder_on([other, FIRST], "ccaa-13-sanidad", date(2025, 1, 1)) == FIRST


def test_no_holders_is_no_holder() -> None:
    assert holder_on([], "ccaa-13-sanidad", date(2025, 1, 1)) is None


def test_only_the_head_of_an_executive_and_a_department_have_a_holder() -> None:
    def body(kind: BodyKind) -> Body:
        return Body("ccaa-13-x", kind, BodyLevel.CCAA, "ccaa-13", "A body", None, None, SOURCE)

    assert [k for k in BodyKind if body(k).has_holder] == [
        BodyKind.EXECUTIVE_HEAD,
        BodyKind.DEPARTMENT,
    ]
