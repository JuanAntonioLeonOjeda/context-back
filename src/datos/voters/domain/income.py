"""Mean net income per person of a municipality, as the INE's ADRH publishes it."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MunicipalIncome:
    municipality_code: str  # INE: province (2) + municipality (3)
    year: int
    euros_per_person: Decimal
    series_code: str  # the INE series, to trace the value back


def income_problems(incomes: Sequence[MunicipalIncome], province_ids: set[str]) -> list[str]:
    """Reasons not to store a table's incomes (empty when sound)."""
    problems: list[str] = []
    seen: set[str] = set()
    for i in incomes:
        if i.municipality_code in seen:
            problems.append(f"municipality {i.municipality_code} is repeated")
        seen.add(i.municipality_code)
        if f"prov-{i.municipality_code[:2]}" not in province_ids:
            problems.append(f"municipality {i.municipality_code}: unknown province")
        if i.euros_per_person <= 0:
            problems.append(f"municipality {i.municipality_code}: income {i.euros_per_person}")
    return problems


def changed_since(
    incomes: Sequence[MunicipalIncome], stored: dict[str, Decimal]
) -> list[MunicipalIncome]:
    """The incomes that are new or differ from the latest stored value: a revision of the INE
    is a new row, an unchanged value is not stored again (as the indicators do)."""
    return [i for i in incomes if stored.get(i.municipality_code) != i.euros_per_person]
