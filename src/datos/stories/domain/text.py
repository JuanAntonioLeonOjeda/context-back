"""The text an article is embedded from."""


def embedding_text(headline: str, lead: str | None) -> str:
    """The headline and the lead as one string.

    No tags: each outlet writes its own (and some none), so they would pull the vectors of two
    outlets covering the same event apart. The classifier reads them; the grouping does not.
    """
    return " ".join(part for part in (headline, lead or "") if part).strip()
