"""Command line of the organization module.

- `load [--data-dir PATH]`: checks the curated files of `data/organization/` (every problem is
  reported at once, with its file and line when it is one row's) and, if there is none, makes the
  bodies, holders and competences in the database mirror them, in one transaction.
"""

import argparse
from pathlib import Path

import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.organization.application.load_organization import (
    InvalidOrganizationError,
    load_organization,
)
from datos.organization.infrastructure.csv_source import (
    InvalidOrganizationFileError,
    read_organization,
)
from datos.organization.infrastructure.pg_organization_repository import PgOrganizationRepository

log = structlog.get_logger(__name__)

DEFAULT_DIR = Path("data/organization")


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.organization")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="check the curated files and load them")
    load.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    try:
        bodies, holders, competences = read_organization(arguments.data_dir)
        # One transaction: if anything fails, the stored organisation stays as it was.
        with build_engine(str(settings.database_url)).begin() as connection:
            counts = load_organization(
                PgOrganizationRepository(connection), bodies, holders, competences
            )
    except (InvalidOrganizationFileError, InvalidOrganizationError) as error:
        log.error("organization_not_loaded", reason=str(error))
        raise SystemExit(1) from error
    log.info(
        "organization_loaded",
        bodies=counts.bodies,
        holders=counts.holders,
        competences=counts.competences,
    )


if __name__ == "__main__":
    main()
