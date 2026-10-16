import httpx
import pytest

from datos.http import USER_AGENT, build_client
from datos.news.infrastructure.read_policy import AI_CRAWLERS, ReadPolicy

URL = "https://www.example.org/noticias/a"


def _policy(robots: str | int | Exception, requests: list[str] | None = None) -> ReadPolicy:
    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(str(request.url))
        if isinstance(robots, Exception):
            raise robots
        if isinstance(robots, int):
            return httpx.Response(robots)
        return httpx.Response(200, text=robots)

    return ReadPolicy(build_client(httpx.MockTransport(handler)))


def test_a_site_that_lets_everyone_in_is_allowed() -> None:
    assert _policy("User-agent: *\nAllow: /\n").allows(URL)


def test_a_site_that_closes_the_page_to_our_collector_is_not_allowed() -> None:
    assert not _policy("User-agent: datos-portfolio\nDisallow: /noticias/\n").allows(URL)
    assert not _policy("User-agent: *\nDisallow: /noticias/\n").allows(URL)


@pytest.mark.parametrize("crawler", AI_CRAWLERS)
def test_a_site_that_blocks_any_ai_crawler_is_not_allowed(crawler: str) -> None:
    robots = f"User-agent: {crawler}\nDisallow: /\n\nUser-agent: *\nAllow: /\n"

    assert not _policy(robots).allows(URL)


def test_ai_crawlers_grouped_under_one_rule_are_all_seen() -> None:
    # ABC and Canarias7 write one block for many user agents.
    robots = "User-agent: Amazonbot\nUser-agent: CCBot\nUser-agent: ClaudeBot\nDisallow: /\n"

    assert not _policy(robots).allows(URL)


def test_a_rule_for_another_part_of_the_site_does_not_close_the_page() -> None:
    assert _policy("User-agent: GPTBot\nDisallow: /privado/\n").allows(URL)


def test_no_robots_txt_means_nothing_is_disallowed() -> None:
    assert _policy(404).allows(URL)
    assert _policy(410).allows(URL)


@pytest.mark.parametrize("status", [401, 403, 500, 503])
def test_a_robots_txt_that_is_forbidden_or_fails_means_no(status: int) -> None:
    assert not _policy(status).allows(URL)


def test_a_robots_txt_that_cannot_be_reached_means_no() -> None:
    assert not _policy(httpx.ConnectError("down")).allows(URL)


def test_robots_txt_is_asked_once_per_site_in_a_run() -> None:
    requests: list[str] = []
    policy = _policy("User-agent: *\nAllow: /\n", requests)

    for path in ("a", "b", "c"):
        policy.allows(f"https://www.example.org/{path}")
    policy.allows("https://other.example.org/a")

    assert requests == [
        "https://www.example.org/robots.txt",
        "https://other.example.org/robots.txt",
    ]


def test_the_collector_is_identified_as_it_is_everywhere_else() -> None:
    assert USER_AGENT.startswith("datos-portfolio")
