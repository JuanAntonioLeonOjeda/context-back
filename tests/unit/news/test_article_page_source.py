from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from datos.news.domain.article import DropReason, to_article
from datos.news.infrastructure.article_page_source import ArticlePageSource, page_item
from datos.news.infrastructure.http_client import build_client

PAGES = Path("tests/fixtures/pages")


def _page(name: str) -> str:
    return (PAGES / f"{name}.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["rtve", "3cat", "rtvc", "telemadrid"])
def test_every_real_page_gives_a_valid_article_with_lead(name: str) -> None:
    article = to_article(name, page_item(_page(name), f"https://{name}.example/a"))

    assert not isinstance(article, DropReason)
    assert article.lead


def test_the_site_name_suffix_is_not_part_of_the_headline() -> None:
    item = page_item(_page("3cat"), "https://www.3cat.cat/a")

    assert item.title is not None and not item.title.endswith("3CatInfo")
    assert item.published_at == datetime(2026, 10, 12, 18, 9, 31, tzinfo=UTC)


def test_entities_in_metadata_are_decoded() -> None:
    # RTVE writes the apostrophes of "'ley de nietos'" as &#39;.
    item = page_item(_page("rtve"), "https://www.rtve.es/a")

    assert item.title is not None and "'ley de nietos'" in item.title


def test_a_title_that_only_mentions_the_site_keeps_it() -> None:
    markup = (
        '<meta property="og:site_name" content="Telemadrid">'
        '<meta property="og:title" content="Telemadrid cumple 37 años">'
    )

    assert page_item(markup, "https://x.example/a").title == "Telemadrid cumple 37 años"


def test_a_page_without_metadata_gives_an_item_the_domain_drops() -> None:
    item = page_item("<html><body><h1>Sin metadatos</h1></body></html>", "https://x.example/a")

    assert to_article("x", item) == DropReason.NO_HEADLINE


def test_every_page_request_waits_the_polite_delay_first() -> None:
    waits: list[float] = []
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=_page("rtvc")))
    source = ArticlePageSource(build_client(transport), delay_s=1.0, sleep=waits.append)

    source.read("https://rtvc.es/a")
    source.read("https://rtvc.es/b")

    assert waits == [1.0, 1.0]
