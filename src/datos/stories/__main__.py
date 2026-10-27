"""Command line of the stories module.

- `embed [--days N] [--encoder NAME]`: embeds the articles of the last N days (60 by default)
  that have no vector for this encoder version. Needs the `ml` group and runs on the author's
  machine, never in the API image.
- `group --threshold T [--window-days N] [--days N]`: groups the articles of the last N days
  (60 by default) into stories with the latest embeddings and stores the run. The threshold has no
  default: it is the author's, and provisional until pairs are labelled (spec, decision 1).
"""

import argparse
from datetime import datetime, time, timedelta

import structlog

from datos.clock import SPAIN, SystemClock
from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.stories.application.embed_articles import embed_new
from datos.stories.application.group_stories import NoEmbeddingsError, group_recent
from datos.stories.domain.story import GroupingSettings
from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository
from datos.stories.infrastructure.pg_story_repository import PgStoryRepository
from datos.stories.infrastructure.sentence_encoder import SentenceEncoder

DEFAULT_ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # ADR-0016
EMBED_WINDOW_DAYS = 60  # spec, decision 3
LINK_WINDOW_DAYS = 3  # spec, decision 1: provisional

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.stories")
    commands = parser.add_subparsers(dest="command", required=True)
    embed = commands.add_parser("embed", help="embed the recent articles with no vector yet")
    embed.add_argument("--days", type=int, default=EMBED_WINDOW_DAYS)
    embed.add_argument("--encoder", default=DEFAULT_ENCODER)
    group = commands.add_parser("group", help="group the recent articles into stories")
    group.add_argument("--threshold", type=float, required=True)
    group.add_argument("--window-days", type=int, default=LINK_WINDOW_DAYS)
    group.add_argument("--days", type=int, default=EMBED_WINDOW_DAYS)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    since = datetime.combine(SystemClock().today(), time.min, tzinfo=SPAIN) - timedelta(
        days=arguments.days
    )
    if arguments.command == "embed":
        embed_new(
            SentenceEncoder.load(arguments.encoder), PgEmbeddingRepository(engine), since=since
        )
        return
    stories = PgStoryRepository(engine)
    try:
        group_recent(
            stories,
            stories,
            GroupingSettings(arguments.threshold, arguments.window_days),
            since=since,
        )
    except NoEmbeddingsError as error:
        log.error("stories_not_grouped", reason=str(error))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
