"""Income bands and vote shares, with cases worked out by hand."""

from decimal import Decimal

import pytest

from datos.voters.domain.profile import (
    OTHERS,
    MunicipalVotes,
    band_index,
    vote_group,
    voter_profile,
)


def _m(
    code: str,
    census: int,
    income: str | None,
    votes: dict[str, int] | None = None,
    blank: int = 0,
) -> MunicipalVotes:
    return MunicipalVotes(
        code,
        census,
        None if income is None else Decimal(income),
        blank,
        {"pp": census} if votes is None else votes,
    )


def _members(municipalities: list[MunicipalVotes]) -> list[tuple[str, ...]]:
    profile = voter_profile(municipalities)
    assert profile is not None
    return [band.municipality_codes for band in profile.bands]


def test_five_equal_municipalities_give_one_per_band_from_the_lowest_income() -> None:
    municipalities = [_m(f"0100{n}", 100, str(10_000 + 1_000 * (5 - n))) for n in range(5)]

    assert _members(municipalities) == [("01004",), ("01003",), ("01002",), ("01001",), ("01000",)]


def test_a_big_municipality_goes_whole_to_the_band_of_its_midpoint() -> None:
    # Census 10, 10, 60, 10, 10 in income order; total 100. Midpoints 5, 15, 50, 85, 95 give
    # 5·mid/100 = 0.25, 0.75, 2.5, 4.25, 4.75 → bands 0, 0, 2, 4, 4: two bands stay empty.
    municipalities = [
        _m("01001", 10, "10000"),
        _m("01002", 10, "11000"),
        _m("01003", 60, "12000"),
        _m("01004", 10, "13000"),
        _m("01005", 10, "14000"),
    ]

    assert _members(municipalities) == [("01001", "01002"), (), ("01003",), (), ("01004", "01005")]


def test_the_band_index_is_exact_on_a_border() -> None:
    # A midpoint exactly at 20 % of the census is the start of the second band, not the end of the
    # first: floor(5 · 20 / 100) = 1. Integers, so no rounding moves it.
    assert band_index(census_before=15, census=10, total=100) == 1
    assert band_index(census_before=14, census=10, total=100) == 0
    assert band_index(census_before=99, census=1, total=100) == 4


def test_equal_incomes_are_ordered_by_ine_code() -> None:
    # Census 50 and 50: midpoints at 25 % and 75 % → bands 1 and 3, the lower code first.
    municipalities = [_m("01002", 50, "10000"), _m("01001", 50, "10000")]

    assert _members(municipalities) == [(), ("01001",), (), ("01002",), ()]


def test_municipalities_without_income_are_left_out_and_named() -> None:
    profile = voter_profile(
        [_m("01001", 50, "10000"), _m("01002", 50, "11000"), _m("01003", 7, None)]
    )

    assert profile is not None
    assert profile.without_income == ("01003",)
    assert profile.census == 100
    assert all("01003" not in b.municipality_codes for b in profile.bands)


def test_a_community_of_one_municipality_has_no_profile() -> None:
    assert voter_profile([_m("51001", 60_000, "13000")]) is None
    assert voter_profile([_m("51001", 60_000, "13000"), _m("51002", 10, None)]) is None


def test_a_group_with_exactly_three_percent_is_shown_and_below_goes_to_others() -> None:
    # Valid votes of the community: 1,000 (no blank). "cs" has 30 (3 %), "pacma" 29 (2.9 %).
    votes = {"pp": 941, "cs": 30, "pacma": 29}
    profile = voter_profile([_m("01001", 500, "10000", votes), _m("01002", 500, "11000", {})])

    assert profile is not None
    assert profile.shown_groups == ("cs", "pp")
    # 01001 (midpoint at 25 % of the census) is alone in band 1.
    assert profile.bands[1].votes == {"pp": 941, "cs": 30, OTHERS: 29}


def test_the_threshold_counts_municipalities_without_income_too() -> None:
    # "upn" has 40 of 1,000 valid votes only thanks to a municipality without income: 4 %, shown.
    profile = voter_profile(
        [
            _m("31001", 500, "10000", {"pp": 500}),
            _m("31002", 460, "11000", {"pp": 460}),
            _m("31003", 40, None, {"lista:U.P.N.": 40}),
        ]
    )

    assert profile is not None
    assert "lista:U.P.N." in profile.shown_groups


def test_a_band_s_votes_and_blank_add_up_to_its_valid_votes() -> None:
    profile = voter_profile(
        [
            _m("01001", 100, "10000", {"pp": 50, "psoe": 40}, blank=10),
            _m("01002", 100, "11000", {"pp": 30, "psoe": 60}, blank=10),
        ]
    )

    assert profile is not None
    for band in profile.bands:
        assert band.blank_votes + sum(band.votes.values()) == band.valid_votes


def test_an_empty_band_has_no_income_range() -> None:
    municipalities = [_m("01001", 10, "10000"), _m("01002", 90, "11000")]

    profile = voter_profile(municipalities)

    assert profile is not None
    empty = [b for b in profile.bands if not b.municipality_codes]
    assert empty and all(b.income_min is None and b.census == 0 for b in empty)


@pytest.mark.parametrize(
    ("head", "acronym", "group"),
    [("000047", "PSC", "psoe"), ("000074", "U.P.N.", "lista:U.P.N.")],
)
def test_a_candidature_counts_for_its_party_or_for_its_own_acronym(
    head: str, acronym: str, group: str
) -> None:
    party_by_head = {"000047": "psoe"}  # PSC's head would be PSOE's code; a direct row here

    assert vote_group(head, acronym, party_by_head) == group


def test_a_municipality_with_no_census_at_the_top_stays_in_the_last_band() -> None:
    # Its midpoint is exactly 100 % of the census: floor(5 · 100 / 100) = 5, one past the last
    # band. The schema allows a census of 0, so the cap matters.
    municipalities = [_m("01001", 100, "10000"), _m("01002", 0, "20000", {})]

    assert _members(municipalities)[-1] == ("01002",)


def test_municipalities_without_any_census_have_no_profile() -> None:
    # No population to split into bands; it must not fail dividing by a total census of 0.
    municipalities = [_m("01001", 0, "10000"), _m("01002", 0, "11000"), _m("01003", 50, None)]

    assert voter_profile(municipalities) is None


def test_the_smallest_census_there_can_be_still_has_a_profile() -> None:
    assert _members([_m("01001", 1, "10000"), _m("01002", 0, "11000")]) == [
        (),
        (),
        ("01001",),
        (),
        ("01002",),
    ]
