"""Income bands and vote shares, with cases worked out by hand."""

from decimal import Decimal

import pytest

from datos.voters.domain.profile import (
    OTHERS,
    MunicipalVotes,
    band_index,
    fixed_limits_grouping,
    vote_group,
    voter_profile,
)


def _m(
    code: str,
    census: int,
    value: str | None,
    votes: dict[str, int] | None = None,
    blank: int = 0,
) -> MunicipalVotes:
    return MunicipalVotes(
        code,
        census,
        None if value is None else Decimal(value),
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
    assert profile.without_value == ("01003",)
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
    assert empty and all(b.value_min is None and b.census == 0 for b in empty)


@pytest.mark.parametrize(
    ("code", "acronym", "group"),
    [
        ("000047", "PSC", "psc"),  # its own row, although its national head is PSOE's
        ("000051", "SUMAR - ECP", "lista:SUMAR - ECP"),  # a coalition: no row, its acronym
        ("000074", "U.P.N.", "lista:U.P.N."),  # a party that is not in the party table
    ],
)
def test_a_candidature_counts_for_its_party_or_for_its_own_acronym(
    code: str, acronym: str, group: str
) -> None:
    party_by_candidature = {"000047": "psc", "000010": "sumar"}

    assert vote_group(code, acronym, party_by_candidature) == group


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


# --- bands cut at fixed values (the size of a municipality) -------------------------------

SIZE_LIMITS = (Decimal(1500), Decimal(8000), Decimal(40000))


def _sized(
    census: int, number: int, votes: dict[str, int] | None = None, blank: int = 0
) -> MunicipalVotes:
    """A municipality whose value is its own census, as the size dimension has it."""
    return _m(f"01{number:03d}", census, str(census), votes, blank)


def _fixed_members(municipalities: list[MunicipalVotes]) -> list[tuple[str, ...]]:
    profile = voter_profile(municipalities, fixed_limits_grouping(SIZE_LIMITS))
    assert profile is not None
    return [band.municipality_codes for band in profile.bands]


def test_a_value_equal_to_a_limit_starts_the_band_that_begins_there() -> None:
    censuses = [999, 1000, 1499, 1500, 7999, 8000, 39999, 40000, 90000]
    municipalities = [_sized(c, i + 1) for i, c in enumerate(censuses)]

    assert _fixed_members(municipalities) == [
        ("01001", "01002", "01003"),  # below 1,500
        ("01004", "01005"),  # 1,500 and 7,999
        ("01006", "01007"),  # 8,000 and 39,999
        ("01008", "01009"),  # 40,000 and more
    ]


def test_n_limits_give_n_plus_one_bands_and_an_empty_one_stays_empty() -> None:
    profile = voter_profile([_sized(100, 1), _sized(50000, 2)], fixed_limits_grouping(SIZE_LIMITS))

    assert profile is not None
    assert [len(b.municipality_codes) for b in profile.bands] == [1, 0, 0, 1]
    empty = [b for b in profile.bands if not b.municipality_codes]
    assert all(b.value_min is None and b.census == 0 for b in empty)
    assert [b.index for b in profile.bands] == [0, 1, 2, 3]


def test_a_big_city_does_not_move_the_small_municipalities_to_other_bands() -> None:
    villages = [_sized(300, 1), _sized(900, 2), _sized(2000, 3), _sized(5000, 4)]
    city = _sized(2_000_000, 5)

    without = _fixed_members(villages)
    with_city = _fixed_members([*villages, city])

    # By census weight the city would take every band but one; by fixed limits it only adds
    # itself to the last band.
    assert with_city[:3] == without[:3]
    assert with_city[3] == ("01005",)


def test_the_votes_of_a_fixed_band_are_added_per_group() -> None:
    a = _sized(2000, 1, {"pp": 100, "psoe": 50}, blank=10)
    b = _sized(3000, 2, {"pp": 200, "psoe": 150}, blank=20)

    profile = voter_profile([a, b], fixed_limits_grouping(SIZE_LIMITS))

    assert profile is not None
    band = profile.bands[1]
    assert band.municipality_codes == ("01001", "01002")
    assert dict(band.votes) == {"pp": 300, "psoe": 200}
    assert (band.valid_votes, band.blank_votes, band.census) == (530, 30, 5000)
    assert (band.value_min, band.value_max) == (Decimal(2000), Decimal(3000))
