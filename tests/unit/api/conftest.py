"""Fakes of the API ports and a client factory, so router tests need no database."""

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from datos.api.app import create_app
from datos.governments.domain.competence import Sector
from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party
from datos.indicators.application.read_indicators import IndicatorInfo, StoredValue
from datos.news.application.community_news import ClassifiedArticle
from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence
from datos.stories.application.community_stories import CommunityStory, StoryArticle, StoryRun
from datos.stories.application.story_tree import TreeRun
from datos.stories.domain.related import Candidate, NewsItem, RelatedSettings
from datos.stories.domain.tree import StoryLink
from datos.territories.territory import Level, Territory
from datos.voters.application.community_voters import (
    CandidatureCount,
    ElectionInfo,
    MunicipalRow,
    SourceInfo,
)
from datos.voters.domain.dimensions import DimensionId

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


class FakeOrganization:
    def __init__(
        self, bodies: list[Body], holders: list[Holder], competences: list[Competence]
    ) -> None:
        self._bodies = bodies
        self._holders = holders
        self._competences = competences

    def bodies(self) -> list[Body]:
        return self._bodies

    def holders(self) -> list[Holder]:
        return self._holders

    def competences(self) -> list[Competence]:
        return self._competences

    def sector_names(self) -> dict[str, str]:
        return {"health": "Sanidad", "taxes": "Impuestos"}


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


SECTORS = [
    Sector("education", "Educación", indicator_id="higher_education_share_16plus"),
    Sector("health", "Sanidad"),
]


class FakeGovernments:
    def __init__(self, terms: list[GovernmentTerm], parties: list[Party]) -> None:
        self._terms = terms
        self._parties = parties

    def terms(self, territory_id: str | None = None) -> list[GovernmentTerm]:
        return [t for t in self._terms if territory_id in (None, t.territory_id)]

    def parties(self) -> list[Party]:
        return list(self._parties)

    def active_sectors(self) -> list[Sector]:
        return list(SECTORS)


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

ELECTION = ElectionInfo("congreso-2023-07", date(2023, 7, 23), "02202307_MUNI.zip")
INCOME = SourceInfo(
    2023,
    "https://servicios.ine.es/wstempus/js/ES/DATOS_METADATAOPERACION/353?date=20230101",
    datetime(2026, 11, 9, 8, 23, tzinfo=UTC),
)
EDUCATION = SourceInfo(
    2023,
    "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176992",
    datetime(2026, 11, 16, 15, 47, tzinfo=UTC),
)
# Two municipalities of Canarias with hand-picked counts: 000031 is CC (mapped), 000005
# PP (mapped), 000099 a candidature that is not in the table.
VOTER_ROWS = [
    MunicipalRow(
        "35016",
        300,
        10,
        Decimal("15000"),
        (
            CandidatureCount("000005", "PP", 100),
            CandidatureCount("000031", "CCa", 60),
            CandidatureCount("000099", "LISTA X", 30),
        ),
    ),
    MunicipalRow(
        "38038",
        200,
        0,
        Decimal("14000"),
        (CandidatureCount("000005", "PP", 120), CandidatureCount("000031", "CCa", 80)),
    ),
]
PARTY_BY_CANDIDATURE = {"congreso-2023-07": {"000005": "pp", "000031": "coalicion-canaria"}}


class FakeVoters:
    def __init__(self, rows: list[MunicipalRow]) -> None:
        self._rows = rows

    def elections(self) -> list[ElectionInfo]:
        return [ELECTION]

    def municipal_rows(
        self, territory_id: str, election_id: str, income_year: int, dimension: DimensionId
    ) -> list[MunicipalRow]:
        return list(self._rows) if territory_id == "ccaa-05" else []

    def income_download(self, year: int) -> SourceInfo | None:
        return INCOME if year == 2023 else None

    def values_source(self, dimension: DimensionId, year: int) -> SourceInfo | None:
        return EDUCATION if year == 2023 else None


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


def _body(
    id_: str,
    kind: BodyKind,
    level: BodyLevel,
    territory: str | None,
    name: str,
    parent: str | None = None,
    dir3: str | None = None,
) -> Body:
    return Body(id_, kind, level, territory, name, parent, dir3, SOURCE)


def _holder(body_id: str, name: str, since: date = date(2023, 6, 17)) -> Holder:
    return Holder(body_id, f"Titular de {body_id}", name, since, None, SOURCE)


# The State and Madrid have a complete executive, Canarias only a head with nobody in it.
# Madrid's departments, by name, case-insensitively: "educación", "Sanidad".
ORGANIZATION: tuple[list[Body], list[Holder], list[Competence]] = (
    [
        _body(
            "es-gobierno",
            BodyKind.EXECUTIVE_HEAD,
            BodyLevel.STATE,
            "es",
            "Presidencia del Gobierno",
        ),
        _body(
            "es-hacienda",
            BodyKind.DEPARTMENT,
            BodyLevel.STATE,
            "es",
            "Ministerio de Hacienda",
            "es-gobierno",
            dir3="E05250001",
        ),
        _body("es-cortes", BodyKind.PARLIAMENT, BodyLevel.STATE, "es", "Cortes Generales"),
        _body("es-supremo", BodyKind.JUDICIARY, BodyLevel.STATE, "es", "Tribunal Supremo"),
        _body(
            "ccaa-13-gobierno",
            BodyKind.EXECUTIVE_HEAD,
            BodyLevel.CCAA,
            "ccaa-13",
            "Presidencia de la Comunidad",
        ),
        _body(
            "ccaa-13-sanidad",
            BodyKind.DEPARTMENT,
            BodyLevel.CCAA,
            "ccaa-13",
            "Consejería de Sanidad",
            "ccaa-13-gobierno",
        ),
        _body(
            "ccaa-13-educacion",
            BodyKind.DEPARTMENT,
            BodyLevel.CCAA,
            "ccaa-13",
            "consejería de educación",
            "ccaa-13-gobierno",
        ),
        _body(
            "ccaa-13-asamblea", BodyKind.PARLIAMENT, BodyLevel.CCAA, "ccaa-13", "Asamblea de Madrid"
        ),
        _body(
            "ccaa-13-tsj",
            BodyKind.JUDICIARY,
            BodyLevel.STATE,
            "ccaa-13",
            "Tribunal Superior de Justicia de Madrid",
        ),
        _body(
            "ccaa-05-gobierno",
            BodyKind.EXECUTIVE_HEAD,
            BodyLevel.CCAA,
            "ccaa-05",
            "Presidencia de Canarias",
        ),
        _body("ccaa-05-cabildo", BodyKind.LOCAL, BodyLevel.LOCAL, "ccaa-05", "Cabildo insular"),
        _body("local-ayuntamiento", BodyKind.LOCAL, BodyLevel.LOCAL, None, "Ayuntamiento"),
    ],
    [
        _holder("es-gobierno", "Pedro Sánchez Pérez-Castejón", date(2023, 11, 17)),
        _holder("es-hacienda", "Arcadi España García", date(2026, 3, 26)),
        _holder("ccaa-13-gobierno", "Isabel Díaz Ayuso"),
        _holder("ccaa-13-sanidad", "Fátima Matute Teresa"),
        _holder("ccaa-13-educacion", "María Mercedes Zarzalejo Carbajo"),
    ],
    [
        Competence(
            "es-hacienda",
            "Hacienda pública, presupuestos y gastos.",
            "RD 829/2023, art. 5.1",
            ("taxes",),
            SOURCE,
        ),
        Competence(
            "ccaa-13-sanidad",
            "Salud y asistencia sanitaria.",
            "Decreto 245/2023, art. 1",
            ("health", "unknown"),
            SOURCE,
        ),
        Competence(
            "ccaa-13-asamblea",
            "Potestad legislativa de la Comunidad.",
            "Estatuto, art. 9",
            ("taxes",),
            SOURCE,
        ),
        Competence(
            "local-ayuntamiento",
            "Urbanismo y vivienda.",
            "Ley 7/1985, art. 25.2.a",
            ("health",),
            SOURCE,
        ),
    ],
)


@pytest.fixture
def news_reader() -> FakeNews:
    return FakeNews()


@pytest.fixture
def stories_reader() -> FakeStories:
    return FakeStories()


@pytest.fixture
def trees_reader() -> FakeTrees:
    return FakeTrees()


class FakeRelated:
    """Article 10 on 16 November; its candidates, and those of each later step, set by a test."""

    def __init__(self) -> None:
        self.items = {
            10: NewsItem(
                10,
                "abc",
                "El juez ordena…",
                datetime(2026, 11, 16, 11, tzinfo=UTC),
                "ABC",
                "https://abc.example/10",
            )
        }
        self.found: dict[int, list[Candidate]] = {}

    def news_item(self, article_id: int) -> NewsItem | None:
        return self.items.get(article_id)

    def candidates(
        self, step_id: int, origin_id: int, settings: RelatedSettings, *, limit: int = 50
    ) -> list[Candidate]:
        return self.found.get(step_id, [])


@pytest.fixture
def related_reader() -> FakeRelated:
    return FakeRelated()


@pytest.fixture
def make_client(
    news_reader: FakeNews,
    stories_reader: FakeStories,
    trees_reader: FakeTrees,
    related_reader: FakeRelated,
) -> Callable[..., TestClient]:
    def make(
        *,
        reachable: bool = True,
        terms: list[GovernmentTerm] = TERMS,
        today: date = TODAY,
        articles: list[ClassifiedArticle] | None = None,
        run: StoryRun | None = None,
        stories: list[CommunityStory] | None = None,
        voter_rows: list[MunicipalRow] = VOTER_ROWS,
        organization: FakeOrganization | None = None,
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
                related=lambda: related_reader,
                voters=lambda: FakeVoters(voter_rows),
                organization=lambda: organization or FakeOrganization(*ORGANIZATION),
                party_by_candidature=PARTY_BY_CANDIDATURE,
                clock=FixedClock(today),
                geometry=GEOMETRY,
                classifier_id="rules",
            )
        )

    return make
