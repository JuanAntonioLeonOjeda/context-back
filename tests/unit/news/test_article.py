from dataclasses import replace
from datetime import UTC, datetime

import pytest

from datos.news.domain.article import (
    LEAD_MAX_CHARS,
    DropReason,
    FeedItem,
    clean_lead,
    complete_with_page,
    normalise_url,
    to_article,
)

WHEN = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)


def _item(**overrides: object) -> FeedItem:
    values: dict[str, object] = {
        "title": "A headline",
        "link": "https://example.org/news/1",
        "published_at": WHEN,
        "summary": "A short lead.",
    }
    return FeedItem(**(values | overrides))  # type: ignore[arg-type]


# --- URLs ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(
            "HTTPS://Example.ORG/news/1?utm_source=x&utm_medium=y",
            "https://example.org/news/1",
            id="tracking-and-case",
        ),
        pytest.param(
            "https://example.org/news/1#comments", "https://example.org/news/1", id="fragment"
        ),
        pytest.param(
            "https://example.org/a?id=7&fbclid=abc", "https://example.org/a?id=7", id="keeps-id"
        ),
        pytest.param("  https://example.org/a  ", "https://example.org/a", id="whitespace"),
    ],
)
def test_normalises_urls_without_losing_the_identity_of_the_article(
    raw: str, expected: str
) -> None:
    assert normalise_url(raw) == expected


# --- leads ---------------------------------------------------------------------------


def test_the_lead_is_plain_text_without_tags_images_or_entities() -> None:
    summary = '<p><img src="x.jpg" width="1"/></p><p>Dijo &quot;hola&quot; &amp; adiós.</p>'

    assert clean_lead(summary) == 'Dijo "hola" & adiós.'


def test_paragraphs_do_not_glue_words_together() -> None:
    assert clean_lead("<p>Uno</p><p>Dos</p>") == "Uno Dos"


def test_scripts_and_styles_never_reach_the_lead() -> None:
    assert clean_lead("<style>p{}</style><script>alert(1)</script>Texto") == "Texto"


def test_a_long_lead_is_cut_at_a_word_boundary_and_never_exceeds_the_limit() -> None:
    lead = clean_lead("palabra " * 200)

    assert lead is not None
    assert len(lead) <= LEAD_MAX_CHARS + 1
    assert lead.endswith("palabra…")


@pytest.mark.parametrize("summary", [None, "", "   ", "<p><img src='x'/></p>"])
def test_a_summary_without_text_gives_no_lead(summary: str | None) -> None:
    assert clean_lead(summary) is None


# --- articles ------------------------------------------------------------------------


def test_builds_an_article_from_a_valid_item() -> None:
    article = to_article("outlet-a", _item(title="  Un\n  titular  ", summary="<p>Lead</p>"))

    assert not isinstance(article, DropReason)
    assert (article.headline, article.lead, article.outlet_id) == ("Un titular", "Lead", "outlet-a")


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        pytest.param({"link": None}, DropReason.NO_LINK, id="no-link"),
        pytest.param({"link": "  "}, DropReason.NO_LINK, id="blank-link"),
        pytest.param({"link": "/news/1"}, DropReason.NOT_HTTP_LINK, id="relative-link"),
        pytest.param({"link": "javascript:alert(1)"}, DropReason.NOT_HTTP_LINK, id="script-link"),
        pytest.param({"title": "  "}, DropReason.NO_HEADLINE, id="blank-headline"),
        pytest.param({"title": None}, DropReason.NO_HEADLINE, id="no-headline"),
        pytest.param({"published_at": None}, DropReason.NO_DATE, id="no-date"),
        pytest.param(
            {"published_at": datetime(2026, 10, 13, 14, 0)}, DropReason.NAIVE_DATE, id="naive-date"
        ),
    ],
)
def test_drops_invalid_items_with_the_reason(
    overrides: dict[str, object], reason: DropReason
) -> None:
    assert to_article("outlet-a", _item(**overrides)) == reason


def test_an_item_without_lead_is_still_an_article() -> None:
    article = to_article("outlet-a", _item(summary=None))

    assert not isinstance(article, DropReason)
    assert article.lead is None


def test_a_page_adds_the_tags_the_listing_lacks_and_never_replaces_the_listings() -> None:
    bare = FeedItem("T", "https://a.example/1", WHEN, None)
    page = FeedItem("T", "https://a.example/1", WHEN, "Lead", tags=("Página",))

    assert complete_with_page(bare, page).tags == ("Página",)
    assert complete_with_page(replace(bare, tags=("Feed",)), page).tags == ("Feed",)
