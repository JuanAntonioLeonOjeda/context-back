"""PostgreSQL storage of outlets and article metadata."""

from collections.abc import Mapping, Sequence

from sqlalchemy import Engine, text

from datos.news.domain.article import Article
from datos.news.domain.outlet import Outlet
from datos.news.domain.tag import Tag

_UPSERT_OUTLET = text(
    """
    INSERT INTO outlets (id, name, home_url, scope, region_id, external_llm_allowed)
    VALUES (:id, :name, :home_url, :scope, :region_id, :external_llm_allowed)
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name, home_url = EXCLUDED.home_url, scope = EXCLUDED.scope,
        region_id = EXCLUDED.region_id, external_llm_allowed = EXCLUDED.external_llm_allowed
    """
)
# Re-reading a feed must not create a second row: the key is (outlet, URL).
_INSERT_ARTICLE = text(
    """
    INSERT INTO articles (outlet_id, url, published_at, headline, lead)
    VALUES (:outlet_id, :url, :published_at, :headline, :lead)
    ON CONFLICT (outlet_id, url) DO NOTHING
    """
)


# A tag is stored once, whoever carries it: the key is its identity.
_INSERT_TAG = text(
    """
    INSERT INTO tags (key, label) VALUES (:key, :label)
    ON CONFLICT (key) DO NOTHING
    """
)
# Joins by (outlet, URL) and key, so a URL the outlet has not stored yet links nothing.
_LINK_TAG = text(
    """
    INSERT INTO article_tags (article_id, tag_id, source)
    SELECT a.id, t.id, 'feed'
    FROM articles a, tags t
    WHERE a.outlet_id = :outlet_id AND a.url = :url AND t.key = :key
    ON CONFLICT DO NOTHING
    """
)

_KNOWN_URLS = text("SELECT url FROM articles WHERE outlet_id = :outlet_id AND url = ANY(:urls)")


class PgNewsRepository:
    """Each call is its own transaction, so one failing feed never rolls back the others."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert_outlets(self, outlets: Sequence[Outlet]) -> None:
        with self._engine.begin() as connection:
            for outlet in outlets:
                connection.execute(
                    _UPSERT_OUTLET,
                    {
                        "id": outlet.id,
                        "name": outlet.name,
                        "home_url": outlet.home_url,
                        "scope": outlet.scope,
                        "region_id": outlet.region_id,
                        "external_llm_allowed": outlet.external_llm_allowed,
                    },
                )

    def add_new(self, articles: Sequence[Article]) -> int:
        inserted = 0
        with self._engine.begin() as connection:
            for article in articles:
                result = connection.execute(
                    _INSERT_ARTICLE,
                    {
                        "outlet_id": article.outlet_id,
                        "url": article.url,
                        "published_at": article.published_at,
                        "headline": article.headline,
                        "lead": article.lead,
                    },
                )
                inserted += result.rowcount
        return inserted

    def known_urls(self, outlet_id: str, urls: Sequence[str]) -> set[str]:
        if not urls:
            return set()
        # Served by the unique index on (outlet_id, url).
        with self._engine.connect() as connection:
            rows = connection.execute(_KNOWN_URLS, {"outlet_id": outlet_id, "urls": list(urls)})
            return {row.url for row in rows}

    def add_tags(self, outlet_id: str, tags_by_url: Mapping[str, Sequence[Tag]]) -> int:
        """Link the feed's tags to stored articles; return how many links were new.

        Safe to repeat: a link already there is left alone, so a feed read again completes the
        articles stored before tags existed and adds nothing twice.
        """
        links = [
            {"outlet_id": outlet_id, "url": url, "key": tag.key}
            for url, tags in tags_by_url.items()
            for tag in tags
        ]
        if not links:
            return 0
        distinct = {tag.key: tag for tags in tags_by_url.values() for tag in tags}
        with self._engine.begin() as connection:
            connection.execute(
                _INSERT_TAG, [{"key": tag.key, "label": tag.label} for tag in distinct.values()]
            )
            result = connection.execute(_LINK_TAG, links)
        return max(result.rowcount, 0)
