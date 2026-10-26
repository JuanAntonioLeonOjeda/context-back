"""Command line of the stories module.

- `embed [--days N] [--encoder NAME]`: embeds the articles of the last N days (60 by default)
  that have no vector for this encoder version. Needs the `ml` group and runs on the author's
  machine, never in the API image.
"""

import argparse
from datetime import datetime, time, timedelta

import structlog

from datos.clock import SPAIN, SystemClock
from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.stories.application.embed_articles import embed_new
from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository
from datos.stories.infrastructure.sentence_encoder import SentenceEncoder

DEFAULT_ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # ADR-0016
EMBED_WINDOW_DAYS = 60  # spec, decision 3

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.stories")
    commands = parser.add_subparsers(dest="command", required=True)
    embed = commands.add_parser("embed", help="embed the recent articles with no vector yet")
    embed.add_argument("--days", type=int, default=EMBED_WINDOW_DAYS)
    embed.add_argument("--encoder", default=DEFAULT_ENCODER)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    repository = PgEmbeddingRepository(build_engine(str(settings.database_url)))
    since = datetime.combine(SystemClock().today(), time.min, tzinfo=SPAIN) - timedelta(
        days=arguments.days
    )
    embed_new(SentenceEncoder.load(arguments.encoder), repository, since=since)


if __name__ == "__main__":
    main()
