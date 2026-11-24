"""The news related to one news item: a chain back in time, one step per earlier news item.

Pure: no I/O, no clock, no vectors. The similarities come from the database (pgvector compares the
articles' vectors); this module only decides which candidate is the next step, when the chain
stops, and how it is shown by day. The rules were chosen by the author on 2026-11-24, reading real
examples (spec related-news):

- the next step is the most similar earlier news item, at least `step_threshold` to the step it
  continues;
- it must also be at least `origin_threshold` to the news item asked for, or small drifts add up
  and the chain ends in another story (a court case drifting into general politics);
- the same outlet with the same news item again is a duplicate, not a step;
- the chain covers at most `max_days` days, and is shown one day at a time.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, tzinfo


@dataclass(frozen=True, slots=True)
class RelatedSettings:
    """Provisional values, returned with every answer so a reader knows how the chain was made."""

    step_threshold: float = 0.70  # minimum cosine similarity to the step it continues
    origin_threshold: float = 0.65  # minimum cosine similarity to the news item asked for
    duplicate_threshold: float = 0.98  # from here, the same outlet's item is the same news again
    window_days: int = 14  # how far back the candidates of a step are looked for
    max_days: int = 8  # days the chain may cover, the first one included


@dataclass(frozen=True, slots=True)
class NewsItem:
    article_id: int
    outlet_id: str
    headline: str
    published_at: datetime
    # What a reader is shown, beside the headline: never the lead (sources audit, section 7).
    outlet_name: str = ""
    url: str = ""


@dataclass(frozen=True, slots=True)
class Candidate:
    """An earlier news item, with its similarity to the current step and to the one asked for."""

    item: NewsItem
    similarity: float
    to_origin: float


@dataclass(frozen=True, slots=True)
class ChainLink:
    item: NewsItem
    similarity: float | None  # to the step before it; None for the news item asked for


@dataclass(frozen=True, slots=True)
class RelatedDay:
    day: date  # in the time zone the chain is shown in
    links: tuple[ChainLink, ...]


def pick_next(
    candidates: Sequence[Candidate], chain: Sequence[ChainLink], settings: RelatedSettings
) -> Candidate | None:
    """The next step of the chain, or None when no candidate qualifies. The most similar candidate
    that passes both thresholds and is not a duplicate wins; the order given does not matter."""
    for candidate in sorted(candidates, key=lambda c: c.similarity, reverse=True):
        if candidate.similarity < settings.step_threshold:
            return None  # sorted: no later candidate can pass either
        if candidate.to_origin < settings.origin_threshold:
            continue
        if _is_duplicate(candidate, chain, settings):
            continue
        return candidate
    return None


def _is_duplicate(
    candidate: Candidate, chain: Sequence[ChainLink], settings: RelatedSettings
) -> bool:
    """The same outlet publishing the same news again: the same headline as an item already in the
    chain, or almost the same text as the step it would continue."""
    same_outlet = [link.item for link in chain if link.item.outlet_id == candidate.item.outlet_id]
    if any(item.headline == candidate.item.headline for item in same_outlet):
        return True
    current = chain[-1].item if chain else None
    return (
        current is not None
        and current.outlet_id == candidate.item.outlet_id
        and candidate.similarity >= settings.duplicate_threshold
    )


def fits(
    chain: Sequence[ChainLink], candidate: Candidate, settings: RelatedSettings, zone: tzinfo
) -> bool:
    """Whether the candidate can join the chain without covering more than `max_days` days."""
    days = {_day(link.item, zone) for link in chain}
    return len(days | {_day(candidate.item, zone)}) <= settings.max_days


def group_by_day(chain: Sequence[ChainLink], zone: tzinfo) -> list[RelatedDay]:
    """The chain one day at a time, newest first, each day's items in the order they joined. A day
    is a calendar day where the reader lives (Spain), not in UTC."""
    days: dict[date, list[ChainLink]] = {}
    for link in chain:
        days.setdefault(_day(link.item, zone), []).append(link)
    return [RelatedDay(day, tuple(links)) for day, links in sorted(days.items(), reverse=True)]


def _day(item: NewsItem, zone: tzinfo) -> date:
    return item.published_at.astimezone(zone).date()
