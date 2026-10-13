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
    needs_page_fetch: bool
