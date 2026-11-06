from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from datos.stories.application.community_stories import CommunityStory, StoryArticle, StoryRun

Client = Callable[..., TestClient]
SPAIN = ZoneInfo("Europe/Madrid")
RUN = StoryRun(7, "encoder-v1", 0.88, 3, datetime(2026, 10, 26, 16, 56, tzinfo=UTC))


class RecordsQuery(Protocol):  # the `stories_reader` fixture (conftest.FakeStories)
    last_query: dict[str, object]


def story_article(
    story_outlet: str, *, day: int = 12, article_id: int = 1, headline: str = "Headline"
) -> StoryArticle:
    return StoryArticle(
        article_id=article_id,
        outlet_id=story_outlet,
        outlet_name=story_outlet.upper(),
        headline=headline,
        url=f"https://{story_outlet}.example/{article_id}",
        published_at=datetime(2026, 10, day, 9, 0, tzinfo=UTC),
    )


def test_a_story_lists_headline_link_and_date_per_outlet_and_never_a_lead_or_a_party(
    make_client: Client,
) -> None:
    story = CommunityStory(3, (story_article("outlet-a"), story_article("outlet-b", article_id=2)))

    body = make_client(run=RUN, stories=[story]).get("/communities/ccaa-05/stories").json()

    [out] = body["stories"]
    assert out["story_id"] == 3
    assert set(out["articles"][0]) == {
        "outlet_id",
        "outlet_name",
        "headline",
        "url",
        "published_at",
    }
    assert [a["outlet_id"] for a in out["articles"]] == ["outlet-a", "outlet-b"]


def test_the_response_says_how_the_stories_were_made(make_client: Client) -> None:
    body = make_client(run=RUN).get("/communities/ccaa-05/stories").json()

    assert body["grouping"] == {
        "run_id": 7,
        "encoder_version": "encoder-v1",
        "threshold": 0.88,
        "window_days": 3,
        "created_at": "2026-10-26T16:56:00Z",
    }


def test_before_any_grouping_run_the_answer_is_empty_and_grouping_is_null(
    make_client: Client,
) -> None:
    response = make_client().get("/communities/ccaa-05/stories")

    assert response.status_code == 200
    assert (response.json()["grouping"], response.json()["stories"]) == (None, [])


def test_the_reader_is_asked_for_the_latest_run_30_days_in_spain_and_the_active_classifier(
    make_client: Client, stories_reader: RecordsQuery
) -> None:
    client = make_client(run=RUN, today=date(2026, 10, 14))

    body = client.get("/communities/ccaa-05/stories?sector=housing").json()

    assert body["since"] == "2026-09-15"
    assert stories_reader.last_query == {
        "run_id": 7,
        "territory_id": "ccaa-05",
        "sector_id": "housing",
        "since": datetime(2026, 9, 15, tzinfo=SPAIN),
        "model_id": "rules",
    }


def test_the_sector_is_optional(make_client: Client, stories_reader: RecordsQuery) -> None:
    body = make_client(run=RUN).get("/communities/ccaa-05/stories").json()

    assert body["sector_id"] is None
    assert stories_reader.last_query["sector_id"] is None


def test_stories_come_newest_first_and_articles_by_outlet_not_by_size_or_time(
    make_client: Client,
) -> None:
    older = CommunityStory(1, (story_article("outlet-a", day=10, article_id=1),))
    newer = CommunityStory(
        2,
        (
            story_article("outlet-a", day=12, article_id=2),
            story_article("outlet-b", day=11, article_id=3),
        ),
    )

    body = make_client(run=RUN, stories=[older, newer]).get("/communities/ccaa-05/stories").json()

    assert [s["story_id"] for s in body["stories"]] == [2, 1]
    assert [a["outlet_id"] for a in body["stories"][0]["articles"]] == ["outlet-a", "outlet-b"]


def test_an_unknown_community_or_the_state_answers_404(make_client: Client) -> None:
    client = make_client()

    for territory_id in ("ccaa-99", "es"):
        response = client.get(f"/communities/{territory_id}/stories")
        assert response.status_code == 404
        assert "unknown community" in response.json()["detail"]


def test_an_unknown_sector_answers_422(make_client: Client) -> None:
    response = make_client().get("/communities/ccaa-05/stories?sector=sport")

    assert response.status_code == 422
