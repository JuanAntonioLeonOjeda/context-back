"""The text every classifier and the training job read from an article."""

from collections.abc import Sequence

# The encoder reads 128 tokens (ADR-0016): the tags go after the headline and are few, so what is
# cut, when something is, is the end of the lead and never the headline (ADR-0019).
TAGS_IN_TEXT_MAX = 8
TAGS_LABEL = "Etiquetas:"


def article_text(headline: str, lead: str | None, tags: Sequence[str] = ()) -> str:
    """The headline, the tags and the lead as one string.

    Written once and used by the classifier and by the training job: a model trained on one text
    and asked about another (a newline instead of a space, no lead when it is short, other tags)
    gives worse answers without failing anywhere. `tags` arrive already filtered and in the
    order of the feed: only the first ones are read.
    """
    parts = [headline]
    if tags:
        parts.append(f"{TAGS_LABEL} {', '.join(tags[:TAGS_IN_TEXT_MAX])}.")
    if lead:
        parts.append(lead)
    return " ".join(parts).strip()
