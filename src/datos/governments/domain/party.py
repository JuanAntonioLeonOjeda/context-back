from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Party:
    id: str
    name: str
    short_name: str
    colour_hex: str
