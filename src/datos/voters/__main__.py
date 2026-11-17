"""Command line of the voters module.

- `load-election --file PATH`: checks and stores the Infoelectoral zip of an election by
  municipality, downloaded by hand into `data/raw/infoelectoral/` (docs/sources-audit.md,
  section 10). Running it again with the same file writes nothing; another file for an election
  that is stored is an error (official results are final).
- `load-income --year YYYY`: the INE's mean net income per person of every municipality for that
  year (ADRH), in one request that the INE takes minutes to answer; only new or revised values
  are stored.
- `load-education --year YYYY --file PATH [--file PATH]`: the percentage of people with higher
  education of every municipality, from the INE's table files 66620.csv and 66623.csv (Censo
  anual de población), downloaded by hand (docs/sources-audit.md, section 12). Give both files:
  with one, the municipalities of the other size are left without a value. Only new or revised
  values are stored.
"""

import argparse
from dataclasses import dataclass
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
from datos.voters.application.load_values import InvalidValuesError, load_values
from datos.voters.infrastructure.adrh_source import AdrhSource, InvalidAdrhResponseError
from datos.voters.infrastructure.infoelectoral import InvalidElectionFileError, read_election_zip
from datos.voters.infrastructure.pg_election_repository import PgElectionRepository
from datos.voters.infrastructure.pg_income_repository import PgIncomeRepository
from datos.voters.infrastructure.pg_value_repository import PgValueRepository
from datos.voters.infrastructure.table_source import (
    AGE_SOURCE,
    BORN_ABROAD_SOURCE,
    EDUCATION_SOURCE,
    InvalidTableFileError,
    TableSource,
    read_table_file,
)

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _TableCommand:
    """A dimension loaded from the INE's table files: the name its loads are stored under
    (migration 0019), the tables it reads and the help of its command."""

    dimension: str
    source: TableSource
    help: str


_TABLE_COMMANDS = {
    "load-education": _TableCommand(
        "education", EDUCATION_SOURCE, "load the INE's higher education by municipality"
    ),
    "load-age": _TableCommand(
        "age", AGE_SOURCE, "load the INE's share aged 70 or over by municipality"
    ),
    "load-born-abroad": _TableCommand(
        "born_abroad", BORN_ABROAD_SOURCE, "load the INE's share born abroad by municipality"
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.voters")
    commands = parser.add_subparsers(dest="command", required=True)
    election = commands.add_parser("load-election", help="check and store an election's results")
    election.add_argument("--file", type=Path, required=True, help="the Infoelectoral zip")
    income = commands.add_parser("load-income", help="load the INE's income by municipality")
    income.add_argument("--year", type=int, required=True)
    for name, command in _TABLE_COMMANDS.items():
        table = commands.add_parser(name, help=command.help)
        table.add_argument("--year", type=int, required=True)
        table.add_argument(
            "--file",
            type=Path,
            action="append",
            required=True,
            help=f"a table file ({', '.join(command.source.pages)})",
        )
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    if arguments.command == "load-income":
        _load_income(str(settings.database_url), arguments.year)
        return
    if arguments.command in _TABLE_COMMANDS:
        _load_table(
            _TABLE_COMMANDS[arguments.command],
            str(settings.database_url),
            arguments.year,
            arguments.file,
        )
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


def _load_table(command: _TableCommand, database_url: str, year: int, paths: list[Path]) -> None:
    try:
        files = [
            read_table_file(p, year, command.source.layout, source_url=command.source.page(p))
            for p in paths
        ]
        stored = load_values(
            command.dimension, files, PgValueRepository(build_engine(database_url)), year=year
        )
    except (InvalidTableFileError, InvalidValuesError) as error:
        log.error(f"{command.dimension}_not_loaded", year=year, reason=str(error))
        raise SystemExit(1) from error
    log.info(
        f"{command.dimension}_loaded",
        year=year,
        stored=stored,
        files=[{"file": f.source_file, "sha256": f.sha256, "counts": len(f.counts)} for f in files],
    )


if __name__ == "__main__":
    main()
