"""The dimensions a profile can be made by: their ids, units and the real limits of size."""

from decimal import Decimal

from datos.voters.domain.dimensions import DIMENSIONS, EDUCATION, INCOME, SIZE, DimensionId
from datos.voters.domain.profile import MunicipalVotes, voter_profile


def _sized(census: int, number: int) -> MunicipalVotes:
    return MunicipalVotes(f"01{number:03d}", census, Decimal(census), 0, {"pp": census})


def test_every_dimension_is_listed_by_its_id_with_its_unit() -> None:
    assert DIMENSIONS == {
        DimensionId.INCOME: INCOME,
        DimensionId.SIZE: SIZE,
        DimensionId.EDUCATION: EDUCATION,
    }
    assert (INCOME.unit, SIZE.unit, EDUCATION.unit) == ("eur_per_person", "electors", "percent")


def test_the_size_bands_start_at_1500_8000_and_40000_electors() -> None:
    censuses = [1499, 1500, 7999, 8000, 39999, 40000]
    municipalities = [_sized(c, i + 1) for i, c in enumerate(censuses)]

    profile = voter_profile(municipalities, SIZE.grouping)

    assert profile is not None
    assert [b.municipality_codes for b in profile.bands] == [
        ("01001",),  # 1,499: below the first limit
        ("01002", "01003"),  # 1,500 and 7,999
        ("01004", "01005"),  # 8,000 and 39,999
        ("01006",),  # 40,000
    ]


def test_education_is_banded_by_equal_census_like_income() -> None:
    assert EDUCATION.grouping is INCOME.grouping
