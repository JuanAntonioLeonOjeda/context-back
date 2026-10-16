"""Command line: uv run python -m datos.news collect [--data-dir PATH]
                     uv run python -m datos.news backfill-page-tags [--days N] [--limit N]

`collect`: run it at most every few hours: every run is one request per feed, plus one per new
article page for sitemaps and section pages (at most 30 per feed, one per second).
`backfill-page-tags`: one request per article without tags, for the outlets whose pages carry
them (`tags_in_page`), one per second.
"""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import structlog

from datos.config import load_settings
from datos.db import build_engine
from datos.http import SourceUnavailableError, build_client
from datos.log_setup import configure_logging
from datos.news.application.backfill_page_tags import backfill_page_tags
from datos.news.application.collect_articles import Sources, collect_articles
from datos.news.infrastructure.article_page_source import ArticlePageSource
from datos.news.infrastructure.csv_source import InvalidNewsFileError, read_feeds, read_outlets
from datos.news.infrastructure.feed_source_by_kind import FeedSourceByKind
from datos.news.infrastructure.pg_repository import PgNewsRepository
from datos.news.infrastructure.read_policy import ReadPolicy
from datos.news.infrastructure.rss_feed_source import RssFeedSource
from datos.news.infrastructure.section_page_source import SectionPageSource
from datos.news.infrastructure.sitemap_feed_source import SitemapFeedSource

DEFAULT_DIR = Path("data/news")

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.news")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="read every feed and store new articles")
    collect.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    backfill = commands.add_parser(
        "backfill-page-tags", help="tag stored articles from their own page, where it has the tags"
    )
    backfill.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    backfill.add_argument(
        "--days", type=int, default=30, help="articles collected in the last N days"
    )
    backfill.add_argument("--limit", type=int, default=500, help="at most N articles per outlet")
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
        sources = Sources(
            feeds=FeedSourceByKind(
                rss=RssFeedSource(client),
                sitemap=SitemapFeedSource(client),
                section=SectionPageSource(client),
            ),
            pages=ArticlePageSource(client, policy=ReadPolicy(client)),
            unavailable=(SourceUnavailableError, httpx.HTTPError),
        )
        if arguments.command == "backfill-page-tags":
            backfill_page_tags(
                sorted({f.outlet_id for f in feeds if f.tags_in_page}),
                since=datetime.now(UTC) - timedelta(days=arguments.days),
                limit=arguments.limit,
                pages=sources.pages,
                repository=PgNewsRepository(engine),
                unavailable=sources.unavailable,
            )
            return
        collect_articles(feeds, outlets, sources, PgNewsRepository(engine))


if __name__ == "__main__":
    main()
