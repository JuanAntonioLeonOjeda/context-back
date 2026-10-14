import itertools
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from datos.classification.application.store_classifications import classify_new
from datos.classification.domain.labels import Labels
from datos.classification.infrastructure.pg_repository import PgClassificationRepository
from datos.classification.infrastructure.rules_classifier import load_rules_classifier
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

SECTORS = frozenset({"education", "health", "housing"})
_names = (f"classification_it_{n}" for n in itertools.count())
HEADLINES = [
    ("El Cabildo de Lanzarote construye 200 viviendas públicas", None),
    ("La Xunta y el ministerio chocan por las plazas MIR", "Se reúnen el lunes."),
    ("Netflix emitirá los 104 partidos del Mundial 2030", None),
]


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A database per test: the repository commits, and classifications cannot be deleted."""
    name = next(_names)
    with create_engine(postgres_url, isolation_level="AUTOCOMMIT").connect() as admin:
        admin.execute(text(f"CREATE DATABASE {name}"))
    url = make_url(postgres_url).set(database=name).render_as_string(hide_password=False)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        PgTerritoryRepository(connection).upsert_all(
            read_territories(Path("data/territories/territories.csv"))
        )
        connection.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id) VALUES"
                " ('outlet-a', 'Outlet A', 'https://a.example', 'national', NULL)"
            )
        )
        for n, (headline, lead) in enumerate(HEADLINES):
            connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
                    " VALUES ('outlet-a', :url, :at, :headline, :lead)"
                ),
                {
                    "url": f"https://a.example/{n}",
                    "at": datetime(2026, 10, 14, 8, n, tzinfo=UTC),
                    "headline": headline,
                    "lead": lead,
                },
            )
    yield engine
    engine.dispose()


def _count(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text("SELECT count(*) FROM classifications")).scalar_one())


def test_classifies_every_article_once_and_a_second_run_stores_nothing(engine: Engine) -> None:
    repository = PgClassificationRepository(engine)
    classifier = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)

    first = classify_new(classifier, repository)
    second = classify_new(classifier, repository)

    assert (first, second) == (3, 0)
    assert _count(engine) == 3


def test_stores_the_labels_the_version_and_the_evidence(engine: Engine) -> None:
    classifier = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)
    classify_new(classifier, PgClassificationRepository(engine))

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT c.communities, c.levels, c.sectors, c.model_id, c.model_version,"
                " c.evidence FROM classifications c JOIN articles a ON a.id = c.article_id"
                " WHERE a.url = 'https://a.example/0'"
            )
        ).one()

    assert (row.communities, row.levels, row.sectors) == (["ccaa-05"], ["local"], ["housing"])
    assert (row.model_id, row.model_version) == ("rules", classifier.model_version)
    assert {(e["term"], e["gives"]) for e in row.evidence} >= {("cabildo", "level:local")}


def test_a_new_version_classifies_everything_again_and_keeps_the_old_rows(engine: Engine) -> None:
    repository = PgClassificationRepository(engine)
    classifier = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)
    classify_new(classifier, repository)

    class NextVersion:
        model_id = classifier.model_id
        model_version = "next"

        def classify(self, headline: str, lead: str | None) -> Labels:
            return classifier.classify(headline, lead)

    classify_new(NextVersion(), repository)

    assert _count(engine) == 6


def test_a_batch_beyond_the_batch_size_is_classified_completely(engine: Engine) -> None:
    repository = PgClassificationRepository(engine)
    classifier = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)

    assert len(repository.unclassified("rules", classifier.model_version, limit=2)) == 2
    assert classify_new(classifier, repository) == 3


@pytest.mark.parametrize(
    "operation",
    [
        "UPDATE classifications SET sectors = '{}'",
        "DELETE FROM classifications",
        "TRUNCATE classifications",
    ],
)
def test_classifications_cannot_be_changed_or_removed(engine: Engine, operation: str) -> None:
    classify_new(
        load_rules_classifier(Path("data/classification"), sector_ids=SECTORS),
        PgClassificationRepository(engine),
    )

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text(operation))


@pytest.mark.parametrize(
    ("column", "value", "constraint"),
    [
        ("levels", "provincial", "classifications_levels_valid"),
        ("communities", "ccaa-99", "classifications_communities_valid"),
    ],
)
def test_labels_outside_the_vocabulary_are_rejected(
    engine: Engine, column: str, value: str, constraint: str
) -> None:
    labels: dict[str, list[str]] = {"communities": [], "sectors": [], "levels": []}
    labels[column] = [value]

    with pytest.raises(DBAPIError, match=constraint), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO classifications (article_id, model_id, model_version, communities,"
                " sectors, levels, evidence) SELECT id, 'x', '1', CAST(:communities AS text[]),"
                " CAST(:sectors AS text[]), CAST(:levels AS text[]), '[]' FROM articles LIMIT 1"
            ),
            labels,
        )


def test_the_repository_gives_the_sector_ids_the_rules_are_validated_against(
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO sectors (id, name)"
                " VALUES ('housing', 'Vivienda'), ('health', 'Sanidad')"
            )
        )

    assert PgClassificationRepository(engine).sector_ids() == {"health", "housing"}
