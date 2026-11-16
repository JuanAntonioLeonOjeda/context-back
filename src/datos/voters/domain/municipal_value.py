"""The value of a profile dimension for one municipality and year, once computed from a file."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MunicipalValue:
    municipality_code: str  # INE: province (2) + municipality (3)
    year: int
    value: Decimal
