"""Command line: uv run python -m datos.indicators load

An ETL job: reads the INE and writes observations. Never called by the API.
"""

import argparse

import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.http import build_client
from datos.indicators.application.load_indicators import load_indicators
from datos.indicators.domain.definitions import INDICATORS
from datos.indicators.infrastructure.ine_client import IneClient
from datos.indicators.infrastructure.ine_source import IneIndicatorSource
from datos.indicators.infrastructure.pg_repository import PgIndicatorRepository
from datos.log_setup import configure_logging

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.indicators")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("load", help="load the latest INE values of every indicator")
    parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    with build_client() as client:
        load_indicators(
            INDICATORS, IneIndicatorSource(IneClient(client)), PgIndicatorRepository(engine)
        )


if __name__ == "__main__":
    main()
