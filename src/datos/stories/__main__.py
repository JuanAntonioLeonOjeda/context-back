"""Command line of the stories module.

- `embed [--days N] [--encoder NAME]`: embeds the articles of the last N days (60 by default)
  that have no vector for this encoder version. Needs the `ml` group and runs on the author's
  machine, never in the API image.
- `group --threshold T [--window-days N] [--days N]`: groups the articles of the last N days
  (60 by default) into stories with the latest embeddings and stores the run. The threshold has no
  default: it is the author's, and provisional until pairs are labelled (spec, decision 1).
- `link --threshold T [--window-days N]`: links each story of the latest grouping run to the earlier
  story it continues (phase history-trace) and stores the run. Same rule for the threshold.
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
from datos.stories.application.link_stories import NoStoriesError, link_stories
from datos.stories.domain.story import GroupingSettings
from datos.stories.domain.tree import TreeSettings
from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository
from datos.stories.infrastructure.pg_story_link_repository import PgStoryLinkRepository
from datos.stories.infrastructure.pg_story_repository import PgStoryRepository
from datos.stories.infrastructure.sentence_encoder import SentenceEncoder

DEFAULT_ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # ADR-0016
EMBED_WINDOW_DAYS = 60  # spec, decision 3
LINK_WINDOW_DAYS = 3  # spec, decision 1: provisional
TREE_WINDOW_DAYS = 14  # history-trace plan: provisional

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
    link = commands.add_parser("link", help="link each story to the earlier story it continues")
    link.add_argument("--threshold", type=float, required=True)
    link.add_argument("--window-days", type=int, default=TREE_WINDOW_DAYS)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    if arguments.command == "embed":
        embed_new(
            SentenceEncoder.load(arguments.encoder),
            PgEmbeddingRepository(engine),
            since=_days_ago(arguments.days),
        )
        return
    if arguments.command == "link":
        links = PgStoryLinkRepository(engine)
        try:
            link_stories(links, links, TreeSettings(arguments.threshold, arguments.window_days))
        except NoStoriesError as error:
            log.error("stories_not_linked", reason=str(error))
            raise SystemExit(1) from error
        return
    stories = PgStoryRepository(engine)
    try:
        group_recent(
            stories,
            stories,
            GroupingSettings(arguments.threshold, arguments.window_days),
            since=_days_ago(arguments.days),
        )
    except NoEmbeddingsError as error:
        log.error("stories_not_grouped", reason=str(error))
        raise SystemExit(1) from error


def _days_ago(days: int) -> datetime:
    """The start of the day `days` days before today in Spain."""
    return datetime.combine(SystemClock().today(), time.min, tzinfo=SPAIN) - timedelta(days=days)


if __name__ == "__main__":
    main()
