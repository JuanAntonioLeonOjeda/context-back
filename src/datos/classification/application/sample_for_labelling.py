"""Use case: draw a sample of articles for hand labelling (data/sampling/README.md).

The articles already in any labelled set are never candidates, so a training sample and the blind
test set can never share an article, whichever is drawn first.
"""

from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from datos.classification.domain.sampling import (
    Candidate,
    EnrichmentTerm,
    Quota,
    SampledArticle,
    Shortfall,
    allocate,
    draw,
    enrichment_pattern,
    is_enriched,
)


class CandidateReader(Protocol):
    def candidates(self, *, until: datetime) -> list[Candidate]:
        """Every stored article collected up to `until`, oldest id first."""
        ...


@dataclass(frozen=True, slots=True)
class Sample:
    articles: tuple[SampledArticle, ...]
    texts: dict[int, Candidate]  # headline and lead of each sampled article, for the labelling tool
    quotas: dict[str, Quota]
    shortfalls: tuple[Shortfall, ...]
    enriched_available: dict[str, int]  # per outlet, before drawing: how many could be enriched


def sample_for_labelling(
    *,
    reader: CandidateReader,
    terms: Sequence[EnrichmentTerm],
    size: int,
    seed: int,
    until: datetime,
    excluded_ids: Collection[int],
) -> Sample:
    excluded = set(excluded_ids)
    candidates = [c for c in reader.candidates(until=until) if c.article_id not in excluded]
    pattern = enrichment_pattern(terms)
    quotas = allocate([c.outlet_id for c in candidates], size)
    articles, shortfalls = draw(candidates, quotas, pattern, seed)
    by_id = {c.article_id: c for c in candidates}
    enriched = Counter(c.outlet_id for c in candidates if is_enriched(c, pattern))
    return Sample(
        articles=tuple(articles),
        texts={a.article_id: by_id[a.article_id] for a in articles},
        quotas=quotas,
        shortfalls=tuple(shortfalls),
        enriched_available={outlet: enriched.get(outlet, 0) for outlet in quotas},
    )
