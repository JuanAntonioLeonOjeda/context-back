"""Which tags of an article the model never reads (ADR-0019).

Some tags say nothing about the topic and give away the outlet ("Home La Razón") or the author
("Artículos Manuel Marraco"). The classifier never sees the outlet (ADR-0015); this keeps a tag
from showing it anyway. Pure functions: the list is data, read from a file by the infrastructure.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

_SPACES = re.compile(r"\s+")


class MatchKind(StrEnum):
    EXACT = "exact"  # the whole tag
    PREFIX = "prefix"  # the tag, or the tag followed by more words: "portada" and "portada local"


class Reason(StrEnum):
    OUTLET_MARKER = "outlet_marker"  # identifies the outlet or its section, not the topic
    BYLINE = "byline"  # the name of the author


@dataclass(frozen=True, slots=True)
class StoplistEntry:
    tag: str  # in tag-key form: lower case, single spaces
    match: MatchKind
    reason: Reason


@dataclass(frozen=True, slots=True)
class ArticleTag:
    key: str  # the identity of the tag; this is what the list is compared with
    label: str  # as the outlet wrote it: what the model reads


def tag_key(label: str) -> str:
    """The key form of a label: the same rule the database enforces for `tags.key`."""
    return _SPACES.sub(" ", label).strip().lower()


def is_listed(key: str, stoplist: Iterable[StoplistEntry]) -> bool:
    for entry in stoplist:
        if key == entry.tag:
            return True
        if entry.match is MatchKind.PREFIX and key.startswith(f"{entry.tag} "):
            return True
    return False


def readable_labels(
    tags: Sequence[ArticleTag], stoplist: Iterable[StoplistEntry]
) -> tuple[str, ...]:
    """The labels of the tags the model may read, in the order they came."""
    entries = tuple(stoplist)
    return tuple(tag.label for tag in tags if not is_listed(tag.key, entries))
