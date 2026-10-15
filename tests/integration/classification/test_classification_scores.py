"""The scores of a model's classifications are stored with them, append-only (ADR-0016, 0006)."""

import itertools
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from datos.classification.application.store_classifications import classify_new
from datos.classification.domain.labels import Labels, Score
from datos.classification.infrastructure.pg_repository import PgClassificationRepository
from datos.classification.infrastructure.rules_classifier import load_rules_classifier
from datos.governments.application.published import CompetenceLevel

pytestmark = pytest.mark.integration

SECTORS = frozenset({"education", "health", "housing"})
_names = (f"classification_scores_it_{n}" for n in itertools.count())


def _config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


def _database(postgres_url: str) -> str:
    name = next(_names)
    with create_engine(postgres_url, isolation_level="AUTOCOMMIT").connect() as admin:
        admin.execute(text(f"CREATE DATABASE {name}"))
    return make_url(postgres_url).set(database=name).render_as_string(hide_password=False)


def _insert_article(engine: Engine) -> int:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES ('outlet-a', 'Outlet A', 'https://a.example', 'national', NULL)"
            )
        )
        return int(
            connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline)"
                    " VALUES ('outlet-a', 'https://a.example/1', now(),"
                    " 'La Xunta y el ministerio chocan por las plazas MIR') RETURNING id"
                )
            ).scalar_one()
        )


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    url = _database(postgres_url)
    command.upgrade(_config(url), "head")
    engine = create_engine(url)
    _insert_article(engine)
    yield engine
    engine.dispose()


class FakeModel:
    """A classifier that says health and the state level, and how sure it is."""

    model_id = "fake-model"
    model_version = "w1"

    def classify(self, headline: str, lead: str | None) -> Labels:
        return Labels(
            communities=frozenset(),
            sectors=frozenset({"health"}),
            levels=frozenset({CompetenceLevel.STATE}),
            scores=(Score("sector:health", 0.83), Score("level:state", 0.61)),
        )


def _scores(engine: Engine, model_id: str) -> list[dict[str, object]]:
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT scores FROM classifications WHERE model_id = :m"), {"m": model_id}
        ).scalar_one()
    assert isinstance(value, list)
    return value


def test_a_models_scores_are_stored_with_its_labels(engine: Engine) -> None:
    classify_new(FakeModel(), PgClassificationRepository(engine))

    assert _scores(engine, "fake-model") == [
        {"label": "sector:health", "probability": 0.83},
        {"label": "level:state", "probability": 0.61},
    ]


def test_the_rules_store_no_scores(engine: Engine) -> None:
    rules = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)
    classify_new(rules, PgClassificationRepository(engine))

    assert _scores(engine, "rules") == []


def test_scores_must_be_a_list(engine: Engine) -> None:
    with pytest.raises(DBAPIError, match="classifications_scores_is_array"), engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO classifications (article_id, model_id, model_version, communities,"
                " sectors, levels, evidence, scores) SELECT id, 'x', '1', '{}', '{}', '{}', '[]',"
                " '{}'::jsonb FROM articles"
            )
        )


def test_scores_cannot_be_changed_afterwards(engine: Engine) -> None:
    classify_new(FakeModel(), PgClassificationRepository(engine))

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text("UPDATE classifications SET scores = '[]'::jsonb"))


def test_the_column_is_added_on_top_of_existing_rows_without_touching_them(
    postgres_url: str,
) -> None:
    url = _database(postgres_url)
    command.upgrade(_config(url), "0005")
    engine = create_engine(url)
    article_id = _insert_article(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO classifications (article_id, model_id, model_version, communities,"
                " sectors, levels, evidence) VALUES (:a, 'rules', 'v0', '{}', '{housing}',"
                " '{local}', '[]')"
            ),
            {"a": article_id},
        )

    command.upgrade(_config(url), "head")

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT model_version, sectors, levels, scores FROM classifications")
        ).one()
        assert (row.model_version, row.sectors, row.levels, row.scores) == (
            "v0",
            ["housing"],
            ["local"],
            [],
        )
        # The append-only trigger of 0005 is still there.
        with pytest.raises(DBAPIError, match="append-only"), engine.begin() as c:
            c.execute(text("DELETE FROM classifications"))
    engine.dispose()
