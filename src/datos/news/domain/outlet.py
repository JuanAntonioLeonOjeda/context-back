from dataclasses import dataclass
from enum import StrEnum


class FeedKind(StrEnum):
    RSS = "rss"
    NEWS_SITEMAP = "news_sitemap"
    HTML_SECTION = "html_section"


@dataclass(frozen=True, slots=True)
class Outlet:
    id: str
    name: str
    home_url: str
    scope: str
    region_id: str | None
    # False: the outlet's text must never be sent to an external LLM (data/news/README.md).
    external_llm_allowed: bool


@dataclass(frozen=True, slots=True)
class Feed:
    outlet_id: str
    kind: FeedKind
    url: str
    section: str
    # True: the listing lacks the lead (or more); each new article's page is read once.
    needs_page_fetch: bool
    # html_section only: regex an absolute link must fully match to count as an article.
    article_url_pattern: str | None = None
    # True: the page of each article carries the outlet's tags (`article:tag`); its feed has none.
    tags_in_page: bool = False
