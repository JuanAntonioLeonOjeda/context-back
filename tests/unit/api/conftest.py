"""Fakes of the API ports and a client factory, so router tests need no database."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from datos.api.app import create_app
from datos.governments.domain.competence import Competence
from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party
from datos.indicators.application.read_indicators import IndicatorInfo, StoredValue
from datos.news.application.community_news import ClassifiedArticle
from datos.territories.territory import Level, Territory

TODAY = date(2026, 10, 13)
FETCHED = datetime(2026, 10, 13, 15, 48, tzinfo=UTC)
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


class FakeIndicators:
    def __init__(self, indicators: list[IndicatorInfo], values: list[StoredValue]) -> None:
        self._indicators = indicators
        self._values = values

    def indicators(self) -> list[IndicatorInfo]:
        return list(self._indicators)

    def current_values(self, territory_id: str) -> list[StoredValue]:
        return [v for v in self._values if territory_id == "ccaa-05"]


INDICATORS = [
    IndicatorInfo("unemployment_rate", "Tasa de paro", "%", Decimal(1), "quarterly", "14506"),
    IndicatorInfo("poverty_or_exclusion_rate", "AROPE", "%", Decimal(1), "annual", "60264"),
]
VALUES = [
    StoredValue("unemployment_rate", 2026, 19, Decimal("12.1"), "EPA452496", FETCHED),
    StoredValue("unemployment_rate", 2026, 20, Decimal("11.6"), "EPA452496", FETCHED),
]


class FakeGovernments:
    def __init__(self, terms: list[GovernmentTerm], parties: list[Party]) -> None:
        self._terms = terms
        self._parties = parties

    def terms(self, territory_id: str | None = None) -> list[GovernmentTerm]:
        return [t for t in self._terms if territory_id in (None, t.territory_id)]

    def parties(self) -> list[Party]:
        return list(self._parties)


class FakeCompetences:
    def __init__(self, competences: list[Competence]) -> None:
        self._competences = competences

    def competences(self) -> list[Competence]:
        return list(self._competences)


class FakeNews:
    """Returns its articles as stored; records the last query so tests can check it."""

    def __init__(self) -> None:
        self.articles: list[ClassifiedArticle] = []
        self.last_query: dict[str, object] = {}

    def sector_ids(self) -> frozenset[str]:
        return frozenset({"education", "health", "housing"})

    def recent(
        self,
        *,
        territory_id: str,
        sector_id: str,
        since: datetime,
        model_id: str,
        per_outlet: int,
    ) -> list[ClassifiedArticle]:
        self.last_query = {
            "territory_id": territory_id,
            "sector_id": sector_id,
            "since": since,
            "model_id": model_id,
            "per_outlet": per_outlet,
        }
        return list(self.articles)


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
def news_reader() -> FakeNews:
    return FakeNews()


@pytest.fixture
def make_client(news_reader: FakeNews) -> Callable[..., TestClient]:
    def make(
        *,
        reachable: bool = True,
        terms: list[GovernmentTerm] = TERMS,
        today: date = TODAY,
        articles: list[ClassifiedArticle] | None = None,
        competences: list[Competence] | None = None,
    ) -> TestClient:
        governments = FakeGovernments(terms, PARTIES)
        territories = FakeTerritories(TERRITORIES)
        indicators = FakeIndicators(INDICATORS, VALUES)
        competence_table = FakeCompetences(competences or [])
        news_reader.articles = articles or []
        return TestClient(
            create_app(
                FixedProbe(reachable=reachable),
                governments=lambda: governments,
                territories=lambda: territories,
                indicators=lambda: indicators,
                competences=lambda: competence_table,
                news=lambda: news_reader,
                clock=FixedClock(today),
                geometry=GEOMETRY,
                classifier_id="rules",
            )
        )

    return make
