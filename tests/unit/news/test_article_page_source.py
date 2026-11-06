from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from datos.http import build_client
from datos.news.domain.article import DropReason, to_article
from datos.news.infrastructure.article_page_source import (
    ArticlePageSource,
    has_mining_reservation,
    page_item,
)
from datos.news.infrastructure.read_policy import ReadPolicy

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


def test_the_tags_of_a_page_are_each_article_tag_meta() -> None:
    item = page_item(_page("rtve-tags"), "https://www.rtve.es/a")

    assert item.tags == ("Podemos", "Sumar", "Política", "Frente Amplio")


def test_tags_listed_with_commas_in_one_meta_are_split() -> None:
    item = page_item(_page("telemadrid-tags"), "https://www.telemadrid.es/a")

    assert item.tags == ("Vinícius Júnior", "Real Madrid", "Fútbol", "Deporte", "Primera División")


def test_the_keywords_metas_are_not_tags() -> None:
    # Telemadrid fills keywords and news_keywords with search-engine phrases.
    markup = (
        '<meta name="keywords" content="noticias madrid, última hora madrid">'
        '<meta name="news_keywords" content="noticias hoy">'
        '<meta property="article:tag" content="Metro">'
    )

    assert page_item(markup, "https://x.example/a").tags == ("Metro",)


def test_a_page_without_article_tag_has_no_tags() -> None:
    assert page_item(_page("rtvc"), "https://rtvc.es/a").tags == ()
    assert page_item(_page("3cat-tags"), "https://www.3cat.cat/a").tags == ("Salut",)


@pytest.mark.parametrize(
    ("markup", "reserved"),
    [
        ('<meta name="tdm-reservation" content="1">', True),
        ('<meta name="tdm-reservation" content="0">', False),
        ('<meta property="og:title" content="x">', False),
    ],
)
def test_a_mining_reservation_in_the_page_is_detected(markup: str, reserved: bool) -> None:
    assert has_mining_reservation(markup) is reserved


def _source(robots: str, page: str, *, tdm: bool = False) -> ArticlePageSource:
    markup = page + ('<meta name="tdm-reservation" content="1">' if tdm else "")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        return httpx.Response(200, text=markup)

    client = build_client(httpx.MockTransport(handler))
    return ArticlePageSource(client, delay_s=0, policy=ReadPolicy(client))


OPEN = "User-agent: *\nAllow: /\n"
AI_BLOCKED = "User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"


def test_the_tags_of_a_page_are_read_where_the_site_allows_it() -> None:
    item = _source(OPEN, _page("rtve-tags")).read("https://www.rtve.es/noticias/a")

    assert item.tags == ("Podemos", "Sumar", "Política", "Frente Amplio")


def test_where_the_site_blocks_ai_crawlers_the_lead_is_read_but_no_tag_is() -> None:
    item = _source(AI_BLOCKED, _page("rtve-tags")).read("https://www.rtve.es/noticias/a")

    assert item.tags == () and item.summary


def test_where_the_page_reserves_mining_no_tag_is_read() -> None:
    item = _source(OPEN, _page("rtve-tags"), tdm=True).read("https://www.rtve.es/noticias/a")

    assert item.tags == () and item.summary
