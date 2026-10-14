"""A stratified sample of articles for hand labelling (data/sampling/README.md).

Pure: the candidates, the terms and a seed in, the sample out. The same inputs give the same
sample. Equal allocation per outlet; within each outlet, half random (drawn first, from all the
outlet's candidates, so it stays a plain random sample) and half enriched (drawn from the rest
that match a broad sector term). The outlet decides only the allocation, never what is drawn.
"""

import random
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum


class Stratum(StrEnum):
    RANDOM = "random"
    ENRICHED = "enriched"


class MatchKind(StrEnum):
    PREFIX = "prefix"  # a word that starts with the stem
    WORD = "word"  # the whole word only (acronyms)


@dataclass(frozen=True, slots=True)
class EnrichmentTerm:
    stem: str
    sector_id: str
    match: MatchKind


@dataclass(frozen=True, slots=True)
class Candidate:
    article_id: int
    outlet_id: str
    url: str
    headline: str
    lead: str | None


@dataclass(frozen=True, slots=True)
class Quota:
    random: int
    enriched: int


@dataclass(frozen=True, slots=True)
class SampledArticle:
    article_id: int
    outlet_id: str
    url: str
    stratum: Stratum


@dataclass(frozen=True, slots=True)
class Shortfall:
    """What an outlet could not provide. `ENRICHED`: enriched articles it lacked, replaced by
    random ones where it had them. `RANDOM`: articles missing from its quota altogether."""

    outlet_id: str
    stratum: Stratum
    missing: int


def normalise(text: str) -> str:
    """Lower case, without accents: "Sanitària" and "sanitaria" read the same."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def enrichment_pattern(terms: Sequence[EnrichmentTerm]) -> re.Pattern[str]:
    """One regular expression for every term, applied to normalised text."""
    if not terms:
        raise ValueError("no enrichment terms")
    parts = [
        rf"\b{re.escape(normalise(t.stem))}\w*"
        if t.match is MatchKind.PREFIX
        else rf"\b{re.escape(normalise(t.stem))}\b"
        for t in terms
    ]
    return re.compile("|".join(parts))


def is_enriched(candidate: Candidate, pattern: re.Pattern[str]) -> bool:
    text = normalise(f"{candidate.headline} {candidate.lead or ''}")
    return pattern.search(text) is not None


def allocate(outlet_ids: Sequence[str], size: int) -> dict[str, Quota]:
    """`size` split evenly among the outlets, the remainder one by one in the order of their ids;
    within an outlet, half random and half enriched, an odd one to the random half."""
    outlets = sorted(set(outlet_ids))
    if not outlets:
        return {}
    base, remainder = divmod(size, len(outlets))
    quotas: dict[str, Quota] = {}
    for index, outlet_id in enumerate(outlets):
        total = base + (1 if index < remainder else 0)
        quotas[outlet_id] = Quota(random=total - total // 2, enriched=total // 2)
    return quotas


def draw(
    candidates: Sequence[Candidate],
    quotas: Mapping[str, Quota],
    pattern: re.Pattern[str],
    seed: int,
) -> tuple[list[SampledArticle], list[Shortfall]]:
    """The sample, shuffled so a labelling session mixes outlets, and what could not be filled."""
    rng = random.Random(seed)  # noqa: S311 - a seeded draw meant to be reproducible, not a secret
    by_outlet: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in sorted(candidates, key=lambda c: c.article_id):
        by_outlet[candidate.outlet_id].append(candidate)

    sample: list[SampledArticle] = []
    shortfalls: list[Shortfall] = []
    for outlet_id in sorted(quotas):
        drawn, missing = _draw_outlet(
            outlet_id, by_outlet.get(outlet_id, []), quotas[outlet_id], pattern, rng
        )
        sample.extend(drawn)
        shortfalls.extend(missing)
    rng.shuffle(sample)
    return sample, shortfalls


def _draw_outlet(
    outlet_id: str,
    pool: list[Candidate],
    quota: Quota,
    pattern: re.Pattern[str],
    rng: random.Random,
) -> tuple[list[SampledArticle], list[Shortfall]]:
    random_part = rng.sample(pool, min(quota.random, len(pool)))
    taken = {c.article_id for c in random_part}
    enriched_pool = [c for c in pool if c.article_id not in taken and is_enriched(c, pattern)]
    enriched_part = rng.sample(enriched_pool, min(quota.enriched, len(enriched_pool)))
    taken |= {c.article_id for c in enriched_part}

    shortfalls: list[Shortfall] = []
    missing_enriched = quota.enriched - len(enriched_part)
    if missing_enriched:
        shortfalls.append(Shortfall(outlet_id, Stratum.ENRICHED, missing_enriched))
        # The gap is filled with random articles, recorded as such: they are random draws.
        rest = [c for c in pool if c.article_id not in taken]
        filler = rng.sample(rest, min(missing_enriched, len(rest)))
        random_part += filler
        taken |= {c.article_id for c in filler}
    missing_random = quota.random + quota.enriched - len(taken)
    if missing_random > 0:
        shortfalls.append(Shortfall(outlet_id, Stratum.RANDOM, missing_random))

    return (
        [_sampled(c, Stratum.RANDOM) for c in random_part]
        + [_sampled(c, Stratum.ENRICHED) for c in enriched_part],
        shortfalls,
    )


def _sampled(candidate: Candidate, stratum: Stratum) -> SampledArticle:
    return SampledArticle(candidate.article_id, candidate.outlet_id, candidate.url, stratum)
