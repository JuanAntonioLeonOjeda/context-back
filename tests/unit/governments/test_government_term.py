from datetime import date

import pytest

from datos.governments.domain.government_term import (
    EmptyPeriod,
    Gap,
    GovernmentTerm,
    NoGoverningParty,
    Overlap,
    PartyRole,
    TermParty,
    in_force_on,
    term_problems,
    timeline_problems,
)

SINCE = date(2020, 1, 1)
TODAY = date(2026, 10, 13)
GOVERNING_A = TermParty("party-a", PartyRole.GOVERNING)
GOVERNING_B = TermParty("party-b", PartyRole.GOVERNING)
SUPPORT_C = TermParty("party-c", PartyRole.EXTERNAL_SUPPORT)


def _term(
    valid_from: date,
    valid_to: date | None,
    *,
    territory_id: str = "ccaa-13",
    parties: tuple[TermParty, ...] = (GOVERNING_A,),
) -> GovernmentTerm:
    return GovernmentTerm(
        territory_id=territory_id,
        president_name="President",
        valid_from=valid_from,
        valid_to=valid_to,
        parties=parties,
        is_caretaker=False,
        source_url="https://www.boe.es/example",
    )


# --- derived kind --------------------------------------------------------------------


def test_a_single_governing_party_is_not_a_coalition() -> None:
    term = _term(SINCE, None, parties=(GOVERNING_A,))

    assert not term.is_coalition
    assert not term.has_external_support


def test_two_governing_parties_with_outside_support_is_a_supported_coalition() -> None:
    term = _term(SINCE, None, parties=(GOVERNING_A, GOVERNING_B, SUPPORT_C))

    assert term.is_coalition
    assert term.has_external_support
    assert term.governing_party_ids == ("party-a", "party-b")


# --- one term ------------------------------------------------------------------------


def test_a_valid_term_has_no_problems() -> None:
    assert term_problems(_term(SINCE, date(2023, 6, 17))) == []


def test_a_term_with_only_external_support_has_no_governing_party() -> None:
    term = _term(SINCE, None, parties=(SUPPORT_C,))

    assert term_problems(term) == [NoGoverningParty(term)]


@pytest.mark.parametrize(
    "valid_to", [date(2020, 1, 1), date(2019, 12, 31)], ids=["zero-days", "ends-before-start"]
)
def test_a_term_must_last_at_least_one_day(valid_to: date) -> None:
    term = _term(SINCE, valid_to)

    assert term_problems(term) == [EmptyPeriod(term)]


# --- in force on a date ---------------------------------------------------------------


def test_on_the_handover_day_the_new_term_is_in_force() -> None:
    old = _term(SINCE, date(2023, 6, 17))
    new = _term(date(2023, 6, 17), None)

    assert in_force_on([old, new], "ccaa-13", date(2023, 6, 16)) == old
    assert in_force_on([old, new], "ccaa-13", date(2023, 6, 17)) == new


def test_no_term_is_in_force_before_the_first_one_or_in_another_territory() -> None:
    terms = [_term(SINCE, None)]

    assert in_force_on(terms, "ccaa-13", date(2019, 12, 31)) is None
    assert in_force_on(terms, "ccaa-14", date(2024, 1, 1)) is None


# --- timeline of a territory ---------------------------------------------------------


def test_consecutive_terms_from_the_start_to_today_have_no_problems() -> None:
    terms = [_term(SINCE, date(2023, 6, 17)), _term(date(2023, 6, 17), None)]

    assert timeline_problems(terms, ["ccaa-13"], since=SINCE, today=TODAY) == []


def test_finds_a_gap_between_two_terms() -> None:
    terms = [_term(SINCE, date(2023, 6, 1)), _term(date(2023, 6, 17), None)]

    assert timeline_problems(terms, ["ccaa-13"], since=SINCE, today=TODAY) == [
        Gap("ccaa-13", date(2023, 6, 1), date(2023, 6, 17))
    ]


def test_finds_a_gap_when_the_first_term_starts_after_the_required_date() -> None:
    terms = [_term(date(2020, 3, 1), None)]

    assert timeline_problems(terms, ["ccaa-13"], since=SINCE, today=TODAY) == [
        Gap("ccaa-13", SINCE, date(2020, 3, 1))
    ]


def test_finds_a_gap_when_the_last_term_ended_and_nothing_is_in_force_today() -> None:
    terms = [_term(SINCE, date(2026, 6, 1))]

    assert timeline_problems(terms, ["ccaa-13"], since=SINCE, today=TODAY) == [
        Gap("ccaa-13", date(2026, 6, 1), None)
    ]


def test_a_territory_with_no_terms_is_one_open_gap() -> None:
    assert timeline_problems([], ["ccaa-13"], since=SINCE, today=TODAY) == [
        Gap("ccaa-13", SINCE, None)
    ]


def test_finds_overlapping_terms() -> None:
    first = _term(SINCE, date(2023, 6, 18))
    second = _term(date(2023, 6, 17), None)

    assert timeline_problems([first, second], ["ccaa-13"], since=SINCE, today=TODAY) == [
        Overlap(first, second)
    ]


def test_two_terms_in_force_overlap() -> None:
    first = _term(SINCE, None)
    second = _term(date(2023, 6, 17), None)

    assert timeline_problems([first, second], ["ccaa-13"], since=SINCE, today=TODAY) == [
        Overlap(first, second)
    ]


def test_checks_each_territory_on_its_own_and_ignores_unlisted_ones() -> None:
    terms = [
        _term(SINCE, None, territory_id="ccaa-13"),
        _term(SINCE, None, territory_id="ccaa-14"),
        _term(date(2021, 1, 1), None, territory_id="ccaa-99"),
    ]

    assert timeline_problems(terms, ["ccaa-13", "ccaa-14"], since=SINCE, today=TODAY) == []


def test_a_long_term_overlapping_two_later_ones_reports_both_and_no_false_gap() -> None:
    # The second term ends before the third starts, but the first covers that interval.
    long = _term(SINCE, date(2024, 1, 1))
    nested = _term(date(2021, 1, 1), date(2022, 1, 1))
    later = _term(date(2023, 1, 1), None)

    assert timeline_problems([long, nested, later], ["ccaa-13"], since=SINCE, today=TODAY) == [
        Overlap(long, nested),
        Overlap(long, later),
    ]
