"""What counts as a valid article, and how headline, lead and URL are cleaned.

Pure functions only. We keep metadata (headline, a short lead, date, outlet, URL); never
bodies. The lead is processed internally and never shown (docs/sources-audit.md, section 7).
"""

import html
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from typing import ClassVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# The database caps the lead at 1,000 characters; we keep it well below.
LEAD_MAX_CHARS = 500
_TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ncid", "outputtype"}


@dataclass(frozen=True, slots=True)
class FeedItem:
    """An item as read from a feed, before any validation."""

    title: str | None
    link: str | None
    published_at: datetime | None
    summary: str | None
    tags: tuple[str, ...] = ()  # as the feed gives them: cleaned by `clean_tags` when stored


@dataclass(frozen=True, slots=True)
class Article:
    outlet_id: str
    url: str
    published_at: datetime
    headline: str
    lead: str | None


class DropReason(StrEnum):
    NO_LINK = "no_link"
    NOT_HTTP_LINK = "not_http_link"
    NO_HEADLINE = "no_headline"
    NO_DATE = "no_date"
    NAIVE_DATE = "naive_date"
    PAGE_UNAVAILABLE = "page_unavailable"


def normalise_url(url: str) -> str:
    """Canonical form used as the identity of an article within its outlet.

    Lowercases scheme and host, drops the fragment and tracking parameters (`utm_*`, `fbclid`,
    ...) and keeps every other query parameter, because some outlets identify articles by one.
    """
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), "")
    )


class _TextExtractor(HTMLParser):
    _SKIPPED: ClassVar[frozenset[str]] = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIPPED:
            self._skip_depth += 1
        elif tag in {"p", "br", "div", "li"}:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIPPED and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def plain_text(markup: str) -> str:
    """Text of an HTML fragment: tags removed, entities decoded, whitespace collapsed."""
    extractor = _TextExtractor()
    extractor.feed(markup)
    extractor.close()
    return extractor.text()


def clean_lead(summary: str | None) -> str | None:
    """Plain text of the feed summary, cut at a word boundary to `LEAD_MAX_CHARS`."""
    if not summary:
        return None
    text = plain_text(summary)
    if not text:
        return None
    if len(text) <= LEAD_MAX_CHARS:
        return text
    cut = text[:LEAD_MAX_CHARS].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return cut + "…"


def complete_with_page(listed: FeedItem, page: FeedItem) -> FeedItem:
    """The listed item with the gaps filled from its article page.

    What the listing says wins (a news sitemap's title is the outlet's own record); the
    page adds what the listing lacks, and always the lead.
    """
    return FeedItem(
        title=listed.title or page.title,
        link=listed.link,
        published_at=listed.published_at or page.published_at,
        summary=listed.summary or page.summary,
        # What the outlet published with the article: the listing's, else the page's.
        tags=listed.tags or page.tags,
    )


def to_article(outlet_id: str, item: FeedItem) -> Article | DropReason:
    """The article for a valid item, or the reason it is dropped."""
    if not item.link or not item.link.strip():
        return DropReason.NO_LINK
    url = normalise_url(item.link)
    if urlsplit(url).scheme not in {"http", "https"} or not urlsplit(url).netloc:
        return DropReason.NOT_HTTP_LINK
    headline = plain_text(html.unescape(item.title or ""))
    if not headline:
        return DropReason.NO_HEADLINE
    if item.published_at is None:
        return DropReason.NO_DATE
    if item.published_at.tzinfo is None:
        return DropReason.NAIVE_DATE
    return Article(
        outlet_id=outlet_id,
        url=url,
        published_at=item.published_at,
        headline=headline,
        lead=clean_lead(item.summary),
    )
