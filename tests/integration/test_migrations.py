import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def test_all_migrations_apply_on_an_empty_database(postgres_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_url)

    command.upgrade(config, "head")

    with create_engine(postgres_url).connect() as connection:
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    script_head = ScriptDirectory.from_config(config).get_current_head()
    assert head == script_head
