"""Whether an outlet's page may be read for its tags (ADR-0019): only where the site allows it.

"Allows" is checked on every run, not once: the site's `robots.txt` lets our collector fetch the
page and blocks no known AI crawler for it. A mining reservation in the page itself is checked by
the page reader. A robots.txt that cannot be read means no.
"""

from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import structlog

from datos.http import USER_AGENT

log = structlog.get_logger(__name__)

# Crawlers of AI companies named in the outlets' robots.txt (docs/sources-audit.md, section 7).
# One of them blocked is enough: the site has said it does not want its pages read for AI.
AI_CRAWLERS = (
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-User",
    "Claude-SearchBot",
    "anthropic-ai",
    "CCBot",
    "Google-Extended",
    "PerplexityBot",
    "Bytespider",
    "Amazonbot",
    "Applebot-Extended",
    "cohere-ai",
    "meta-externalagent",
)
_MAX_ROBOTS_CHARS = 500_000


class ReadPolicy:
    def __init__(self, client: httpx.Client, *, user_agent: str = USER_AGENT) -> None:
        self._client = client
        self._user_agent = user_agent
        self._robots: dict[str, RobotFileParser | None] = {}  # per host, for this run

    def allows(self, url: str) -> bool:
        parser = self._parser(url)
        if parser is None:
            return False
        return parser.can_fetch(self._user_agent, url) and all(
            parser.can_fetch(crawler, url) for crawler in AI_CRAWLERS
        )

    def _parser(self, url: str) -> RobotFileParser | None:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            self._robots[host] = self._fetch(f"{host}/robots.txt")
        return self._robots[host]

    def _fetch(self, robots_url: str) -> RobotFileParser | None:
        try:
            response = self._client.get(robots_url)
        except httpx.HTTPError as error:
            log.warning("robots_unreadable", url=robots_url, reason=type(error).__name__)
            return None
        parser = RobotFileParser()
        if response.status_code in (404, 410):
            parser.parse([])  # no robots.txt: nothing is disallowed
        elif response.status_code in (401, 403):
            parser.parse(["User-agent: *", "Disallow: /"])
        elif response.status_code == 200:
            parser.parse(response.text[:_MAX_ROBOTS_CHARS].splitlines())
        else:
            log.warning("robots_unreadable", url=robots_url, status=response.status_code)
            return None
        return parser
