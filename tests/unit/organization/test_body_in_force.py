"""The days a body exists: half-open like a holder's period, and open when nothing is known."""

from dataclasses import replace
from datetime import date

from datos.organization.domain.body import Body, BodyKind, BodyLevel

SOURCE = "https://example.org/source"
BODY = Body("ccaa-13-sanidad", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", "Sanidad",
            "ccaa-13-gobierno", None, SOURCE)  # fmt: skip


def test_a_body_without_a_period_exists_on_every_day() -> None:
    assert BODY.in_force_on(date(1900, 1, 1))
    assert BODY.in_force_on(date(2999, 12, 31))


def test_the_first_day_belongs_to_the_body_and_the_last_one_does_not() -> None:
    body = replace(BODY, valid_from=date(2023, 6, 17), valid_to=date(2026, 1, 1))

    assert not body.in_force_on(date(2023, 6, 16))
    assert body.in_force_on(date(2023, 6, 17))
    assert body.in_force_on(date(2025, 12, 31))
    assert not body.in_force_on(date(2026, 1, 1))


def test_a_period_with_only_one_end_is_open_on_the_other_side() -> None:
    starts = replace(BODY, valid_from=date(2023, 6, 17))
    ends = replace(BODY, valid_to=date(2026, 1, 1))

    assert (starts.in_force_on(date(2023, 6, 16)), starts.in_force_on(date(2999, 1, 1))) == (
        False,
        True,
    )
    assert (ends.in_force_on(date(1900, 1, 1)), ends.in_force_on(date(2026, 1, 1))) == (
        True,
        False,
    )
