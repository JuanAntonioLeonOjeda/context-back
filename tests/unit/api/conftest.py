"""Fakes of the API ports and a client factory, so router tests need no database."""

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from datos.api.app import create_app
from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party
from datos.indicators.application.read_indicators import IndicatorInfo, StoredValue
from datos.news.application.community_news import ClassifiedArticle
from datos.stories.application.community_stories import CommunityStory, StoryArticle, StoryRun
from datos.stories.application.story_tree import TreeRun
from datos.stories.domain.tree import StoryLink
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
        until: datetime,
        model_id: str,
        per_outlet_per_day: int,
    ) -> list[ClassifiedArticle]:
        self.last_query = {
            "territory_id": territory_id,
            "sector_id": sector_id,
            "since": since,
            "until": until,
            "model_id": model_id,
            "per_outlet_per_day": per_outlet_per_day,
        }
        return list(self.articles)

    def latest_per_tree(
        self, *, territory_id: str, sector_id: str, model_id: str
    ) -> list[ClassifiedArticle]:
        self.last_query = {
            "territory_id": territory_id,
            "sector_id": sector_id,
            "model_id": model_id,
        }
        return list(self.articles)


class FakeStories:
    """Returns its stories as stored; records the last query so tests can check it."""

    def __init__(self) -> None:
        self.run: StoryRun | None = None
        self.found: list[CommunityStory] = []
        self.last_query: dict[str, object] = {}

    def sector_ids(self) -> frozenset[str]:
        return frozenset({"education", "health", "housing"})

    def latest_run(self) -> StoryRun | None:
        return self.run

    def stories(
        self,
        *,
        run_id: int,
        territory_id: str,
        sector_id: str | None,
        since: datetime,
        model_id: str,
    ) -> list[CommunityStory]:
        self.last_query = {
            "run_id": run_id,
            "territory_id": territory_id,
            "sector_id": sector_id,
            "since": since,
            "model_id": model_id,
        }
        return list(self.found)


class FakeTrees:
    """Serves one tree run, its links and the articles of its stories."""

    def __init__(self) -> None:
        self.run: TreeRun | None = None
        self.link_rows: list[StoryLink] = []
        self.articles: dict[int, tuple[StoryArticle, ...]] = {}

    def latest_tree_run(self) -> TreeRun | None:
        return self.run

    def links(self, tree_run_id: int) -> list[StoryLink]:
        return list(self.link_rows)

    def story_articles(
        self, story_run_id: int, story_ids: Sequence[int]
    ) -> Mapping[int, tuple[StoryArticle, ...]]:
        return {i: self.articles[i] for i in story_ids}


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
def stories_reader() -> FakeStories:
    return FakeStories()


@pytest.fixture
def trees_reader() -> FakeTrees:
    return FakeTrees()


@pytest.fixture
def make_client(
    news_reader: FakeNews, stories_reader: FakeStories, trees_reader: FakeTrees
) -> Callable[..., TestClient]:
    def make(
        *,
        reachable: bool = True,
        terms: list[GovernmentTerm] = TERMS,
        today: date = TODAY,
        articles: list[ClassifiedArticle] | None = None,
        run: StoryRun | None = None,
        stories: list[CommunityStory] | None = None,
    ) -> TestClient:
        governments = FakeGovernments(terms, PARTIES)
        territories = FakeTerritories(TERRITORIES)
        indicators = FakeIndicators(INDICATORS, VALUES)
        news_reader.articles = articles or []
        stories_reader.run = run
        stories_reader.found = stories or []
        return TestClient(
            create_app(
                FixedProbe(reachable=reachable),
                governments=lambda: governments,
                territories=lambda: territories,
                indicators=lambda: indicators,
                news=lambda: news_reader,
                stories=lambda: stories_reader,
                trees=lambda: trees_reader,
                clock=FixedClock(today),
                geometry=GEOMETRY,
                classifier_id="rules",
            )
        )

    return make
