"""The tags of articles as the model may read them: filtered by the stoplist, in feed order."""

from collections.abc import Collection, Sequence

from sqlalchemy import Connection, text

from datos.classification.domain.tag_stoplist import ArticleTag, StoplistEntry, readable_labels
from datos.classification.infrastructure.tag_stoplist_file import read_tag_stoplist

# What the feed gave, first; what was read from the body (ADR-0019), after. A link made before tags
# had a place has none and comes last, then by the order the tag was first stored.
_TAGS = text(
    """
    SELECT at.article_id, t.key, t.label
    FROM article_tags at
    JOIN tags t ON t.id = at.tag_id
    WHERE at.article_id = ANY(:ids)
    ORDER BY at.article_id, (at.source = 'body'), at.position NULLS LAST, t.id
    """
)


def default_stoplist(stoplist: Sequence[StoplistEntry] | None) -> Sequence[StoplistEntry]:
    """The list to use: the one given, or the versioned file. Never an empty list by omission."""
    return read_tag_stoplist() if stoplist is None else stoplist


def readable_tags_by_article(
    connection: Connection, article_ids: Collection[int], stoplist: Sequence[StoplistEntry]
) -> dict[int, tuple[str, ...]]:
    """For each article that has any, the labels the model may read."""
    tags: dict[int, list[ArticleTag]] = {}
    seen: set[tuple[int, str]] = set()
    for row in connection.execute(_TAGS, {"ids": list(article_ids)}):
        if (row.article_id, row.key) in seen:  # the same tag from the feed and from the body
            continue
        seen.add((row.article_id, row.key))
        tags.setdefault(row.article_id, []).append(ArticleTag(row.key, row.label))
    return {i: readable_labels(found, stoplist) for i, found in tags.items()}
