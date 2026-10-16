"""Tags an outlet publishes with an article, cleaned to be stored once each (ADR-0019).

Pure functions. A tag is data about the article, not its text: "Sanidad", "Elecciones Generales".
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

# The database caps a label at 100 characters. A longer "tag" is a sentence, not a tag.
TAG_MAX_CHARS = 100
# An article with dozens of tags (El País gives up to 24) keeps the first ones, in feed order.
TAGS_PER_ARTICLE_MAX = 30
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Tag:
    key: str  # the identity: "hospital  X" and "Hospital X" are the same tag
    label: str  # as the outlet wrote it (spaces collapsed)


def clean_tags(raw: Iterable[str]) -> tuple[Tag, ...]:
    """The distinct, valid tags of an item, in order of appearance.

    Drops empty ones and ones too long to be a tag; two spellings of the same tag count once.
    """
    seen: dict[str, Tag] = {}
    for text in raw:
        label = _SPACES.sub(" ", text).strip()
        if not label or len(label) > TAG_MAX_CHARS:
            continue
        key = label.lower()
        seen.setdefault(key, Tag(key=key, label=label))
    return tuple(seen.values())[:TAGS_PER_ARTICLE_MAX]
