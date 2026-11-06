"""Command line of the voters module.

- `load-election --file PATH`: checks and stores the Infoelectoral zip of an election by
  municipality, downloaded by hand into `data/raw/infoelectoral/` (docs/sources-audit.md,
  section 10). Running it again with the same file writes nothing; another file for an election
  that is stored is an error (official results are final).
"""

import argparse
from pathlib import Path

import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.voters.application.load_election import (
    ElectionAlreadyLoadedError,
    InvalidElectionError,
    load_election,
)
from datos.voters.infrastructure.infoelectoral import InvalidElectionFileError, read_election_zip
from datos.voters.infrastructure.pg_election_repository import PgElectionRepository

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.voters")
    commands = parser.add_subparsers(dest="command", required=True)
    election = commands.add_parser("load-election", help="check and store an election's results")
    election.add_argument("--file", type=Path, required=True, help="the Infoelectoral zip")
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
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


if __name__ == "__main__":
    main()
