"""Fakes of the API ports and a client factory, so router tests need no database."""

from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient

from datos.api.app import create_app
from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party
from datos.territories.territory import Level, Territory

TODAY = date(2026, 10, 13)
SOURCE = "https://www.boe.es/example"


class FixedProbe:
    def __init__(self, *, reachable: bool = True) -> None:
        self._reachable = reachable

    def is_reachable(self) -> bool:
        return self._reachable


class FixedClock:
    def __init__(self, today: date = TODAY) -> None:
        self._today = today

    def today(self) -> date:
        return self._today


class FakeTerritories:
    def __init__(self, territories: list[Territory]) -> None:
        self._territories = territories

    def by_level(self, level: Level) -> list[Territory]:
        return [t for t in self._territories if t.level is level]


class FakeGovernments:
    def __init__(self, terms: list[GovernmentTerm], parties: list[Party]) -> None:
        self._terms = terms
        self._parties = parties

    def terms(self, territory_id: str | None = None) -> list[GovernmentTerm]:
        return [t for t in self._terms if territory_id in (None, t.territory_id)]

    def parties(self) -> list[Party]:
        return list(self._parties)


GEOMETRY: dict[str, object] = {"type": "FeatureCollection", "attribution": "test", "features": []}

TERRITORIES = [
    Territory("es", None, "España", Level.STATE, None),
    Territory("ccaa-05", "05", "Canarias", Level.CCAA, "es"),
    Territory("ccaa-13", "13", "Comunidad de Madrid", Level.CCAA, "es"),
]
PARTIES = [
    Party("asg", "Agrupación Socialista Gomera", "ASG", "#9e9e9e"),
    Party("coalicion-canaria", "Coalición Canaria", "CC", "#9e9e9e"),
    Party("pp", "Partido Popular", "PP", "#9e9e9e"),
]


def term(
    territory_id: str,
    valid_from: date,
    valid_to: date | None,
    parties: dict[str, PartyRole],
    *,
    is_caretaker: bool = False,
) -> GovernmentTerm:
    return GovernmentTerm(
        territory_id=territory_id,
        president_name="President",
        valid_from=valid_from,
        valid_to=valid_to,
        parties=tuple(TermParty(p, role, f"{SOURCE}/{p}") for p, role in parties.items()),
        is_caretaker=is_caretaker,
        source_url=SOURCE,
    )


TERMS = [
    term(
        "ccaa-05",
        date(2023, 5, 28),
        date(2023, 7, 14),
        {"coalicion-canaria": PartyRole.GOVERNING},
        is_caretaker=True,
    ),
    term(
        "ccaa-05",
        date(2023, 7, 14),
        None,
        {
            "pp": PartyRole.GOVERNING,
            "coalicion-canaria": PartyRole.GOVERNING,
            "asg": PartyRole.EXTERNAL_SUPPORT,
        },
    ),
    term("ccaa-13", date(2023, 6, 23), None, {"pp": PartyRole.GOVERNING}),
]


@pytest.fixture
def make_client() -> Callable[..., TestClient]:
    def make(
        *,
        reachable: bool = True,
        terms: list[GovernmentTerm] = TERMS,
        today: date = TODAY,
    ) -> TestClient:
        governments = FakeGovernments(terms, PARTIES)
        territories = FakeTerritories(TERRITORIES)
        return TestClient(
            create_app(
                FixedProbe(reachable=reachable),
                governments=lambda: governments,
                territories=lambda: territories,
                clock=FixedClock(today),
                geometry=GEOMETRY,
            )
        )

    return make
