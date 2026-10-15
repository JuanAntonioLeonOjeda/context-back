"""The text every classifier and the training job read from an article."""


def article_text(headline: str, lead: str | None) -> str:
    """The headline and the lead as one string.

    Written once and used by the classifier and by the training job: a model trained on one text
    and asked about another (a newline instead of a space, no lead when it is short) gives worse
    answers without failing anywhere.
    """
    return f"{headline} {lead or ''}".strip()
