"""Command line: uv run python -m datos.territories load [--csv PATH]"""

import argparse
from pathlib import Path

import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

DEFAULT_CSV = Path("data/territories/territories.csv")

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.territories")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="load territories from the versioned CSV")
    load.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    territories = read_territories(arguments.csv)
    with build_engine(str(settings.database_url)).begin() as connection:
        PgTerritoryRepository(connection).upsert_all(territories)
    log.info("territories_loaded", count=len(territories), source=str(arguments.csv))


if __name__ == "__main__":
    main()
