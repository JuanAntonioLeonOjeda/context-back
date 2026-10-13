"""Command line: uv run python -m datos.news collect [--data-dir PATH]

Run it at most every 15 minutes: every run is one request per feed.
"""

import argparse
from pathlib import Path

import httpx
import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.news.application.collect_articles import collect_articles
from datos.news.infrastructure.csv_source import InvalidNewsFileError, read_feeds, read_outlets
from datos.news.infrastructure.pg_repository import PgNewsRepository
from datos.news.infrastructure.rss_feed_source import (
    FeedUnavailableError,
    RssFeedSource,
    build_client,
)

DEFAULT_DIR = Path("data/news")

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.news")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="read every RSS feed and store new articles")
    collect.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    data_dir: Path = arguments.data_dir
    try:
        outlets = read_outlets(data_dir / "outlets.csv")
        feeds = read_feeds(data_dir / "feeds.csv", outlets)
    except InvalidNewsFileError as error:
        log.error("news_not_collected", reason=str(error))
        raise SystemExit(1) from error
    engine = build_engine(str(settings.database_url))
    with build_client() as client:
        collect_articles(
            feeds,
            outlets,
            RssFeedSource(client),
            PgNewsRepository(engine),
            unavailable=(FeedUnavailableError, httpx.HTTPError),
        )


if __name__ == "__main__":
    main()
