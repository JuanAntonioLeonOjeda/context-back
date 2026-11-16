"""The value of a profile dimension for one municipality and year, once computed from a file."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MunicipalValue:
    municipality_code: str  # INE: province (2) + municipality (3)
    year: int
    value: Decimal


def unknown_province_problems(
    values: Sequence[MunicipalValue], province_ids: set[str]
) -> list[str]:
    """One problem for every municipality whose province is not a territory we have: the database
    refuses it anyway (foreign key), and this says which one before anything is written."""
    return [
        f"municipality {v.municipality_code}: unknown province"
        for v in values
        if f"prov-{v.municipality_code[:2]}" not in province_ids
    ]


def changed_since(
    values: Sequence[MunicipalValue], stored: Mapping[str, Decimal]
) -> list[MunicipalValue]:
    """The values that are new or differ from the latest stored one: a revision of the INE is a
    new row, an unchanged value is not stored again (as the income and the indicators do)."""
    return [v for v in values if stored.get(v.municipality_code) != v.value]
