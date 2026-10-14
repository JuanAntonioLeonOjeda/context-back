"""Command line: uv run python -m datos.classification classify-new [--rules-dir PATH]

Classifies the articles the rules classifier has not seen yet (a new version of the rules, that
is, any change in data/classification/, classifies everything again). Run it after each
collection.
"""

import argparse
from pathlib import Path

import structlog

from datos.classification.application.store_classifications import classify_new
from datos.classification.infrastructure.pg_repository import PgClassificationRepository
from datos.classification.infrastructure.rules_classifier import (
    InvalidRulesFileError,
    load_rules_classifier,
)
from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging

DEFAULT_RULES_DIR = Path("data/classification")

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.classification")
    commands = parser.add_subparsers(dest="command", required=True)
    classify = commands.add_parser("classify-new", help="classify the articles not seen yet")
    classify.add_argument("--rules-dir", type=Path, default=DEFAULT_RULES_DIR)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    repository = PgClassificationRepository(build_engine(str(settings.database_url)))
    try:
        classifier = load_rules_classifier(arguments.rules_dir, sector_ids=repository.sector_ids())
    except InvalidRulesFileError as error:
        log.error("articles_not_classified", reason=str(error))
        raise SystemExit(1) from error
    classify_new(classifier, repository)


if __name__ == "__main__":
    main()
