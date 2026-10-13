from pathlib import Path

import pytest

from datos.news.domain.outlet import FeedKind
from datos.news.infrastructure.csv_source import InvalidNewsFileError, read_feeds, read_outlets

DATA = Path("data/news")


def test_the_versioned_outlets_and_feeds_are_consistent() -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = read_feeds(DATA / "feeds.csv", outlets)

    assert len(outlets) == 14
    assert {f.outlet_id for f in feeds} == {o.id for o in outlets}
    assert all(f.kind is FeedKind.RSS or f.needs_page_fetch for f in feeds)
    assert all(
        (f.kind is FeedKind.HTML_SECTION) == (f.article_url_pattern is not None) for f in feeds
    )


def test_outlets_that_block_ai_crawlers_never_allow_an_external_llm() -> None:
    outlets = {o.id: o for o in read_outlets(DATA / "outlets.csv")}

    for blocked in ("el-mundo", "el-pais", "abc", "el-confidencial", "la-razon", "la-vanguardia"):
        assert outlets[blocked].external_llm_allowed is False
    assert outlets["canarias7"].external_llm_allowed is False


def test_a_feed_of_an_unknown_outlet_is_rejected(tmp_path: Path) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    path = tmp_path / "feeds.csv"
    path.write_text(
        "outlet_id,kind,url,section,needs_page_fetch\nnobody,rss,https://x.example/rss,home,false\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidNewsFileError, match="unknown outlet nobody"):
        read_feeds(path, outlets)


def test_an_unknown_feed_kind_is_rejected_with_its_line(tmp_path: Path) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    path = tmp_path / "feeds.csv"
    path.write_text(
        "outlet_id,kind,url,section,needs_page_fetch\nabc,atom,https://x.example/rss,home,false\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidNewsFileError, match=r"feeds\.csv line 2"):
        read_feeds(path, outlets)


HEADER = "outlet_id,kind,url,section,needs_page_fetch,article_url_pattern\n"


@pytest.mark.parametrize(
    "row",
    [
        "rtve,html_section,https://www.rtve.es/x/,politics,true,\n",  # section without pattern
        "abc,rss,https://x.example/rss,home,false,https://x\\.example/.+\n",  # pattern on rss
        "rtve,html_section,https://www.rtve.es/x/,politics,true,https://(unclosed\n",
    ],
)
def test_the_article_url_pattern_is_required_valid_and_only_for_sections(
    tmp_path: Path, row: str
) -> None:
    path = tmp_path / "feeds.csv"
    path.write_text(HEADER + row, encoding="utf-8")

    with pytest.raises(InvalidNewsFileError, match=r"feeds\.csv line 2"):
        read_feeds(path, read_outlets(DATA / "outlets.csv"))
