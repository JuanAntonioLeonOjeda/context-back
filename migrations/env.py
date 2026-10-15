"""Alembic environment.

Migrations are written by hand and forward-only (ADR-0010), so there is no
`target_metadata` and autogeneration is not used.
"""

from alembic import context
from sqlalchemy import create_engine, pool

from datos.config import load_settings


def _database_url() -> str:
    # Tests pass the URL of their container through the Alembic config.
    configured = context.config.get_main_option("sqlalchemy.url")
    return configured or str(load_settings().database_url)


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline mode is not supported: run migrations against a database.")
run_migrations_online()
