"""Command line: uv run python -m datos.governments load [--data-dir PATH]"""

import argparse
from datetime import date
from pathlib import Path

import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.governments.application.load_governments import (
    InvalidGovernmentsDatasetError,
    load_competences,
    load_governments,
)
from datos.governments.infrastructure.csv_source import (
    InvalidGovernmentsFileError,
    read_competences,
    read_parties,
    read_sectors,
    read_terms,
)
from datos.governments.infrastructure.pg_repository import PgGovernmentRepository
from datos.log_setup import configure_logging

DEFAULT_DIR = Path("data/governments")
# Governments are loaded from this date; earlier terms exist only to cover its start.
SINCE = date(2020, 1, 1)

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.governments")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser(
        "load", help="validate and load parties, government terms, sectors and competences"
    )
    load.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    data_dir: Path = arguments.data_dir
    try:
        parties = read_parties(data_dir / "parties.csv")
        terms = read_terms(
            data_dir / "government_terms.csv", data_dir / "government_term_parties.csv"
        )
        sectors = read_sectors(data_dir / "sectors.csv")
        competences = read_competences(data_dir / "competences.csv")
        # One transaction: if the competences are invalid, the governments are not written either.
        with build_engine(str(settings.database_url)).begin() as connection:
            repository = PgGovernmentRepository(connection)
            load_governments(repository, parties, terms, since=SINCE, today=date.today())
            load_competences(repository, sectors, competences)
    except (InvalidGovernmentsFileError, InvalidGovernmentsDatasetError) as error:
        # Nothing was written: the transaction rolled back. Exit code 1 for scripts and CI.
        log.error("governments_not_loaded", reason=str(error))
        raise SystemExit(1) from error
    log.info(
        "governments_loaded",
        parties=len(parties),
        terms=len(terms),
        sectors=len(sectors),
        competences=len(competences),
        source=str(data_dir),
    )


if __name__ == "__main__":
    main()
