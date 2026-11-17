"""The parameters a community's municipalities can be grouped by in a voter profile.

A dimension is data: an id, the unit of its values and how its values are cut into bands. A new
dimension is a new entry here and a way to read its value, not another branch in the profile
(spec voters-dimensions, decision 1). The values describe areas, never people.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from datos.voters.domain.profile import Grouping, equal_census_grouping, fixed_limits_grouping

# The lowest census of every band of the size dimension but the first. The census is the electoral
# one (what the election files give), so the limits are in electors, not in inhabitants: 1,500
# electors is about a municipality of 2,000 inhabitants (spec voters-dimensions, decision 2).
SIZE_LIMITS = (Decimal(1500), Decimal(8000), Decimal(40000))


class DimensionId(StrEnum):
    INCOME = "income"
    SIZE = "size"
    # The value of the last three is loaded from a file of the INE, and the id is also the
    # `dimension` its loads are stored under (migration 0019).
    EDUCATION = "education"
    AGE = "age"
    BORN_ABROAD = "born_abroad"


@dataclass(frozen=True, slots=True)
class Dimension:
    id: DimensionId
    unit: str  # what a value counts: "eur_per_person", "electors"
    grouping: Grouping


INCOME = Dimension(DimensionId.INCOME, "eur_per_person", equal_census_grouping)
SIZE = Dimension(DimensionId.SIZE, "electors", fixed_limits_grouping(SIZE_LIMITS))
# The share of the population aged 15 or over with higher education, in percent. Bands of about
# the same census like income: the share is read against the rest of the community, and the
# distribution is skewed (national median 24.6 %, from 3 % to 64 %), so fixed limits would leave
# bands empty in most communities (spec voters-dimensions, decision 3).
EDUCATION = Dimension(DimensionId.EDUCATION, "percent", equal_census_grouping)

# The share of the population aged 15 or over who are 70 or older. Only the municipalities of 500
# inhabitants or more have it: the INE's table by age does not exist for the smaller ones, which
# are counted apart as without a value (spec voters-age-origin, decision 1). Equal-census bands,
# for the same reason as education.
AGE = Dimension(DimensionId.AGE, "percent", equal_census_grouping)
# The share of the population aged 15 or over born abroad (table 66621, same coverage as age).
BORN_ABROAD = Dimension(DimensionId.BORN_ABROAD, "percent", equal_census_grouping)

DIMENSIONS: dict[DimensionId, Dimension] = {
    d.id: d for d in (INCOME, SIZE, EDUCATION, AGE, BORN_ABROAD)
}
