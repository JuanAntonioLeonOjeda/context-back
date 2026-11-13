"""Command line of the voters module.

- `load-election --file PATH`: checks and stores the Infoelectoral zip of an election by
  municipality, downloaded by hand into `data/raw/infoelectoral/` (docs/sources-audit.md,
  section 10). Running it again with the same file writes nothing; another file for an election
  that is stored is an error (official results are final).
- `load-income --year YYYY`: the INE's mean net income per person of every municipality for that
  year (ADRH), in one request that the INE takes minutes to answer; only new or revised values
  are stored.
"""

import argparse
from pathlib import Path

import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.http import SourceUnavailableError, build_client
from datos.log_setup import configure_logging
from datos.voters.application.load_election import (
    ElectionAlreadyLoadedError,
    InvalidElectionError,
    load_election,
)
from datos.voters.application.load_income import InvalidIncomeError, load_income
from datos.voters.infrastructure.adrh_source import AdrhSource, InvalidAdrhResponseError
from datos.voters.infrastructure.infoelectoral import InvalidElectionFileError, read_election_zip
from datos.voters.infrastructure.pg_election_repository import PgElectionRepository
from datos.voters.infrastructure.pg_income_repository import PgIncomeRepository

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.voters")
    commands = parser.add_subparsers(dest="command", required=True)
    election = commands.add_parser("load-election", help="check and store an election's results")
    election.add_argument("--file", type=Path, required=True, help="the Infoelectoral zip")
    income = commands.add_parser("load-income", help="load the INE's income by municipality")
    income.add_argument("--year", type=int, required=True)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    if arguments.command == "load-income":
        _load_income(str(settings.database_url), arguments.year)
        return
    path: Path = arguments.file
    try:
        file = read_election_zip(path)
        # One transaction: if anything fails, nothing of the election is stored.
        with build_engine(str(settings.database_url)).begin() as connection:
            outcome = load_election(PgElectionRepository(connection), file)
    except (InvalidElectionFileError, InvalidElectionError, ElectionAlreadyLoadedError) as error:
        log.error("election_not_loaded", file=str(path), reason=str(error))
        raise SystemExit(1) from error
    log.info(
        "election_" + outcome.value,
        election=file.election.id,
        file=file.source_file,
        sha256=file.sha256,
        municipalities=len(file.results),
        candidatures=len(file.candidatures),
        vote_rows=len(file.votes),
    )


def _load_income(database_url: str, year: int) -> None:
    try:
        with build_client() as client:
            stored = load_income(
                AdrhSource(client), PgIncomeRepository(build_engine(database_url)), year=year
            )
    except (InvalidAdrhResponseError, InvalidIncomeError, SourceUnavailableError) as error:
        log.error("income_not_loaded", year=year, reason=str(error))
        raise SystemExit(1) from error
    log.info("income_loaded", year=year, stored=stored)


if __name__ == "__main__":
    main()
